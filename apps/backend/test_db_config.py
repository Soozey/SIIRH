from sqlalchemy.engine import make_url

from app.config.config import settings


def get_database_url() -> str:
    return settings.DATABASE_URL


def get_psycopg2_config() -> dict:
    url = make_url(settings.DATABASE_URL)
    return {
        "host": url.host or "127.0.0.1",
        "port": int(url.port or 5432),
        "database": url.database,
        "user": url.username,
        "password": url.password,
    }
