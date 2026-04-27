# SIIRH / SIHMADA Recovery Workspace

This repository contains the current SIIRH application under recovery and controlled expansion.

## Current Status

- existing payroll module preserved
- backend: FastAPI monolith in `siirh-backend`
- frontend: React/Vite app in `siirh-frontend`
- recovery documentation added for audit, protection, migration, RBAC, and tests

## Read First

- `EXISTING_SYSTEM_AUDIT.md`
- `PAYROLL_PROTECTION_MAP.md`
- `DATA_MODEL_GAP_ANALYSIS.md`
- `RECOVERY_PLAN.md`
- `MIGRATION_PLAN.md`
- `RBAC_GAP_REPORT.md`

## Key Principle

Do not break payroll. New RH, inspection, alert, and compliance capabilities must be integrated around the existing payroll backend through controlled migrations and adapters.

## Local Run

### Backend

1. create a `.env` from `.env.example`
2. install backend requirements
3. run `python start_server.py` from `siirh-backend`

### Frontend

1. create a `.env` from `.env.example`
2. run `npm install`
3. run `npm run dev` in `siirh-frontend`

## Execution Visibility Required

After executing the build, you MUST verify and SHOW RESULTS in the UI.

### Mandatory Post-Build Verification

#### UI Verification Mode (Critical)

Open the application as different roles:

- `ADMIN`
- `HR`
- `EMPLOYER`
- `EMPLOYEE`
- `LABOR_INSPECTOR`

For each role:

- Navigate through the interface
- Verify that new modules are visible
- Verify that menus exist and are clickable
- Verify that pages load real data, not empty placeholders

If nothing is visible, you MUST fix frontend integration.

### Force Visual Output

You MUST create visible elements in the interface.

Add a dashboard section named `SIIRH LEGAL MODULES STATUS`.

This must display:

- Modules implemented
- Number of procedures created
- Number of PV generated
- Number of test cases

No empty dashboard is allowed.

### Create Real Test Data Visible in UI

Create and expose in the UI:

- 2 companies:
  - `ENTREPRISE AVENIR SARL`
  - `MADATECH INDUSTRIES`
- At least 5 employees each
- 1 active dispute
- 1 conciliation case
- 1 failed conciliation (`PV NON-CONCILIATION`)
- 1 resignation
- 1 dismissal
- 1 technical unemployment case

These MUST be visible in:

- Employee list
- Disputes module
- Inspector view

If data is not visible, fix the query, API, or role filter.

### Button Test (Critical)

Scan all buttons in the UI.

- If a button does nothing, fix it
- If a button is not connected to the backend, connect it
- If an API exists but is not used, link it

Output required:

- List of fixed buttons

### Route and API Validation

- Check all frontend routes
- Check all API endpoints
- Check permissions per role

If an error exists, fix it immediately.

### Error Logging Panel

Add a temporary admin panel named `DEBUG EXECUTION PANEL`.

This must show:

- Last migrations executed
- Last seed executed
- Last errors
- Modules created

Remove it only when the application is fully stable.

### Final Check (Mandatory)

Before finishing, confirm all of the following:

- I can click and see the new modules
- I can open a dispute
- I can see a PV
- I can see companies and employees

If the answer is no to any item, continue fixing until the UI shows real results.
