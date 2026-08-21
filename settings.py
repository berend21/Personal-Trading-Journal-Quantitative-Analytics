from flask import render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest
from extensions import app
from database import get_db
from login import login_required
import re


APP_VERSION = "0.3.0"
BUILD_DATE = "June 2025"


def is_valid_email(email):
    return re.match(
        r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',
        email
    ) is not None


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    conn = get_db()

    user = conn.execute(
        'SELECT id, email, password, created_at FROM users WHERE email = ?',
        (session['username'],)
    ).fetchone()

    if user is None:
        session.clear()
        flash('User account could not be found.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_email':
            return change_email(conn, user)

        if action == 'change_password':
            return change_password(conn, user)

        flash('Invalid settings request.', 'danger')
        return redirect(url_for('settings'))

    return render_template(
        'settings.html',
        user=user,
        app_version=APP_VERSION,
        build_date = BUILD_DATE
    )


def change_email(conn, user):
    new_email = request.form.get('new_email', '').strip().lower()

    if not new_email:
        flash('Email address is required.', 'danger')
        return redirect(url_for('settings'))

    if not is_valid_email(new_email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('settings'))

    if new_email == user['email'].lower():
        flash('This is already your current email address.', 'info')
        return redirect(url_for('settings'))

    existing_user = conn.execute(
        'SELECT id FROM users WHERE email = ? AND id != ?',
        (new_email, user['id'])
    ).fetchone()

    if existing_user:
        flash('That email address is already in use.', 'danger')
        return redirect(url_for('settings'))

    conn.execute(
        'UPDATE users SET email = ? WHERE id = ?',
        (new_email, user['id'])
    )
    conn.commit()

    session['username'] = new_email

    flash('Email updated successfully!', 'success')
    return redirect(url_for('settings'))


def change_password(conn, user):
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not check_password_hash(user['password'], current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('settings'))

    if len(new_password) < 7:
        flash('New password must be at least 7 characters long.', 'danger')
        return redirect(url_for('settings'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('settings'))

    if check_password_hash(user['password'], new_password):
        flash('New password must be different from your current password.', 'danger')
        return redirect(url_for('settings'))

    hashed_password = generate_password_hash(new_password)

    conn.execute(
        'UPDATE users SET password = ? WHERE id = ?',
        (hashed_password, user['id'])
    )
    conn.commit()

    flash('Password changed successfully!', 'success')
    return redirect(url_for('settings'))
