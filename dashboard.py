from flask import render_template
from extensions import app
from login import login_required


@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')
