from flask import render_template, request, flash, redirect, url_for, jsonify
from extensions import app
from database import get_db
from login import login_required
from werkzeug.utils import secure_filename
import os
import time
from datetime import datetime

app.config['UPLOAD_FOLDER']= 'static/uploads'
KNOWLEDGE_UPLOAD_FOLDER = 'static/uploads/knowledge'
os.makedirs(KNOWLEDGE_UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'webm', 'ogg'}

@app.route('/knowledge', methods=['GET', 'POST'])
@app.route('/knowledge/<int:article_id>', methods=['GET', 'POST'])
@login_required
def knowledge(article_id=None):
    conn = get_db()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        action = request.form.get('action') or request.args.get('action')
        
        if action == 'get_article':
            article = conn.execute('SELECT * FROM knowledge_articles WHERE id = ?', 
                                  (request.args.get('id'),)).fetchone()
            if article:
                 
                return jsonify({
                    'id': article['id'],
                    'title': article['title'],
                    'content': article['content'],
                    'category': article['category'],
                    'tags': article['tags'],
                    'featured_image': article['featured_image'],
                    'type': article['type'] or 'document',  # Fallback
                    'created_at': article['created_at'][:10] if article['created_at'] else '',
                    'updated_at': article['updated_at'][:10] if article['updated_at'] else ''
                })
             
            return jsonify({'error': 'Article not found'}), 404
        
        elif action == 'delete':
            try:
                del_article_id = request.form.get('id')
                article = conn.execute('SELECT featured_image FROM knowledge_articles WHERE id = ?', 
                                      (del_article_id,)).fetchone()
                
                if article and article['featured_image']:
                    try:
                        os.remove(os.path.join(KNOWLEDGE_UPLOAD_FOLDER, article['featured_image']))
                    except OSError:
                        pass
                
                conn.execute('DELETE FROM knowledge_articles WHERE id = ?', (del_article_id,))
                conn.commit()
                 
                return jsonify({'success': True})
            except Exception as e:
                 
                return jsonify({'success': False, 'error': str(e)}), 500
        
        elif action == 'edit':
            try:
                edit_article_id = request.form.get('id')
                title = request.form.get('title', '').strip()
                content = request.form.get('content', '')
                category = request.form.get('category', '')
                tags = request.form.get('tags', '')
                entry_type = request.form.get('type', 'document')
                
                if not title:
                    return jsonify({'success': False, 'error': 'Title is required'}), 400
                
                conn.execute('''
                    UPDATE knowledge_articles 
                    SET title=?, content=?, category=?, tags=?, type=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', (title, content, category, tags, entry_type, edit_article_id))
                conn.commit()
                 
                return jsonify({'success': True})
            except Exception as e:
                 
                return jsonify({'success': False, 'error': str(e)}), 500

    if request.method == 'POST' and not request.headers.get('X-Requested-With'):
        action = request.form.get('action')
        entry_type = request.form.get('type', 'document')  
        
        if action in ['upload', 'edit']:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '')
            category = request.form.get('category', '')
            tags = request.form.get('tags', '')
            
            if not title:
                flash('Title is required', 'error')
                 
                return redirect(url_for('knowledge'))
            
            file = request.files.get('file')
            filename = None
            if file and file.filename:
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                allowed_extensions = {'pdf', 'mp4', 'webm', 'ogg', 'avi', 'mov', 'png', 'jpg', 'jpeg', 'gif'}
                if file_ext not in allowed_extensions:
                    flash('Invalid file type', 'error')
                     
                    return redirect(url_for('knowledge'))
                
                filename = secure_filename(file.filename)
                timestamp = int(time.time())
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(KNOWLEDGE_UPLOAD_FOLDER, filename)
                os.makedirs(KNOWLEDGE_UPLOAD_FOLDER, exist_ok=True)
                
                try:
                    with open(filepath, 'wb') as f:
                        while True:
                            chunk = file.stream.read(1024 * 1024)  
                            if not chunk:
                                break
                            f.write(chunk)
                except Exception as e:
                    flash(f'Upload failed: {str(e)}', 'error')
                     
                    return redirect(url_for('knowledge'))
            
            if action == 'upload':
                created_at = datetime.utcnow().isoformat()
                conn.execute('''
                    INSERT INTO knowledge_articles (title, content, category, tags, featured_image, created_at, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (title, content, category, tags, filename, created_at, entry_type))
                conn.commit()
                flash('Entry added successfully!', 'success')
            
            elif action == 'edit' and article_id:
                sql = '''
                    UPDATE knowledge_articles 
                    SET title=?, content=?, category=?, tags=?, type=?, updated_at=CURRENT_TIMESTAMP
                '''
                params = [title, content, category, tags, entry_type]
                if filename:  
                    old_article = conn.execute('SELECT featured_image FROM knowledge_articles WHERE id=?', (article_id,)).fetchone()
                    if old_article and old_article['featured_image']:
                        try:
                            os.remove(os.path.join(KNOWLEDGE_UPLOAD_FOLDER, old_article['featured_image']))
                        except OSError:
                            pass
                    sql += ', featured_image=?'
                    params.append(filename)
                sql += ' WHERE id=?'
                params.append(article_id)
                conn.execute(sql, params)
                conn.commit()
                flash('Entry updated successfully!', 'success')
            
             
            return redirect(url_for('knowledge'))

    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    query = 'SELECT * FROM knowledge_articles WHERE 1=1'
    params = []

    if search:
        query += ' AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])

    if category_filter:
        query += ' AND category LIKE ?'
        params.append(f'%{category_filter}%')

    query += ' ORDER BY created_at DESC'

    articles = conn.execute(query, params).fetchall()

    categories_result = conn.execute('''
        SELECT category FROM knowledge_articles 
        WHERE category IS NOT NULL AND category != ''
    ''').fetchall()

    all_categories = set()
    for row in categories_result:
        all_categories.update(c.strip() for c in row['category'].split(',') if c.strip())

    categories = sorted(all_categories)

    selected_article = None
    if article_id:
        selected_article = conn.execute('SELECT * FROM knowledge_articles WHERE id = ?', 
                                       (article_id,)).fetchone()

    articles_list = []
    for article in articles:
        article_dict = {
            'id': article['id'],
            'title': article['title'],
            'content': article['content'],
            'category': article['category'],
            'tags': article['tags'],
            'featured_image': article['featured_image'],
            'created_at': article['created_at'],
            'type': article['type'] or 'document'  
        }
        articles_list.append(article_dict)

  
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'articles': articles_list})

    return render_template('knowledge.html', 
                           articles=articles_list,
                           categories=categories,
                           search=search,
                           selected_category=category_filter,
                           selected_article=selected_article)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
