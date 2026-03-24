from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import (
    ROLE_MODULE_MATRIX,
    ROLES_REQUIRING_EMPLOYER_SCOPE,
    ROLES_REQUIRING_WORKER_BINDING,
    USER_ADMIN_ROLES,
    can_assign_role,
    create_session_for_user,
    get_current_user,
    hash_password,
    list_role_catalog,
    require_roles,
    resolve_user_employer_id,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.UserSessionOut)
def login(payload: schemas.UserLoginIn, db: Session = Depends(get_db)):
    user = db.query(models.AppUser).filter(models.AppUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    token = create_session_for_user(db, user)
    return schemas.UserSessionOut(
        token=token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role_code=user.role_code,
        employer_id=user.employer_id,
        worker_id=user.worker_id,
    )


@router.get("/me", response_model=schemas.UserSessionOut)
def me(user: models.AppUser = Depends(get_current_user)):
    return schemas.UserSessionOut(
        token="",
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role_code=user.role_code,
        employer_id=user.employer_id,
        worker_id=user.worker_id,
    )


def _resolve_scope(
    db: Session,
    role_code: str,
    employer_id: Optional[int],
    worker_id: Optional[int],
) -> tuple[Optional[int], Optional[int]]:
    if role_code not in ROLE_MODULE_MATRIX:
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

    if role_code in ROLES_REQUIRING_WORKER_BINDING and worker_id is None:
        raise HTTPException(status_code=400, detail=f"role '{role_code}' requires worker_id")

    if role_code in ROLES_REQUIRING_EMPLOYER_SCOPE and employer_id is None:
        raise HTTPException(status_code=400, detail=f"role '{role_code}' requires employer_id")

    if employer_id is not None:
        employer_exists = db.query(models.Employer.id).filter(models.Employer.id == employer_id).first()
        if not employer_exists:
            raise HTTPException(status_code=404, detail="Employer not found")

    return employer_id, worker_id


def _ensure_admin_scope(db: Session, actor: models.AppUser, target_employer_id: Optional[int], target_role: str) -> None:
    if not can_assign_role(actor.role_code, target_role):
        raise HTTPException(status_code=403, detail="Role assignment forbidden")

    if actor.role_code in {"admin", "rh"}:
        return

    if actor.role_code != "employeur":
        raise HTTPException(status_code=403, detail="Forbidden")

    if not actor.employer_id:
        raise HTTPException(status_code=403, detail="No employer scope on actor")

    if target_employer_id != actor.employer_id:
        raise HTTPException(status_code=403, detail="Cannot manage users outside own employer")


def _can_view_user(db: Session, actor: models.AppUser, target: models.AppUser) -> bool:
    if actor.role_code == "admin":
        return True
    if actor.role_code == "rh":
        return target.role_code != "admin"
    if actor.role_code != "employeur":
        return actor.id == target.id
    target_employer_id = resolve_user_employer_id(db, target)
    return bool(actor.employer_id and target_employer_id == actor.employer_id)


@router.get("/roles", response_model=list[schemas.RoleCatalogItemOut])
def get_roles(
    assignable_only: bool = Query(False),
    user: models.AppUser = Depends(get_current_user),
):
    roles = list_role_catalog()
    if assignable_only:
        return [role for role in roles if can_assign_role(user.role_code, role["code"])]
    return roles


@router.get("/users", response_model=list[schemas.AppUserOut])
def list_users(
    employer_id: Optional[int] = Query(None),
    role_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*USER_ADMIN_ROLES)),
):
    if employer_id is not None and user.role_code == "employeur" and employer_id != user.employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rows = db.query(models.AppUser).order_by(models.AppUser.username.asc()).all()
    out = []
    for row in rows:
        if not _can_view_user(db, user, row):
            continue
        resolved_employer_id = resolve_user_employer_id(db, row)
        if employer_id is not None and resolved_employer_id != employer_id:
            continue
        if role_code and row.role_code != role_code:
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
        raise HTTPException(status_code=400, detail="Username is required")
    if db.query(models.AppUser.id).filter(models.AppUser.username == normalized_username).first():
        raise HTTPException(status_code=409, detail="Username already exists")

    employer_id, worker_id = _resolve_scope(
        db,
        role_code=payload.role_code,
        employer_id=payload.employer_id,
        worker_id=payload.worker_id,
    )
    _ensure_admin_scope(db, user, employer_id, payload.role_code)

    obj = models.AppUser(
        username=normalized_username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_code=payload.role_code,
        is_active=payload.is_active,
        employer_id=employer_id,
        worker_id=worker_id,
    )
    db.add(obj)
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
        raise HTTPException(status_code=404, detail="User not found")

    if not _can_view_user(db, user, target):
        raise HTTPException(status_code=403, detail="Forbidden")

    changes = payload.model_dump(exclude_unset=True)
    next_role = changes.get("role_code", target.role_code)
    next_employer_id = changes["employer_id"] if "employer_id" in changes else target.employer_id
    next_worker_id = changes["worker_id"] if "worker_id" in changes else target.worker_id

    next_employer_id, next_worker_id = _resolve_scope(
        db,
        role_code=next_role,
        employer_id=next_employer_id,
        worker_id=next_worker_id,
    )
    _ensure_admin_scope(db, user, next_employer_id, next_role)

    if "full_name" in changes:
        target.full_name = changes["full_name"]
    if "password" in changes:
        target.password_hash = hash_password(changes["password"])
    if "role_code" in changes:
        target.role_code = next_role
    if "is_active" in changes:
        target.is_active = changes["is_active"]
    if "role_code" in changes or "employer_id" in changes or "worker_id" in changes:
        target.employer_id = next_employer_id
        target.worker_id = next_worker_id

    db.commit()
    db.refresh(target)
    return target


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
