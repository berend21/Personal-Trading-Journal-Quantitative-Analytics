from extensions import app
import os

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "FLASK_SECRET_KEY is not set. "
        "Set it before starting the app."
    )

app.config["SECRET_KEY"] = SECRET_KEY


app.config['SESSION_COOKIE_SAMESITE'] = "Strict"
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True 


app.config['PERMANENT_SESSION_LIFETIME'] = 86400
app.config['WTF_CSRF_TIME_LIMIT'] = 86400
app.config['UPLOAD_FOLDER']= 'static/uploads'
app.config["MAX_CONTENT_LENGTH"] = 64*1024*1024

