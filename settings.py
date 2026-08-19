from flask import render_template, request, flash, redirect, url_for, session
from extensions import app
from database import get_db
from login import login_required

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    APP_VERSION = datetime.now().strftime('%B %d, %Y')
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute('SELECT * FROM users LIMIT 1').fetchone()


    if request.method == 'POST':
        if 'new_email' in request.form:
            new_email = request.form['new_email']
            conn.execute('UPDATE users SET email = ? WHERE id = ?', (new_email, user['id']))
            conn.commit()
            flash('Email updated successfully!', 'success')
            session['username'] = new_email
            return redirect(url_for('settings'))
        elif 'current_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            
            if not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                hashed = generate_password_hash(new_password)
                conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, user['id']))
                conn.commit()
                flash('Password changed successfully!', 'success')
            return redirect(url_for('settings'))
        
    
    return render_template('settings.html', user=user, app_version=APP_VERSION)
