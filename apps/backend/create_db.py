# create_db.py
import sys
from pathlib import Path

# 1) Ajouter le dossier du projet au PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# 2) Importer la Base SQLAlchemy (toutes les tables)
from app.models import Base

# 3) Importer l'engine défini dans app/config.py
from app.config import engine


def main() -> None:
    print("Création des tables en base…")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées (ou déjà existantes).")


if __name__ == "__main__":
    main()
