from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import depuis config.py au lieu de db.py
from .config.config import Base, engine, create_tables
from . import models

# Création des tables au démarrage
create_tables()

app = FastAPI(title="SIRH Paie MG")

# Autorise ton front Vite (ports 5173/5174, localhost ET 127.0.0.1)
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import et inclusion des routers
from .routers import employers, workers, variables, payroll, type_regimes
app.include_router(employers.router)
app.include_router(workers.router)
app.include_router(variables.router)
app.include_router(payroll.router)
app.include_router(type_regimes.router)