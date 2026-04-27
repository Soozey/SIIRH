# Architecture

## Current Architecture

### Backend

- one FastAPI application
- SQLAlchemy models in a shared monolith
- routers mixing API orchestration, business logic, imports, and reporting

### Frontend

- one React SPA
- route set still focused on payroll-centric operations

## Target Internal Domains

- auth/rbac
- core RH
- payroll
- time and activity
- documents
- declarations/compliance
- inspection du travail
- SST/ATMP
- talents
- messages
- alerts
- reporting/audit
