# init_db.py
"""
Script simple pour créer les tables de la base PostgreSQL
à partir des modèles SQLAlchemy (app.models).
À lancer UNE FOIS quand tu changes la structure des modèles.
"""

from sqlalchemy import create_engine
from app.config.config import settings
from app.models import Base


def init_db():
    print("🔧 Connexion à la base :", settings.DATABASE_URL)
    engine = create_engine(settings.DATABASE_URL, echo=True, pool_pre_ping=True)
    print("📦 Création des tables (si elles n'existent pas)...")
    Base.metadata.create_all(bind=engine)
    print("✅ Base initialisée avec succès.")


if __name__ == "__main__":
    init_db()
