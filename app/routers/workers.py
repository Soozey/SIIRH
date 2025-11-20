from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..config.config import get_db
from .. import models, schemas

router = APIRouter(prefix="/workers", tags=["workers"])

@router.get("", response_model=List[schemas.WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    return db.query(models.Worker).all()

@router.get("/{worker_id}", response_model=schemas.WorkerOut)
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    w = db.query(models.Worker).get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    return w

@router.post("", response_model=schemas.WorkerOut)
def create_worker(data: schemas.WorkerIn, db: Session = Depends(get_db)):
    # Ajuste auto VHM/Hebdo si secteur fourni
    vhm = data.vhm
    hebdo = data.horaire_hebdo
    # if data.secteur == "agricole":
    #     vhm, hebdo = 173.33, 40.0
    # elif data.secteur == "non_agricole":
    #     vhm, hebdo = 200.0, 46.0

    obj = models.Worker(
        employer_id=data.employer_id,
        matricule=data.matricule,
        nom=data.nom, prenom=data.prenom,
        type_regime_id=data.type_regime_id,
        adresse=data.adresse,
        nombre_enfant=data.nombre_enfant,
        salaire_base=data.salaire_base,
        salaire_horaire=data.salaire_horaire or (data.salaire_base / vhm if vhm else 0),
        vhm=vhm,
        horaire_hebdo=hebdo,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/{worker_id}", response_model=schemas.WorkerOut)
def update_worker(worker_id: int, data: schemas.WorkerIn, db: Session = Depends(get_db)):
    w = db.query(models.Worker).get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")

    # Mise à jour basique
    for k, v in data.dict().items():
        setattr(w, k, v)

    # Recalcule auto si secteur change
    if data.secteur == "agricole":
        w.vhm, w.horaire_hebdo = 173.33, 40.0
    elif data.secteur == "non_agricole":
        w.vhm, w.horaire_hebdo = 200.0, 46.0

    if not w.salaire_horaire and w.vhm:
        w.salaire_horaire = w.salaire_base / w.vhm

    db.commit(); db.refresh(w)
    return w

@router.delete("/{worker_id}")
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    w = db.query(models.Worker).get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    db.delete(w); db.commit()
    return {"ok": True}

