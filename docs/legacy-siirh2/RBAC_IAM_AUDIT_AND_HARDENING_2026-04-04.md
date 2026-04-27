# RBAC / IAM Audit & Hardening Report (2026-04-04)

## Scope
- Backend: FastAPI + SQLAlchemy models/routers/security.
- Frontend: React route/menu guards and IAM admin panel.
- Constraint respected: no payroll formula/motor changes.

## A. Roles found in code
- Canonical base roles: `admin`, `rh`, `employeur`, `direction`, `departement`, `manager`, `employe`, `comptable`, `juridique`, `inspecteur`, `audit`, `recrutement`.
- Enterprise roles: full target catalog implemented in `app/iam_role_catalog.py` (64+ role codes including tenant owner/admin, DG, DRH, assistante RH, paie, conformité, portage client roles, support borné, lecture seule).
- Aliases kept for backward compatibility (`drh`, `dg`, `pdg`, `agent`, `paie`, `inspection_travail`).

## B. Permissions found
- Central permission catalog by `module:action`.
- Actions: `read`, `create`, `write`, `validate`, `approve`, `close`, `export`, `print`, `document`, `delete`, `admin`.
- Module-level matrix in `app/security.py` (`ROLE_MODULE_MATRIX`) as source of truth fallback.
- Persistent IAM overrides via DB tables.

## C. Data models / tables
- `iam_roles`
- `iam_permissions`
- `iam_role_permissions`
- `iam_role_activations` (installation scope activation/deactivation)
- `iam_user_roles` (multi-role assignments + validity windows + delegation)
- `iam_user_permission_overrides` (user-level allow/deny overrides)
- Existing `app_users.role_code` retained for compatibility, widened to 80 chars.

## D. Linked screens
- `src/pages/DataTransfer.tsx` now hosts import/export/update + IAM panel.
- `src/components/IamAccessManagerPanel.tsx`:
  - role activation by installation,
  - multi-role assignment per user,
  - role permission matrix (checkboxes by module/action),
  - effective access preview.

## E. Linked menus
- `src/components/Navigation.tsx` uses module permissions and multi-role checks.
- Session badge uses effective role (`effective_role_code`).

## F. Front routes
- `src/rbac.ts` provides route-to-module mapping and access check.
- `src/App.tsx` wraps pages with `RoleRoute` + `canAccessPath`.

## G. Backend endpoints
- IAM endpoints in `app/routers/auth.py`:
  - role catalog,
  - role activations,
  - role permissions update,
  - user role assignments,
  - user access preview,
  - user permission overrides.

## H. Guards / middlewares / policies
- `user_has_any_role()` now used broadly for multi-role evaluation.
- `require_module_access()` for master-data critical APIs.
- `require_roles()` hardened with route-aware module/action guard fallback (backend enforcement even if legacy endpoint still uses role-only guard).

## I. Gaps vs target matrix
- Before: partial single-role assumptions and some primary-role-only checks.
- After: enterprise role catalog present, multi-role aggregation active, installation activation active, assignment constraints + scoped checks aligned.

## J. Security risks found & fixed
- Fixed: residual single-role checks in critical routers/services.
- Fixed: role activation/assignment checks now consider all active roles.
- Fixed: seed duplication risk in IAM role-permission generation (`*:read` duplicate conflict).
- Added backend route-level module guard fallback to prevent front-only permission illusions.

## K. Backend present but frontend missing
- IAM backend capabilities already present; surfaced in real UI panel under DataTransfer.

## L. Frontend present but not really wired
- IAM panel actions are wired to live APIs (`/auth/iam/*`, `/auth/users`, `/auth/roles`).

## M. Wrongly visible screens
- Sidebar hide/show now based on multi-role + module permissions.
- Backend remains final authority (403 if frontend tries unauthorized action).

## N. Missing role screens
- Core role admin screen delivered via IAM panel (activation + assignment + permission matrix + preview).

## O. Regression risks
- Route-module heuristic in `require_roles()` can affect legacy endpoints if wrong prefix mapping.
- Mitigation: explicit map + tests added; unmapped routes keep existing behavior.

## P. Architecture recommendation
- Keep DB IAM tables as source of truth.
- Keep frontend as projection only.
- Continue migrating legacy endpoints from `require_roles()` to explicit `require_module_access(module, action)` per endpoint for stricter long-term control.

## Q. Migration points
- `9c2e5f7a1b90_add_iam_habilitations_tables.py`
- `af3d91b1c742_widen_app_user_role_code_for_enterprise.py`

## R. Code cleanup points
- Continue replacing hardcoded role lists per endpoint with module-permission dependencies.
- Normalize remaining alias role usage in old modules.

## S. Reinforced tests
- `test_iam_rbac_hardening.py`:
  - multi-role permission union,
  - role deactivation effect,
  - self/manager scope checks,
  - delegated admin activation,
  - backend block when module write/admin permission removed.
- Existing payroll guardrail tests executed.

---

## Final matrix status
- Target role matrix: implemented in enterprise catalog (with aliases/backward compatibility).
- Multi-role per user: implemented and persisted.
- Installation role activation/deactivation: implemented and persisted.
- Fine-grained module/action checkboxes: implemented.
- Access preview: implemented.
- Audit trail for IAM changes: implemented through audit service calls.

## Explicit non-regression statements
- Payroll calculation logic/formulas were not modified.
- No destructive schema change was introduced.
- Existing data compatibility preserved via additive IAM tables + role_code length widening.
