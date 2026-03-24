"""
Router pour l'acces au referentiel centralise de constantes.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config.config import get_db
from .. import models
from ..constants import (
    BUSINESS_CONSTANTS,
    DOCUMENT_FIELDS,
    DOCUMENT_TEMPLATES,
    PAYROLL_CONSTANTS,
    VALIDATION_CONSTANTS,
)
from ..services.master_data_service import build_worker_document_payload
from ..security import READ_PAYROLL_ROLES, can_access_employer, can_access_worker, get_current_user, require_roles


router = APIRouter(
    prefix="/constants",
    tags=["constants"],
    dependencies=[Depends(require_roles(*READ_PAYROLL_ROLES))],
)


@router.get("/payroll")
def get_payroll_constants() -> Dict[str, Any]:
    return PAYROLL_CONSTANTS


@router.get("/business")
def get_business_constants() -> Dict[str, Any]:
    return BUSINESS_CONSTANTS


@router.get("/document-fields")
def get_document_fields() -> Dict[str, Any]:
    return DOCUMENT_FIELDS


@router.get("/document-templates")
def get_document_templates() -> Dict[str, Any]:
    return DOCUMENT_TEMPLATES


@router.get("/validation")
def get_validation_constants() -> Dict[str, Any]:
    return VALIDATION_CONSTANTS


@router.get("/dropdowns/{field_name}")
def get_dropdown_options(field_name: str) -> List[Dict[str, Any]]:
    if field_name not in VALIDATION_CONSTANTS["dropdowns"]:
        raise HTTPException(status_code=404, detail=f"Dropdown '{field_name}' not found")
    return VALIDATION_CONSTANTS["dropdowns"][field_name]


@router.get("/formulas")
def get_predefined_formulas() -> Dict[str, str]:
    return PAYROLL_CONSTANTS["formules"]


@router.get("/variables")
def get_formula_variables() -> Dict[str, str]:
    return PAYROLL_CONSTANTS["variables"]


@router.get("/field-categories")
def get_field_categories() -> Dict[str, List[Dict[str, str]]]:
    categories: Dict[str, List[Dict[str, str]]] = {}
    for section_name, section_fields in DOCUMENT_FIELDS.items():
        for field_name, field_info in section_fields.items():
            category = field_info["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(
                {
                    "key": f"{section_name}.{field_name}",
                    "label": field_info["label"],
                    "type": field_info["type"],
                    "description": field_info["description"],
                }
            )
    return categories


@router.get("/worker-data/{worker_id}")
def get_worker_constants(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    return build_worker_document_payload(db, worker)


@router.get("/employer-data/{employer_id}")
def get_employer_constants(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    if not can_access_employer(db, user, employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    return {
        "raison_sociale": employer.raison_sociale,
        "adresse": employer.adresse or "",
        "ville": employer.ville or "",
        "nif": employer.nif or "",
        "stat": employer.stat or "",
        "cnaps_num": employer.cnaps_num or "",
        "representant": employer.representant or "",
        "rep_fonction": employer.rep_fonction or "",
    }


@router.get("/system-data")
def get_system_constants():
    from datetime import datetime

    now = datetime.now()
    return {
        "date_aujourd_hui": now.strftime("%d/%m/%Y"),
        "annee_courante": str(now.year),
    }
