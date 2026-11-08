import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables before reading configuration
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DB_SSL_CA = os.environ.get("DB_SSL_CA")

    if DB_SSL_CA:
        SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_timeout": 30,
    "connect_args": {
        "ssl_ca": DB_SSL_CA,
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
        "connect_timeout": 15,
        "read_timeout": 30,
        "write_timeout": 30,
    },
}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    UPLOAD_FOLDER = str(
        BASE_DIR / "instance" / "private_uploads"
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    )

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
