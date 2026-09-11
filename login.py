from functools import wraps

from flask import render_template, flash, session, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import app, limiter
from database import get_db

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=12)])
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
    submit = SubmitField('Complete Setup')

@app.route('/setup', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
@limiter.limit("20 per hour")
def setup():
    conn = get_db()

    # Setup is only available before the single owner account exists.
    account_exists = conn.execute(
        'SELECT 1 FROM users WHERE id = 1'
    ).fetchone()

    if account_exists:
        return redirect(url_for('login'))


    form = SetupForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        password_hash = generate_password_hash(password)

        conn.execute(
            '''
            INSERT INTO users (id, email, password)
            VALUES (1, ?, ?)
            ''',
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
        user = conn.execute(
            '''
            SELECT *
            FROM users
            WHERE id = 1
            '''
        ).fetchone()


        if (user and user['email'].lower() == email and check_password_hash(user['password'], password)):

            session.clear()
            session['authenticated'] = True
            session.permanent = True

            return redirect(url_for('dashboard'))

        flash('Invalid credentials', 'error')

    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session.get('authenticated'):
            return f(*args, **kwargs)

        conn = get_db()

        account_exists = conn.execute(
            'SELECT 1 FROM users WHERE id = 1'
        ).fetchone()

        if not account_exists:
            return redirect(url_for('setup'))

        return redirect(url_for('login'))



    return decorated_function

