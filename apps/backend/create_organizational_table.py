#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')

from app.config.config import engine, Base
from app.models import OrganizationalNode

def create_tables():
    """Crée toutes les tables manquantes"""
    try:
        print("Création des tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables créées avec succès!")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        return False

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)