# backend/app/routers/payroll.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..config.config import get_db
from .. import models
from ..payroll_logic import compute_preview

router = APIRouter(prefix="/payroll", tags=["payroll"])

@router.get("/preview")
def payroll_preview(worker_id: int = Query(...), period: str = Query(...), db: Session = Depends(get_db)):
    worker = db.query(models.Worker).get(worker_id)
    if not worker:
        raise HTTPException(404, "Worker not found")
    employer = db.query(models.Employer).get(worker.employer_id)
    if not employer:
        raise HTTPException(404, "Employer not found")

    payvar = db.query(models.PayVar).filter(
        models.PayVar.worker_id == worker_id,
        models.PayVar.period == period
    ).first()

    lines, totals = compute_preview(employer, worker, payvar, period)
    return {
        "employer": {
            "id": employer.id,
            "raison_sociale": employer.raison_sociale,
            "nif": employer.nif,
            "stat": employer.stat,
            "cnaps": employer.cnaps_num
        },
        "worker": {
            "id": worker.id,
            "matricule": worker.matricule,
            "nom": worker.nom,
            "prenom": worker.prenom,
            "poste": worker.poste,
            "categorie_prof": worker.categorie_prof,
            "cnaps": worker.cnaps_num,
            "secteur": worker.secteur,
        },
        "period": period,
        "lines": lines,
        "totaux": totals
    }
