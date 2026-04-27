#!/usr/bin/env python3
"""
Windows-friendly local launcher for the SIIRH backend.
"""

import sys

import uvicorn


def main():
    print("Demarrage du backend SIIRH")
    print("Endpoints disponibles:")
    print("  - http://127.0.0.1:8001/constants/payroll")
    print("  - http://127.0.0.1:8001/constants/business")
    print("  - http://127.0.0.1:8001/constants/document-fields")
    print("  - http://127.0.0.1:8001/constants/field-categories")
    print("  - http://127.0.0.1:8001/constants/system-data")
    print("  - http://127.0.0.1:8001/docs")
    print()

    try:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8001,
            reload=False,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nServeur arrete par l'utilisateur")
    except Exception as exc:
        print(f"Erreur lors du demarrage: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
