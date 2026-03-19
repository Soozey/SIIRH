from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import create_session_for_user, get_current_user, verify_password


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
