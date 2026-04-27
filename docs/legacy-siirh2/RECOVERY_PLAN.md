# Recovery Plan

## Goal

Recover the repository into a coherent SIIRH/SIHMADA platform without breaking the existing payroll module.

## Operating Principles

- payroll first protection
- additive change before replacement
- no invasive payroll refactor without mapped dependencies
- versioned schema changes only
- test before touching sensitive flows

## Phase 0 - Audit and Freeze

- map existing backend, frontend, schema, and payroll dependencies
- isolate stable vs fragile flows
- publish recovery and protection documents
- add payroll guardrail tests

## Phase 1 - Platform Safety Layer

- introduce `.env.example` and runtime config flags
- centralize file storage behavior
- prepare authoritative migration strategy
- add audit log and RBAC schema
- add endpoint protection incrementally

## Phase 2 - Shared Core Without Payroll Breakage

- introduce employee dossier and contract entities
- introduce alert engine tables
- introduce document registry and attachment policy
- introduce inspection case model
- introduce unified company/site/org references

## Phase 3 - Build Missing Modules Around Payroll

- recruitment
- onboarding/offboarding
- administrative dossier
- discipline and conflicts
- inspection du travail
- SST/ATMP
- talents
- declarations/compliance

## Immediate Priorities

1. Keep payroll endpoints and tables stable.
2. Stop schema drift from spreading further.
3. Build RBAC, audit, document, and alert foundations.
4. Implement inspection as a real tracked process between employee, employer, and inspector.
