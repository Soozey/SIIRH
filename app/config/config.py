# backend/app/config.py
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

class Settings(BaseSettings):
    # Si un .env ou une variable d'environnement DATABASE_URL existent, ils priment.
    DATABASE_URL: str = "postgresql+psycopg2://postgres:admindev007@127.0.0.1:5432/db_siirh_app"
    JWT_SECRET: str = "change_me"
    JWT_ALGO: str = "HS256"

    class Config:
        env_file = ".env"  # permet d'utiliser backend/.env si présent

# Instance des settings
settings = Settings()

# Configuration SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True, 
    echo=True  # Mettez à False en production
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dépendance pour obtenir une session DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Crée toutes les tables dans la base de données"""
    Base.metadata.create_all(bind=engine)