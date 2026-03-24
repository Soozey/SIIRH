from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..config.config import get_db
from datetime import datetime
from .. import models, schemas
from ..security import READ_PAYROLL_ROLES, WRITE_RH_ROLES, can_access_worker, can_manage_worker, get_current_user, require_roles
from ..services.audit_service import record_audit
from ..services.master_data_service import sync_worker_master_data

router = APIRouter(prefix="/workers", tags=["workers"])

from typing import Optional

from sqlalchemy import or_, func


def _apply_worker_search(query, q: Optional[str]):
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            or_(
                models.Worker.matricule.ilike(search_filter),
                models.Worker.nom.ilike(search_filter),
                models.Worker.prenom.ilike(search_filter),
                func.concat(models.Worker.nom, ' ', models.Worker.prenom).ilike(search_filter),
                func.concat(models.Worker.prenom, ' ', models.Worker.nom).ilike(search_filter)
            )
        )
    return query


def _apply_worker_scope(query, db: Session, user: models.AppUser):
    if user.role_code in {"admin", "rh", "comptable", "audit"}:
        return query
    if user.role_code in {"employeur", "direction", "juridique", "recrutement", "inspecteur"} and user.employer_id:
        return query.filter(models.Worker.employer_id == user.employer_id)
    if user.role_code == "employe" and user.worker_id:
        return query.filter(models.Worker.id == user.worker_id)
    if user.role_code in {"manager", "departement"} and user.worker_id:
        manager_worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        if manager_worker and manager_worker.organizational_unit_id:
            return query.filter(models.Worker.organizational_unit_id == manager_worker.organizational_unit_id)
    return query.filter(models.Worker.id == -1)

@router.get("", response_model=List[schemas.WorkerOut])
def list_workers(
    employer_id: Optional[int] = None,
    q: Optional[str] = None,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = _apply_worker_scope(db.query(models.Worker), db, user)
    if employer_id:
        query = query.filter(models.Worker.employer_id == employer_id)
    query = _apply_worker_search(query, q)
    query = query.order_by(models.Worker.nom.asc(), models.Worker.prenom.asc())
    if page and page_size:
        query = query.offset((page - 1) * page_size).limit(page_size)
    return query.all()


@router.get("/paginated", response_model=schemas.PaginatedWorkersOut)
def list_workers_paginated(
    employer_id: Optional[int] = None,
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = _apply_worker_scope(db.query(models.Worker), db, user)
    if employer_id:
        query = query.filter(models.Worker.employer_id == employer_id)
    query = _apply_worker_search(query, q)
    total = query.count()
    items = query.order_by(models.Worker.nom.asc(), models.Worker.prenom.asc()).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = ceil(total / page_size) if total else 1
    return schemas.PaginatedWorkersOut(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)

@router.get("/{worker_id}", response_model=schemas.WorkerOut)
def get_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    w = db.query(models.Worker).get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_access_worker(db, user, w):
        raise HTTPException(403, "Forbidden")
    return w

@router.post("", response_model=schemas.WorkerOut)
def create_worker(
    data: schemas.WorkerIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    if not can_manage_worker(db, user, employer_id=data.employer_id):
        raise HTTPException(403, "Forbidden")
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
        nature_contrat=data.nature_contrat,
        categorie_prof=data.categorie_prof,
        poste=data.poste,
        avantage_vehicule=data.avantage_vehicule,
        avantage_logement=data.avantage_logement,
        avantage_telephone=data.avantage_telephone,
        avantage_autres=data.avantage_autres,
        
        # Champs organisationnels
        etablissement=data.etablissement,
        departement=data.departement,
        service=data.service,
        unite=data.unite,
        
        # Débauche
        date_debauche=data.date_debauche,
        type_sortie=data.type_sortie,
        groupe_preavis=data.groupe_preavis,
        jours_preavis_deja_faits=data.jours_preavis_deja_faits,
    )
    db.add(obj)
    db.flush()
    sync_worker_master_data(db, obj)
    record_audit(
        db,
        actor=user,
        action="worker.create",
        entity_type="worker",
        entity_id=obj.id,
        route="/workers",
        employer_id=obj.employer_id,
        worker_id=obj.id,
        after=obj,
    )
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/{worker_id}", response_model=schemas.WorkerOut)
def update_worker(
    worker_id: int,
    data: schemas.WorkerIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    w = db.query(models.Worker).get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_manage_worker(db, user, worker=w):
        raise HTTPException(403, "Forbidden")
    before = {
        "salaire_base": w.salaire_base,
        "poste": w.poste,
        "categorie_prof": w.categorie_prof,
        "organizational_unit_id": w.organizational_unit_id,
    }

    # Mise à jour basique
    for k, v in data.dict().items():
        setattr(w, k, v)

    if not w.salaire_horaire and w.vhm:
        w.salaire_horaire = w.salaire_base / w.vhm
    sync_worker_master_data(db, w)

    record_audit(
        db,
        actor=user,
        action="worker.update",
        entity_type="worker",
        entity_id=w.id,
        route=f"/workers/{worker_id}",
        employer_id=w.employer_id,
        worker_id=w.id,
        before=before,
        after=w,
    )
    db.commit()
    db.refresh(w)
    return w

@router.patch("/{worker_id}/organizational", response_model=schemas.WorkerOut)
def update_worker_organizational(
    worker_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    """Mise à jour des données organisationnelles d'un salarié"""
    w = db.query(models.Worker).get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_manage_worker(db, user, worker=w):
        raise HTTPException(403, "Forbidden")
    before = {"etablissement": w.etablissement, "departement": w.departement, "service": w.service, "unite": w.unite}

    # Mise à jour seulement des champs organisationnels fournis
    organizational_fields = ['etablissement', 'departement', 'service', 'unite']
    for field in organizational_fields:
        if field in data:
            setattr(w, field, data[field])
    sync_worker_master_data(db, w)

    record_audit(
        db,
        actor=user,
        action="worker.organizational.update",
        entity_type="worker",
        entity_id=w.id,
        route=f"/workers/{worker_id}/organizational",
        employer_id=w.employer_id,
        worker_id=w.id,
        before=before,
        after=w,
    )
    db.commit()
    db.refresh(w)
    return w

@router.patch("/{worker_id}", response_model=schemas.WorkerOut)
def patch_worker(
    worker_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    w = db.query(models.Worker).get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_manage_worker(db, user, worker=w):
        raise HTTPException(403, "Forbidden")
    before = {"salaire_base": w.salaire_base, "solde_conge_initial": w.solde_conge_initial}

    for k, v in data.items():
        if hasattr(w, k):
            setattr(w, k, v)

    if w.vhm and w.vhm > 0:
        w.salaire_horaire = w.salaire_base / w.vhm
    sync_worker_master_data(db, w)

    record_audit(
        db,
        actor=user,
        action="worker.patch",
        entity_type="worker",
        entity_id=w.id,
        route=f"/workers/{worker_id}",
        employer_id=w.employer_id,
        worker_id=w.id,
        before=before,
        after=w,
    )
    db.commit()
    db.refresh(w)
    return w


@router.delete("/all")
def delete_all_workers(
    employer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    try:
        query = db.query(models.Worker)
        if employer_id:
            query = query.filter(models.Worker.employer_id == employer_id)
        
        workers = query.all()
        count = len(workers)
        
        for w in workers:
            if not can_manage_worker(db, user, worker=w):
                raise HTTPException(403, "Forbidden")
            db.delete(w)
            
        db.commit()
        return {"message": f"{count} travailleurs supprimés", "count": count}
    except Exception as e:
        db.rollback()
        import traceback
        with open("last_error.txt", "w") as f:
            f.write(str(e))
            f.write("\n")
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{worker_id}")
def delete_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    with open("deletion_debug.log", "a") as log:
        log.write(f"[{datetime.now()}] Starting delete_worker for id={worker_id}\n")
    try:
        w = db.query(models.Worker).get(worker_id)
        if not w:
            raise HTTPException(404, "Worker not found")
        if not can_manage_worker(db, user, worker=w):
            raise HTTPException(403, "Forbidden")
        before = {"id": w.id, "matricule": w.matricule, "nom": w.nom, "prenom": w.prenom}
        
        # Nettoyage manuel des dépendances (même logique que batch_delete)
        # 1. HS/HM
        db.query(models.HSJourHS).filter(
            models.HSJourHS.calculation_id_HS.in_(
                db.query(models.HSCalculationHS.id_HS).filter(models.HSCalculationHS.worker_id_HS == worker_id)
            )
        ).delete(synchronize_session=False)
        db.query(models.PayrollHsHm).filter(models.PayrollHsHm.worker_id == worker_id).delete(synchronize_session=False)
        db.query(models.HSCalculationHS).filter(models.HSCalculationHS.worker_id_HS == worker_id).delete(synchronize_session=False)
        
        # 2. Primes
        db.query(models.PayrollPrime).filter(models.PayrollPrime.worker_id == worker_id).delete(synchronize_session=False)
        db.query(models.WorkerPrimeLink).filter(models.WorkerPrimeLink.worker_id == worker_id).delete(synchronize_session=False)
        db.query(models.WorkerPrime).filter(models.WorkerPrime.worker_id == worker_id).delete(synchronize_session=False)
        
        # 3. PayVars
        db.query(models.PayVar).filter(models.PayVar.worker_id == worker_id).delete(synchronize_session=False)
        
        # 4. Autres
        db.query(models.Absence).filter(models.Absence.worker_id == worker_id).delete(synchronize_session=False)
        db.query(models.Avance).filter(models.Avance.worker_id == worker_id).delete(synchronize_session=False)
        db.query(models.Leave).filter(models.Leave.worker_id == worker_id).delete(synchronize_session=False)
        db.query(models.Permission).filter(models.Permission.worker_id == worker_id).delete(synchronize_session=False)
        db.query(models.WorkerPositionHistory).filter(models.WorkerPositionHistory.worker_id == worker_id).delete(synchronize_session=False)

        # 5. Enfin le worker
        db.delete(w)
        record_audit(
            db,
            actor=user,
            action="worker.delete",
            entity_type="worker",
            entity_id=worker_id,
            route=f"/workers/{worker_id}",
            employer_id=w.employer_id,
            worker_id=w.id,
            before=before,
            after=None,
        )
        db.commit()
        return {"ok": True}
        
    except Exception as e:
        db.rollback()
        import traceback
        with open("last_error.txt", "w") as f:
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete_batch")
def delete_workers_batch(
    data: schemas.WorkerListDelete,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    Supprime plusieurs travailleurs en une seule requête (par liste d'IDs).
    """
    with open("deletion_debug.log", "a") as log:
        log.write(f"[{datetime.now()}] Starting delete_workers_batch for ids={data.ids}\n")
    try:
        if not data.ids:
            return {"message": "Aucun ID fourni", "count": 0}
            
        # Nettoyage manuel des dépendances AVANT suppression pour éviter les FK violations
        # (Au cas où les cascades SQLAlchemy échouent ou sont incomplètes)
        ids = data.ids
        
        # 1. HS/HM Calculs & Lignes de paie
        # On doit supprimer les JOURS d'abord car HSCalculationHS est le parent
        db.query(models.HSJourHS).filter(
            models.HSJourHS.calculation_id_HS.in_(
                db.query(models.HSCalculationHS.id_HS).filter(models.HSCalculationHS.worker_id_HS.in_(ids))
            )
        ).delete(synchronize_session=False)
        
        db.query(models.PayrollHsHm).filter(models.PayrollHsHm.worker_id.in_(ids)).delete(synchronize_session=False)
        db.query(models.HSCalculationHS).filter(models.HSCalculationHS.worker_id_HS.in_(ids)).delete(synchronize_session=False)
        
        # 2. Primes
        db.query(models.PayrollPrime).filter(models.PayrollPrime.worker_id.in_(ids)).delete(synchronize_session=False)
        db.query(models.WorkerPrimeLink).filter(models.WorkerPrimeLink.worker_id.in_(ids)).delete(synchronize_session=False)
        # Note: WorkerPrimeLink & WorkerPrime ont cascade, mais on force pour être sûr
        
        # 3. PayVars (Variables de paie)
        db.query(models.PayVar).filter(models.PayVar.worker_id.in_(ids)).delete(synchronize_session=False)
        
        # 4. Autres (Absences, Avances...)
        db.query(models.Absence).filter(models.Absence.worker_id.in_(ids)).delete(synchronize_session=False)
        db.query(models.Avance).filter(models.Avance.worker_id.in_(ids)).delete(synchronize_session=False)
        db.query(models.Leave).filter(models.Leave.worker_id.in_(ids)).delete(synchronize_session=False)
        db.query(models.Permission).filter(models.Permission.worker_id.in_(ids)).delete(synchronize_session=False)
        db.query(models.WorkerPositionHistory).filter(models.WorkerPositionHistory.worker_id.in_(ids)).delete(synchronize_session=False)

        # 5. Suppression des travailleurs
        # On récupère les workers à supprimer
        workers_to_delete = db.query(models.Worker).filter(models.Worker.id.in_(ids)).all()
        count = len(workers_to_delete)
        
        for w in workers_to_delete:
            if not can_manage_worker(db, user, worker=w):
                raise HTTPException(403, "Forbidden")
            record_audit(
                db,
                actor=user,
                action="worker.delete.batch",
                entity_type="worker",
                entity_id=w.id,
                route="/workers/delete_batch",
                employer_id=w.employer_id,
                worker_id=w.id,
                before={"id": w.id, "matricule": w.matricule, "nom": w.nom, "prenom": w.prenom},
                after=None,
            )
            db.delete(w)
            
        db.commit()
        return {"message": f"{count} travailleurs supprimés", "count": count}
    except Exception as e:
        db.rollback()
        import traceback
        with open("last_error.txt", "w") as f:
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# GESTION DES PRIMES PERSONNALISÉES (WORKER)
# ==========================================

@router.post("/{worker_id}/primes", response_model=schemas.WorkerPrimeOut)
def create_worker_prime(worker_id: int, prime: schemas.WorkerPrimeIn, db: Session = Depends(get_db)):
    worker = db.query(models.Worker).get(worker_id)
    if not worker:
        raise HTTPException(404, "Salarié non trouvé")
        
    db_prime = models.WorkerPrime(**prime.dict(), worker_id=worker_id)
    db.add(db_prime)
    db.commit()
    db.refresh(db_prime)
    return db_prime

@router.put("/{worker_id}/primes/{prime_id}", response_model=schemas.WorkerPrimeOut)
def update_worker_prime(worker_id: int, prime_id: int, prime_data: schemas.WorkerPrimeIn, db: Session = Depends(get_db)):
    db_prime = db.query(models.WorkerPrime).filter(
        models.WorkerPrime.id == prime_id,
        models.WorkerPrime.worker_id == worker_id
    ).first()
    
    if not db_prime:
        raise HTTPException(404, "Prime non trouvée")
        
    for key, value in prime_data.dict().items():
        setattr(db_prime, key, value)
        
    db.commit()
    db.refresh(db_prime)
    return db_prime

@router.delete("/{worker_id}/primes/{prime_id}", status_code=204)
def delete_worker_prime(worker_id: int, prime_id: int, db: Session = Depends(get_db)):
    db_prime = db.query(models.WorkerPrime).filter(
        models.WorkerPrime.id == prime_id,
        models.WorkerPrime.worker_id == worker_id
    ).first()
    
    if not db_prime:
        raise HTTPException(404, "Prime non trouvée")
        
    db.delete(db_prime)
    db.commit()
    return None


# ==========================
# GESTION HISTORIQUE POSTES
# ==========================

@router.post("/{worker_id}/history", response_model=schemas.WorkerPositionHistoryOut)
def create_worker_history(worker_id: int, history: schemas.WorkerPositionHistoryIn, db: Session = Depends(get_db)):
    worker = db.query(models.Worker).get(worker_id)
    if not worker:
        raise HTTPException(404, "Salarié non trouvé")
        
    db_hist = models.WorkerPositionHistory(**history.dict(), worker_id=worker_id)
    db.add(db_hist)
    db.commit()
    db.refresh(db_hist)
    return db_hist

@router.delete("/{worker_id}/history/{history_id}", status_code=204)
def delete_worker_history(worker_id: int, history_id: int, db: Session = Depends(get_db)):
    db_hist = db.query(models.WorkerPositionHistory).filter(
        models.WorkerPositionHistory.id == history_id,
        models.WorkerPositionHistory.worker_id == worker_id
    ).first()
    
    if not db_hist:
        raise HTTPException(404, "Entrée d'historique non trouvée")
        
    db.delete(db_hist)
    db.commit()
    return None
