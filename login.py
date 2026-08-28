from functools import wraps

from flask import render_template, flash, session, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import app, limiter
from database import get_db

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=7)])
    submit = SubmitField('Login')

class SetupForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=12)]
    )
    submit = SubmitField('Create Account')

@app.route('/setup', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def setup():
    conn = get_db()

    # Setup is only available when there are no users.
    user_count = conn.execute(
        'SELECT COUNT(*) FROM users'
    ).fetchone()[0]

    if user_count > 0:
        return redirect(url_for('login'))

    form = SetupForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        password_hash = generate_password_hash(password)

        conn.execute(
            'INSERT INTO users (email, password) VALUES (?, ?)',
            (email, password_hash)
        )
        conn.commit()

        flash('Account created successfully. You can now log in.', 'success')

        return redirect(url_for('login'))

    return render_template('setup.html', form=form)



@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?',(email,) ).fetchone()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = email
            session.permanent = True

            return redirect(url_for('index'))

        flash('Invalid credentials', 'error')

    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get('user_id'):
            conn = get_db()

            user_count = conn.execute(
                'SELECT COUNT(*) FROM users'
            ).fetchone()[0]

            if user_count == 0:
                return redirect(url_for('setup'))

            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function

