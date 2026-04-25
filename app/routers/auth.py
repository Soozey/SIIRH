import re
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db, settings
from ..security import (
    ROLE_ASSIGNMENT_MATRIX,
    ROLE_MODULE_MATRIX,
    ROLES_REQUIRING_EMPLOYER_SCOPE,
    ROLES_REQUIRING_WORKER_BINDING,
    USER_ADMIN_ROLES,
    ensure_demo_accounts,
    build_user_access_profile_for_user,
    can_assign_role,
    create_session_for_user,
    get_current_user,
    get_user_active_role_codes,
    get_role_module_permissions,
    is_role_enabled,
    hash_password,
    list_role_catalog,
    list_permission_catalog,
    normalize_role_code,
    normalize_role_key,
    require_roles,
    resolve_user_employer_id,
    user_has_any_role,
    verify_password,
)
from ..services.audit_service import record_audit
from ..services.legal_operations_service import seed_legal_demo_data


router = APIRouter(prefix="/auth", tags=["auth"])


PUBLIC_REGISTRATION_ALLOWED_ROLES = {
    "salarie_agent",
    "salarie_periode_essai",
    "travailleur_journalier",
    "travailleur_saisonnier",
    "travailleur_temps_partiel",
    "travailleur_porte",
    "interimaire",
    "ancien_salarie",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ACCOUNT_PENDING = "PENDING_APPROVAL"
ACCOUNT_ACTIVE = "ACTIVE"
ACCOUNT_SUSPENDED = "SUSPENDED"
ACCOUNT_REJECTED = "REJECTED"
ACCOUNT_PASSWORD_RESET_REQUIRED = "PASSWORD_RESET_REQUIRED"
ACCOUNT_STATUSES = {
    ACCOUNT_PENDING,
    ACCOUNT_ACTIVE,
    ACCOUNT_SUSPENDED,
    ACCOUNT_REJECTED,
    ACCOUNT_PASSWORD_RESET_REQUIRED,
}


def _json_object(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _now() -> datetime:
    return datetime.utcnow()


def _normalize_account_status(value: Optional[str], is_active: bool = True) -> str:
    status_value = (value or "").strip().upper()
    if not status_value:
        return ACCOUNT_ACTIVE if is_active else ACCOUNT_SUSPENDED
    if status_value not in ACCOUNT_STATUSES:
        raise HTTPException(status_code=400, detail="Statut de compte invalide")
    return status_value


def _apply_account_status(target: models.AppUser, status_value: str, actor: Optional[models.AppUser] = None) -> None:
    normalized = _normalize_account_status(status_value, bool(target.is_active))
    target.account_status = normalized
    if normalized == ACCOUNT_ACTIVE:
        target.is_active = True
        target.must_change_password = False
        target.approved_at = target.approved_at or _now()
        target.approved_by = target.approved_by or (actor.id if actor else None)
    elif normalized == ACCOUNT_PASSWORD_RESET_REQUIRED:
        target.is_active = True
        target.must_change_password = True
        target.approved_at = target.approved_at or _now()
        target.approved_by = target.approved_by or (actor.id if actor else None)
    elif normalized == ACCOUNT_PENDING:
        target.is_active = False
        target.must_change_password = False
    elif normalized == ACCOUNT_REJECTED:
        target.is_active = False
        target.must_change_password = False
        target.rejected_at = _now()
        target.rejected_by = actor.id if actor else target.rejected_by
    elif normalized == ACCOUNT_SUSPENDED:
        target.is_active = False
        target.must_change_password = False


def _revoke_user_sessions(db: Session, user_id: int) -> None:
    db.query(models.AuthSession).filter(
        models.AuthSession.user_id == user_id,
        models.AuthSession.revoked_at.is_(None),
    ).update({"revoked_at": models.func.now()}, synchronize_session=False)


def _session_out(token: str, user: models.AppUser, access_profile: dict) -> schemas.UserSessionOut:
    return schemas.UserSessionOut(
        token=token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role_code=user.role_code,
        employer_id=user.employer_id,
        worker_id=user.worker_id,
        effective_role_code=access_profile["effective_role_code"],
        role_label=access_profile["role_label"],
        role_scope=access_profile["role_scope"],
        module_permissions=access_profile["module_permissions"],
        assigned_role_codes=access_profile["assigned_role_codes"],
        account_status=_normalize_account_status(getattr(user, "account_status", None), bool(user.is_active)),
        must_change_password=bool(getattr(user, "must_change_password", False)),
    )


@router.post("/login", response_model=schemas.UserSessionOut)
def login(payload: schemas.UserLoginIn, db: Session = Depends(get_db)):
    username = payload.username.strip()
    normalized_username = username.lower() if "@" in username else username
    user = db.query(models.AppUser).filter(models.AppUser.username == normalized_username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    account_status = _normalize_account_status(getattr(user, "account_status", None), bool(user.is_active))
    if account_status == ACCOUNT_PENDING:
        raise HTTPException(status_code=403, detail="Compte en attente de validation administrateur")
    if account_status == ACCOUNT_REJECTED:
        raise HTTPException(status_code=403, detail="Compte refusé par l'administrateur")
    if account_status == ACCOUNT_SUSPENDED or not user.is_active:
        raise HTTPException(status_code=403, detail="Compte suspendu ou inactif")

    token = create_session_for_user(db, user)
    user.last_login_at = _now()
    db.commit()
    access_profile = build_user_access_profile_for_user(db, user)
    return _session_out(token, user, access_profile)


@router.get("/me", response_model=schemas.UserSessionOut)
def me(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    access_profile = build_user_access_profile_for_user(db, user)
    return _session_out("", user, access_profile)


@router.get("/access-profile", response_model=schemas.UserAccessProfileOut)
def get_access_profile(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    access_profile = build_user_access_profile_for_user(db, user)
    return schemas.UserAccessProfileOut(
        role_code=user.role_code,
        effective_role_code=access_profile["effective_role_code"],
        role_label=access_profile["role_label"],
        role_scope=access_profile["role_scope"],
        module_permissions=access_profile["module_permissions"],
        assigned_role_codes=access_profile["assigned_role_codes"],
    )


def _resolve_scope(
    db: Session,
    role_code: str,
    employer_id: Optional[int],
    worker_id: Optional[int],
) -> tuple[Optional[int], Optional[int]]:
    effective_role_code = normalize_role_code(role_code)
    if effective_role_code not in ROLE_MODULE_MATRIX:
        raise HTTPException(status_code=400, detail="Unknown role_code")

    worker = None
    if worker_id is not None:
        worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        if employer_id is None:
            employer_id = worker.employer_id
        elif employer_id != worker.employer_id:
            raise HTTPException(status_code=400, detail="Worker and employer mismatch")

    if effective_role_code in ROLES_REQUIRING_WORKER_BINDING and worker_id is None:
        raise HTTPException(status_code=400, detail=f"role '{role_code}' requires worker_id")

    if effective_role_code in ROLES_REQUIRING_EMPLOYER_SCOPE and employer_id is None:
        raise HTTPException(status_code=400, detail=f"role '{role_code}' requires employer_id")

    if employer_id is not None:
        employer_exists = db.query(models.Employer.id).filter(models.Employer.id == employer_id).first()
        if not employer_exists:
            raise HTTPException(status_code=404, detail="Employer not found")

    return employer_id, worker_id


def _can_actor_assign_role(db: Session, actor: models.AppUser, target_role: str) -> bool:
    actor_roles = get_user_active_role_codes(db, actor)
    for role_code in actor_roles:
        if can_assign_role(role_code, target_role, db):
            return True
    return False


def _ensure_admin_scope(db: Session, actor: models.AppUser, target_employer_id: Optional[int], target_role: str) -> None:
    if not _can_actor_assign_role(db, actor, target_role):
        raise HTTPException(status_code=403, detail="Role assignment forbidden")

    if user_has_any_role(db, actor, "admin", "rh"):
        return

    if not user_has_any_role(db, actor, "employeur"):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not actor.employer_id:
        raise HTTPException(status_code=403, detail="No employer scope on actor")

    if target_employer_id != actor.employer_id:
        raise HTTPException(status_code=403, detail="Cannot manage users outside own employer")


def _can_view_user(db: Session, actor: models.AppUser, target: models.AppUser) -> bool:
    if user_has_any_role(db, actor, "admin"):
        return True
    if user_has_any_role(db, actor, "rh"):
        return not user_has_any_role(db, target, "admin")
    if not user_has_any_role(db, actor, "employeur"):
        return actor.id == target.id
    target_employer_id = resolve_user_employer_id(db, target)
    return bool(actor.employer_id and target_employer_id == actor.employer_id)


@router.get("/roles", response_model=list[schemas.RoleCatalogItemOut])
def get_roles(
    assignable_only: bool = Query(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    roles = list_role_catalog(db)
    if assignable_only:
        return [role for role in roles if _can_actor_assign_role(db, user, role["code"])]
    return roles


@router.get("/public-roles", response_model=list[schemas.RoleCatalogPublicItemOut])
def get_public_roles(
    db: Session = Depends(get_db),
):
    rows = list_role_catalog(db, include_inactive=True)
    return [
        schemas.RoleCatalogPublicItemOut(
            code=item["code"],
            label=item["label"],
            scope=item["scope"],
            base_role_code=item.get("base_role_code"),
            is_active=bool(item.get("is_active", True)),
        )
        for item in rows
    ]


def _validate_registration_password(password: str) -> None:
    candidate = password or ""
    if len(candidate) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères")
    checks = [
        any(char.isupper() for char in candidate),
        any(char.islower() for char in candidate),
        any(char.isdigit() for char in candidate),
    ]
    if not all(checks):
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe doit contenir une majuscule, une minuscule et un chiffre",
        )


@router.get("/public-registration-config", response_model=schemas.PublicRegistrationConfigOut)
def get_public_registration_config(
    db: Session = Depends(get_db),
):
    catalog = {
        item["code"]: item
        for item in list_role_catalog(db, include_inactive=False)
        if item["code"] in PUBLIC_REGISTRATION_ALLOWED_ROLES
    }
    roles = [
        schemas.PublicRegistrationRoleOut(
            code=code,
            label=catalog[code]["label"],
            scope=catalog[code]["scope"],
        )
        for code in sorted(catalog.keys())
    ]
    return schemas.PublicRegistrationConfigOut(
        enabled=settings.AUTH_PUBLIC_REGISTRATION_ENABLED,
        password_policy="Min 8 caracteres, avec majuscule, minuscule et chiffre.",
        allowed_roles=roles,
    )


@router.get("/demo-accounts", response_model=list[schemas.PublicDemoAccountOut])
def get_public_demo_accounts(
    db: Session = Depends(get_db),
):
    demo_sync = ensure_demo_accounts(db)
    seed_legal_demo_data(db)
    db.commit()
    display_labels = {
        "admin": "Administrateur système",
        "employer_admin": "Administrateur employeur",
        "hr_manager": "Responsable RH",
        "hr_officer": "Chargé RH",
        "employee": "Employé",
        "labor_inspector": "Inspecteur du travail",
        "labor_inspector_supervisor": "Inspecteur principal",
        "staff_delegate": "Délégué du personnel",
        "works_council_member": "Comité d’entreprise",
        "judge_readonly": "Juge",
        "court_clerk_readonly": "Greffier",
        "auditor_readonly": "Auditeur",
        "inspecteur": "Inspecteur (alias actif)",
    }
    accounts = [
        schemas.PublicDemoAccountOut(
            label=display_labels.get(str(item["role_code"]).strip().lower(), str(item["label"])),
            role_code=str(item["role_code"]),
            username=str(item["username"]),
        )
        for item in demo_sync["quick_accounts"]
        if str(item.get("username", "")).strip()
    ]
    preferred_role_order = [
        "admin",
        "employer_admin",
        "hr_manager",
        "hr_officer",
        "employee",
        "labor_inspector",
        "labor_inspector_supervisor",
        "staff_delegate",
        "works_council_member",
        "judge_readonly",
        "court_clerk_readonly",
        "auditor_readonly",
        "inspecteur",
    ]
    legal_demo_rows = (
        db.query(models.AppUser)
        .filter(models.AppUser.role_code.in_(preferred_role_order), models.AppUser.is_active.is_(True))
        .order_by(models.AppUser.role_code.asc(), models.AppUser.username.asc())
        .all()
    )
    emitted_role_codes = {item.role_code.strip().lower() for item in accounts}
    for role_code in preferred_role_order:
        if role_code in emitted_role_codes:
            continue
        row = next((item for item in legal_demo_rows if (item.role_code or "").strip().lower() == role_code), None)
        if row is None:
            continue
        accounts.append(
            schemas.PublicDemoAccountOut(
                label=display_labels.get(role_code, role_code.replace("_", " ")),
                role_code=role_code,
                username=row.username,
            )
        )
    deduped: dict[str, schemas.PublicDemoAccountOut] = {}
    for item in accounts:
        deduped[item.username.lower()] = item
    return list(deduped.values())


@router.post("/register", response_model=schemas.PublicRegisterOut, status_code=201)
def register_public_user(
    payload: schemas.PublicRegisterIn,
    db: Session = Depends(get_db),
):
    if not settings.AUTH_PUBLIC_REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail="L'inscription publique est désactivée")

    username = payload.username.strip().lower()
    if not EMAIL_RE.match(username):
        raise HTTPException(status_code=400, detail="L'identifiant doit être une adresse email valide")
    if db.query(models.AppUser.id).filter(models.AppUser.username == username).first():
        raise HTTPException(status_code=409, detail="Cette adresse email existe déjà")

    _validate_registration_password(payload.password)

    role_code = normalize_role_key(payload.role_code or "salarie_agent")
    if role_code not in PUBLIC_REGISTRATION_ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Rôle non autorisé pour l'inscription publique")
    if not is_role_enabled(db, role_code):
        raise HTTPException(status_code=400, detail="Ce rôle est désactivé pour cette installation")

    matricule = payload.worker_matricule.strip()
    worker = db.query(models.Worker).filter(models.Worker.matricule == matricule).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Matricule introuvable")
    existing_worker_user = (
        db.query(models.AppUser)
        .filter(models.AppUser.worker_id == worker.id)
        .order_by(models.AppUser.id.asc())
        .first()
    )
    if existing_worker_user:
        raise HTTPException(status_code=409, detail="Un compte est déjà lié à ce salarié")

    full_name = payload.full_name.strip() if payload.full_name else ""
    if not full_name:
        full_name = " ".join(part for part in [worker.prenom, worker.nom] if part).strip() or username.split("@")[0]

    user_obj = models.AppUser(
        username=username,
        full_name=full_name,
        password_hash=hash_password(payload.password),
        role_code=role_code,
        is_active=False,
        account_status=ACCOUNT_PENDING,
        must_change_password=False,
        employer_id=worker.employer_id,
        worker_id=worker.id,
    )
    db.add(user_obj)
    db.flush()
    record_audit(
        db,
        actor=None,
        action="auth.public_register",
        entity_type="app_user",
        entity_id=user_obj.id,
        route="/auth/register",
        employer_id=user_obj.employer_id,
        worker_id=user_obj.worker_id,
        after={
            "username": user_obj.username,
            "role_code": user_obj.role_code,
            "account_status": user_obj.account_status,
            "worker_matricule": worker.matricule,
        },
    )
    db.commit()
    db.refresh(user_obj)
    return schemas.PublicRegisterOut(
        user_id=user_obj.id,
        username=user_obj.username,
        full_name=user_obj.full_name,
        role_code=user_obj.role_code,
        account_status=user_obj.account_status,
        employer_id=user_obj.employer_id,
        worker_id=user_obj.worker_id or worker.id,
        created_at=user_obj.created_at,
    )


@router.get("/users", response_model=list[schemas.AppUserOut])
def list_users(
    employer_id: Optional[int] = Query(None),
    role_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    if employer_id is not None and user_has_any_role(db, user, "employeur") and employer_id != user.employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rows = db.query(models.AppUser).order_by(models.AppUser.username.asc()).all()
    out = []
    for row in rows:
        if not _can_view_user(db, user, row):
            continue
        resolved_employer_id = resolve_user_employer_id(db, row)
        if employer_id is not None and resolved_employer_id != employer_id:
            continue
        if role_code and not user_has_any_role(db, row, role_code):
            continue
        out.append(row)
    return out


@router.post("/users", response_model=schemas.AppUserOut)
def create_user(
    payload: schemas.AppUserCreateIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    normalized_username = payload.username.strip()
    if not normalized_username:
        raise HTTPException(status_code=400, detail="Le nom d'utilisateur est obligatoire")
    if db.query(models.AppUser.id).filter(models.AppUser.username == normalized_username).first():
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur existe déjà")

    normalized_role_code = normalize_role_key(payload.role_code)
    if not is_role_enabled(db, normalized_role_code):
        raise HTTPException(status_code=400, detail="Role is disabled for this installation")
    employer_id, worker_id = _resolve_scope(
        db,
        role_code=normalized_role_code,
        employer_id=payload.employer_id,
        worker_id=payload.worker_id,
    )
    _ensure_admin_scope(db, user, employer_id, normalized_role_code)
    requested_status = payload.account_status
    if not requested_status:
        requested_status = ACCOUNT_PASSWORD_RESET_REQUIRED if payload.must_change_password else (ACCOUNT_ACTIVE if payload.is_active else ACCOUNT_SUSPENDED)
    normalized_status = _normalize_account_status(requested_status, payload.is_active)

    obj = models.AppUser(
        username=normalized_username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_code=normalized_role_code,
        is_active=payload.is_active,
        account_status=normalized_status,
        must_change_password=payload.must_change_password,
        employer_id=employer_id,
        worker_id=worker_id,
    )
    _apply_account_status(obj, normalized_status, user)
    db.add(obj)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="auth.user.create",
        entity_type="app_user",
        entity_id=obj.id,
        route="/auth/users",
        employer_id=obj.employer_id,
        worker_id=obj.worker_id,
        after={
            "username": obj.username,
            "role_code": obj.role_code,
            "is_active": obj.is_active,
            "account_status": obj.account_status,
            "must_change_password": obj.must_change_password,
            "employer_id": obj.employer_id,
            "worker_id": obj.worker_id,
        },
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/users/{user_id}", response_model=schemas.AppUserOut)
def update_user(
    user_id: int,
    payload: schemas.AppUserUpdateIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")

    before = {
        "full_name": target.full_name,
        "role_code": target.role_code,
        "is_active": target.is_active,
        "account_status": _normalize_account_status(getattr(target, "account_status", None), bool(target.is_active)),
        "must_change_password": bool(getattr(target, "must_change_password", False)),
        "employer_id": target.employer_id,
        "worker_id": target.worker_id,
    }

    changes = payload.model_dump(exclude_unset=True)
    next_role = normalize_role_key(changes.get("role_code", target.role_code))
    next_employer_id = changes["employer_id"] if "employer_id" in changes else target.employer_id
    next_worker_id = changes["worker_id"] if "worker_id" in changes else target.worker_id

    next_employer_id, next_worker_id = _resolve_scope(
        db,
        role_code=next_role,
        employer_id=next_employer_id,
        worker_id=next_worker_id,
    )
    if not is_role_enabled(db, next_role):
        raise HTTPException(status_code=400, detail="Role is disabled for this installation")
    _ensure_admin_scope(db, user, next_employer_id, next_role)

    if "full_name" in changes:
        target.full_name = changes["full_name"]
    if "password" in changes:
        target.password_hash = hash_password(changes["password"])
        target.must_change_password = True
        target.account_status = ACCOUNT_PASSWORD_RESET_REQUIRED
        target.is_active = True
    if "role_code" in changes:
        target.role_code = next_role
    if "account_status" in changes and changes["account_status"] is not None:
        _apply_account_status(target, changes["account_status"], user)
    elif "is_active" in changes:
        target.is_active = changes["is_active"]
        target.account_status = ACCOUNT_ACTIVE if changes["is_active"] else ACCOUNT_SUSPENDED
    if "must_change_password" in changes and changes["must_change_password"] is not None:
        target.must_change_password = bool(changes["must_change_password"])
        if target.must_change_password:
            target.account_status = ACCOUNT_PASSWORD_RESET_REQUIRED
            target.is_active = True
        elif target.account_status == ACCOUNT_PASSWORD_RESET_REQUIRED:
            target.account_status = ACCOUNT_ACTIVE
    if "role_code" in changes or "employer_id" in changes or "worker_id" in changes:
        target.employer_id = next_employer_id
        target.worker_id = next_worker_id
    if not target.is_active:
        _revoke_user_sessions(db, target.id)

    record_audit(
        db,
        actor=user,
        action="auth.user.update",
        entity_type="app_user",
        entity_id=target.id,
        route=f"/auth/users/{target.id}",
        employer_id=target.employer_id,
        worker_id=target.worker_id,
        before=before,
        after={
            "full_name": target.full_name,
            "role_code": target.role_code,
            "is_active": target.is_active,
            "account_status": target.account_status,
            "must_change_password": target.must_change_password,
            "employer_id": target.employer_id,
            "worker_id": target.worker_id,
        },
    )
    db.commit()
    db.refresh(target)
    return target


@router.patch("/users/{user_id}/status", response_model=schemas.AppUserOut)
def update_user_status(
    user_id: int,
    payload: schemas.AppUserStatusUpdateIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    if target.id == user.id and payload.status.upper() != ACCOUNT_ACTIVE:
        raise HTTPException(status_code=400, detail="Modification de votre propre statut interdite")

    before = {"account_status": target.account_status, "is_active": target.is_active}
    _apply_account_status(target, payload.status, user)
    if not target.is_active:
        _revoke_user_sessions(db, target.id)
    record_audit(
        db,
        actor=user,
        action="auth.user.status_update",
        entity_type="app_user",
        entity_id=target.id,
        route=f"/auth/users/{target.id}/status",
        before=before,
        after={"account_status": target.account_status, "is_active": target.is_active},
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/users/{user_id}/approve", response_model=schemas.AppUserOut)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    _ensure_admin_scope(db, user, resolve_user_employer_id(db, target), target.role_code)
    before = {"account_status": target.account_status, "is_active": target.is_active}
    _apply_account_status(target, ACCOUNT_ACTIVE, user)
    existing_assignment = (
        db.query(models.IamUserRole.id)
        .filter(
            models.IamUserRole.user_id == target.id,
            models.IamUserRole.role_code == normalize_role_key(target.role_code),
        )
        .first()
    )
    if existing_assignment is None:
        db.add(
            models.IamUserRole(
                user_id=target.id,
                role_code=normalize_role_key(target.role_code),
                employer_id=target.employer_id,
                worker_id=target.worker_id,
                is_active=True,
                delegated_by_user_id=user.id,
            )
        )
    record_audit(
        db,
        actor=user,
        action="auth.user.approve",
        entity_type="app_user",
        entity_id=target.id,
        route=f"/auth/users/{target.id}/approve",
        before=before,
        after={"account_status": target.account_status, "is_active": target.is_active},
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/users/{user_id}/reject", response_model=schemas.AppUserOut)
def reject_user(
    user_id: int,
    payload: Optional[schemas.AppUserRejectIn] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Refus de votre propre compte interdit")
    before = {"account_status": target.account_status, "is_active": target.is_active}
    _apply_account_status(target, ACCOUNT_REJECTED, user)
    _revoke_user_sessions(db, target.id)
    record_audit(
        db,
        actor=user,
        action="auth.user.reject",
        entity_type="app_user",
        entity_id=target.id,
        route=f"/auth/users/{target.id}/reject",
        before=before,
        after={"account_status": target.account_status, "reason": payload.reason if payload else None},
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/users/{user_id}/suspend", response_model=schemas.AppUserOut)
def suspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Suspension de votre propre compte interdite")
    before = {"account_status": target.account_status, "is_active": target.is_active}
    _apply_account_status(target, ACCOUNT_SUSPENDED, user)
    _revoke_user_sessions(db, target.id)
    record_audit(
        db,
        actor=user,
        action="auth.user.suspend",
        entity_type="app_user",
        entity_id=target.id,
        route=f"/auth/users/{target.id}/suspend",
        before=before,
        after={"account_status": target.account_status, "is_active": target.is_active},
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/users/{user_id}/reset-password", response_model=schemas.AppUserOut)
def reset_user_password(
    user_id: int,
    payload: schemas.AppUserResetPasswordIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    _validate_registration_password(payload.temporary_password)
    before = {
        "account_status": target.account_status,
        "must_change_password": target.must_change_password,
    }
    target.password_hash = hash_password(payload.temporary_password)
    target.must_change_password = bool(payload.must_change_password)
    if target.must_change_password:
        target.account_status = ACCOUNT_PASSWORD_RESET_REQUIRED
        target.is_active = True
    elif target.account_status == ACCOUNT_PASSWORD_RESET_REQUIRED:
        target.account_status = ACCOUNT_ACTIVE
    _revoke_user_sessions(db, target.id)
    record_audit(
        db,
        actor=user,
        action="auth.user.reset_password",
        entity_type="app_user",
        entity_id=target.id,
        route=f"/auth/users/{target.id}/reset-password",
        before=before,
        after={
            "account_status": target.account_status,
            "must_change_password": target.must_change_password,
            "password_hash_rotated": True,
        },
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/change-password", response_model=schemas.UserSessionOut)
def change_own_password(
    payload: schemas.AppUserChangePasswordIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=403, detail="Mot de passe actuel invalide")
    _validate_registration_password(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    if user.account_status == ACCOUNT_PASSWORD_RESET_REQUIRED:
        user.account_status = ACCOUNT_ACTIVE
        user.is_active = True
    record_audit(
        db,
        actor=user,
        action="auth.user.change_password",
        entity_type="app_user",
        entity_id=user.id,
        route="/auth/change-password",
        after={"must_change_password": False, "password_hash_rotated": True},
    )
    db.commit()
    db.refresh(user)
    access_profile = build_user_access_profile_for_user(db, user)
    return _session_out("", user, access_profile)


@router.delete("/users/{user_id}", response_model=schemas.AppUserOut)
def delete_user(
    user_id: int,
    payload: schemas.AppUserDeleteIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=403, detail="Mot de passe de confirmation invalide")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Suppression de votre propre compte interdite")

    before = {
        "username": target.username,
        "full_name": target.full_name,
        "role_code": target.role_code,
        "is_active": target.is_active,
        "employer_id": target.employer_id,
        "worker_id": target.worker_id,
    }
    target.is_active = False
    target.account_status = ACCOUNT_SUSPENDED
    target.must_change_password = False
    _revoke_user_sessions(db, target.id)
    record_audit(
        db,
        actor=user,
        action="auth.user.delete",
        entity_type="app_user",
        entity_id=str(target.id),
        route=f"/auth/users/{target.id}",
        employer_id=target.employer_id,
        worker_id=target.worker_id,
        before=before,
        after={
            "username": target.username,
            "full_name": target.full_name,
            "role_code": target.role_code,
            "is_active": target.is_active,
            "account_status": target.account_status,
            "employer_id": target.employer_id,
            "worker_id": target.worker_id,
        },
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/bootstrap-role-logins")
def bootstrap_role_logins(
    employer_id: Optional[int] = Query(None),
    user: models.AppUser = Depends(require_roles("admin", "rh")),
    db: Session = Depends(get_db),
):
    summary = ensure_demo_accounts(db, preferred_employer_id=employer_id)

    record_audit(
        db,
        actor=user,
        action="auth.bootstrap_role_logins",
        entity_type="app_user",
        entity_id="bulk",
        route="/auth/bootstrap-role-logins",
        employer_id=summary["employer_id"],
        after={
            "created": summary["created"],
            "updated": summary["updated"],
            "skipped": summary["skipped"],
            "worker_accounts": summary["worker_accounts"],
            "quick_accounts": summary["quick_accounts"],
            "password_policy": "bootstrap_password_rotated_and_hidden",
        },
    )
    db.commit()

    return {
        "ok": True,
        "employer_id": summary["employer_id"],
        "created": summary["created"],
        "updated": summary["updated"],
        "skipped": summary["skipped"],
        "quick_accounts": summary["quick_accounts"],
        "worker_accounts": summary["worker_accounts"],
    }


@router.get("/iam/summary", response_model=schemas.IamSummaryOut)
def get_iam_summary(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    _ = user
    return schemas.IamSummaryOut(
        total_users=db.query(models.AppUser.id).count(),
        pending_users=db.query(models.AppUser.id).filter(models.AppUser.account_status == ACCOUNT_PENDING).count(),
        active_users=db.query(models.AppUser.id).filter(models.AppUser.account_status == ACCOUNT_ACTIVE).count(),
        suspended_users=db.query(models.AppUser.id).filter(models.AppUser.account_status == ACCOUNT_SUSPENDED).count(),
        rejected_users=db.query(models.AppUser.id).filter(models.AppUser.account_status == ACCOUNT_REJECTED).count(),
        password_reset_required_users=db.query(models.AppUser.id).filter(
            models.AppUser.account_status == ACCOUNT_PASSWORD_RESET_REQUIRED
        ).count(),
        roles_count=db.query(models.IamRole.code).count(),
        permissions_count=db.query(models.IamPermission.code).count(),
    )


@router.get("/iam/permissions", response_model=list[schemas.IamPermissionCatalogItemOut])
def get_iam_permissions(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh")),
):
    _ = user
    return list_permission_catalog(db)


@router.get("/iam/role-activations", response_model=list[schemas.IamRoleActivationOut])
def get_iam_role_activations(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh")),
):
    _ = user
    roles = list_role_catalog(db, include_inactive=True)
    return [
        schemas.IamRoleActivationOut(role_code=item["code"], is_enabled=bool(item.get("is_active", True)))
        for item in roles
    ]


@router.put("/iam/role-activations/{role_code}", response_model=schemas.IamRoleActivationOut)
def update_iam_role_activation(
    role_code: str,
    payload: schemas.IamRoleActivationUpdateIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh")),
):
    normalized_role = normalize_role_key(role_code)
    if normalized_role not in ROLE_ASSIGNMENT_MATRIX["admin"]:
        raise HTTPException(status_code=404, detail="Unknown role")
    if not _can_actor_assign_role(db, user, normalized_role):
        raise HTTPException(status_code=403, detail="Forbidden")
    if normalized_role == "admin" and not payload.is_enabled:
        raise HTTPException(status_code=400, detail="Cannot disable canonical admin role")

    row = (
        db.query(models.IamRoleActivation)
        .filter(
            models.IamRoleActivation.scope_key == "installation",
            models.IamRoleActivation.role_code == normalized_role,
        )
        .first()
    )
    before = {"is_enabled": bool(row.is_enabled)} if row else {"is_enabled": True}
    if row is None:
        row = models.IamRoleActivation(
            scope_key="installation",
            role_code=normalized_role,
            is_enabled=payload.is_enabled,
            updated_by_user_id=user.id,
        )
        db.add(row)
    else:
        row.is_enabled = payload.is_enabled
        row.updated_by_user_id = user.id

    record_audit(
        db,
        actor=user,
        action="auth.iam.role_activation.update",
        entity_type="iam_role_activation",
        entity_id=normalized_role,
        route=f"/auth/iam/role-activations/{normalized_role}",
        before=before,
        after={"is_enabled": payload.is_enabled},
    )
    db.commit()
    return schemas.IamRoleActivationOut(role_code=normalized_role, is_enabled=payload.is_enabled)


@router.put("/iam/roles/{role_code}/permissions", response_model=schemas.IamRolePermissionsOut)
def update_iam_role_permissions(
    role_code: str,
    payload: schemas.IamRolePermissionsUpdateIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh")),
):
    normalized_role = normalize_role_key(role_code)
    if normalized_role not in ROLE_ASSIGNMENT_MATRIX["admin"]:
        raise HTTPException(status_code=404, detail="Unknown role")
    if not _can_actor_assign_role(db, user, normalized_role):
        raise HTTPException(status_code=403, detail="Forbidden")

    before = get_role_module_permissions(db, normalized_role)
    db.query(models.IamRolePermission).filter(models.IamRolePermission.role_code == normalized_role).delete(synchronize_session=False)

    def expand_action(action: str) -> set[str]:
        if action == "admin":
            return {"read", "create", "write", "validate", "approve", "close", "export", "print", "document", "delete", "admin"}
        if action == "write":
            return {"read", "create", "write", "validate", "approve", "close", "export", "print", "document", "delete"}
        if action == "read":
            return {"read"}
        return set()

    for module, actions in payload.modules.items():
        module_code = (module or "").strip().lower()
        if not module_code:
            continue
        for compact_action in actions:
            action = (compact_action or "").strip().lower()
            if action not in {"read", "write", "admin"}:
                continue
            for granular in expand_action(action):
                permission_code = f"{module_code}:{granular}"
                permission = db.query(models.IamPermission).filter(models.IamPermission.code == permission_code).first()
                if permission is None:
                    permission = models.IamPermission(
                        code=permission_code,
                        module=module_code,
                        action=granular,
                        label=f"{module_code}.{granular}",
                        sensitivity="base",
                    )
                    db.add(permission)
                    db.flush()
                db.add(
                    models.IamRolePermission(
                        role_code=normalized_role,
                        permission_code=permission_code,
                        is_granted=True,
                    )
                )

    after = get_role_module_permissions(db, normalized_role)
    record_audit(
        db,
        actor=user,
        action="auth.iam.role_permissions.update",
        entity_type="iam_role_permissions",
        entity_id=normalized_role,
        route=f"/auth/iam/roles/{normalized_role}/permissions",
        before=before,
        after=after,
    )
    db.commit()
    return schemas.IamRolePermissionsOut(role_code=normalized_role, modules=after)


@router.get("/iam/users/{user_id}/roles", response_model=list[schemas.IamUserRoleAssignmentOut])
def get_user_role_assignments(
    user_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    return (
        db.query(models.IamUserRole)
        .filter(models.IamUserRole.user_id == user_id)
        .order_by(models.IamUserRole.role_code.asc(), models.IamUserRole.id.asc())
        .all()
    )


@router.put("/iam/users/{user_id}/roles", response_model=list[schemas.IamUserRoleAssignmentOut])
def set_user_role_assignments(
    user_id: int,
    payload: schemas.IamUserRoleAssignmentSetIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")

    before = (
        db.query(models.IamUserRole)
        .filter(models.IamUserRole.user_id == user_id)
        .order_by(models.IamUserRole.id.asc())
        .all()
    )
    before_payload = [
        {
            "role_code": row.role_code,
            "employer_id": row.employer_id,
            "worker_id": row.worker_id,
            "is_active": row.is_active,
            "valid_from": row.valid_from,
            "valid_until": row.valid_until,
        }
        for row in before
    ]

    db.query(models.IamUserRole).filter(models.IamUserRole.user_id == user_id).delete(synchronize_session=False)
    for entry in payload.assignments:
        normalized_role = normalize_role_key(entry.role_code)
        if not is_role_enabled(db, normalized_role):
            raise HTTPException(status_code=400, detail=f"Role '{normalized_role}' disabled")
        if not _can_actor_assign_role(db, user, normalized_role):
            raise HTTPException(status_code=403, detail=f"Cannot assign role '{normalized_role}'")
        scoped_employer_id, scoped_worker_id = _resolve_scope(
            db,
            role_code=normalized_role,
            employer_id=entry.employer_id,
            worker_id=entry.worker_id,
        )
        _ensure_admin_scope(db, user, scoped_employer_id, normalized_role)
        db.add(
            models.IamUserRole(
                user_id=user_id,
                role_code=normalized_role,
                employer_id=scoped_employer_id,
                worker_id=scoped_worker_id,
                is_active=entry.is_active,
                valid_from=entry.valid_from,
                valid_until=entry.valid_until,
                delegated_by_user_id=user.id if user.id != target.id else None,
            )
        )

    db.flush()
    rows = (
        db.query(models.IamUserRole)
        .filter(models.IamUserRole.user_id == user_id)
        .order_by(models.IamUserRole.role_code.asc(), models.IamUserRole.id.asc())
        .all()
    )
    after_payload = [
        {
            "role_code": row.role_code,
            "employer_id": row.employer_id,
            "worker_id": row.worker_id,
            "is_active": row.is_active,
            "valid_from": row.valid_from,
            "valid_until": row.valid_until,
        }
        for row in rows
    ]

    record_audit(
        db,
        actor=user,
        action="auth.iam.user_roles.replace",
        entity_type="iam_user_roles",
        entity_id=str(user_id),
        route=f"/auth/iam/users/{user_id}/roles",
        employer_id=target.employer_id,
        worker_id=target.worker_id,
        before=before_payload,
        after=after_payload,
    )
    db.commit()
    return rows


@router.get("/iam/users/{user_id}/access-preview", response_model=schemas.UserAccessProfileOut)
def preview_user_access_profile(
    user_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    access_profile = build_user_access_profile_for_user(db, target)
    return schemas.UserAccessProfileOut(
        role_code=target.role_code,
        effective_role_code=access_profile["effective_role_code"],
        role_label=access_profile["role_label"],
        role_scope=access_profile["role_scope"],
        module_permissions=access_profile["module_permissions"],
        assigned_role_codes=access_profile["assigned_role_codes"],
    )


@router.get("/iam/users/{user_id}/permission-overrides", response_model=list[schemas.IamUserPermissionOverrideOut])
def get_user_permission_overrides(
    user_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")
    return (
        db.query(models.IamUserPermissionOverride)
        .filter(models.IamUserPermissionOverride.user_id == user_id)
        .order_by(models.IamUserPermissionOverride.permission_code.asc())
        .all()
    )


@router.put("/iam/users/{user_id}/permission-overrides", response_model=list[schemas.IamUserPermissionOverrideOut])
def set_user_permission_overrides(
    user_id: int,
    payload: schemas.IamUserPermissionOverrideSetIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    target = db.query(models.AppUser).filter(models.AppUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Accès refusé")

    known_permissions = {item["code"] for item in list_permission_catalog(db)}
    before = (
        db.query(models.IamUserPermissionOverride)
        .filter(models.IamUserPermissionOverride.user_id == user_id)
        .order_by(models.IamUserPermissionOverride.id.asc())
        .all()
    )
    before_payload = [
        {
            "permission_code": row.permission_code,
            "is_allowed": row.is_allowed,
            "reason": row.reason,
            "expires_at": row.expires_at,
        }
        for row in before
    ]

    db.query(models.IamUserPermissionOverride).filter(
        models.IamUserPermissionOverride.user_id == user_id
    ).delete(synchronize_session=False)

    for entry in payload.overrides:
        code = normalize_role_key(entry.permission_code).replace(".", ":")
        if code not in known_permissions:
            raise HTTPException(status_code=400, detail=f"Unknown permission_code '{entry.permission_code}'")
        db.add(
            models.IamUserPermissionOverride(
                user_id=user_id,
                permission_code=code,
                is_allowed=entry.is_allowed,
                reason=entry.reason,
                expires_at=entry.expires_at,
                updated_by_user_id=user.id,
            )
        )

    db.flush()
    rows = (
        db.query(models.IamUserPermissionOverride)
        .filter(models.IamUserPermissionOverride.user_id == user_id)
        .order_by(models.IamUserPermissionOverride.permission_code.asc())
        .all()
    )
    after_payload = [
        {
            "permission_code": row.permission_code,
            "is_allowed": row.is_allowed,
            "reason": row.reason,
            "expires_at": row.expires_at,
        }
        for row in rows
    ]
    record_audit(
        db,
        actor=user,
        action="auth.iam.user_permission_overrides.replace",
        entity_type="iam_user_permission_overrides",
        entity_id=str(user_id),
        route=f"/auth/iam/users/{user_id}/permission-overrides",
        employer_id=target.employer_id,
        worker_id=target.worker_id,
        before=before_payload,
        after=after_payload,
    )
    db.commit()
    return rows


@router.post("/logout")
def logout(
    user: models.AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(models.AuthSession).filter(
        models.AuthSession.user_id == user.id,
        models.AuthSession.revoked_at.is_(None),
    ).update({"revoked_at": models.func.now()})
    db.commit()
    return {"ok": True}


@router.get("/audit-logs", response_model=list[schemas.AuditLogOut])
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh")),
):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc(), models.AuditLog.id.desc())
    if user_id is not None:
        rows = rows.filter(models.AuditLog.actor_user_id == user_id)
    if action:
        rows = rows.filter(models.AuditLog.action.ilike(f"%{action.strip()}%"))
    items = rows.limit(limit).all()
    return [
        schemas.AuditLogOut(
            id=item.id,
            actor_user_id=item.actor_user_id,
            actor_role=item.actor_role,
            actor_username=item.actor.username if item.actor else None,
            actor_full_name=item.actor.full_name if item.actor else None,
            action=item.action,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            route=item.route,
            employer_id=item.employer_id,
            worker_id=item.worker_id,
            before=_json_object(item.before_json),
            after=_json_object(item.after_json),
            created_at=item.created_at,
        )
        for item in items
    ]
