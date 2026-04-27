# Data Model Gap Analysis

## Current State

The current model is payroll-led. `Worker` acts as:

- employee identity
- contract summary
- assignment container
- payroll source
- leave balance carrier
- document target

This keeps the existing product usable, but it is not sufficient for a coherent end-to-end SIIRH.

## Structural Problems

### 1. RH master data is denormalized inside `workers`

Missing separate master entities for:

- employee dossier
- employment contract
- contract amendment
- assignment
- onboarding/offboarding checklist
- employee documents
- disciplinary cases
- compliance obligations

### 2. Organization exists in three shapes

- strings on `workers`
- `organizational_units`
- `organizational_nodes`

### 3. Payroll input domain is spread across incompatible shapes

- overtime in `payvars`
- overtime in `payroll_hs_hm`
- absences in `payvars`
- absences in `absences`
- advances in `payvars`
- advances in `avances`
- advantages in `workers`
- advantages again in `payvars`

### 4. No institutional security schema

Missing tables for users, roles, permissions, sessions, audit logs, and access logs.

### 5. No inspection schema

Missing case, participant, message, attachment, status history, and compliance entities.

### 6. No alert schema

Missing rule, instance, acknowledgement, resolution, and history entities.

## Immediate Decision

The old payroll schema is not replaced now.
It is wrapped and documented, while the wider SIIRH data model grows beside it through controlled migrations.
