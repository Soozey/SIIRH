#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')

from app.config.config import engine
from sqlalchemy import text

def recreate_organizational_table():
    """Supprime et recrée la table organizational_nodes avec toutes les colonnes"""
    
    drop_sql = text("DROP TABLE IF EXISTS organizational_nodes CASCADE;")
    
    create_sql = text("""
    CREATE TABLE organizational_nodes (
        id SERIAL PRIMARY KEY,
        employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
        parent_id INTEGER REFERENCES organizational_nodes(id) ON DELETE CASCADE,
        level VARCHAR(20) NOT NULL CHECK (level IN ('etablissement', 'departement', 'service', 'unite')),
        name VARCHAR(255) NOT NULL,
        code VARCHAR(50),
        description TEXT,
        path TEXT,
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        updated_by INTEGER,
        
        -- Contraintes d'intégrité
        CONSTRAINT valid_hierarchy CHECK (
            (level = 'etablissement' AND parent_id IS NULL) OR 
            (level != 'etablissement' AND parent_id IS NOT NULL)
        ),
        CONSTRAINT unique_name_per_parent UNIQUE (employer_id, parent_id, name),
        CONSTRAINT no_self_reference CHECK (id != parent_id)
    );
    """)
    
    indexes_sql = text("""
    -- Index pour les performances
    CREATE INDEX idx_organizational_nodes_employer ON organizational_nodes(employer_id);
    CREATE INDEX idx_organizational_nodes_parent ON organizational_nodes(parent_id);
    CREATE INDEX idx_organizational_nodes_level ON organizational_nodes(level);
    CREATE INDEX idx_organizational_nodes_path ON organizational_nodes(path);
    CREATE INDEX idx_organizational_nodes_active ON organizational_nodes(is_active);
    CREATE INDEX idx_organizational_nodes_hierarchy ON organizational_nodes(employer_id, parent_id, level);
    """)
    
    try:
        with engine.connect() as conn:
            print("Suppression de l'ancienne table...")
            conn.execute(drop_sql)
            
            print("Création de la nouvelle table...")
            conn.execute(create_sql)
            
            print("Création des index...")
            conn.execute(indexes_sql)
            
            conn.commit()
        
        print("✅ Table organizational_nodes recréée avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    success = recreate_organizational_table()
    sys.exit(0 if success else 1)