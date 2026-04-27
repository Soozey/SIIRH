# RBAC Gap Report

## Current State

There is no active RBAC implementation in the repository.

Evidence:

- `siirh-backend/app/routers/auth.py` is empty
- `siirh-backend/app/security.py` is empty
- routers do not enforce role-based access
- frontend navigation is not user-role aware in practice

## Risks

- payroll data is exposed without role isolation
- inspection-sensitive complaints cannot be protected
- document access cannot be restricted properly
- no auditability for privileged actions

## Required Roles

- Admin
- RH
- Comptable
- Employeur
- Manager
- Employe
- Inspecteur
- Observateur/Audit

## Required Permission Domains

- employer_admin
- worker_admin
- payroll_view
- payroll_edit_inputs
- payroll_run
- payroll_reporting
- declarations_manage
- contracts_manage
- documents_manage
- leave_approve
- inspection_case_create
- inspection_case_assign
- inspection_case_view_confidential
- inspection_case_reply
- sst_manage
- alerts_manage
- system_admin
