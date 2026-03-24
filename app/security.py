from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from . import models
from .config.config import get_db, settings


READ_PAYROLL_ROLES = {"admin", "rh", "comptable", "employeur", "direction", "manager", "departement", "employe"}
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
            "time_absence": ["read", "write"],
            "payroll": ["read", "write"],
            "declarations": ["read", "write"],
            "talents": ["read", "write"],
            "sst": ["read", "write"],
            "reporting": ["read", "write"],
            "compliance": ["read", "write"],
        },
    },
    "employeur": {
        "label": "Direction employeur",
        "scope": "company",
        "modules": {
            "recruitment": ["read", "write"],
            "contracts": ["read", "write"],
            "workforce": ["read", "write"],
            "time_absence": ["read", "write"],
            "payroll": ["read", "write"],
            "declarations": ["read", "write"],
            "talents": ["read", "write"],
            "sst": ["read", "write"],
            "reporting": ["read", "write"],
            "compliance": ["read", "write"],
        },
    },
    "direction": {
        "label": "Direction",
        "scope": "company",
        "modules": {
            "recruitment": ["read"],
            "contracts": ["read"],
            "workforce": ["read"],
            "time_absence": ["read"],
            "payroll": ["read"],
            "declarations": ["read"],
            "talents": ["read"],
            "sst": ["read"],
            "reporting": ["read"],
            "compliance": ["read", "write"],
        },
    },
    "departement": {
        "label": "Responsable departement",
        "scope": "organizational_unit",
        "modules": {
            "recruitment": ["read"],
            "contracts": ["read"],
            "workforce": ["read"],
            "time_absence": ["read", "write"],
            "payroll": ["read"],
            "talents": ["read"],
            "sst": ["read"],
            "reporting": ["read"],
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
        },
    },
    "employe": {
        "label": "Employe",
        "scope": "self",
        "modules": {
            "employee_portal": ["read", "write"],
            "time_absence": ["read", "write"],
            "documents": ["read"],
        },
    },
    "comptable": {
        "label": "Comptabilite paie",
        "scope": "company",
        "modules": {
            "payroll": ["read", "write"],
            "declarations": ["read", "write"],
            "reporting": ["read", "write"],
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
        },
    },
    "inspecteur": {
        "label": "Inspection du travail",
        "scope": "assigned_case_or_company",
        "modules": {
            "compliance": ["read", "write"],
            "employee_portal": ["read", "write"],
            "reporting": ["read"],
            "declarations": ["read"],
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
        },
    },
    "recrutement": {
        "label": "Charge recrutement",
        "scope": "company",
        "modules": {
            "recruitment": ["read", "write"],
            "workforce": ["read"],
            "talents": ["read"],
        },
    },
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
    "admin": set(ROLE_MODULE_MATRIX.keys()),
    "rh": {code for code in ROLE_MODULE_MATRIX.keys() if code != "admin"},
    "employeur": {"direction", "departement", "manager", "employe", "comptable", "juridique", "inspecteur", "recrutement"},
}


def list_role_catalog() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for role_code in sorted(ROLE_MODULE_MATRIX.keys()):
        role_entry = ROLE_MODULE_MATRIX[role_code]
        rows.append(
            {
                "code": role_code,
                "label": role_entry.get("label", role_code),
                "scope": role_entry.get("scope", "unknown"),
                "modules": role_entry.get("modules", {}),
            }
        )
    return rows


def can_assign_role(actor_role: str, target_role: str) -> bool:
    allowed = ROLE_ASSIGNMENT_MATRIX.get(actor_role, set())
    return target_role in allowed


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


def seed_default_admin(db: Session):
    existing = db.query(models.AppUser).count()
    if existing:
        return

    admin = models.AppUser(
        username=settings.DEFAULT_ADMIN_USERNAME,
        full_name="System Administrator",
        password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        role_code="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()


def _get_manager_unit_id(db: Session, user: models.AppUser) -> Optional[int]:
    if not user.worker_id:
        return None
    worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
    return worker.organizational_unit_id if worker else None


def resolve_user_employer_id(db: Session, user: models.AppUser) -> Optional[int]:
    if user.employer_id:
        return user.employer_id
    if not user.worker_id:
        return None
    worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
    return worker.employer_id if worker else None


def can_access_employer(db: Session, user: models.AppUser, employer_id: int) -> bool:
    if user.role_code in {"admin", "rh", "comptable", "audit"}:
        return True
    if user.role_code in {"employeur", "direction", "juridique", "recrutement"}:
        return bool(user.employer_id and user.employer_id == employer_id)
    if user.role_code == "inspecteur":
        return bool(user.employer_id and user.employer_id == employer_id)
    if user.role_code in {"manager", "departement", "employe"}:
        return resolve_user_employer_id(db, user) == employer_id
    return False


def has_module_access(role_code: str, module: str, action: str = "read") -> bool:
    entry = ROLE_MODULE_MATRIX.get(role_code)
    if not entry:
        return False
    modules = entry.get("modules", {})
    if "*" in modules:
        return action in modules["*"]
    allowed = modules.get(module, [])
    return action in allowed


def can_access_worker(db: Session, user: models.AppUser, worker: models.Worker) -> bool:
    if user.role_code in {"admin", "rh", "comptable", "audit"}:
        return True
    if user.role_code in {"employeur", "direction", "juridique", "recrutement"}:
        return bool(user.employer_id and user.employer_id == worker.employer_id)
    if user.role_code == "inspecteur":
        return bool(user.employer_id and user.employer_id == worker.employer_id)
    if user.role_code == "employe":
        return user.worker_id == worker.id
    if user.role_code in {"manager", "departement"}:
        manager_unit_id = _get_manager_unit_id(db, user)
        return bool(manager_unit_id and manager_unit_id == worker.organizational_unit_id)
    return False


def can_manage_worker(db: Session, user: models.AppUser, worker: Optional[models.Worker] = None, employer_id: Optional[int] = None) -> bool:
    target_employer_id = employer_id or (worker.employer_id if worker else None)
    if user.role_code in {"admin", "rh"}:
        return True
    if user.role_code == "employeur" and user.employer_id and target_employer_id:
        return user.employer_id == target_employer_id
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
        models.AuthSession.expires_at >= datetime.utcnow(),
    ).first()

    if not session or not session.user or not session.user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    session.last_seen_at = datetime.utcnow()
    db.commit()
    return session.user


def require_roles(*roles: str) -> Callable:
    allowed = set(roles)

    def dependency(user: models.AppUser = Depends(get_current_user)) -> models.AppUser:
        if user.role_code not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency


def create_session_for_user(db: Session, user: models.AppUser) -> str:
    token = create_session_token()
    session = models.AuthSession(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=12),
    )
    db.add(session)
    db.commit()
    return token
