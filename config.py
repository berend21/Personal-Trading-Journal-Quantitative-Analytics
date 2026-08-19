from extensions import app
import configparser

app.config['SESSION_COOKIE_SAMESITE'] = "Strict"
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True 

app.config['PERMANENT_SESSION_LIFETIME'] = 86400
app.config['WTF_CSRF_TIME_LIMIT'] = 86400
app.config['UPLOAD_FOLDER']= 'static/uploads'
app.config["MAX_CONTENT_LENGTH"] = 512*1024*1024

config = configparser.ConfigParser()
config.read('config.ini')
app.secret_key = config['flask']['secret_key']
