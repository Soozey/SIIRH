# SIIRH

Monorepo officiel SIIRH Madagascar.

## Structure

- `apps/backend` : API FastAPI, SQLAlchemy, Alembic, moteur RH/paie.
- `apps/frontend` : application React/Vite.
- `infra` : fichiers Docker, Nginx et déploiement.
- `scripts` : scripts utiles de maintenance.
- `docs` : documentation projet et rapport de migration.

## Développement backend

```powershell
cd apps/backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API locale : `http://localhost:8000`
Documentation OpenAPI : `http://localhost:8000/docs`

## Développement frontend

```powershell
cd apps/frontend
npm install
npm run dev
```

Frontend local : `http://localhost:5173`

## Build et vérification

```powershell
cd apps/frontend
npm run lint
npm run build
```

```powershell
cd apps/backend
python -m pytest
```

## Sécurité

Ne pas commiter de fichier `.env`, base locale, logs, dumps, `uploads`, `node_modules` ou `dist`.
Utiliser `.env.example` comme modèle.
