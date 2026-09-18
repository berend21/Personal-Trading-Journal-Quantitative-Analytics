from flask import render_template, request, redirect, url_for, flash, session, jsonify, g
import os
from flask_wtf.csrf import  CSRFError

import logging
from logging.handlers import RotatingFileHandler
from extensions import app
from dotenv import load_dotenv
load_dotenv()
import config

app.config.from_object(config)
OWNER_USER_ID = app.config["OWNER_USER_ID"]

handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5)  
handler.setLevel(logging.DEBUG)  
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)  

logging.basicConfig(handlers=[handler], level=logging.DEBUG)

from database import init_db, get_db, close_db
app.teardown_appcontext(close_db)
from login import login_required
from dashboard import dashboard
from spot import spot
from journal import journal, render_journal_calendar
from gallery import gallery
from analytics import analytics
from notes import notes
from knowledge import knowledge
from settings import settings
from todo import todo
from trades import trades, user_detail
from utils.formatting import parse_time, smart_price
from services.media_service import compress_image

@app.before_request
def load_current_user():
    g.user = None

    if session.get('authenticated'):
        g.user = get_db().execute(
            '''
            SELECT id, email, display_name, created_at
            FROM users
            WHERE id = ?
            ''',
            (OWNER_USER_ID,)
        ).fetchone()

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
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com "
            "https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    return response

KNOWLEDGE_UPLOAD_FOLDER = 'static/uploads/knowledge'
os.makedirs(KNOWLEDGE_UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'webm', 'ogg'}

MAX_REASON_LEN    = 4000
MAX_FEEDBACK_LEN  = 8000


@app.route('/rules', methods=['GET'])
@login_required
def rules():
    return render_template('rules.html')

@app.route('/toggle_theme', methods=['POST'])
@login_required
def toggle_theme():
    current = session.get('theme', 'light')
    session['theme'] = 'dark' if current == 'light' else 'light'
    return redirect(request.referrer or url_for('index'))


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
        debug=False,
        use_reloader=False)
