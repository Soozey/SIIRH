# Existing System Audit

## Executive Summary

This repository already contains a working payroll-centered SIIRH application with:

- `siirh-backend`: FastAPI + SQLAlchemy monolith
- `siirh-frontend`: React 19 + TypeScript + Vite frontend
- PostgreSQL schema partially managed by Alembic
- Existing payroll calculation and payslip preview flows

The current product is not a full SIIRH platform yet. It is a payroll-first application with partial RH support around workers, employers, overtime, absences, leave, reporting, document templates, and organizational structures.

The payroll engine must be treated as a protected asset. It is already in use and its business logic is spread across preview generation, import flows, reporting, and worker/employer settings.

## Current Stack

### Backend

- FastAPI
- SQLAlchemy ORM
- Alembic
- PostgreSQL
- OpenPyXL for Excel imports/exports

Key files:

- `siirh-backend/app/main.py`
- `siirh-backend/app/models.py`
- `siirh-backend/app/payroll_logic.py`
- `siirh-backend/app/routers/payroll.py`
- `siirh-backend/app/routers/payroll_hs_hm.py`
- `siirh-backend/app/routers/reporting.py`

### Frontend

- React 19
- TypeScript
- Vite
- Axios
- React Query
- Tailwind
- MUI + Heroicons

Key files:

- `siirh-frontend/src/App.tsx`
- `siirh-frontend/src/pages/PayrollRun.tsx`
- `siirh-frontend/src/pages/Workers.tsx`
- `siirh-frontend/src/pages/Reporting.tsx`

## Functional Coverage Actually Present

### Stable or usable today

- Employers CRUD
- Workers CRUD
- Payroll run creation
- Payroll preview by worker and in bulk
- Overtime and majoration import/manual link to payroll
- Prime management and payroll overrides
- Leave and permission balances
- Reporting from payroll previews
- Basic document template and custom contract storage
- Two organizational structure systems with partial frontend integration

### Fragile or debt-heavy

- Payroll preview assembly mixes ORM, raw SQL workaround, imports, and reporting needs
- `create_all()` is still executed at app startup despite Alembic being present
- CORS is open to `*`
- `auth.py` and `security.py` are empty
- DB credentials are hardcoded in code
- Encoding corruption is present in source strings and comments
- Frontend uses both shared API config and hardcoded backend URLs
- Some tests are standalone scripts instead of a reliable regression suite

### Incomplete or missing

- RBAC
- audit trail for sensitive actions
- inspection du travail
- recruitment
- onboarding/offboarding
- personnel files
- compliance workflows
- declarations module at production level
- talents/performance
- SST/ATMP module
- intelligent alerts
- offline/resilience strategy
- user-facing tutorials/contextual help across modules

### Simulated, suspended, or partially wired

- suspended matricule subsystem
- legacy and new organizational systems run in parallel
- document management is template-centric, not a real document lifecycle module
- absences page is a calculator UI, not a workflow engine
- leave/permission module is directly tied to payroll periods, with no approval chain

## Payroll Perimeter Identified

Core payroll data model currently relies on:

- `Employer`
- `Worker`
- `PayVar`
- `PayrollRun`
- `PayrollHsHm`
- `PayrollPrime`
- `Absence`
- `Avance`
- `Leave`
- `Permission`
- `Prime`
- `WorkerPrime`
- `WorkerPrimeLink`
- `CalendarDay`

## Immediate Recovery Conclusion

1. Freeze payroll business logic except for proven defects.
2. Add payroll guardrail tests before touching surrounding modules.
3. Stop extending the current data model ad hoc.
4. Introduce versioned schema governance, RBAC, audit, alerts, inspection, and document infrastructure around the payroll core.
5. Build new RH modules by extension and integration, not by replacing payroll internals.
