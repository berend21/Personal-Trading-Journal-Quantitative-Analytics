# STS Trading Journal - Built by a legend in 2025
# Lightning fast, faster than these other tradesystems

from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify, g
import sqlite3
import os

from functools import wraps
import io
from datetime import datetime, timedelta

from flask_wtf.csrf import CSRFProtect, CSRFError
from PIL import Image
import io

import logging
from logging.handlers import RotatingFileHandler
import json
from extensions import app

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


csrf = CSRFProtect(app)

handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5)  # 10MB per file, keep 5 backups
handler.setLevel(logging.DEBUG)  
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)  


logging.basicConfig(handlers=[handler], level=logging.DEBUG)

from config import *

PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

##Import modules
from database import *
app.teardown_appcontext(close_db)
from login import *
from spot import *
from journal import *
from gallery import *
from analytics import *
from notes import *
from knowledge import *
from settings import *
from todo import *
from trades import *


@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    app.logger.warning(f"CSRF Error: {e.description}")
    session.clear()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': 
        return jsonify({
            'success': False, 
            'message': 'Session expired. Please login again.',
            'redirect': url_for('login', _external=True)
        }), 401
    else:  
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('login'))
    
@app.after_request
def add_security_headers(response):

    if request.path.startswith('/static/uploads/knowledge/') and request.path.endswith('.pdf'):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com fonts.gstatic.com cdnjs.cloudflare.com; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data: fonts.gstatic.com fonts.googleapis.com cdnjs.cloudflare.com cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'self';"
        )
        return response
    
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com fonts.gstatic.com cdnjs.cloudflare.com; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: fonts.gstatic.com fonts.googleapis.com cdnjs.cloudflare.com cdn.jsdelivr.net;"
        "connect-src 'self';" 
    )
    return response


KNOWLEDGE_UPLOAD_FOLDER = 'static/uploads/knowledge'
os.makedirs(KNOWLEDGE_UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'webm', 'ogg'}



MAX_REASON_LEN    = 4000
MAX_FEEDBACK_LEN  = 8000


def migrate_gallery_table():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gallery'")
    if not cursor.fetchone():
        print("Gallery table does not exist yet. Skipping migration.")
        conn.close()
        return
 
    cursor.execute("SELECT id, image_path FROM gallery")
    rows = cursor.fetchall()
    updated = False
    for row in rows:
        image_path = row['image_path']
        if image_path:  
            try:
                json.loads(image_path)  
            except json.JSONDecodeError:
                json_paths = json.dumps([image_path])
                cursor.execute("UPDATE gallery SET image_path = ? WHERE id = ?", (json_paths, row['id']))
                updated = True
    
    conn.commit()
    conn.close()
    if updated:
        print("Gallery table migrated to support multi-images in image_path.")
    else:
        print("Gallery table already supports multi-images.")
    


def parse_time(s):
    if not s:
        return None
    s = s.replace('T', ' ').strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def compress_image(file, max_width=2000, quality=100):  #
    try:
        file.seek(0)  
        img = Image.open(file)
        file.seek(0)  
        original_format = img.format.lower() if img.format else 'jpeg'

        if original_format in ['jpg', 'jpeg'] and img.width <= max_width:
            file.seek(0)  # Return original untouched
            logging.info("Skipping compression for JPEG (no resize needed)")
            return file

        resized = False
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
            resized = True
        
        output = io.BytesIO()
        
        if original_format in ['jpg', 'jpeg']:
            img.save(output, format='JPEG', quality=quality, optimize=True)
        elif original_format == 'png':
            img.save(output, format='PNG', optimize=True, compress_level=5)  
        else:

            img.save(output, format='PNG', optimize=True, compress_level=5)
        
        output.seek(0)
        return output
    except Exception as e:
        logging.error(f"Image compression failed: {e}")
        file.seek(0)  
        return file  






@app.route('/rules', methods=['GET', 'POST'])
@login_required
def rules():
    return render_template('rules.html')


@app.route('/toggle_theme', methods=['POST'])
@login_required
def toggle_theme():
    current = session.get('theme', 'light')
    session['theme'] = 'dark' if current == 'light' else 'light'
    return redirect(request.referrer or url_for('index'))



def smart_price(value):
    try:
        if value is None:
            return ""
        val = float(value)
        if val == 0:
            return "0"
        abs_val = abs(val)
        if abs_val < 1e-6:
            return f"{val:.2e}"

        if abs_val < 0.01:
            prec = 8
        elif abs_val < 1:
            prec = 6
        elif abs_val < 10:
            prec = 5
        elif abs_val < 1000:
            prec = 3
        elif abs_val < 10000:
            prec = 2
        elif abs_val < 100000:
            prec = 1
        else:
            prec = 0

        formatted = f"{val:.{prec}f}"
        formatted = formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted
        return formatted
    except Exception:
        return str(value)


app.jinja_env.filters['smart_price'] = smart_price

def get_date_filter(start_date=None, end_date=None):
    if start_date and end_date:
        return "AND close_time BETWEEN :start_date AND :end_date", {
            "start_date": start_date,
            "end_date": end_date
        }
    elif start_date:
        return "AND close_time >= :start_date", {"start_date": start_date}
    elif end_date:
        return "AND close_time <= :end_date", {"end_date": end_date}
    else:
        return "", {}



if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1',  
        port=5000,
        debug=True,
        use_reloader=False)
