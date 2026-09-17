from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from symbol_icons import get_symbol_icon


app = Flask(__name__)

app.jinja_env.globals["symbol_icon_data"] = get_symbol_icon

csrf = CSRFProtect(app)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]
)

limiter.init_app(app)
