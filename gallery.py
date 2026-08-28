from flask import render_template, request, flash, redirect, url_for, jsonify, abort
from extensions import app
from database import get_db
from login import login_required
from werkzeug.utils import secure_filename, safe_join

import os
import json
import math

import secrets
from PIL import Image, UnidentifiedImageError

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_IMAGE_WIDTH = 10000
MAX_IMAGE_HEIGHT = 10000
MAX_IMAGE_PIXELS = 25_000_000

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
MAX_IMAGE_SIZE = 20 * 1024 * 1024




@app.route('/gallery', methods=['GET', 'POST'])
@login_required
def gallery():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()

            if len(title) > 200:
                flash('Title is too long', 'error')
                return redirect(url_for('gallery'))

            if len(description) > 5000:
                flash('Description is too long', 'error')
                return redirect(url_for('gallery'))

            images = [
                image
                for image in request.files.getlist('images')
                if image.filename
            ]

            
            if not title:
                flash('Title is required', 'error')
                return redirect(url_for('gallery'))  
            

            if not images:
                flash('At least one image required', 'error')
                return redirect(url_for('gallery'))

                        
            image_paths = []

            for image in images:
                extension = get_safe_extension(image.filename)

                if extension is None:
                    flash('Invalid image file', 'error')
                    return redirect(url_for('gallery'))

                if image.content_length and image.content_length > MAX_IMAGE_SIZE:
                    flash('Image is too large', 'error')
                    return redirect(url_for('gallery'))


                if not validate_image(image, extension):
                    flash('Invalid or unsafe image file', 'error')
                    return redirect(url_for('gallery'))

                filename = secrets.token_hex(32) + extension

                filepath = safe_join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )

                if filepath is None:
                    app.logger.warning(
                        "Unsafe upload path rejected"
                    )
                    flash('Invalid image path', 'error')
                    return redirect(url_for('gallery'))

                try:
                    image.save(filepath)
                except OSError:
                    app.logger.exception(
                        "Failed to save gallery image"
                    )
                    flash('Failed to save image', 'error')
                    return redirect(url_for('gallery'))

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

            if len(title) > 200:
                flash('Title is too long', 'error')
                return redirect(url_for('gallery'))

            if len(description) > 5000:
                flash('Description is too long', 'error')
                return redirect(url_for('gallery'))

            if img_id and title:
                conn.execute(
                    'UPDATE gallery SET title=?, description=? WHERE id=?',
                    (title, description, img_id)
                )
                conn.commit()

                flash('Post updated successfully!', 'success')
                return redirect(url_for('gallery'))

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
                            filepath = safe_join(
                                app.config['UPLOAD_FOLDER'],
                                path
                            )

                            if filepath is None:
                                app.logger.warning(
                                    "Unsafe gallery file path rejected"
                                )

                                continue

                            os.remove(filepath)

                        except FileNotFoundError:
                            pass

                        except OSError:
                            app.logger.exception(
                                "Failed to delete gallery file"
                            )


                conn.execute('DELETE FROM gallery WHERE id=?', (img_id,))
                conn.commit()
                flash('Post deleted successfully!', 'success')
                return redirect(url_for('gallery'))
            else:
                flash('Invalid delete request', 'error')
                return redirect(url_for('gallery'))  
       
        flash('Invalid action', 'error')
        return redirect(url_for('gallery'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    sort_order = request.args.get('sort', 'desc')  
    
    per_page = 24
    offset = (page - 1) * per_page

    where_clause = ""
    search_params = []
    if search:
        where_clause = "WHERE (title LIKE ? OR description LIKE ?)"
        search_param = f"%{search}%"
        search_params = [search_param, search_param]

    count_query = f"SELECT COUNT(*) as total FROM gallery {where_clause}"
    total_posts = conn.execute(count_query, search_params).fetchone()['total']
    
    total_images_query = f"""
        SELECT COALESCE(SUM(json_array_length(image_path)), 0) as total_images
        FROM gallery {where_clause}
    """
    total_images_result = conn.execute(total_images_query, search_params).fetchone()
    total_images = total_images_result['total_images'] or 0
    total_pages = math.ceil(total_posts / per_page)

    if sort_order == 'asc':
        order_by = "ORDER BY created_at ASC"  
    else:
        order_by = "ORDER BY created_at DESC"  

    # 
    query = f"""
        SELECT id, title, description, image_path, created_at FROM gallery {where_clause}
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


def get_safe_extension(filename):
    filename = secure_filename(filename or '')

    if not filename:
        return None

    _, extension = os.path.splitext(filename)
    extension = extension.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return None

    return extension


def validate_image(file, expected_extension):
    try:
        image = Image.open(file)

        image.verify()

        file.seek(0)

        image = Image.open(file)

        width, height = image.size

        if width > MAX_IMAGE_WIDTH:
            return False

        if height > MAX_IMAGE_HEIGHT:
            return False

        if width * height > MAX_IMAGE_PIXELS:
            return False

        expected_formats = {
            '.jpg': {'JPEG'},
            '.jpeg': {'JPEG'},
            '.png': {'PNG'},
            '.webp': {'WEBP'},
        }

        allowed_formats = expected_formats.get(
            expected_extension,
            set()
        )

        if image.format not in allowed_formats:
            return False

        file.seek(0)

        return True

    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
    ):
        file.seek(0)
        return False

