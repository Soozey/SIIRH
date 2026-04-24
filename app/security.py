from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
import unicodedata
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import models
from .config.config import get_db, settings
from .iam_role_catalog import build_enterprise_role_definitions


ROLE_INSTALLATION_SCOPE = "installation"
WRITE_EQUIVALENT_ACTIONS = {"create", "write", "validate", "approve", "close", "export", "print", "document", "delete"}
READ_METHODS = {"GET", "HEAD", "OPTIONS"}

# Garde de coherance front/back: meme si un endpoint utilise encore require_roles,
# on applique aussi la matrice module/action derivee du chemin HTTP.
REQUEST_MODULE_RULES: list[tuple[str, str, Optional[str]]] = [
    ("/auth/bootstrap-role-logins", "master_data", "admin"),
    ("/auth/users", "master_data", "admin"),
    ("/auth/iam", "master_data", "admin"),
    ("/system-data-import", "master_data", "admin"),
    ("/system-data-export", "master_data", "admin"),
    ("/system-update", "master_data", "admin"),
    ("/master-data", "master_data", None),
    ("/statutory-exports/preview", "declarations", "read"),
    ("/reporting/generate", "reporting", "read"),
    ("/reporting/export-excel", "reporting", "read"),
    ("/reporting/export-journal", "reporting", "read"),
    ("/recruitment/import", "recruitment", None),
    ("/recruitment", "recruitment", None),
    ("/custom-contracts", "contracts", None),
    ("/document-templates", "contracts", None),
    ("/generated-documents", "employee_portal", None),
    ("/workers/import", "workforce", None),
    ("/workers", "workforce", None),
    ("/employers", "workforce", None),
    ("/hierarchical-organization", "organization", None),
    ("/organizational-structure", "organization", None),
    ("/organization", "organization", None),
    ("/type_regimes", "organization", None),
    ("/payroll-hs-hm", "payroll", None),
    ("/payroll", "payroll", None),
    ("/primes", "payroll", None),
    ("/variables", "payroll", None),
    ("/calendar", "time_absence", None),
    ("/hs", "time_absence", None),
    ("/absences", "time_absence", None),
    ("/leaves", "time_absence", None),
    ("/declarations", "declarations", None),
    ("/statutory-exports", "declarations", None),
    ("/reporting", "reporting", None),
    ("/talents", "talents", None),
    ("/sst", "sst", None),
    ("/people-ops", "people_ops", None),
    ("/employee-portal", "employee_portal", None),
    ("/messages", "messages", None),
    ("/compliance", "compliance", None),
]

READ_PAYROLL_ROLES = {
    "admin",
    "rh",
    "comptable",
    "employeur",
    "direction",
    "manager",
    "departement",
    "employe",
    "juridique",
    "inspecteur",
    "recrutement",
    "audit",
}
WRITE_RH_ROLES = {"admin", "rh", "employeur"}
MANAGER_REVIEW_ROLES = {"admin", "rh", "manager", "departement"}
RH_REVIEW_ROLES = {"admin", "rh", "direction"}
PAYROLL_WRITE_ROLES = {"admin", "rh", "employeur", "comptable"}

ROLE_MODULE_MATRIX = {
    "admin": {
        "label": "Administration globale",
        "scope": "global",
        "modules": {"*": ["read", "write", "admin"]},
    },
    "rh": {
        "label": "Ressources humaines",
        "scope": "global_or_company",
        "modules": {
            "recruitment": ["read", "write"],
            "contracts": ["read", "write"],
            "workforce": ["read", "write"],
            "organization": ["read", "write"],
            "time_absence": ["read", "write"],
            "payroll": ["read", "write"],
            "declarations": ["read", "write"],
            "talents": ["read", "write"],
            "people_ops": ["read", "write"],
            "sst": ["read", "write"],
            "reporting": ["read", "write"],
            "compliance": ["read", "write"],
            "messages": ["read", "write"],
            "employee_portal": ["read", "write"],
            "master_data": ["read", "admin"],
        },
    },
    "employeur": {
        "label": "Direction employeur",
        "scope": "company",
        "modules": {
            "recruitment": ["read", "write"],
            "contracts": ["read", "write"],
            "workforce": ["read", "write"],
            "organization": ["read", "write"],
            "time_absence": ["read", "write"],
            "payroll": ["read", "write"],
            "declarations": ["read", "write"],
            "talents": ["read", "write"],
            "people_ops": ["read", "write"],
            "sst": ["read", "write"],
            "reporting": ["read", "write"],
            "compliance": ["read", "write"],
            "messages": ["read", "write"],
            "employee_portal": ["read", "write"],
            "master_data": ["read", "admin"],
        },
    },
    "direction": {
        "label": "Direction",
        "scope": "company",
        "modules": {
            "recruitment": ["read"],
            "contracts": ["read"],
            "workforce": ["read"],
            "organization": ["read"],
            "time_absence": ["read"],
            "payroll": ["read"],
            "declarations": ["read"],
            "talents": ["read"],
            "people_ops": ["read"],
            "sst": ["read"],
            "reporting": ["read"],
            "compliance": ["read"],
            "messages": ["read", "write"],
            "employee_portal": ["read"],
            "master_data": ["read"],
        },
    },
    "departement": {
        "label": "Responsable departement",
        "scope": "organizational_unit",
        "modules": {
            "recruitment": ["read"],
            "contracts": ["read"],
            "workforce": ["read"],
            "organization": ["read"],
            "time_absence": ["read", "write"],
            "payroll": ["read"],
            "talents": ["read"],
            "sst": ["read"],
            "reporting": ["read"],
            "messages": ["read", "write"],
            "employee_portal": ["read", "write"],
        },
    },
    "manager": {
        "label": "Manager",
        "scope": "organizational_unit",
        "modules": {
            "workforce": ["read"],
            "time_absence": ["read", "write"],
            "payroll": ["read"],
            "reporting": ["read"],
            "talents": ["read"],
            "messages": ["read", "write"],
            "employee_portal": ["read", "write"],
        },
    },
    "employe": {
        "label": "Employe",
        "scope": "self",
        "modules": {
            "employee_portal": ["read", "write"],
            "time_absence": ["read", "write"],
            "documents": ["read"],
            "messages": ["read", "write"],
        },
    },
    "comptable": {
        "label": "Comptabilite paie",
        "scope": "company",
        "modules": {
            "payroll": ["read", "write"],
            "declarations": ["read", "write"],
            "reporting": ["read", "write"],
            "workforce": ["read"],
            "organization": ["read"],
        },
    },
    "juridique": {
        "label": "Juridique / conformite",
        "scope": "company",
        "modules": {
            "contracts": ["read", "write"],
            "compliance": ["read", "write"],
            "declarations": ["read"],
            "reporting": ["read"],
            "employee_portal": ["read", "write"],
            "messages": ["read", "write"],
        },
    },
    "inspecteur": {
        "label": "Inspection du travail",
        "scope": "assigned_case_or_company",
        "modules": {
            "contracts": ["read", "write"],
            "workforce": ["read"],
            "master_data": ["read"],
            "compliance": ["read", "write"],
            "employee_portal": ["read", "write"],
            "reporting": ["read"],
            "declarations": ["read"],
            "messages": ["read"],
        },
    },
    "audit": {
        "label": "Audit interne",
        "scope": "global_or_company",
        "modules": {
            "reporting": ["read"],
            "declarations": ["read"],
            "payroll": ["read"],
            "compliance": ["read"],
            "employee_portal": ["read"],
            "messages": ["read"],
        },
    },
    "judge_readonly": {
        "label": "Juge",
        "scope": "read_only_external",
        "modules": {
            "compliance": ["read"],
            "employee_portal": ["read"],
            "messages": ["read"],
        },
    },
    "court_clerk_readonly": {
        "label": "Greffier",
        "scope": "read_only_external",
        "modules": {
            "compliance": ["read"],
            "employee_portal": ["read"],
            "messages": ["read"],
        },
    },
    "recrutement": {
        "label": "Charge recrutement",
        "scope": "company",
        "modules": {
            "recruitment": ["read", "write"],
            "workforce": ["read"],
            "talents": ["read"],
            "messages": ["read", "write"],
        },
    },
}

ENTERPRISE_ROLE_MODULE_OVERRIDES: dict[str, dict[str, list[str]]] = {
    "employer_admin": {
        "master_data": ["read", "admin"],
    },
    "hr_manager": {
        "master_data": ["read", "admin"],
    },
    "hr_officer": {
        "contracts": ["read", "write"],
        "workforce": ["read", "write"],
        "organization": ["read", "write"],
        "time_absence": ["read", "write"],
        "people_ops": ["read", "write"],
        "sst": ["read", "write"],
        "compliance": ["read"],
        "employee_portal": ["read", "write"],
        "messages": ["read", "write"],
        "reporting": ["read"],
    },
    "employee": {},
    "labor_inspector": {
        "contracts": ["read", "write"],
        "workforce": ["read"],
        "master_data": ["read"],
        "compliance": ["read", "write"],
        "employee_portal": ["read", "write"],
        "reporting": ["read"],
        "declarations": ["read"],
        "messages": ["read", "write"],
        "people_ops": ["read"],
    },
    "labor_inspector_supervisor": {
        "contracts": ["read", "write"],
        "workforce": ["read"],
        "master_data": ["read"],
        "compliance": ["read", "write", "admin"],
        "employee_portal": ["read", "write"],
        "reporting": ["read"],
        "declarations": ["read"],
        "messages": ["read", "write"],
        "people_ops": ["read"],
    },
    "staff_delegate": {
        "employee_portal": ["read", "write"],
        "time_absence": ["read"],
        "messages": ["read", "write"],
        "compliance": ["read", "write"],
        "people_ops": ["read"],
        "reporting": ["read"],
    },
    "works_council_member": {
        "employee_portal": ["read", "write"],
        "messages": ["read", "write"],
        "compliance": ["read", "write"],
        "people_ops": ["read"],
        "reporting": ["read"],
    },
    "judge_readonly": {
        "compliance": ["read"],
        "employee_portal": ["read"],
        "messages": ["read"],
    },
    "court_clerk_readonly": {
        "compliance": ["read"],
        "employee_portal": ["read"],
        "messages": ["read"],
    },
    "intra_user": {
        "messages": ["read", "write"],
        "reporting": ["read"],
        "workforce": ["read"],
        "organization": ["read"],
    },
    "auditor_readonly": {
        "reporting": ["read"],
        "declarations": ["read"],
        "compliance": ["read"],
        "messages": ["read"],
        "people_ops": ["read"],
    },
}

STRICT_ROLE_MODULE_WHITELISTS: dict[str, set[str]] = {
    "employee": {"employee_portal", "time_absence", "documents", "messages"},
    "judge_readonly": {"compliance", "employee_portal", "messages"},
    "court_clerk_readonly": {"compliance", "employee_portal", "messages"},
    "auditor_readonly": {"reporting", "declarations", "compliance", "messages", "people_ops"},
}

ENTERPRISE_ROLE_DEFINITIONS = build_enterprise_role_definitions()

# Alias metier conserves pour retrocompatibilite.
ROLE_CODE_ALIASES = {
    "drh": "rh",
    "pdg": "direction",
    "dg": "direction",
    "agent": "employe",
    "paie": "comptable",
    "inspection_travail": "inspecteur",
}

ALIAS_ROLE_PROFILES = {
    "drh": {"label": "Directeur des ressources humaines", "scope": "global_or_company"},
    "pdg": {"label": "Direction generale (consultatif)", "scope": "read_only_global"},
    "dg": {"label": "Direction generale (consultatif)", "scope": "read_only_global"},
    "agent": {"label": "Agent / Salarie", "scope": "self"},
    "paie": {"label": "Gestionnaire paie", "scope": "company"},
    "inspection_travail": {"label": "Inspection du travail", "scope": "assigned_case_or_company"},
}

USER_ADMIN_ROLES = {"admin", "rh", "employeur"}
ROLES_REQUIRING_EMPLOYER_SCOPE = {
    "employeur",
    "direction",
    "departement",
    "manager",
    "employe",
    "comptable",
    "juridique",
    "inspecteur",
    "recrutement",
}
ROLES_REQUIRING_WORKER_BINDING = {"manager", "departement", "employe"}
ROLE_ASSIGNMENT_MATRIX = {
    "admin": set(ENTERPRISE_ROLE_DEFINITIONS.keys()),
    "rh": {code for code, data in ENTERPRISE_ROLE_DEFINITIONS.items() if data["base_role_code"] != "admin"},
    "employeur": {
        code
        for code, data in ENTERPRISE_ROLE_DEFINITIONS.items()
        if data["base_role_code"] in {"direction", "departement", "manager", "employe", "comptable", "juridique", "inspecteur", "recrutement"}
    },
}

DEMO_LOGIN_PASSWORD = "Siirh2026"
DEMO_LOGIN_DOMAIN = "siirh.com"
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LEGACY_DEMO_USERNAMES = {
    "admin@siirh.com": ["admin"],
    "drh@siirh.com": ["drh"],
    "rh@siirh.com": ["rh"],
    "comptable@siirh.com": ["comptable", "paie"],
    "dg@siirh.com": ["pdg", "dg", "direction"],
    "inspecteur@siirh.com": ["inspecteur", "inspection_travail"],
    "manager@siirh.com": ["manager"],
}


def normalize_role_key(role_code: str) -> str:
    return (role_code or "").strip().lower()


def resolve_role_definition(role_code: str) -> Dict[str, str]:
    key = normalize_role_key(role_code)
    direct = ENTERPRISE_ROLE_DEFINITIONS.get(key)
    if direct:
        return {"code": key, **direct}
    alias_target = ROLE_CODE_ALIASES.get(key)
    if alias_target:
        target_def = ENTERPRISE_ROLE_DEFINITIONS.get(alias_target) or {}
        return {
            "code": key,
            "label": target_def.get("label", key),
            "scope": target_def.get("scope", "unknown"),
            "base_role_code": alias_target,
        }
    if key in ROLE_MODULE_MATRIX:
        role_entry = ROLE_MODULE_MATRIX[key]
        return {
            "code": key,
            "label": role_entry.get("label", key),
            "scope": role_entry.get("scope", "unknown"),
            "base_role_code": key,
        }
    return {"code": key, "label": key, "scope": "unknown", "base_role_code": key}


def normalize_role_code(role_code: str) -> str:
    return resolve_role_definition(role_code)["base_role_code"]


def _expand_compact_action(compact_action: str) -> set[str]:
    action = (compact_action or "").strip().lower()
    if action == "admin":
        return {"read", "create", "write", "validate", "approve", "close", "export", "print", "document", "delete", "admin"}
    if action == "write":
        return {"read", "create", "write", "validate", "approve", "close", "export", "print", "document", "delete"}
    if action == "read":
        return {"read"}
    return {action} if action else set()


def _compact_actions(granular_actions: set[str]) -> List[str]:
    compact: list[str] = []
    if "admin" in granular_actions:
        return ["read", "write", "admin"]
    if "read" in granular_actions:
        compact.append("read")
    if granular_actions.intersection(WRITE_EQUIVALENT_ACTIONS):
        if "read" not in compact:
            compact.append("read")
        compact.append("write")
    return compact


def _safe_query_role_activations(db: Session) -> dict[str, bool]:
    try:
        rows = (
            db.query(models.IamRoleActivation)
            .filter(models.IamRoleActivation.scope_key == ROLE_INSTALLATION_SCOPE)
            .all()
        )
        return {normalize_role_key(row.role_code): bool(row.is_enabled) for row in rows}
    except Exception:
        return {}


def is_role_enabled(db: Session, role_code: str) -> bool:
    key = normalize_role_key(role_code)
    activations = _safe_query_role_activations(db)
    if key in activations:
        return activations[key]
    try:
        role = db.query(models.IamRole).filter(models.IamRole.code == key).first()
        if role is not None:
            return bool(role.is_active)
    except Exception:
        pass
    return True


def get_role_module_permissions(db: Optional[Session], role_code: str) -> Dict[str, List[str]]:
    key = normalize_role_key(role_code)
    base_role_code = normalize_role_code(role_code)
    granular_by_module: dict[str, set[str]] = {}

    if db is not None:
        try:
            links = (
                db.query(models.IamRolePermission, models.IamPermission)
                .join(models.IamPermission, models.IamPermission.code == models.IamRolePermission.permission_code)
                .filter(
                    models.IamRolePermission.role_code == key,
                    models.IamRolePermission.is_granted.is_(True),
                )
                .all()
            )
            for link, permission in links:
                _ = link
                module = (permission.module or "").strip().lower()
                if not module:
                    continue
                if module not in granular_by_module:
                    granular_by_module[module] = set()
                granular_by_module[module].add((permission.action or "").strip().lower())
        except Exception:
            granular_by_module = {}

    role_entry = ROLE_MODULE_MATRIX.get(base_role_code, {})
    compact_modules = role_entry.get("modules", {})
    for module, compact_actions in compact_modules.items():
        if module not in granular_by_module:
            granular_by_module[module] = set()
        for action in compact_actions:
            granular_by_module[module].update(_expand_compact_action(action))

    override_modules = ENTERPRISE_ROLE_MODULE_OVERRIDES.get(key, {})
    for module, compact_actions in override_modules.items():
        if module not in granular_by_module:
            granular_by_module[module] = set()
        for action in compact_actions:
            granular_by_module[module].update(_expand_compact_action(action))

    compact_modules: dict[str, list[str]] = {}
    for module, actions in granular_by_module.items():
        compact_modules[module] = _compact_actions(actions)
    return compact_modules


def get_user_active_role_codes(db: Session, user: models.AppUser) -> List[str]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    role_codes: set[str] = set()
    primary_role = normalize_role_key(user.role_code)
    if primary_role and is_role_enabled(db, primary_role):
        role_codes.add(primary_role)

    try:
        assignments = (
            db.query(models.IamUserRole)
            .filter(models.IamUserRole.user_id == user.id, models.IamUserRole.is_active.is_(True))
            .all()
        )
        for assignment in assignments:
            if assignment.valid_from and assignment.valid_from > now:
                continue
            if assignment.valid_until and assignment.valid_until < now:
                continue
            role_code = normalize_role_key(assignment.role_code)
            if not role_code or not is_role_enabled(db, role_code):
                continue
            role_codes.add(role_code)
    except Exception:
        pass

    return sorted(role_codes)


def get_user_effective_base_roles(db: Session, user: models.AppUser) -> set[str]:
    return {normalize_role_code(code) for code in get_user_active_role_codes(db, user)}


def user_has_any_role(db: Session, user: models.AppUser, *roles: str) -> bool:
    allowed_raw = {normalize_role_key(role) for role in roles}
    allowed_effective = {normalize_role_code(role) for role in roles}
    for role_code in get_user_active_role_codes(db, user):
        if role_code in allowed_raw:
            return True
        if normalize_role_code(role_code) in allowed_effective:
            return True
    return False


def _resolve_effective_role_priority(role_codes: List[str]) -> str:
    priority = [
        "admin",
        "rh",
        "employeur",
        "comptable",
        "juridique",
        "direction",
        "departement",
        "manager",
        "inspecteur",
        "judge_readonly",
        "court_clerk_readonly",
        "audit",
        "recrutement",
        "employe",
    ]
    effective_roles = {normalize_role_code(role_code) for role_code in role_codes}
    for role in priority:
        if role in effective_roles:
            return role
    return normalize_role_code(role_codes[0]) if role_codes else "unknown"


def _apply_user_permission_overrides(
    db: Session,
    user: models.AppUser,
    granular_map: Dict[str, set[str]],
) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        overrides = (
            db.query(models.IamUserPermissionOverride, models.IamPermission)
            .join(models.IamPermission, models.IamPermission.code == models.IamUserPermissionOverride.permission_code)
            .filter(models.IamUserPermissionOverride.user_id == user.id)
            .all()
        )
        for override, permission in overrides:
            if override.expires_at and override.expires_at < now:
                continue
            module = (permission.module or "").strip().lower()
            action = (permission.action or "").strip().lower()
            if not module or not action:
                continue
            if module not in granular_map:
                granular_map[module] = set()
            if override.is_allowed:
                granular_map[module].add(action)
            else:
                granular_map[module].discard(action)
    except Exception:
        return


def build_user_access_profile_for_user(db: Session, user: models.AppUser) -> Dict[str, Any]:
    role_codes = get_user_active_role_codes(db, user)
    if not role_codes:
        role_codes = [normalize_role_key(user.role_code)]

    merged_granular: dict[str, set[str]] = {}
    for role_code in role_codes:
        modules = get_role_module_permissions(db, role_code)
        for module, actions in modules.items():
            if module not in merged_granular:
                merged_granular[module] = set()
            for action in actions:
                merged_granular[module].update(_expand_compact_action(action))

    _apply_user_permission_overrides(db, user, merged_granular)

    active_raw_roles = {normalize_role_key(role_code) for role_code in role_codes}
    for role_code, allowed_modules in STRICT_ROLE_MODULE_WHITELISTS.items():
        if role_code not in active_raw_roles:
            continue
        merged_granular = {
            module: actions
            for module, actions in merged_granular.items()
            if module in allowed_modules or module == "*"
        }

    compact_modules: dict[str, list[str]] = {}
    for module, actions in merged_granular.items():
        compact_modules[module] = _compact_actions(actions)

    effective_role_code = _resolve_effective_role_priority(role_codes)
    if len(role_codes) == 1:
        role_def = resolve_role_definition(role_codes[0])
        role_label = role_def.get("label", role_codes[0])
        role_scope = role_def.get("scope", "unknown")
    else:
        role_label = f"Profil compose ({len(role_codes)} roles)"
        role_scope = "composite"

    return {
        "effective_role_code": effective_role_code,
        "role_label": role_label,
        "role_scope": role_scope,
        "module_permissions": compact_modules,
        "assigned_role_codes": role_codes,
    }


def build_user_access_profile(role_code: str) -> Dict[str, Any]:
    normalized = normalize_role_code(role_code)
    entry = ROLE_MODULE_MATRIX.get(normalized, {})
    alias_profile = ALIAS_ROLE_PROFILES.get(normalize_role_key(role_code), {})
    return {
        "effective_role_code": normalized,
        "role_label": alias_profile.get("label") or entry.get("label", role_code),
        "role_scope": alias_profile.get("scope") or entry.get("scope", "unknown"),
        "module_permissions": entry.get("modules", {}),
        "assigned_role_codes": [normalize_role_key(role_code)] if role_code else [],
    }


def _list_role_catalog_fallback() -> List[Dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for role_code in sorted(ENTERPRISE_ROLE_DEFINITIONS.keys()):
        role_def = resolve_role_definition(role_code)
        modules = ROLE_MODULE_MATRIX.get(role_def["base_role_code"], {}).get("modules", {})
        rows.append(
            {
                "code": role_code,
                "label": role_def.get("label", role_code),
                "scope": role_def.get("scope", "unknown"),
                "base_role_code": role_def.get("base_role_code", normalize_role_code(role_code)),
                "modules": modules,
                "is_active": True,
            }
        )
    return rows


def list_role_catalog(db: Optional[Session] = None, include_inactive: bool = True) -> List[Dict[str, Any]]:
    if db is None:
        return _list_role_catalog_fallback()
    try:
        query = db.query(models.IamRole).order_by(models.IamRole.code.asc())
        if not include_inactive:
            query = query.filter(models.IamRole.is_active.is_(True))
        rows = query.all()
        if not rows:
            return _list_role_catalog_fallback()
        activations = _safe_query_role_activations(db)
        payload_map: dict[str, dict[str, Any]] = {}
        for row in rows:
            modules = get_role_module_permissions(db, row.code)
            payload_map[row.code] = {
                "code": row.code,
                "label": row.label,
                "scope": row.scope,
                "base_role_code": row.base_role_code,
                "modules": modules,
                "is_active": activations.get(normalize_role_key(row.code), bool(row.is_active)),
            }

        # Merge fallback definitions so newly declared enterprise roles are visible
        # immediately in the UI even if the IAM catalog was seeded before the code update.
        for fallback in _list_role_catalog_fallback():
            if fallback["code"] in payload_map:
                continue
            role_key = normalize_role_key(fallback["code"])
            if not include_inactive and activations.get(role_key) is False:
                continue
            payload_map[fallback["code"]] = {
                **fallback,
                "is_active": activations.get(role_key, bool(fallback.get("is_active", True))),
            }
        return [payload_map[key] for key in sorted(payload_map.keys())]
    except Exception:
        return _list_role_catalog_fallback()


def list_permission_catalog(db: Optional[Session] = None) -> List[Dict[str, Any]]:
    if db is not None:
        try:
            rows = db.query(models.IamPermission).order_by(models.IamPermission.module.asc(), models.IamPermission.action.asc()).all()
            if rows:
                return [
                    {
                        "code": row.code,
                        "module": row.module,
                        "action": row.action,
                        "label": row.label,
                        "sensitivity": row.sensitivity,
                    }
                    for row in rows
                ]
        except Exception:
            pass

    permissions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for role_def in ROLE_MODULE_MATRIX.values():
        for module, actions in role_def.get("modules", {}).items():
            for action in actions:
                for granular in _expand_compact_action(action):
                    code = f"{module}:{granular}"
                    if code in seen:
                        continue
                    seen.add(code)
                    permissions.append(
                        {
                            "code": code,
                            "module": module,
                            "action": granular,
                            "label": f"{module}.{granular}",
                            "sensitivity": "base",
                        }
                    )
    return sorted(permissions, key=lambda item: item["code"])


def can_assign_role(actor_role: str, target_role: str, db: Optional[Session] = None) -> bool:
    normalized_actor = normalize_role_code(actor_role)
    normalized_target_key = normalize_role_key(target_role)
    normalized_target = normalize_role_code(target_role)
    if db is not None and not is_role_enabled(db, normalized_target_key):
        return False
    if normalized_actor == "admin":
        return True
    if normalized_actor == "rh":
        return normalized_target != "admin"
    if normalized_actor == "employeur":
        return normalized_target in {"direction", "departement", "manager", "employe", "comptable", "juridique", "inspecteur", "recrutement"}
    allowed = ROLE_ASSIGNMENT_MATRIX.get(normalized_actor, set())
    return normalized_target_key in allowed or normalized_target in {normalize_role_code(code) for code in allowed}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return secrets.compare_digest(candidate, digest)


def create_session_token() -> str:
    return secrets.token_urlsafe(48)


def seed_iam_catalog(db: Session) -> None:
    try:
        _ = db.query(models.IamRole).limit(1).first()
    except Exception:
        return

    for role_code in sorted(ENTERPRISE_ROLE_DEFINITIONS.keys()):
        role_def = resolve_role_definition(role_code)
        row = db.query(models.IamRole).filter(models.IamRole.code == role_code).first()
        if row is None:
            row = models.IamRole(
                code=role_code,
                label=role_def["label"],
                description=f"Role systeme {role_def['label']}",
                scope=role_def["scope"],
                base_role_code=role_def["base_role_code"],
                is_system=True,
                is_active=True,
            )
            db.add(row)
        else:
            row.label = role_def["label"]
            row.scope = role_def["scope"]
            row.base_role_code = role_def["base_role_code"]

    permission_rows = list_permission_catalog(None)
    for item in permission_rows:
        exists = db.query(models.IamPermission).filter(models.IamPermission.code == item["code"]).first()
        if exists is None:
            db.add(
                models.IamPermission(
                    code=item["code"],
                    module=item["module"],
                    action=item["action"],
                    label=item["label"],
                    sensitivity=item["sensitivity"],
                )
            )

    db.flush()

    for role_code in sorted(ENTERPRISE_ROLE_DEFINITIONS.keys()):
        modules = get_role_module_permissions(None, role_code)
        emitted_permission_codes: set[str] = set()
        for module, actions in modules.items():
            for action in actions:
                granular_actions = _expand_compact_action(action)
                for granular in granular_actions:
                    permission_code = f"{module}:{granular}"
                    if permission_code in emitted_permission_codes:
                        continue
                    emitted_permission_codes.add(permission_code)
                    permission_exists = db.query(models.IamPermission.code).filter(models.IamPermission.code == permission_code).first()
                    if not permission_exists:
                        continue
                    existing_link = (
                        db.query(models.IamRolePermission.id)
                        .filter(
                            models.IamRolePermission.role_code == role_code,
                            models.IamRolePermission.permission_code == permission_code,
                        )
                        .first()
                    )
                    if existing_link:
                        continue
                    db.add(
                        models.IamRolePermission(
                            role_code=role_code,
                            permission_code=permission_code,
                            is_granted=True,
                        )
                    )

    for role_code in sorted(ENTERPRISE_ROLE_DEFINITIONS.keys()):
        activation = (
            db.query(models.IamRoleActivation)
            .filter(
                models.IamRoleActivation.scope_key == ROLE_INSTALLATION_SCOPE,
                models.IamRoleActivation.role_code == role_code,
            )
            .first()
        )
        if activation is None:
            db.add(
                models.IamRoleActivation(
                    scope_key=ROLE_INSTALLATION_SCOPE,
                    role_code=role_code,
                    is_enabled=True,
                )
            )

    db.commit()


def _is_valid_email(value: str) -> bool:
    return bool(EMAIL_REGEX.match((value or "").strip().lower()))


def _slug_for_email(value: str, fallback: str = "utilisateur") -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    compact = re.sub(r"[^a-z0-9]+", ".", ascii_value.lower()).strip(".")
    return compact or fallback


def _worker_demo_username(worker: models.Worker) -> str:
    existing_email = (worker.email or "").strip().lower()
    if _is_valid_email(existing_email):
        return existing_email
    first = _slug_for_email(worker.prenom or "")
    last = _slug_for_email(worker.nom or "")
    matricule = _slug_for_email(worker.matricule or str(worker.id), fallback=f"w{worker.id}")
    return f"{first}.{last}.{matricule}@{DEMO_LOGIN_DOMAIN}".replace("..", ".")


def _worker_full_name(worker: models.Worker) -> str:
    full = f"{worker.prenom or ''} {worker.nom or ''}".strip()
    return full or f"Salarie {worker.matricule or worker.id}"


def _is_legacy_demo_username(value: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"admin", "drh", "rh", "comptable", "paie", "pdg", "dg", "inspecteur", "manager", "agent"}:
        return True
    return normalized.endswith(f"@{DEMO_LOGIN_DOMAIN}")


def _upsert_demo_account(
    db: Session,
    *,
    username: str,
    role_code: str,
    full_name: str,
    employer_id: Optional[int] = None,
    worker: Optional[models.Worker] = None,
    legacy_usernames: Optional[list[str]] = None,
) -> dict[str, str]:
    normalized_username = (username or "").strip().lower()
    normalized_role = normalize_role_key(role_code)
    scoped_employer_id = worker.employer_id if worker is not None else employer_id
    scoped_worker_id = worker.id if worker is not None else None
    base_role_code = normalize_role_code(normalized_role)
    if base_role_code in ROLES_REQUIRING_EMPLOYER_SCOPE and scoped_employer_id is None:
        return {"status": "skipped", "username": normalized_username, "reason": "missing_employer_scope"}
    if base_role_code in ROLES_REQUIRING_WORKER_BINDING and scoped_worker_id is None:
        return {"status": "skipped", "username": normalized_username, "reason": "missing_worker_scope"}

    existing = db.query(models.AppUser).filter(models.AppUser.username == normalized_username).first()
    if existing is None and legacy_usernames:
        legacy_rows = (
            db.query(models.AppUser)
            .filter(models.AppUser.username.in_([(item or "").strip().lower() for item in legacy_usernames]))
            .order_by(models.AppUser.id.asc())
            .all()
        )
        if legacy_rows:
            existing = legacy_rows[0]

    if existing is None:
        db.add(
            models.AppUser(
                username=normalized_username,
                full_name=full_name,
                password_hash=hash_password(DEMO_LOGIN_PASSWORD),
                role_code=normalized_role,
                is_active=True,
                employer_id=scoped_employer_id,
                worker_id=scoped_worker_id,
            )
        )
        return {"status": "created", "username": normalized_username}

    # Migration legacy login -> email login when available.
    if existing.username != normalized_username:
        conflict = (
            db.query(models.AppUser.id)
            .filter(models.AppUser.username == normalized_username, models.AppUser.id != existing.id)
            .first()
        )
        if conflict is None:
            existing.username = normalized_username

    existing.full_name = full_name
    existing.password_hash = hash_password(DEMO_LOGIN_PASSWORD)
    existing.role_code = normalized_role
    existing.is_active = True
    existing.employer_id = scoped_employer_id
    existing.worker_id = scoped_worker_id
    return {"status": "updated", "username": existing.username}


def ensure_demo_accounts(db: Session, preferred_employer_id: Optional[int] = None) -> dict[str, Any]:
    selected_employer_id = preferred_employer_id
    if selected_employer_id is None:
        first_employer = db.query(models.Employer).order_by(models.Employer.id.asc()).first()
        selected_employer_id = first_employer.id if first_employer else None

    workers: list[models.Worker] = []
    if selected_employer_id is not None:
        workers = (
            db.query(models.Worker)
            .filter(models.Worker.employer_id == selected_employer_id)
            .order_by(models.Worker.id.asc())
            .all()
        )

    manager_worker = next((item for item in workers if item.organizational_unit_id is not None), workers[0] if workers else None)

    role_accounts = [
        ("admin@siirh.com", "admin", "Admin Systeme", None, None),
        ("drh@siirh.com", "drh", "DRH", None, None),
        ("rh@siirh.com", "rh", "Gestionnaire RH", None, None),
        ("comptable@siirh.com", "comptable", "Comptable Paie", selected_employer_id, None),
        ("dg@siirh.com", "dg", "Direction Generale", selected_employer_id, None),
        ("inspecteur@siirh.com", "inspecteur", "Inspecteur du Travail", selected_employer_id, None),
        ("manager@siirh.com", "manager", "Manager", selected_employer_id, manager_worker),
    ]

    created: list[str] = []
    updated: list[str] = []
    skipped: list[dict[str, str]] = []
    quick_accounts: list[dict[str, str]] = []

    for username, role_code, full_name, employer_id, worker in role_accounts:
        result = _upsert_demo_account(
            db,
            username=username,
            role_code=role_code,
            full_name=full_name,
            employer_id=employer_id,
            worker=worker,
            legacy_usernames=LEGACY_DEMO_USERNAMES.get(username),
        )
        status = result["status"]
        if status == "created":
            created.append(result["username"])
        elif status == "updated":
            updated.append(result["username"])
        else:
            skipped.append({"username": result["username"], "reason": result.get("reason", "skipped")})
        quick_accounts.append(
            {
                "label": full_name,
                "role_code": role_code,
                "username": result["username"],
            }
        )

    worker_accounts: list[dict[str, Any]] = []
    for worker in workers[:8]:
        desired_username = _worker_demo_username(worker)
        existing_candidates = (
            db.query(models.AppUser)
            .filter(models.AppUser.worker_id == worker.id)
            .order_by(models.AppUser.id.asc())
            .all()
        )
        existing = next(
            (item for item in existing_candidates if normalize_role_code(item.role_code) == "employe"),
            existing_candidates[0] if existing_candidates else None,
        )
        if existing is None:
            existing = (
                db.query(models.AppUser)
                .filter(models.AppUser.username == desired_username)
                .order_by(models.AppUser.id.asc())
                .first()
            )
        if existing is None:
            user = models.AppUser(
                username=desired_username,
                full_name=_worker_full_name(worker),
                password_hash=hash_password(DEMO_LOGIN_PASSWORD),
                role_code="salarie_agent",
                is_active=True,
                employer_id=worker.employer_id,
                worker_id=worker.id,
            )
            db.add(user)
            created.append(desired_username)
            worker_accounts.append(
                {
                    "worker_id": worker.id,
                    "matricule": worker.matricule,
                    "full_name": _worker_full_name(worker),
                    "username": desired_username,
                    "status": "created",
                }
            )
            continue

        if _is_legacy_demo_username(existing.username):
            conflict = (
                db.query(models.AppUser.id)
                .filter(models.AppUser.username == desired_username, models.AppUser.id != existing.id)
                .first()
            )
            if conflict is None:
                existing.username = desired_username
        existing.full_name = _worker_full_name(worker)
        existing.password_hash = hash_password(DEMO_LOGIN_PASSWORD)
        existing.is_active = True
        existing.employer_id = worker.employer_id
        if normalize_role_code(existing.role_code) == "employe" or _is_legacy_demo_username(existing.username):
            existing.role_code = normalize_role_key(existing.role_code or "salarie_agent") or "salarie_agent"
        updated.append(existing.username)
        worker_accounts.append(
            {
                "worker_id": worker.id,
                "matricule": worker.matricule,
                "full_name": _worker_full_name(worker),
                "username": existing.username,
                "status": "updated",
            }
        )

    agent_account = next((item for item in worker_accounts if item.get("username")), None)
    if agent_account is not None:
        quick_accounts.append(
            {
                "label": "Agent salarie",
                "role_code": "salarie_agent",
                "username": str(agent_account["username"]),
            }
        )

    legacy_aliases = {"agent"}
    for aliases in LEGACY_DEMO_USERNAMES.values():
        legacy_aliases.update((item or "").strip().lower() for item in aliases if item)
    for legacy_username in sorted(alias for alias in legacy_aliases if alias and "@" not in alias):
        legacy_user = db.query(models.AppUser).filter(models.AppUser.username == legacy_username).first()
        if not legacy_user:
            continue
        replacement = f"legacy.{_slug_for_email(legacy_username, fallback='user')}.{legacy_user.id}@{DEMO_LOGIN_DOMAIN}"
        conflict = (
            db.query(models.AppUser.id)
            .filter(models.AppUser.username == replacement, models.AppUser.id != legacy_user.id)
            .first()
        )
        if conflict is None:
            legacy_user.username = replacement
        legacy_user.is_active = False
        updated.append(legacy_user.username)

    db.flush()
    return {
        "employer_id": selected_employer_id,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "quick_accounts": quick_accounts,
        "worker_accounts": worker_accounts,
    }


def seed_default_admin(db: Session):
    seed_iam_catalog(db)
    default_username = settings.DEFAULT_ADMIN_USERNAME.strip().lower()
    admin = db.query(models.AppUser).filter(models.AppUser.username == default_username).first()
    if admin is None:
        legacy_admin = db.query(models.AppUser).filter(models.AppUser.username == "admin").first()
        if legacy_admin is not None:
            conflict = (
                db.query(models.AppUser.id)
                .filter(models.AppUser.username == default_username, models.AppUser.id != legacy_admin.id)
                .first()
            )
            if conflict is None:
                legacy_admin.username = default_username
            admin = legacy_admin
        else:
            admin = models.AppUser(
                username=default_username,
                full_name="System Administrator",
                password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role_code="admin",
                is_active=True,
            )
            db.add(admin)

    if admin is not None:
        admin.role_code = "admin"
        admin.is_active = True
        admin.password_hash = hash_password(settings.DEFAULT_ADMIN_PASSWORD)

    ensure_demo_accounts(db)
    db.commit()


def _get_manager_unit_id(db: Session, user: models.AppUser) -> Optional[int]:
    if not user.worker_id:
        return None
    worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
    return worker.organizational_unit_id if worker else None


def _is_same_or_descendant_unit(db: Session, target_unit_id: Optional[int], ancestor_unit_id: Optional[int]) -> bool:
    if not target_unit_id or not ancestor_unit_id:
        return False
    if target_unit_id == ancestor_unit_id:
        return True
    current = db.query(models.OrganizationalUnit).filter(models.OrganizationalUnit.id == target_unit_id).first()
    visited: set[int] = set()
    while current and current.parent_id and current.id not in visited:
        visited.add(current.id)
        if current.parent_id == ancestor_unit_id:
            return True
        current = current.parent
    return False


def resolve_user_employer_id(db: Session, user: models.AppUser) -> Optional[int]:
    if user.employer_id:
        return user.employer_id
    if not user.worker_id:
        return None
    worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
    return worker.employer_id if worker else None


def get_inspector_assigned_employer_ids(db: Session, user: models.AppUser) -> set[int]:
    employer_ids: set[int] = set()
    if user.employer_id:
        employer_ids.add(user.employer_id)

    assignment_rows = (
        db.query(models.LabourInspectorAssignment.employer_id)
        .filter(
            models.LabourInspectorAssignment.inspector_user_id == user.id,
            models.LabourInspectorAssignment.status == "active",
        )
        .all()
    )
    employer_ids.update(employer_id for (employer_id,) in assignment_rows if employer_id is not None)

    case_rows = (
        db.query(models.InspectorCase.employer_id)
        .filter(models.InspectorCase.assigned_inspector_user_id == user.id)
        .all()
    )
    employer_ids.update(employer_id for (employer_id,) in case_rows if employer_id is not None)

    backup_case_rows = (
        db.query(models.InspectorCase.employer_id)
        .join(models.InspectorCaseAssignment, models.InspectorCaseAssignment.case_id == models.InspectorCase.id)
        .filter(
            models.InspectorCaseAssignment.inspector_user_id == user.id,
            models.InspectorCaseAssignment.status == "active",
        )
        .all()
    )
    employer_ids.update(employer_id for (employer_id,) in backup_case_rows if employer_id is not None)
    return employer_ids


def can_access_employer(db: Session, user: models.AppUser, employer_id: int) -> bool:
    effective_roles = get_user_effective_base_roles(db, user)
    if effective_roles.intersection({"admin", "rh", "comptable", "audit"}):
        return True
    if effective_roles.intersection({"employeur", "direction", "juridique", "recrutement"}):
        return bool(user.employer_id and user.employer_id == employer_id)
    if "inspecteur" in effective_roles:
        return employer_id in get_inspector_assigned_employer_ids(db, user)
    if effective_roles.intersection({"manager", "departement", "employe"}):
        return resolve_user_employer_id(db, user) == employer_id
    return False


def has_module_access(role_code: str, module: str, action: str = "read") -> bool:
    normalized_role = normalize_role_code(role_code)
    entry = ROLE_MODULE_MATRIX.get(normalized_role)
    if not entry:
        return False
    modules = entry.get("modules", {})
    if "*" in modules:
        return action in modules["*"]
    allowed = modules.get(module, [])
    return action in allowed


def has_module_access_for_user(db: Session, user: models.AppUser, module: str, action: str = "read") -> bool:
    profile = build_user_access_profile_for_user(db, user)
    permissions = profile.get("module_permissions", {})
    global_actions = set(permissions.get("*", []))
    if "admin" in global_actions or action in global_actions:
        return True
    module_actions = set(permissions.get(module, []))
    if "admin" in module_actions:
        return True
    return action in module_actions


def _infer_module_guard_from_request(request: Optional[Request]) -> Optional[tuple[str, str]]:
    if request is None:
        return None
    path = (request.url.path or "").strip().lower().rstrip("/")
    method = (request.method or "").strip().upper()
    if not path:
        return None

    if path.startswith("/document-templates/") and "/apply/" in path:
        return "contracts", "read"

    for prefix, module, explicit_action in REQUEST_MODULE_RULES:
        normalized_prefix = prefix.lower().rstrip("/")
        if not normalized_prefix:
            continue
        if path == normalized_prefix or path.startswith(f"{normalized_prefix}/"):
            if explicit_action:
                return module, explicit_action
            inferred_action = "read" if method in READ_METHODS else "write"
            return module, inferred_action
    return None


def can_access_worker(db: Session, user: models.AppUser, worker: models.Worker) -> bool:
    effective_roles = get_user_effective_base_roles(db, user)
    if effective_roles.intersection({"admin", "rh", "comptable", "audit"}):
        return True
    if effective_roles.intersection({"employeur", "direction", "juridique", "recrutement"}):
        return bool(user.employer_id and user.employer_id == worker.employer_id)
    if "inspecteur" in effective_roles:
        return worker.employer_id in get_inspector_assigned_employer_ids(db, user)
    if "employe" in effective_roles and user.worker_id == worker.id:
        return True
    if effective_roles.intersection({"manager", "departement"}):
        manager_unit_id = _get_manager_unit_id(db, user)
        return _is_same_or_descendant_unit(db, worker.organizational_unit_id, manager_unit_id)
    return False


def can_manage_worker(db: Session, user: models.AppUser, worker: Optional[models.Worker] = None, employer_id: Optional[int] = None) -> bool:
    target_employer_id = employer_id or (worker.employer_id if worker else None)
    effective_roles = get_user_effective_base_roles(db, user)
    if effective_roles.intersection({"admin", "rh"}):
        return True
    if "employeur" in effective_roles and user.employer_id and target_employer_id:
        return user.employer_id == target_employer_id
    if "inspecteur" in effective_roles and target_employer_id:
        return target_employer_id in get_inspector_assigned_employer_ids(db, user)
    return False


def get_current_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> models.AppUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token = authorization.split(" ", 1)[1].strip()
    session = db.query(models.AuthSession).filter(
        models.AuthSession.token == token,
        models.AuthSession.revoked_at.is_(None),
        models.AuthSession.expires_at >= datetime.now(timezone.utc),
    ).first()

    if not session or not session.user or not session.user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    session.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return session.user


def require_roles(*roles: str) -> Callable:
    def dependency(
        user: models.AppUser = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None,
    ) -> models.AppUser:
        if not user_has_any_role(db, user, *roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        guard = _infer_module_guard_from_request(request)
        if guard:
            module, action = guard
            if not has_module_access_for_user(db, user, module, action):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency


def require_module_access(module: str, action: str = "read") -> Callable:
    def dependency(
        user: models.AppUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> models.AppUser:
        if not has_module_access_for_user(db, user, module, action):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency


def create_session_for_user(db: Session, user: models.AppUser) -> str:
    token = create_session_token()
    session = models.AuthSession(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=12),
    )
    db.add(session)
    db.commit()
    return token
