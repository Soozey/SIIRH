# Endpoint Reconciliation

## Scope

Audit ciblé des modules frontend actifs les plus sensibles:

- `Employers`
- `Workers`
- `PayrollRun`
- `Payslip`
- `LeavePermissionManagement`
- `Absences`
- `Reporting`
- composants documentaires et organisationnels associés

## Fixed During This Pass

- Added missing backend route `GET /employers/{employer_id}` used by frontend employer editing.
- Replaced hardcoded frontend calls in `Absences.tsx` with the shared authenticated `api` client.
- Added authenticated document generation routes for payslips and contracts.
- Added authenticated reporting PDF route: `POST /generated-documents/reporting`.
- Added workflow review routes:
  - `POST /leaves/leave/{leave_id}/review/manager`
  - `POST /leaves/leave/{leave_id}/review/rh`
  - `POST /leaves/permission/{permission_id}/review/manager`
  - `POST /leaves/permission/{permission_id}/review/rh`
- Added paginated worker route usage on frontend through `GET /workers/paginated`.
- Fixed reporting and bulk payslip filters so both legacy text values and hierarchical node IDs resolve correctly backend-side.
- Secured `document-templates/*` with RBAC and audit logging.
- Secured `workers/import/*` with RBAC, employer scope checks, and import audit logging.

## Reconciled Module Map

### Employers

- Frontend routes: `/employers`, `/employers/{id}`, `/employers/{id}/logo`
- Backend coverage: present
- Hardening added: RBAC, audit trail, scope enforcement

### Workers

- Frontend routes: `/workers`, `/workers/paginated`, `/workers/{id}`, `/workers/delete_batch`
- Backend coverage: present
- Hardening added: RBAC on CRUD and batch delete, audit trail

### Payroll

- Frontend routes: `/payroll/get-or-create-run`, `/payroll/runs`, `/payroll/preview`, `/payroll/bulk-preview`
- Backend coverage: present
- Hardening added: salary visibility scope, bulk preview restrictions

### Leave & Permission

- Frontend routes: `/leaves/{payroll_run_id}/all`, `/leaves/leave`, `/leaves/permission`, delete routes
- Backend coverage: present
- Added production workflow: pending manager -> pending RH -> approved/rejected

### Reporting

- Frontend routes: `/reporting/metadata`, `/reporting/generate`, `/reporting/export-excel`, `/reporting/journal-columns/{employer_id}`, `/reporting/export-journal`
- Backend coverage: present
- Hardening added: reporting scope enforcement, worker-level filtering, search filters, hierarchical filter reconciliation, PDF export

### Documents

- Frontend hooks/routes: `/custom-contracts/*`, `/document-templates/*`, `/generated-documents/*`
- Backend coverage: present
- Hardening added this pass: RBAC and audit on `custom-contracts`, RBAC and audit on `document-templates`, secured generated PDF endpoints

## Remaining Residual Risk

- Some legacy auxiliary routers still expose business data without uniform audit coverage.
- Existing encoding noise remains in a subset of legacy labels and comments.
- Full automated endpoint contract test matrix still needs to be expanded module by module.
- Frontend production bundle still exceeds 500 kB and should be split before a commercial high-traffic rollout.
