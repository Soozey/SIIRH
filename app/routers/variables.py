from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config.config import get_db
from .. import models, schemas

router = APIRouter(
    prefix="/variables",
    tags=["variables"],
)


@router.post("/upsert", response_model=schemas.PayVarOut, summary="Upsert Variables")
def upsert_variables(payload: schemas.PayVarIn, db: Session = Depends(get_db)):
    """
    Crée ou met à jour les variables de paie (PayVar) d'un salarié pour une période donnée.

    - Si un enregistrement existe déjà pour (worker_id, period) -> on le met à jour.
    - Sinon -> on le crée.
    """

    # 1) Chercher s'il existe déjà des variables pour ce worker + period
    var = (
        db.query(models.PayVar)
        .filter(
            models.PayVar.worker_id == payload.worker_id,
            models.PayVar.period == payload.period,
        )
        .first()
    )

    # 2) Si pas trouvé, on en crée un
    if var is None:
        var = models.PayVar(worker_id=payload.worker_id, period=payload.period)
        db.add(var)

    # 3) Mettre à jour tous les champs de PayVar présents dans PayVarIn
    # (sauf worker_id et period qu'on a déjà positionnés)
    data = payload.model_dump()

    for field_name, value in data.items():
        if field_name in ("worker_id", "period"):
            continue
        if hasattr(var, field_name):
            setattr(var, field_name, value)

    # 4) Sauvegarder en base
    db.commit()
    db.refresh(var)

    return var
