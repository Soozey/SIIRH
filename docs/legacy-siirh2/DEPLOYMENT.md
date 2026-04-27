# Deployment

## Current Deployment Shape

- backend service
- frontend SPA
- PostgreSQL database

## Required Environment Variables

- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_ALGO`
- `AUTO_CREATE_TABLES`
- `UPLOAD_DIR`
- `VITE_API_URL`

## Production Notes

- disable `AUTO_CREATE_TABLES`
- run Alembic migrations before startup
- restrict CORS to known origins
- externalize secrets
- mount a persistent uploads volume
- back up database and document storage together
