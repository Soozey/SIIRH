# Payroll Protection Map

## Objective

Protect the existing payroll module and all dependent flows while the wider SIIRH platform is being completed.

## Protected Assets

### Business logic files

- `siirh-backend/app/payroll_logic.py`
- `siirh-backend/app/leave_logic.py`
- `siirh-backend/app/utils/hs_hm_calculations.py`

### Payroll-facing routers

- `siirh-backend/app/routers/payroll.py`
- `siirh-backend/app/routers/payroll_hs_hm.py`
- `siirh-backend/app/routers/primes.py`
- `siirh-backend/app/routers/reporting.py`
- `siirh-backend/app/routers/variables.py`
- `siirh-backend/app/routers/calendar.py`
- `siirh-backend/app/routers/leaves.py`

### Payroll data tables

- `workers`
- `employers`
- `payvars`
- `payroll_runs`
- `payroll_hs_hm`
- `payroll_primes`
- `primes`
- `worker_primes`
- `worker_prime_links`
- `absences`
- `avances`
- `leaves`
- `permissions`
- `calendar_days`
- `type_regimes`

## Payroll Invariants

These must not change without explicit regression evidence and migration coverage:

- salary base and hourly rate derivation
- contribution rate override resolution
- CNaPS / SMIE / FMFP calculation order
- formula constant exposure and evaluation semantics
- overtime import to payslip mapping
- prime formula and override precedence
- leave and permission summary display on payslip
- payroll run uniqueness by employer and period
- one payroll HS/HM aggregate per payroll run and worker
- one payvar per worker and period

## Highest Risk Change Zones

### Red zone

- `payroll_logic.py`
- line assembly in `generate_preview_data`
- amount reconstruction used by reporting
- historical reconstruction for termination-related calculations

### Orange zone

- `models.Worker`
- `models.Employer`
- `models.PayVar`
- `models.PayrollHsHm`
- `models.PayrollPrime`
- import endpoints in `payroll_hs_hm.py`

### Yellow zone

- new service layer around documents, alerts, inspection, audit, RBAC
- new schema tables unrelated to current payroll paths
- new frontend routes for missing modules

## Change Protocol

1. Reproduce the business rule with a test.
2. Map dependencies touching that rule.
3. Apply the smallest possible change.
4. Run payroll guardrail tests.
5. Document schema or logic impact in `CHANGELOG.md`.
