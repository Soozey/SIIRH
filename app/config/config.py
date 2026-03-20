from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


def normalize_database_url(database_url: str) -> str:
    url = make_url(database_url.strip())

    if url.drivername in {"postgresql", "postgres", "postgresql+psycopg2"}:
        url = url.set(drivername="postgresql+psycopg")

    return url.render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg://postgres:change_me@127.0.0.1:5432/db_siirh_app"
    JWT_SECRET: str = "change_me"
    JWT_ALGO: str = "HS256"
    AUTO_CREATE_TABLES: bool = True
    UPLOAD_DIR: str = "uploads"
    AUTH_REQUIRED: bool = True
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "Admin123!"
    DOCUMENT_VERIFY_SECRET: str = "change_document_secret"
    APP_PUBLIC_URL: str = "http://127.0.0.1:8001"

    def __init__(self, **values):
        super().__init__(**values)
        self.DATABASE_URL = normalize_database_url(self.DATABASE_URL)


settings = Settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency used to obtain a scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create database tables from the SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)
