# Migration Plan

## Current Situation

Alembic exists, but the application still creates tables at runtime. Migrations are not yet the sole source of schema truth.

## Migration Policy

- no manual schema drift for production evolution
- one versioned Alembic migration per structural change
- additive migrations first
- rollback notes when feasible
- schema changes impacting payroll must have regression tests

## Recovery Steps

### Step 1 - Baseline inventory

- compare live schema against `models.py`
- compare `models.py` against Alembic history
- record missing migrations and out-of-band tables

### Step 2 - Freeze runtime drift

- keep `AUTO_CREATE_TABLES=true` by default for backward compatibility
- allow environments to disable it explicitly
- move to Alembic-only bootstrap as soon as baseline is aligned

### Step 3 - Priority migration families

1. RBAC and audit
2. document storage and registry
3. alert engine
4. inspection du travail
5. SST/ATMP
6. employee dossier and contract normalization

## Payroll Protection Rule

No migration may rename or drop payroll-critical structures until non-regression coverage proves a safe replacement.
