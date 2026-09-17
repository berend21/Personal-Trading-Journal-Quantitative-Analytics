import os
from pathlib import Path
from datetime import timedelta

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "FLASK_SECRET_KEY is not set. "
        "Set it before starting the app."
    )


SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
OWNER_USER_ID = 1


WTF_CSRF_TIME_LIMIT = 86400

MAX_CONTENT_LENGTH = 64 * 1024 * 1024

UPLOAD_FOLDER = Path(__file__).resolve().parent / "static" / "uploads"

PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
