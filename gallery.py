from flask import render_template, request, flash, redirect, url_for, jsonify
from extensions import app
from database import get_db
from login import login_required
from werkzeug.utils import secure_filename
import time
import os
import json
import math

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'webm', 'ogg'}


@app.route('/gallery', methods=['GET', 'POST'])
@login_required
def gallery():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            images = request.files.getlist('images')
            
            if not title:
                flash('Title is required', 'error')
                return redirect(url_for('gallery'))  
            
            if not images or any(not allowed_file(img.filename) for img in images if img.filename):
                flash('Invalid image file(s)', 'error')
                return redirect(url_for('gallery')) 
            
            image_paths = []
            for image in images:
                if image.filename == '': continue
                filename = secure_filename(image.filename)
                filename = f"gallery_{int(time.time())}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)
                image_paths.append(filename)
            
            if not image_paths:
                flash('At least one image required', 'error')
                return redirect(url_for('gallery')) 
            
            json_paths = json.dumps(image_paths)
            conn.execute('INSERT INTO gallery (title, description, image_path) VALUES (?, ?, ?)',
                         (title, description, json_paths))
            conn.commit()
            flash('Post added successfully!', 'success')
            return redirect(url_for('gallery'))
        
        elif action == 'edit':
            img_id = request.form.get('id')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            if img_id and title:
                conn.execute('UPDATE gallery SET title=?, description=? WHERE id=?',
                             (title, description, img_id))
                conn.commit()
                flash('Post updated successfully!', 'success')
                return redirect(url_for('gallery'))
            else:
                flash('Invalid edit data', 'error')
                return redirect(url_for('gallery'))  
        
        elif action == 'delete':
            img_id = request.form.get('id')
            if img_id:
                img = conn.execute('SELECT image_path FROM gallery WHERE id=?', (img_id,)).fetchone()
                if img and img['image_path']:
                    try:
                        paths = json.loads(img['image_path'])
                    except json.JSONDecodeError:
                        paths = [img['image_path']]
                    for path in paths:
                        try:
                            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], path))
                        except OSError:
                            pass
                conn.execute('DELETE FROM gallery WHERE id=?', (img_id,))
                conn.commit()
                flash('Post deleted successfully!', 'success')
                return redirect(url_for('gallery'))
            else:
                flash('Invalid delete request', 'error')
                return redirect(url_for('gallery'))  
       
        flash('Invalid action', 'error')
        return redirect(url_for('gallery'))

    # 🔥 NEW SORTING LOGIC
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    sort_order = request.args.get('sort', 'desc')  # 'desc' (newest) or 'asc' (oldest)
    
    per_page = 24
    offset = (page - 1) * per_page

    where_clause = ""
    search_params = []
    if search:
        where_clause = "WHERE (title LIKE ? OR description LIKE ?)"
        search_param = f"%{search}%"
        search_params = [search_param, search_param]

    # Count total for pagination
    count_query = f"SELECT COUNT(*) as total FROM gallery {where_clause}"
    total_posts = conn.execute(count_query, search_params).fetchone()['total']
    
    total_images_query = f"""
        SELECT COALESCE(SUM(json_array_length(image_path)), 0) as total_images
        FROM gallery {where_clause}
    """
    total_images_result = conn.execute(total_images_query, search_params).fetchone()
    total_images = total_images_result['total_images'] or 0
    total_pages = math.ceil(total_posts / per_page)

    # 🔥 DYNAMIC SORTING ORDER
    if sort_order == 'asc':
        order_by = "ORDER BY created_at ASC"  # Oldest first
    else:
        order_by = "ORDER BY created_at DESC"  # Newest first (default)

    # Fetch current page with dynamic sorting
    query = f"""
        SELECT * FROM gallery {where_clause}
        {order_by}
        LIMIT ? OFFSET ?
    """
    all_params = search_params + [per_page, offset]
    rows = conn.execute(query, all_params).fetchall()

    images = []
    for row in rows:
        try:
            paths = json.loads(row['image_path']) if row['image_path'] else []
        except json.JSONDecodeError:
            paths = [row['image_path']] if row['image_path'] else []
        images.append({
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'image_path': paths,
            'created_at': row['created_at']
        })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'images': images,
            'has_more': page < total_pages,
            'next_page': page + 1 if page < total_pages else None,
            'total_posts': total_posts,
            'total_images': total_images
        })

    return render_template('gallery.html',
                        images=images,
                        page=page,
                        total_pages=total_pages,
                        has_more=page < total_pages,
                        search=search,
                        sort_order=sort_order,  
                        total_posts=total_posts,      
                        total_images=total_images    
    )
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
