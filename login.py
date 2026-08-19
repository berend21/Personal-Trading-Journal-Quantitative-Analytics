import re

from functools import wraps

from flask import render_template, flash, session, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import check_password_hash
from extensions import app

from database import get_db

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=7)])
    submit = SubmitField('Login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if form.validate_on_submit(): 
        email = form.email.data
        password = form.password.data

        email_regex = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        if not re.match(email_regex, email):
            flash('Please enter a valid email address.', 'error')
            return render_template('login.html', form=form)  
        
        if len(password) < 7:
            flash('Password must be at least 7 characters long.', 'error')
            return render_template('login.html', form=form)

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ?',
            (email,)
        ).fetchone()

        
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = email
            print("Redirecting to:", url_for('index', _external=True))
            return redirect(url_for('index', _external=True))
        else:
            flash('Invalid credentials', 'error')
            return render_template('login.html', form=form)  
    

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
