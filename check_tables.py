#!/usr/bin/env python3
import sqlite3
import os

db_path = "siirh.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print("Tables existantes:")
    for table in sorted(tables):
        print(f"  - {table}")
    
    conn.close()
else:
    print("Base de données non trouvée !")