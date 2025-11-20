# backend/app/routers/type_regimes.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from ..config.config import get_db
from .. import models, schemas

router = APIRouter(prefix="/type_regimes", tags=["type_regimes"])


# ---------- Helpers ----------
def _get_or_404(db: Session, regime_id: int) -> models.TypeRegime:
    obj = db.query(models.TypeRegime).get(regime_id)
    if not obj:
        raise HTTPException(status_code=404, detail="TypeRegime not found")
    return obj


# ---------- List with filters ----------
@router.get("", response_model=List[schemas.TypeRegimeOut])
def list_type_regimes(
    q: Optional[str] = Query(None, description="Recherche sur code/label (contient)"),
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(models.TypeRegime)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.TypeRegime.code.ilike(like)) | (models.TypeRegime.label.ilike(like))
        )
    return query.offset(skip).limit(limit).all()


# ---------- Retrieve ----------
@router.get("/{regime_id}", response_model=schemas.TypeRegimeOut)
def retrieve_type_regime(regime_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, regime_id)


# ---------- Create ----------
@router.post("", response_model=schemas.TypeRegimeOut, status_code=status.HTTP_201_CREATED)
def create_type_regime(data: schemas.TypeRegimeIn, db: Session = Depends(get_db)):
    # Unicité du code
    if db.query(models.TypeRegime).filter_by(code=data.code).first():
        raise HTTPException(status_code=400, detail="Code already exists")
    obj = models.TypeRegime(**data.dict())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Double filet de sécurité si contrainte d'unicité côté DB
        raise HTTPException(status_code=400, detail="Code already exists")
    db.refresh(obj)
    return obj


# ---------- Full update (PUT) ----------
@router.put("/{regime_id}", response_model=schemas.TypeRegimeOut)
def update_type_regime(regime_id: int, data: schemas.TypeRegimeIn, db: Session = Depends(get_db)):
    obj = _get_or_404(db, regime_id)

    # Empêcher la collision de codes
    if db.query(models.TypeRegime).filter(
        models.TypeRegime.code == data.code,
        models.TypeRegime.id != regime_id
    ).first():
        raise HTTPException(status_code=400, detail="Code already exists")

    for k, v in data.dict().items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unique constraint failed")
    db.refresh(obj)
    return obj


# ---------- Partial update (PATCH) ----------
@router.patch("/{regime_id}", response_model=schemas.TypeRegimeOut)
def patch_type_regime(regime_id: int, data: schemas.TypeRegimeIn, db: Session = Depends(get_db)):
    obj = _get_or_404(db, regime_id)
    payload = data.dict(exclude_unset=True)

    # Collision éventuelle sur code
    new_code = payload.get("code")
    if new_code and db.query(models.TypeRegime).filter(
        models.TypeRegime.code == new_code,
        models.TypeRegime.id != regime_id
    ).first():
        raise HTTPException(status_code=400, detail="Code already exists")

    for k, v in payload.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unique constraint failed")
    db.refresh(obj)
    return obj


# ---------- Delete ----------
@router.delete("/{regime_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_type_regime(regime_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, regime_id)

    # Empêcher la suppression si des employeurs y sont liés (optionnel)
    linked = db.query(models.Employer).filter(models.Employer.type_regime_id == regime_id).first()
    if linked:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: regime is referenced by at least one employer",
        )

    db.delete(obj)
    db.commit()
    return None


# ---------- Seed defaults (pratique) ----------
@router.post("/seed-defaults", response_model=List[schemas.TypeRegimeOut])
def seed_defaults(db: Session = Depends(get_db)):
    """
    Crée/Met à jour les deux régimes standards.
    Adapte les VHM selon ta règle métier.
    """
    defaults = [
        {"code": "agricole", "label": "Régime Agricole", "vhm": 200.0},
        {"code": "non_agricole", "label": "Régime Non Agricole", "vhm": 173.33},
    ]
    out = []
    for d in defaults:
        obj = db.query(models.TypeRegime).filter_by(code=d["code"]).first()
        if obj:
            obj.label = d["label"]
            obj.vhm = d["vhm"]
        else:
            obj = models.TypeRegime(**d)
            db.add(obj)
        db.commit()
        db.refresh(obj)
        out.append(obj)
    return out
