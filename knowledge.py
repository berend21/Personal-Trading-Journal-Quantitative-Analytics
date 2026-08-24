from flask import render_template, request, flash, redirect, url_for, jsonify
from extensions import app
from database import get_db
from login import login_required
from werkzeug.utils import secure_filename
import os
from uuid import uuid4

app.config['UPLOAD_FOLDER']= 'static/uploads'
KNOWLEDGE_UPLOAD_FOLDER = 'static/uploads/knowledge'
os.makedirs(KNOWLEDGE_UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'webm', 'ogg', 'pdf', 'gif', 'avi', 'mov'}
ALLOWED_TYPES = {'document', 'learning'}
MAX_KNOWLEDGE_FILE_SIZE = 50 * 1024 * 1024


@app.route('/knowledge', methods=['GET', 'POST'])
@app.route('/knowledge/<int:article_id>', methods=['GET', 'POST'])
@login_required
def knowledge(article_id=None):
    conn = get_db()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        action = request.form.get('action') or request.args.get('action')
        
        if action == 'get_article':
            article_id_param = request.args.get('id')

            if not article_id_param or not article_id_param.isdigit():
                return jsonify({'error': 'Invalid article ID'}), 400

            article = conn.execute(
                'SELECT * FROM knowledge_articles WHERE id = ?',
                (int(article_id_param),)
            ).fetchone()

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

                if not del_article_id or not del_article_id.isdigit():
                    return jsonify({
                        'success': False,
                        'error': 'Invalid article ID'
                    }), 400

                del_article_id = int(del_article_id)

                article = conn.execute(
                    'SELECT featured_image FROM knowledge_articles WHERE id = ?',
                    (del_article_id,)
                ).fetchone()

                if not article:
                    return jsonify({
                        'success': False,
                        'error': 'Article not found'
                    }), 404

                conn.execute(
                    'DELETE FROM knowledge_articles WHERE id = ?',
                    (del_article_id,)
                )
                conn.commit()

                if article['featured_image']:
                    delete_knowledge_file(article['featured_image'])

                return jsonify({'success': True})

            except Exception as e:
                conn.rollback()

                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        
        elif action == 'edit':
            try:
                edit_article_id = request.form.get('id')

                if not edit_article_id or not edit_article_id.isdigit():
                    return jsonify({
                        'success': False,
                        'error': 'Invalid article ID'
                    }), 400

                edit_article_id = int(edit_article_id)

                article = conn.execute(
                    'SELECT * FROM knowledge_articles WHERE id = ?',
                    (edit_article_id,)
                ).fetchone()

                if not article:
                    return jsonify({
                        'success': False,
                        'error': 'Article not found'
                    }), 404

                title = request.form.get('title', '').strip()
                content = request.form.get('content', '')
                category = request.form.get('category', '').strip()
                tags = request.form.get('tags', '').strip()
                entry_type = request.form.get('type', 'document').strip().lower()

                if not title:
                    return jsonify({
                        'success': False,
                        'error': 'Title is required'
                    }), 400

                if entry_type not in ALLOWED_TYPES:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid entry type'
                    }), 400

                new_filename = None
                file = request.files.get('file')

                if file and file.filename:
                    try:
                        new_filename = save_knowledge_file(file)
                    except ValueError as e:
                        return jsonify({
                            'success': False,
                            'error': str(e)
                        }), 400

                if new_filename:
                    conn.execute('''
                        UPDATE knowledge_articles
                        SET title=?,
                            content=?,
                            category=?,
                            tags=?,
                            type=?,
                            featured_image=?,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (
                        title,
                        content,
                        category,
                        tags,
                        entry_type,
                        new_filename,
                        edit_article_id
                    ))
                else:
                    conn.execute('''
                        UPDATE knowledge_articles
                        SET title=?,
                            content=?,
                            category=?,
                            tags=?,
                            type=?,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (
                        title,
                        content,
                        category,
                        tags,
                        entry_type,
                        edit_article_id
                    ))

                conn.commit()

                if new_filename and article['featured_image']:
                    delete_knowledge_file(article['featured_image'])

                return jsonify({'success': True})

            except Exception as e:
                conn.rollback()

                if new_filename:
                    delete_knowledge_file(new_filename)

                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500


    if request.method == 'POST' and not request.headers.get('X-Requested-With'):
        action = request.form.get('action')
        entry_type = request.form.get('type', 'document').strip().lower()
        if entry_type not in ALLOWED_TYPES:
            flash('Invalid entry type', 'error')
            return redirect(url_for('knowledge'))
        
        if action in ['upload', 'edit']:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '')
            category = request.form.get('category', '')
            tags = request.form.get('tags', '')
            
            if not title:
                flash('Title is required', 'error')
                return redirect(url_for('knowledge'))

            if entry_type == 'learning' and not content.strip():
                flash('Content is required for learning entries', 'error')
                return redirect(url_for('knowledge'))

            if entry_type == 'document' and action == 'upload' and not request.files.get('file'):
                flash('A file is required for document entries', 'error')
                return redirect(url_for('knowledge'))


            file = request.files.get('file')
            filename = None



            if file and file.filename:
                try:
                    filename = save_knowledge_file(file)
                except ValueError as e:
                    flash(str(e), 'error')
                    return redirect(url_for('knowledge'))
                except Exception as e:
                    flash(f'Upload failed: {str(e)}', 'error')
                    return redirect(url_for('knowledge'))

            
            if action == 'upload':
                try:
                    conn.execute('''
                        INSERT INTO knowledge_articles
                        (title, content, category, tags, featured_image, type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (title, content, category, tags, filename, entry_type))
                    conn.commit()

                    flash('Entry added successfully!', 'success')

                except Exception as e:
                    conn.rollback()

                    if filename:
                        delete_knowledge_file(filename)

                    flash(f'Upload failed: {str(e)}', 'error')

            
            elif action == 'edit' and article_id:
                old_article = conn.execute(
                    'SELECT * FROM knowledge_articles WHERE id=?',
                    (article_id,)
                ).fetchone()

                if not old_article:
                    if filename:
                        delete_knowledge_file(filename)

                    flash('Article not found', 'error')
                    return redirect(url_for('knowledge'))

                try:
                    if filename:
                        conn.execute('''
                            UPDATE knowledge_articles
                            SET title=?,
                                content=?,
                                category=?,
                                tags=?,
                                type=?,
                                featured_image=?,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        ''', (
                            title,
                            content,
                            category,
                            tags,
                            entry_type,
                            filename,
                            article_id
                        ))
                    else:
                        conn.execute('''
                            UPDATE knowledge_articles
                            SET title=?,
                                content=?,
                                category=?,
                                tags=?,
                                type=?,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        ''', (
                            title,
                            content,
                            category,
                            tags,
                            entry_type,
                            article_id
                        ))

                    conn.commit()

                    if filename and old_article['featured_image']:
                        delete_knowledge_file(old_article['featured_image'])

                    flash('Entry updated successfully!', 'success')

                except Exception as e:
                    conn.rollback()

                    if filename:
                        delete_knowledge_file(filename)

                    flash(f'Update failed: {str(e)}', 'error')

            
             
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
            'updated_at': article['updated_at'],
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
    if not filename or '.' not in filename:
        return False



    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS

def save_knowledge_file(file):
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        raise ValueError('Invalid file type')

    original_filename = secure_filename(file.filename)

    if not original_filename:
        raise ValueError('Invalid filename')

    extension = original_filename.rsplit('.', 1)[1].lower()

    filename = f'{uuid4().hex}.{extension}'
    filepath = os.path.join(KNOWLEDGE_UPLOAD_FOLDER, filename)

    try:
        file.save(filepath)

        if os.path.getsize(filepath) > MAX_KNOWLEDGE_FILE_SIZE:
            os.remove(filepath)
            raise ValueError('File is too large. Maximum size is 50MB')

    except ValueError:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        raise

    except Exception:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        raise

    return filename



def delete_knowledge_file(filename):
    """Delete a Knowledge Base attachment if it exists."""
    if not filename:
        return

    filename = os.path.basename(filename)

    filepath = os.path.join(KNOWLEDGE_UPLOAD_FOLDER, filename)

    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
    except OSError:
        pass
