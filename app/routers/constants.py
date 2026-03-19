"""
Router pour l'accès au référentiel centralisé de constantes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from ..config.config import get_db
from ..constants import (
    PAYROLL_CONSTANTS,
    BUSINESS_CONSTANTS, 
    DOCUMENT_FIELDS,
    DOCUMENT_TEMPLATES,
    VALIDATION_CONSTANTS
)

router = APIRouter(prefix="/constants", tags=["constants"])

@router.get("/payroll")
def get_payroll_constants() -> Dict[str, Any]:
    """
    Retourne toutes les constantes relatives à la paie
    """
    return PAYROLL_CONSTANTS

@router.get("/business")
def get_business_constants() -> Dict[str, Any]:
    """
    Retourne toutes les constantes métier
    """
    return BUSINESS_CONSTANTS

@router.get("/document-fields")
def get_document_fields() -> Dict[str, Any]:
    """
    Retourne tous les champs disponibles pour les documents
    """
    return DOCUMENT_FIELDS

@router.get("/document-templates")
def get_document_templates() -> Dict[str, Any]:
    """
    Retourne tous les templates de documents prédéfinis
    """
    return DOCUMENT_TEMPLATES

@router.get("/validation")
def get_validation_constants() -> Dict[str, Any]:
    """
    Retourne toutes les constantes de validation
    """
    return VALIDATION_CONSTANTS

@router.get("/dropdowns/{field_name}")
def get_dropdown_options(field_name: str) -> List[Dict[str, Any]]:
    """
    Retourne les options d'une liste déroulante spécifique
    """
    if field_name not in VALIDATION_CONSTANTS["dropdowns"]:
        raise HTTPException(status_code=404, detail=f"Dropdown '{field_name}' not found")
    
    return VALIDATION_CONSTANTS["dropdowns"][field_name]

@router.get("/formulas")
def get_predefined_formulas() -> Dict[str, str]:
    """
    Retourne les formules prédéfinies pour les calculs de paie
    """
    return PAYROLL_CONSTANTS["formules"]

@router.get("/variables")
def get_formula_variables() -> Dict[str, str]:
    """
    Retourne les variables disponibles dans les formules
    """
    return PAYROLL_CONSTANTS["variables"]

@router.get("/field-categories")
def get_field_categories() -> Dict[str, List[Dict[str, str]]]:
    """
    Retourne les champs regroupés par catégorie pour l'interface
    """
    categories = {}
    
    for section_name, section_fields in DOCUMENT_FIELDS.items():
        for field_name, field_info in section_fields.items():
            category = field_info["category"]
            if category not in categories:
                categories[category] = []
            
            categories[category].append({
                "key": f"{section_name}.{field_name}",
                "label": field_info["label"],
                "type": field_info["type"],
                "description": field_info["description"]
            })
    
    return categories

@router.get("/worker-data/{worker_id}")
def get_worker_constants(worker_id: int, db: Session = Depends(get_db)):
    """
    Retourne les données d'un travailleur formatées pour l'insertion dans les documents
    """
    from .. import models
    
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Formater les données selon les constantes
    worker_data = {
        "matricule": worker.matricule,
        "nom": worker.nom,
        "prenom": worker.prenom,
        "nom_complet": f"{worker.prenom} {worker.nom}",
        "sexe": "Masculin" if worker.sexe == "M" else "Féminin",
        "date_naissance": worker.date_naissance.strftime("%d/%m/%Y") if worker.date_naissance else "",
        "lieu_naissance": worker.lieu_naissance or "",
        "adresse": worker.adresse or "",
        "cin": worker.cin or "",
        "cnaps": worker.cnaps_num or "",
        "date_embauche": worker.date_embauche.strftime("%d/%m/%Y") if worker.date_embauche else "",
        "poste": worker.poste or "",
        "categorie_prof": worker.categorie_prof or "",
        "salaire_base": f"{worker.salaire_base:,.0f} Ar" if worker.salaire_base else "0 Ar",
        "nature_contrat": worker.nature_contrat or "",
        # Champs organisationnels
        "etablissement": worker.etablissement or "",
        "departement": worker.departement or "",
        "service": worker.service or "",
        "unite": worker.unite or ""
    }
    
    return worker_data

@router.get("/employer-data/{employer_id}")
def get_employer_constants(employer_id: int, db: Session = Depends(get_db)):
    """
    Retourne les données d'un employeur formatées pour l'insertion dans les documents
    """
    from .. import models
    
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    # Formater les données selon les constantes
    employer_data = {
        "raison_sociale": employer.raison_sociale,
        "adresse": employer.adresse or "",
        "ville": employer.ville or "",
        "nif": employer.nif or "",
        "stat": employer.stat or "",
        "cnaps_num": employer.cnaps_num or "",
        "representant": employer.representant or "",
        "rep_fonction": employer.rep_fonction or ""
    }
    
    return employer_data

@router.get("/system-data")
def get_system_constants():
    """
    Retourne les données système (dates, etc.)
    """
    from datetime import datetime
    
    now = datetime.now()
    
    return {
        "date_aujourd_hui": now.strftime("%d/%m/%Y"),
        "annee_courante": str(now.year)
    }