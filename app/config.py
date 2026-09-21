from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_db_uri(uri):
    # Some Postgres hosts still hand out "postgres://" URLs, but SQLAlchemy 1.4+ requires
    # the "postgresql://" scheme.
    if uri and uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql://", 1)
    return uri


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _normalize_db_uri(
        os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL")
    ) or f"sqlite:///{BASE_DIR / 'instance' / 'app.db'}"