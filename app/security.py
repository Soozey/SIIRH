from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from . import models
from .config.config import get_db, settings


READ_PAYROLL_ROLES = {"admin", "rh", "comptable", "employeur", "manager", "employe"}
WRITE_RH_ROLES = {"admin", "rh", "employeur"}
MANAGER_REVIEW_ROLES = {"admin", "rh", "manager"}
RH_REVIEW_ROLES = {"admin", "rh"}


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


def can_access_worker(db: Session, user: models.AppUser, worker: models.Worker) -> bool:
    if user.role_code in {"admin", "rh", "comptable", "audit"}:
        return True
    if user.role_code == "employeur":
        return user.employer_id == worker.employer_id
    if user.role_code == "employe":
        return user.worker_id == worker.id
    if user.role_code == "manager":
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
