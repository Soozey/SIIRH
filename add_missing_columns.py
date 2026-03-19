#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')

from app.config.config import engine
from sqlalchemy import text

def add_missing_columns():
    """Ajoute les colonnes manquantes à la table organizational_nodes"""
    
    alter_sql = text("""
    -- Ajouter les colonnes manquantes si elles n'existent pas
    DO $$ 
    BEGIN
        -- Ajouter la colonne path si elle n'existe pas
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'organizational_nodes' AND column_name = 'path') THEN
            ALTER TABLE organizational_nodes ADD COLUMN path TEXT;
        END IF;
        
        -- Ajouter la colonne code si elle n'existe pas
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'organizational_nodes' AND column_name = 'code') THEN
            ALTER TABLE organizational_nodes ADD COLUMN code VARCHAR(50);
        END IF;
        
        -- Ajouter la colonne description si elle n'existe pas
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'organizational_nodes' AND column_name = 'description') THEN
            ALTER TABLE organizational_nodes ADD COLUMN description TEXT;
        END IF;
        
        -- Ajouter la colonne created_by si elle n'existe pas
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'organizational_nodes' AND column_name = 'created_by') THEN
            ALTER TABLE organizational_nodes ADD COLUMN created_by INTEGER;
        END IF;
        
        -- Ajouter la colonne updated_by si elle n'existe pas
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'organizational_nodes' AND column_name = 'updated_by') THEN
            ALTER TABLE organizational_nodes ADD COLUMN updated_by INTEGER;
        END IF;
    END $$;
    """)
    
    try:
        with engine.connect() as conn:
            conn.execute(alter_sql)
            conn.commit()
        print("✅ Colonnes ajoutées avec succès!")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    success = add_missing_columns()
    sys.exit(0 if success else 1)