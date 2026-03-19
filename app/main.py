from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import depuis config.py au lieu de db.py
from .config.config import Base, engine, create_tables, settings
from . import models
from .routers import employers, workers, variables, payroll, hs, absences, payroll_hs_hm, type_regimes, primes, calendar, leaves, workers_import, reporting, custom_contracts, auth, generated_documents
from .services.file_storage import get_upload_root
from .security import seed_default_admin

# Création des tables au démarrage
if settings.AUTO_CREATE_TABLES:
    create_tables()
    from .config.config import SessionLocal
    db = SessionLocal()
    try:
        seed_default_admin(db)
    finally:
        db.close()

app = FastAPI(title="SIRH Paie MG")

# Autorise ton front Vite (ports 5173/5174, localhost ET 127.0.0.1)
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques pour les logos
from fastapi.staticfiles import StaticFiles

# Création du dossier uploads s'il n'existe pas
UPLOAD_DIR = Path(get_upload_root(settings.UPLOAD_DIR))

# Montage du dossier pour accès via /static
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")


# Import et inclusion des routers
app.include_router(employers.router)
app.include_router(workers.router)
app.include_router(workers_import.router)
app.include_router(variables.router)
app.include_router(payroll.router)
app.include_router(type_regimes.router)
app.include_router(absences.router)
app.include_router(hs.router)
app.include_router(payroll_hs_hm.router)
app.include_router(primes.router)
app.include_router(calendar.router)
app.include_router(leaves.router)
app.include_router(reporting.router)
app.include_router(auth.router)
app.include_router(generated_documents.router)

# Import du nouveau router constants
from .routers import constants
app.include_router(constants.router)

# Import du router custom_contracts
app.include_router(custom_contracts.router)

# Import du router document_templates
from .routers import document_templates
app.include_router(document_templates.router)

# Import du nouveau router organization
from .routers import organization
app.include_router(organization.router)

# Import du nouveau router organizational_structure
from .routers import organizational_structure
app.include_router(organizational_structure.router)

# ❌ DÉSACTIVÉ - Système matricule suspendu (réversible)
# from .routers import matricule_api
# app.include_router(matricule_api.router)
# from .middleware.matricule_error_handler import setup_error_handling
# app = setup_error_handling(app)

# Import du nouveau router hierarchical_organization
from .routers import hierarchical_organization
app.include_router(hierarchical_organization.router)
