from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any, Optional
from ..config.config import get_db
from .. import models, schemas
from .payroll import generate_preview_data
from ..security import can_access_worker, require_roles
from ..services.organizational_filters import apply_worker_hierarchy_filters
from datetime import datetime, date
import pandas as pd
import io
from fastapi.responses import StreamingResponse
import logging
import traceback

# Configuration du logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reporting", tags=["reporting"])
REPORTING_ROLES = {"admin", "rh", "comptable", "employeur", "manager"}


def _ensure_reporting_scope(db: Session, user: models.AppUser, employer_id: int):
    if user.role_code in {"admin", "rh", "comptable", "audit"}:
        return
    if user.role_code == "employeur" and user.employer_id == employer_id:
        return
    if user.role_code == "manager" and user.worker_id:
        manager_worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        if manager_worker and manager_worker.employer_id == employer_id:
            return
    raise HTTPException(status_code=403, detail="Forbidden")


def _prepare_report_columns(request: schemas.ReportRequest) -> List[str]:
    columns = list(dict.fromkeys(request.columns))
    if request.include_matricule and "matricule" not in columns:
        columns.insert(0, "matricule")
    return columns


def _build_report_filters(request: schemas.ReportRequest) -> Dict[str, Optional[str]]:
    return {
        "etablissement": request.etablissement,
        "departement": request.departement,
        "service": request.service,
        "unite": request.unite,
        "matricule_search": request.matricule_search,
        "worker_name_search": request.worker_name_search,
    }

def get_dynamic_journal_columns(employer_id: int, db: Session) -> List[str]:
    """
    Génère dynamiquement les colonnes pour l'État de paie en incluant
    toutes les primes définies pour l'employeur.
    """
    # Colonnes de base (identité et salaire)
    base_columns = [
        "matricule", "nom", "prenom", "cin", "cnaps_num", "date_embauche", "poste", "categorie_prof",
        "mode_paiement", "nombre_enfant", "etablissement", "departement", "service", "unite",  # Champs organisationnels ajoutés
        "salaire_base", "vhm"
    ]
    
    # Colonnes de gains (salaire et heures) - SANS les primes fixes supprimées
    gains_columns = [
        "Salaire de base",
        "HS Non Imposable 130%", "HS Imposable 130%", "HS Non Imposable 150%", "HS Imposable 150%",
        "Heures Majorées Nuit Hab. 30%", "Heures Majorées Nuit Occ. 50%",
        "Heures Majorées Dimanche 40%", "Heures Majorées Jours Fériés 50%"
    ]
    
    # Récupérer dynamiquement les primes de l'employeur
    employer_primes = db.query(models.Prime).filter(
        models.Prime.employer_id == employer_id,
        models.Prime.is_active == True
    ).order_by(models.Prime.label).all()
    
    # Ajouter les primes dynamiques (déplacées après Maj. JF 50%)
    dynamic_primes = [prime.label for prime in employer_primes]
    
    # Colonnes d'avantages en nature
    avantages_columns = [
        "Avantage en nature véhicule", "Avantage en nature logement", "Avantage en nature téléphone"
    ]
    
    # Colonnes de totaux et charges (avec réorganisation)
    totals_columns = [
        "brut_total",
        "Cotisation CNaPS", "Cotisation SMIE", 
        "Charges salariales",  # Déplacé juste après SMIE Salarié
        "Total CNaPS", "Total SMIE", 
        "IRSA", 
        "Avance sur salaire", "Avance sur salaire (quinzaine)", "Autres Déductions",
        "net_a_payer",
        "CNaPS Patronal", "SMIE Patronal", "FMFP Patronal", "Charges patronales",
        "cout_total_employeur"
    ]
    
    # Assembler toutes les colonnes dans le nouvel ordre
    return base_columns + gains_columns + dynamic_primes + avantages_columns + totals_columns


# Liste des colonnes standards pour un État de paie exhaustif (version statique pour compatibilité)
STANDARD_JOURNAL_COLUMNS = [
    "matricule", "nom", "prenom", "cin", "cnaps_num", "date_embauche", "poste", "categorie_prof",
    "mode_paiement", "nombre_enfant", "etablissement", "departement", "service", "unite",  # Champs organisationnels ajoutés
    "salaire_base", "vhm", "Salaire de base",
    "HS Non Imposable 130%", "HS Imposable 130%", "HS Non Imposable 150%", "HS Imposable 150%",
    "Heures Majorées Nuit Hab. 30%", "Heures Majorées Nuit Occ. 50%",
    "Heures Majorées Dimanche 40%", "Heures Majorées Jours Fériés 50%",
    # Primes dynamiques seront insérées ici par get_dynamic_journal_columns
    "Avantage en nature véhicule", "Avantage en nature logement", "Avantage en nature téléphone",
    "brut_total",
    "Cotisation CNaPS", "Cotisation SMIE", "Charges salariales",
    "Total CNaPS", "Total SMIE", 
    "IRSA", 
    "Avance sur salaire", "Avance sur salaire (quinzaine)", "Autres Déductions",
    "net_a_payer",
    "CNaPS Patronal", "SMIE Patronal", "FMFP Patronal", "Charges patronales", "cout_total_employeur"
]

@router.get("/metadata", response_model=schemas.ReportMetadataOut)
def get_report_metadata(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REPORTING_ROLES)),
):
    """
    Retourne la liste de toutes les colonnes disponibles pour le reporting.
    """
    try:
        _ensure_reporting_scope(db, user, employer_id)
        fields = []
        
        # --- Identité ---
        identity_fields = [
            ("matricule", "Matricule"), ("nom", "Nom"), ("prenom", "Prénom"),
            ("sexe", "Sexe"), ("adresse", "Adresse"), ("email", "Email"),
            ("telephone", "Téléphone"), ("cin", "CIN"), ("date_naissance", "Date Naissance"),
            ("date_embauche", "Date Embauche"), ("poste", "Poste"), ("categorie_prof", "Catégorie Professionnelle"),
            ("nature_contrat", "Nature Contrat"), ("mode_paiement", "Mode de Paiement"),
            ("cnaps_num", "N° CNaPS"), ("nombre_enfant", "Nombre d'enfants à charge")
        ]
        for fid, label in identity_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Identité"))

        # --- Structure Organisationnelle ---
        organizational_fields = [
            ("etablissement", "Établissement"), ("departement", "Département"),
            ("service", "Service"), ("unite", "Unité")
        ]
        for fid, label in organizational_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Structure Organisationnelle"))

        # --- Base ---
        base_fields = [
            ("salaire_base", "Salaire Base"), ("salaire_horaire", "Taux Horaire"),
            ("vhm", "VHM"), ("horaire_hebdo", "Horaire Hebdo")
        ]
        for fid, label in base_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Base"))

        # --- Gains ---
        rubric_fields = [
            ("Salaire de base", "Salaire de base"),
            ("HS Non Imposable 130%", "HSNI 130%"), ("HS Imposable 130%", "HSI 130%"),
            ("HS Non Imposable 150%", "HSNI 150%"), ("HS Imposable 150%", "HSI 150%"),
            ("Heures Majorées Nuit Hab. 30%", "Maj. Nuit 30%"),
            ("Heures Majorées Nuit Occ. 50%", "Maj. Nuit 50%"),
            ("Heures Majorées Dimanche 40%", "Maj. Dimanche 40%"),
            ("Heures Majorées Jours Fériés 50%", "Maj. JF 50%"),
            # Primes fixes supprimées : Prime fixe, Prime variable, 13ème mois, Allocation familiale
            ("Avantage en nature véhicule", "Avantage Véhicule"),
            ("Avantage en nature logement", "Avantage Logement"),
            ("Avantage en nature téléphone", "Avantage Téléphone"),
            ("Autres avantages en natures", "Autres Avantages")
        ]
        
        employer_primes = db.query(models.Prime).filter(models.Prime.employer_id == employer_id).all()
        for p in employer_primes:
            rubric_fields.append((p.label, p.label))
            
        for fid, label in rubric_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Gains"))

        # --- Retenues ---
        deduction_fields = [
            ("Cotisation CNaPS", "CNaPS Salarié"), ("Cotisation SMIE", "SMIE Salarié"),
            ("IRSA", "IRSA"), ("Avance sur salaire", "Avance sur salaire"),
            ("Avance sur salaire (quinzaine)", "Avance Quinzaine"),
            ("Avance spéciale (mensuelle)", "Avance Spéciale"),
            ("Autres Déductions", "Autres Déductions")
        ]
        for fid, label in deduction_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Retenues"))

        # --- Charges Patronales ---
        patronal_fields = [
            ("CNaPS Patronal", "CNaPS Patronal"), ("SMIE Patronal", "SMIE Patronal"),
            ("FMFP Patronal", "FMFP Patronal"), ("Charges patronales", "Total Charges Patronales")
        ]
        for fid, label in patronal_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Charges Patronales"))

        # --- Résultats ---
        result_fields = [
            ("brut_total", "TOTAL BRUT"), 
            ("Total CNaPS", "Total CNaPS (Sal. + Pat.)"), 
            ("Total SMIE", "Total SMIE (Sal. + Pat.)"),
            ("Charges salariales", "Total Charges Salariales"),
            ("net_a_payer", "NET À PAYER"),
            ("cout_total_employeur", "COÛT TOTAL EMPLOYEUR")
        ]
        for fid, label in result_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Résultats"))

        # --- Autres ---
        other_fields = [
            ("DAYSWORK", "Jours Travaillés"), ("leave_balance", "Solde Congés")
        ]
        for fid, label in other_fields:
            fields.append(schemas.ReportField(id=fid, label=label, category="Autres"))

        return schemas.ReportMetadataOut(fields=fields)
    except Exception as e:
        logger.error(f"Error in get_report_metadata: {e}")
        raise HTTPException(500, detail=str(e))

def get_full_report_data(
    employer_id: int, 
    start_period: str, 
    end_period: str, 
    selected_columns: List[str], 
    db: Session,
    filters: Optional[Dict] = None,
    viewer: Optional[models.AppUser] = None,
):
    try:
        start_dt = datetime.strptime(start_period, "%Y-%m").date()
        end_dt = datetime.strptime(end_period, "%Y-%m").date()
        
        months = []
        curr = start_dt
        while curr <= end_dt:
            months.append(curr.strftime("%Y-%m"))
            if curr.month == 12:
                curr = date(curr.year + 1, 1, 1)
            else:
                curr = date(curr.year, curr.month + 1, 1)
                
        # Base query for workers
        query = db.query(models.Worker).filter(models.Worker.employer_id == employer_id)
        
        query = apply_worker_hierarchy_filters(
            query,
            db,
            employer_id=employer_id,
            filters=filters,
        )

        if filters:
            matricule_search = filters.get("matricule_search")
            worker_name_search = filters.get("worker_name_search")
            if matricule_search:
                query = query.filter(models.Worker.matricule.ilike(f"%{matricule_search}%"))
            if worker_name_search:
                search_filter = f"%{worker_name_search}%"
                query = query.filter(
                    or_(
                        models.Worker.nom.ilike(search_filter),
                        models.Worker.prenom.ilike(search_filter),
                        models.Worker.matricule.ilike(search_filter),
                    )
                )

        workers = query.all()
        report_data = []
        
        worker_cols = [c for c in selected_columns if hasattr(models.Worker, c)]
        calc_cols = [c for c in selected_columns if c not in worker_cols]
        
        for idx, worker in enumerate(workers):
            if viewer and not can_access_worker(db, viewer, worker):
                continue
            if idx % 50 == 0:
                logger.info(f"Processing worker {idx+1}/{len(workers)} (Matricule: {worker.matricule})")
            
            worker_record = {"_worker_id": worker.id}
            
            # Static attributes
            for col_id in worker_cols:
                val = getattr(worker, col_id)
                if isinstance(val, (date, datetime)):
                    val = val.isoformat()
                worker_record[col_id] = val if val is not None else ""
            
            # Aggregated values
            # IMPORTANT: We only aggregate if there are calc_cols
            aggregated_values = {col: 0.0 for col in calc_cols}
            
            for period in months:
                try:
                    if calc_cols:
                        preview = generate_preview_data(worker.id, period, db)
                        if preview:
                            for col_id in calc_cols:
                                found = False
                                for line in preview.get("lines", []):
                                    label_norm = line["label"].lower()
                                    col_norm = col_id.lower()
                                    
                                    # Match exact label or heuristic for deductions
                                    if line["label"] == col_id or label_norm == col_norm:
                                        val = float(line.get("montant_sal", 0) or 0)
                                        aggregated_values[col_id] += abs(val) # Always positive in reports
                                        found = True
                                    elif col_id == "Avance sur salaire" and "avance" in label_norm:
                                        val = float(line.get("montant_sal", 0) or 0)
                                        aggregated_values[col_id] += abs(val)
                                        found = True
                                    elif col_id.endswith(" Patronal"):
                                        clean_label = col_id.replace(" Patronal", "")
                                        if clean_label in line["label"] or ("Cotisation " + clean_label) == line["label"]:
                                             aggregated_values[col_id] += float(line.get("montant_pat", 0) or 0)
                                             found = True
                                
                                # Totals Fallback (already handles match or ID mismatches)
                                if not found and col_id in preview.get("totaux", {}):
                                    aggregated_values[col_id] += abs(float(preview["totaux"][col_id] or 0))
                                elif not found:
                                    if col_id == "brut_total":
                                        aggregated_values[col_id] += float(preview["totaux"].get("brut", 0) or 0)
                                    elif col_id == "net_a_payer":
                                        aggregated_values[col_id] += float(preview["totaux"].get("net", 0) or 0)
                                    elif col_id == "cout_total_employeur":
                                        brut = float(preview["totaux"].get("brut", 0) or 0)
                                        pat = float(preview["totaux"].get("cotisations_patronales", 0) or 0)
                                        aggregated_values[col_id] += (brut + pat)
                                    elif col_norm == "irsa":
                                        aggregated_values[col_id] += abs(float(preview["totaux"].get("irsa", 0) or 0))
                                    # Nouvelles colonnes de totaux
                                    elif col_id == "Total CNaPS":
                                        cnaps_sal = abs(float(preview["totaux"].get("cotisations_salariales", 0) or 0))
                                        cnaps_pat = float(preview["totaux"].get("cotisations_patronales", 0) or 0)
                                        # Approximation: CNaPS représente généralement la majorité des cotisations
                                        aggregated_values[col_id] += (cnaps_sal + cnaps_pat)
                                    elif col_id == "Total SMIE":
                                        # Calculer SMIE total à partir des lignes spécifiques
                                        smie_sal = 0.0
                                        smie_pat = 0.0
                                        for line in preview.get("lines", []):
                                            if "SMIE" in line["label"]:
                                                smie_sal += abs(float(line.get("montant_sal", 0) or 0))
                                                smie_pat += float(line.get("montant_pat", 0) or 0)
                                        aggregated_values[col_id] += (smie_sal + smie_pat)
                                    elif col_id == "Charges salariales":
                                        aggregated_values[col_id] += abs(float(preview["totaux"].get("cotisations_salariales", 0) or 0))
                                    elif col_id == "Charges patronales":
                                        aggregated_values[col_id] += float(preview["totaux"].get("cotisations_patronales", 0) or 0)
                                
                                if col_id == "DAYSWORK":
                                    aggregated_values[col_id] += float(preview.get("debug_constants", {}).get("DAYSWORK", 0))
                                elif col_id == "leave_balance" and period == months[-1]:
                                    if "leave_summary" in preview and "balance" in preview["leave_summary"]:
                                        worker_record["leave_balance"] = preview["leave_summary"]["balance"]
                                    else:
                                        from ..leave_logic import calculate_leave_balance
                                        lb = calculate_leave_balance(db, worker.id, period)
                                        worker_record["leave_balance"] = lb.get("balance", 0.0)
                except Exception as e:
                    logger.debug(f"Skip period {period} for worker {worker.matricule}: {e}")
                    continue
            
            worker_record.update(aggregated_values)
            report_data.append(worker_record)
            
        return report_data
    except Exception as e:
        logger.error(f"Global error in get_full_report_data: {e}\n{traceback.format_exc()}")
        raise

@router.post("/generate")
def generate_report(
    request: schemas.ReportRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REPORTING_ROLES)),
):
    try:
        _ensure_reporting_scope(db, user, request.employer_id)
        filters = _build_report_filters(request)
        return get_full_report_data(
            request.employer_id,
            request.start_period,
            request.end_period,
            _prepare_report_columns(request),
            db,
            filters=filters,
            viewer=user,
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@router.post("/export-excel")
def export_report_excel(
    request: schemas.ReportRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REPORTING_ROLES)),
):
    try:
        _ensure_reporting_scope(db, user, request.employer_id)
        filters = _build_report_filters(request)
        data = get_full_report_data(
            request.employer_id,
            request.start_period,
            request.end_period,
            _prepare_report_columns(request),
            db,
            filters=filters,
            viewer=user,
        )
        return generate_excel_response(data, request.employer_id, f"{request.start_period}_to_{request.end_period}", db)
    except Exception as e:
        logger.error(f"Export Excel Error: {e}")
        raise HTTPException(500, detail=f"Export failed: {str(e)}")

@router.get("/journal-columns/{employer_id}")
def get_journal_columns(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REPORTING_ROLES)),
):
    """
    Retourne les colonnes dynamiques pour l'État de paie d'un employeur spécifique.
    """
    try:
        _ensure_reporting_scope(db, user, employer_id)
        columns = get_dynamic_journal_columns(employer_id, db)
        return {"columns": columns}
    except Exception as e:
        logger.error(f"Error getting journal columns: {e}")
        raise HTTPException(500, detail=str(e))

@router.get("/export-journal")
def export_journal(
    employer_id: int,
    period: str,
    etablissement: Optional[str] = None,
    departement: Optional[str] = None,
    service: Optional[str] = None,
    unite: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REPORTING_ROLES))
):
    try:
        # Utiliser les colonnes dynamiques basées sur les primes de l'employeur
        _ensure_reporting_scope(db, user, employer_id)
        dynamic_columns = get_dynamic_journal_columns(employer_id, db)
        
        filters = {
            "etablissement": etablissement,
            "departement": departement,
            "service": service,
            "unite": unite,
        }
        data = get_full_report_data(employer_id, period, period, dynamic_columns, db, filters=filters, viewer=user)
        return generate_excel_response(data, employer_id, period, db, is_journal=True)
    except Exception as e:
        logger.error(f"Export Journal Error: {e}")
        raise HTTPException(500, detail=f"Journal export failed: {str(e)}")

def generate_excel_response(data: List[Dict], employer_id: int, period: str, db: Session, is_journal: bool = False):
    if not data:
        raise HTTPException(404, "No results found.")
        
    try:
        df = pd.DataFrame(data)
        # Preserve specific column order for Journal
        if is_journal:
            # Utiliser l'ordre dynamique correct au lieu de STANDARD_JOURNAL_COLUMNS
            dynamic_columns = get_dynamic_journal_columns(employer_id, db)
            # Filtrer seulement les colonnes qui existent dans les résultats
            cols = [c for c in dynamic_columns if c in df.columns]
            # Ajouter les colonnes restantes qui ne sont pas dans dynamic_columns
            remaining_cols = [c for c in df.columns if not c.startswith("_") and c not in cols]
            df = df[cols + remaining_cols]
        else:
            df = df[[c for c in df.columns if not c.startswith("_")]]

        meta = get_report_metadata(employer_id, db)
        col_mapping = {f.id: f.label for f in meta.fields}
        df.rename(columns=col_mapping, inplace=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Paie')
            
            worksheet = writer.sheets['Paie']
            
            # Identifier les colonnes numériques pour le formatage
            numeric_columns = [
                'salaire_base', 'Salaire de base', 'brut_total', 
                'HS Non Imposable 130%', 'HS Imposable 130%', 'HS Non Imposable 150%', 'HS Imposable 150%',
                'Heures Majorées Nuit Hab. 30%', 'Heures Majorées Nuit Occ. 50%',
                'Heures Majorées Dimanche 40%', 'Heures Majorées Jours Fériés 50%',
                'Avantage en nature véhicule', 'Avantage en nature logement', 'Avantage en nature téléphone',
                'Cotisation CNaPS', 'CNaPS Patronal', 'Total CNaPS',
                'Cotisation SMIE', 'SMIE Patronal', 'Total SMIE', 
                'Charges salariales', 'Charges patronales',
                'IRSA', 'Avance sur salaire', 'net_a_payer', 'cout_total_employeur'
            ]
            
            for i, col in enumerate(df.columns):
                # Auto-adjust width (basic)
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                col_letter = chr(65 + (i % 26)) if i < 26 else chr(65 + (i // 26 - 1)) + chr(65 + (i % 26))
                worksheet.column_dimensions[col_letter].width = min(max_len, 40)
                
                # Appliquer le formatage numérique avec 2 décimales pour les colonnes monétaires
                original_col_name = None
                # Trouver le nom original de la colonne avant renommage
                for orig_name, mapped_name in col_mapping.items():
                    if mapped_name == col:
                        original_col_name = orig_name
                        break
                
                # Vérifier si c'est une colonne numérique (montant)
                is_numeric = (original_col_name and (
                    original_col_name in numeric_columns or 
                    'Prime' in original_col_name or 
                    '13ème' in original_col_name or 
                    'Avantage' in original_col_name
                )) or any(keyword in col.lower() for keyword in ['prime', '13ème', 'avantage', 'salaire', 'brut', 'cnaps', 'smie', 'irsa', 'avance', 'net', 'charges', 'coût'])
                
                if is_numeric:
                    # Appliquer le format numérique avec 2 décimales
                    for row_num in range(2, len(df) + 2):  # Commencer à la ligne 2 (après l'en-tête)
                        cell = worksheet[f'{col_letter}{row_num}']
                        cell.number_format = '#,##0.00'

        output.seek(0)
        filename = f"{'Journal' if is_journal else 'Reporting'}_{period}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error in generate_excel_response: {e}")
        raise


