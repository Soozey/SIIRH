#!/usr/bin/env python3
"""
Script pour démarrer le serveur SIIRH avec le référentiel de constantes
"""
import uvicorn
import sys
import os

def main():
    print("🚀 Démarrage du serveur SIIRH avec référentiel de constantes")
    print("📊 Endpoints disponibles:")
    print("  - http://localhost:8000/constants/payroll")
    print("  - http://localhost:8000/constants/business") 
    print("  - http://localhost:8000/constants/document-fields")
    print("  - http://localhost:8000/constants/field-categories")
    print("  - http://localhost:8000/constants/system-data")
    print("  - http://localhost:8000/docs (Documentation Swagger)")
    print()
    
    try:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Serveur arrêté par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()