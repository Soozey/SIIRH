from typing import Optional

from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..config.config import get_db
from .. import models, schemas
from ..security import (
    READ_PAYROLL_ROLES,
    WRITE_RH_ROLES,
    can_access_employer,
    require_roles,
    resolve_user_employer_id,
    user_has_any_role,
)
from ..services.audit_service import record_audit
from ..services.file_storage import build_static_path, sanitize_filename_part, save_upload_file
import json

router = APIRouter(prefix="/employers", tags=["employers"])


def _ensure_employer_scope(db: Session, user: models.AppUser, employer_id: int):
    if not can_access_employer(db, user, employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")


def _deserialize_lists(emp: models.Employer):
    try:
        emp.etablissements = json.loads(emp.etablissements or "[]")
        emp.departements = json.loads(emp.departements or "[]")
        emp.services = json.loads(emp.services or "[]")
        emp.unites = json.loads(emp.unites or "[]")
    except (json.JSONDecodeError, TypeError):
        emp.etablissements = []
        emp.departements = []
        emp.services = []
        emp.unites = []
    return emp

@router.post("", response_model=schemas.EmployerOut)
def create_employer(
    data: schemas.EmployerIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    try:
        # Vérifier si le type_regime_id existe
        if data.type_regime_id:
            type_regime = db.query(models.TypeRegime).filter(models.TypeRegime.id == data.type_regime_id).first()
            if not type_regime:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"TypeRegime avec ID {data.type_regime_id} non trouvé"
                )
        
        # Convert organizational lists to JSON strings
        data_dict = data.dict()
        data_dict['etablissements'] = json.dumps(data.etablissements or [])
        data_dict['departements'] = json.dumps(data.departements or [])
        data_dict['services'] = json.dumps(data.services or [])
        data_dict['unites'] = json.dumps(data.unites or [])
        
        obj = models.Employer(**data_dict)
        db.add(obj)
        db.flush()
        record_audit(
            db,
            actor=user,
            action="employer.create",
            entity_type="employer",
            entity_id=obj.id,
            route="/employers",
            employer_id=obj.id,
            after=obj,
        )
        db.commit()
        db.refresh(obj)
        return _deserialize_lists(obj)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur base de données: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )

@router.get("", response_model=list[schemas.EmployerOut])
def list_employers(
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = db.query(models.Employer)
    if user_has_any_role(db, user, "employeur", "direction", "juridique", "recrutement", "inspecteur"):
        if user.employer_id:
            query = query.filter(models.Employer.id == user.employer_id)
        else:
            query = query.filter(models.Employer.id == -1)
    elif user_has_any_role(db, user, "manager", "departement", "employe"):
        scoped_employer_id = resolve_user_employer_id(db, user)
        if scoped_employer_id:
            query = query.filter(models.Employer.id == scoped_employer_id)
        else:
            query = query.filter(models.Employer.id == -1)
    query = query.order_by(models.Employer.raison_sociale.asc())
    if page and page_size:
        query = query.offset((page - 1) * page_size).limit(page_size)
    return [_deserialize_lists(emp) for emp in query.all()]


@router.get("/paginated", response_model=schemas.PaginatedEmployersOut)
def list_employers_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = db.query(models.Employer)
    if user_has_any_role(db, user, "employeur", "direction", "juridique", "recrutement", "inspecteur"):
        if user.employer_id:
            query = query.filter(models.Employer.id == user.employer_id)
        else:
            query = query.filter(models.Employer.id == -1)
    elif user_has_any_role(db, user, "manager", "departement", "employe"):
        scoped_employer_id = resolve_user_employer_id(db, user)
        if scoped_employer_id:
            query = query.filter(models.Employer.id == scoped_employer_id)
        else:
            query = query.filter(models.Employer.id == -1)
    total = query.count()
    items = query.order_by(models.Employer.raison_sociale.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return schemas.PaginatedEmployersOut(
        items=[_deserialize_lists(emp) for emp in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 1,
    )


@router.get("/{employer_id}", response_model=schemas.EmployerOut)
def get_employer(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    _ensure_employer_scope(db, user, employer_id)
    emp = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employeur non trouve")
    return _deserialize_lists(emp)


@router.put("/{employer_id}", response_model=schemas.EmployerOut)
def update_employer(
    employer_id: int,
    data: schemas.EmployerIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    _ensure_employer_scope(db, user, employer_id)
    emp = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employeur non trouvé")
        
    try:
        before = models.Employer(
            id=emp.id,
            raison_sociale=emp.raison_sociale,
            type_regime_id=emp.type_regime_id,
            taux_pat_cnaps=emp.taux_pat_cnaps,
            taux_pat_smie=emp.taux_pat_smie,
            plafond_cnaps_base=emp.plafond_cnaps_base,
            plafond_smie=emp.plafond_smie,
            etablissements=emp.etablissements,
            departements=emp.departements,
            services=emp.services,
            unites=emp.unites,
            logo_path=emp.logo_path,
        )
        # Detect regime change
        old_regime_id = emp.type_regime_id
        new_regime_id = data.type_regime_id
        
        # Convert organizational lists to JSON strings
        data_dict = data.dict()
        data_dict['etablissements'] = json.dumps(data.etablissements or [])
        data_dict['departements'] = json.dumps(data.departements or [])
        data_dict['services'] = json.dumps(data.services or [])
        data_dict['unites'] = json.dumps(data.unites or [])
        
        # Update fields
        for key, value in data_dict.items():
            setattr(emp, key, value)
            
        # If regime changed, propagate to workers
        if new_regime_id and new_regime_id != old_regime_id:
            new_regime = db.query(models.TypeRegime).filter(models.TypeRegime.id == new_regime_id).first()
            if new_regime:
                workers = db.query(models.Worker).filter(models.Worker.employer_id == employer_id).all()
                for w in workers:
                    w.type_regime_id = new_regime.id
                    w.vhm = new_regime.vhm
                    # Update salary per hour
                    if w.vhm and w.vhm > 0:
                         w.salaire_horaire = w.salaire_base / w.vhm
        
        record_audit(
            db,
            actor=user,
            action="employer.update",
            entity_type="employer",
            entity_id=emp.id,
            route=f"/employers/{employer_id}",
            employer_id=emp.id,
            before=before,
            after=emp,
        )
        db.commit()
        db.refresh(emp)

        return _deserialize_lists(emp)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{employer_id}")
def delete_employer(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    _ensure_employer_scope(db, user, employer_id)
    emp = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employeur non trouvé")
    
    try:
        before = models.Employer(
            id=emp.id,
            raison_sociale=emp.raison_sociale,
            type_regime_id=emp.type_regime_id,
            logo_path=emp.logo_path,
        )
        db.delete(emp)
        record_audit(
            db,
            actor=user,
            action="employer.delete",
            entity_type="employer",
            entity_id=employer_id,
            route=f"/employers/{employer_id}",
            employer_id=employer_id,
            before=before,
            after=None,
        )
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        # Check foreign key constraints (e.g., linked workers)
        if "foreign key" in str(e).lower():
             raise HTTPException(status_code=400, detail="Impossible de supprimer cet employeur car il a des salariés ou bulletins liés.")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{employer_id}/organizational-data/workers")
def get_workers_organizational_data(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """Récupère toutes les données organisationnelles réelles des salariés pour un employeur"""
    _ensure_employer_scope(db, user, employer_id)
    try:
        # Récupérer tous les salariés de l'employeur avec leurs données organisationnelles
        workers = db.query(models.Worker).filter(
            models.Worker.employer_id == employer_id
        ).all()
        
        # Extraire les valeurs uniques non nulles et non vides
        etablissements = set()
        departements = set()
        services = set()
        unites = set()
        
        for worker in workers:
            if worker.effective_etablissement and worker.effective_etablissement.strip():
                etablissements.add(worker.effective_etablissement.strip())
            if worker.effective_departement and worker.effective_departement.strip():
                departements.add(worker.effective_departement.strip())
            if worker.effective_service and worker.effective_service.strip():
                services.add(worker.effective_service.strip())
            if worker.effective_unite and worker.effective_unite.strip():
                unites.add(worker.effective_unite.strip())
        
        return {
            "etablissements": sorted(list(etablissements)),
            "departements": sorted(list(departements)),
            "services": sorted(list(services)),
            "unites": sorted(list(unites))
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la récupération des données organisationnelles: {str(e)}")

@router.get("/{employer_id}/organizational-data/hierarchical")
def get_hierarchical_organizational_data(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """Récupère les données organisationnelles depuis les structures hiérarchiques"""
    _ensure_employer_scope(db, user, employer_id)
    try:
        # Récupérer toutes les unités organisationnelles de l'employeur
        organizational_units = db.query(models.OrganizationalUnit).filter(
            models.OrganizationalUnit.employer_id == employer_id
        ).all()
        
        # Organiser par niveau
        etablissements = set()
        departements = set()
        services = set()
        unites = set()
        
        for unit in organizational_units:
            if unit.level == 'etablissement':
                etablissements.add(unit.name)
            elif unit.level == 'departement':
                departements.add(unit.name)
            elif unit.level == 'service':
                services.add(unit.name)
            elif unit.level == 'unite':
                unites.add(unit.name)
        
        return {
            "etablissements": sorted(list(etablissements)),
            "departements": sorted(list(departements)),
            "services": sorted(list(services)),
            "unites": sorted(list(unites))
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la récupération des données hiérarchiques: {str(e)}")

@router.get("/{employer_id}/organizational-data/filtered")
def get_filtered_organizational_data(
    employer_id: int,
    etablissement: str = None,
    departement: str = None,
    service: str = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """Récupère les données organisationnelles filtrées en cascade"""
    _ensure_employer_scope(db, user, employer_id)
    try:
        # Construire la requête de base
        query = db.query(models.Worker).filter(models.Worker.employer_id == employer_id)
        
        # Appliquer les filtres en cascade
        if etablissement:
            query = query.filter(models.Worker.etablissement == etablissement)
        if departement:
            query = query.filter(models.Worker.departement == departement)
        if service:
            query = query.filter(models.Worker.service == service)
        
        workers = query.all()
        
        # Extraire les valeurs uniques disponibles selon les filtres appliqués
        etablissements = set()
        departements = set()
        services = set()
        unites = set()
        
        for worker in workers:
            if worker.effective_etablissement and worker.effective_etablissement.strip():
                etablissements.add(worker.effective_etablissement.strip())
            if worker.effective_departement and worker.effective_departement.strip():
                departements.add(worker.effective_departement.strip())
            if worker.effective_service and worker.effective_service.strip():
                services.add(worker.effective_service.strip())
            if worker.effective_unite and worker.effective_unite.strip():
                unites.add(worker.effective_unite.strip())
        
        return {
            "etablissements": sorted(list(etablissements)),
            "departements": sorted(list(departements)),
            "services": sorted(list(services)),
            "unites": sorted(list(unites))
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la récupération des données filtrées: {str(e)}")

@router.get("/{employer_id}/organizational-data/hierarchical-filtered")
def get_hierarchical_filtered_organizational_data(
    employer_id: int,
    etablissement: str = None,
    departement: str = None,
    service: str = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """Récupère les données organisationnelles filtrées en cascade depuis les structures hiérarchiques"""
    _ensure_employer_scope(db, user, employer_id)
    try:
        # Récupérer toutes les unités organisationnelles de l'employeur
        all_units = db.query(models.OrganizationalUnit).filter(
            models.OrganizationalUnit.employer_id == employer_id
        ).all()
        
        # Créer un dictionnaire pour accès rapide par ID
        units_by_id = {unit.id: unit for unit in all_units}
        
        # Fonction pour vérifier si une unité est descendante d'une autre (par nom et niveau)
        def is_descendant_of(unit, ancestor_name, ancestor_level):
            current = unit
            while current and current.parent_id:
                parent = units_by_id.get(current.parent_id)
                if not parent:
                    break
                if parent.level == ancestor_level and parent.name == ancestor_name:
                    return True
                current = parent
            return False
        
        # Fonction pour trouver une unité par nom et niveau
        def find_unit_by_name_and_level(name, level):
            for unit in all_units:
                if unit.name == name and unit.level == level:
                    return unit
            return None
        
        # Fonction pour obtenir tous les descendants d'une unité
        def get_all_descendants(unit_id):
            descendants = []
            for unit in all_units:
                if unit.parent_id == unit_id:
                    descendants.append(unit)
                    descendants.extend(get_all_descendants(unit.id))
            return descendants
        
        # Déterminer les unités à inclure selon les filtres
        units_to_include = []
        
        if service:
            # Si un service est spécifié, inclure seulement ce service et ses unités
            service_unit = find_unit_by_name_and_level(service, 'service')
            if service_unit:
                units_to_include.append(service_unit)
                units_to_include.extend(get_all_descendants(service_unit.id))
        elif departement:
            # Si un département est spécifié, inclure ce département et tous ses descendants
            dept_unit = find_unit_by_name_and_level(departement, 'departement')
            if dept_unit:
                units_to_include.append(dept_unit)
                units_to_include.extend(get_all_descendants(dept_unit.id))
        elif etablissement:
            # Si un établissement est spécifié, inclure cet établissement et tous ses descendants
            etab_unit = find_unit_by_name_and_level(etablissement, 'etablissement')
            if etab_unit:
                units_to_include.append(etab_unit)
                units_to_include.extend(get_all_descendants(etab_unit.id))
        else:
            # Aucun filtre, inclure toutes les unités
            units_to_include = all_units
        
        # Organiser par niveau
        etablissements = set()
        departements = set()
        services = set()
        unites = set()
        
        for unit in units_to_include:
            if unit.level == 'etablissement':
                etablissements.add(unit.name)
            elif unit.level == 'departement':
                departements.add(unit.name)
            elif unit.level == 'service':
                services.add(unit.name)
            elif unit.level == 'unite':
                unites.add(unit.name)
        
        return {
            "etablissements": sorted(list(etablissements)),
            "departements": sorted(list(departements)),
            "services": sorted(list(services)),
            "unites": sorted(list(unites))
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la récupération des données hiérarchiques filtrées: {str(e)}")

from fastapi import UploadFile, File
import os

@router.post("/{employer_id}/logo")
def upload_logo(
    employer_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    _ensure_employer_scope(db, user, employer_id)
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"logo_employer_{sanitize_filename_part(str(employer_id))}{file_extension}"
    save_upload_file(file.file, filename=filename)
    logo_url = build_static_path(filename)
    previous_logo_path = employer.logo_path
    employer.logo_path = logo_url
    record_audit(
        db,
        actor=user,
        action="employer.logo.update",
        entity_type="employer",
        entity_id=employer.id,
        route=f"/employers/{employer_id}/logo",
        employer_id=employer.id,
        before={"logo_path": previous_logo_path},
        after={"logo_path": logo_url},
    )
    db.commit()
    db.refresh(employer)
    
    return {"logo_path": logo_url}
