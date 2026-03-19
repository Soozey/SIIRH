# backend/app/routers/payroll.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from ..config.config import get_db, settings
from .. import models
from .. import schemas as models_schemas
from ..payroll_logic import compute_preview
from ..leave_logic import get_leave_summary_for_period, get_permission_summary_for_period
from ..security import READ_PAYROLL_ROLES, can_access_worker, require_roles
from ..services.organizational_filters import apply_worker_hierarchy_filters
from datetime import datetime, date

router = APIRouter(prefix="/payroll", tags=["payroll"])
PAYROLL_BULK_ROLES = {"admin", "rh", "comptable", "employeur", "manager"}


def _filter_runs_for_user(query, db: Session, user: models.AppUser):
    if user.role_code in {"admin", "rh", "comptable", "audit"}:
        return query
    if user.role_code == "employeur" and user.employer_id:
        return query.filter(models.PayrollRun.employer_id == user.employer_id)
    if user.worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        if worker:
            return query.filter(models.PayrollRun.employer_id == worker.employer_id)
    return query.filter(models.PayrollRun.id == -1)

@router.post("/get-or-create-run", response_model=models_schemas.PayrollRunOut)
def get_or_create_payroll_run_endpoint(
    period: str = Query(...),
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_BULK_ROLES)),
):
    """
    RÃ©cupÃ¨re un payroll_run existant pour (employer_id, period)
    ou en crÃ©e un nouveau s'il n'existe pas.
    """
    if user.role_code == "employeur" and user.employer_id != employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if user.role_code == "manager":
        manager_worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        if not manager_worker or manager_worker.employer_id != employer_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    run = db.query(models.PayrollRun).filter(
        models.PayrollRun.employer_id == employer_id,
        models.PayrollRun.period == period
    ).first()
    
    if not run:

        run = models.PayrollRun(
            employer_id=employer_id,
            period=period,
            generated_at=date.today()
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
    return run

@router.get("/runs", response_model=list[models_schemas.PayrollRunOut])
def get_all_payroll_runs(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_BULK_ROLES)),
):
    """Get all payroll runs ordered by period descending with employer name"""
    runs = _filter_runs_for_user(
        db.query(
        models.PayrollRun.id,
        models.PayrollRun.employer_id,
        models.PayrollRun.period,
        models.PayrollRun.generated_at,
        models.Employer.raison_sociale.label("employer_name")
    ).join(
        models.Employer, models.PayrollRun.employer_id == models.Employer.id
        ),
        db,
        user,
    ).order_by(models.PayrollRun.period.desc()).all()
    
    return runs


@router.get("/preview")
def payroll_preview(
    worker_id: int = Query(...),
    period: str = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    return generate_preview_data(worker_id, period, db)

@router.get("/bulk-preview")
def payroll_bulk_preview(
    employer_id: int = Query(...),
    period: str = Query(...),
    etablissement: Optional[str] = Query(None),
    departement: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    unite: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_BULK_ROLES)),
):
    if user.role_code == "employeur" and user.employer_id != employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Construire la requÃªte de base pour les travailleurs de l'employeur
    query = db.query(models.Worker).filter(models.Worker.employer_id == employer_id)
    
    query = apply_worker_hierarchy_filters(
        query,
        db,
        employer_id=employer_id,
        filters={
            "etablissement": etablissement,
            "departement": departement,
            "service": service,
            "unite": unite,
        },
    )
    
    # RÃ©cupÃ©rer les travailleurs filtrÃ©s
    workers = query.all()
    
    results = []
    for worker in workers:
        if not can_access_worker(db, user, worker):
            continue
        try:
            data = generate_preview_data(worker.id, period, db)
            results.append(data)
        except Exception as e:
            # Log error but continue processing other workers
            continue
    
    return results

def generate_preview_data(worker_id: int, period: str, db: Session):
    if not period or "-" not in period:
        raise HTTPException(400, "La pÃ©riode est requise (format YYYY-MM)")
        
    try:
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
    
        # RAW SQL Workaround for broken ORM
        from sqlalchemy import text
        sql = text("""
            SELECT label, formula_nombre, formula_base, formula_taux, operation_1, operation_2, is_active
            FROM worker_primes
            WHERE worker_id = :w
        """)
        raw_rows = db.execute(sql, {"w": worker_id}).fetchall()
        
        class SimplePrime:
            def __init__(self, row):
                self.label = row.label
                self.formula_nombre = row.formula_nombre
                self.formula_base = row.formula_base
                self.formula_taux = row.formula_taux
                self.operation_1 = row.operation_1
                self.operation_2 = row.operation_2
                self.is_active = row.is_active
    
        explicit_primes = [SimplePrime(row) for row in raw_rows]
        
        # RÃ©cupÃ©rer les donnÃ©es HS/HM si elles existent pour ce worker et cette pÃ©riode
        # Chercher un payroll_run pour cette pÃ©riode
        payroll_run = db.query(models.PayrollRun).filter(
            models.PayrollRun.employer_id == employer.id,
            models.PayrollRun.period == period
        ).first()
        
        hs_hm_data = None
        if payroll_run:
            # RÃ©cupÃ©rer les HS/HM pour ce worker
            hs_hm = db.query(models.PayrollHsHm).filter(
                models.PayrollHsHm.payroll_run_id == payroll_run.id,
                models.PayrollHsHm.worker_id == worker_id
            ).first()
            
            if hs_hm:
                # Fallback Calculation for Amounts if 0
                taux_h = worker.salaire_horaire
                # Fix: model uses 'vhm', not 'volume_horaire_mensuel'
                if not taux_h and getattr(worker, 'vhm', 0):
                     taux_h = worker.salaire_base / worker.vhm
                taux_h = taux_h or 0.0

                hs_config = [
                    ("hsni_130", 1.3), ("hsi_130", 1.3),
                    ("hsni_150", 1.5), ("hsi_150", 1.5),
                    ("hmnh", 0.3), ("hmno", 0.5),
                    ("hmd", 0.4), ("hmjf", 0.5)
                ]
                
                def _calc(h_val, m_val, coef):
                    if h_val > 0 and (not m_val or m_val == 0):
                        return h_val * taux_h * coef
                    return m_val

                hs_hm_data = {
                    "hsni_130_heures": float(hs_hm.hsni_130_heures),
                    "hsi_130_heures": float(hs_hm.hsi_130_heures),
                    "hsni_150_heures": float(hs_hm.hsni_150_heures),
                    "hsi_150_heures": float(hs_hm.hsi_150_heures),
                    "hmnh_heures": float(hs_hm.hmnh_heures),
                    "hmno_heures": float(hs_hm.hmno_heures),
                    "hmd_heures": float(hs_hm.hmd_heures),
                    "hmjf_heures": float(hs_hm.hmjf_heures),
                    
                    "hsni_130_montant": _calc(float(hs_hm.hsni_130_heures), float(hs_hm.hsni_130_montant), 1.3),
                    "hsi_130_montant": _calc(float(hs_hm.hsi_130_heures), float(hs_hm.hsi_130_montant), 1.3),
                    "hsni_150_montant": _calc(float(hs_hm.hsni_150_heures), float(hs_hm.hsni_150_montant), 1.5),
                    "hsi_150_montant": _calc(float(hs_hm.hsi_150_heures), float(hs_hm.hsi_150_montant), 1.5),
                    "hmnh_montant": _calc(float(hs_hm.hmnh_heures), float(hs_hm.hmnh_montant), 0.3),
                    "hmno_montant": _calc(float(hs_hm.hmno_heures), float(hs_hm.hmno_montant), 0.5),
                    "hmd_montant": _calc(float(hs_hm.hmd_heures), float(hs_hm.hmd_montant), 0.4),
                    "hmjf_montant": _calc(float(hs_hm.hmjf_heures), float(hs_hm.hmjf_montant), 0.5),
                    
                    "source_type": hs_hm.source_type,
                }

        # RÃ©cupÃ©rer les absences importÃ©es pour cette pÃ©riode
        absence_data = None
        absence_record = db.query(models.Absence).filter(
            models.Absence.worker_id == worker_id,
            models.Absence.mois == period
        ).first()
        
        if absence_record:
            absence_data = {
                "ABSM_J": float(absence_record.ABSM_J or 0),
                "ABSM_H": float(absence_record.ABSM_H or 0),
                "ABSNR_J": float(absence_record.ABSNR_J or 0),
                "ABSNR_H": float(absence_record.ABSNR_H or 0),
                "ABSMP": float(absence_record.ABSMP or 0),
                "ABS1_J": float(absence_record.ABS1_J or 0),
                "ABS1_H": float(absence_record.ABS1_H or 0),
                "ABS2_J": float(absence_record.ABS2_J or 0),
                "ABS2_H": float(absence_record.ABS2_H or 0),
            }

        # RÃ©cupÃ©rer les Overrides Primes (PayrollPrime)
        primes_overrides = {}
        payroll_primes = db.query(models.PayrollPrime).filter(
            models.PayrollPrime.worker_id == worker_id,
            models.PayrollPrime.period == period
        ).all()
        
        for pp in payroll_primes:
            primes_overrides[pp.prime_label] = {
                "nombre": float(pp.nombre) if pp.nombre is not None else None,
                "base": float(pp.base) if pp.base is not None else None
            }
        
        # RÃ©cupÃ©rer les avances importÃ©es pour cette pÃ©riode
        avance_data = None
        avance_record = db.query(models.Avance).filter(
            models.Avance.worker_id == worker_id,
            models.Avance.periode == period
        ).first()
        
        if avance_record:
            avance_data = {
                "montant": float(avance_record.montant or 0)
            }

        if avance_record:
            avance_data = {
                "montant": float(avance_record.montant or 0)
            }

        # Reuse the full overrides from earlier (which include nombre & base)
        primes_overrides_data = primes_overrides

        # --- FIX: Injecter les primes importÃ©es qui ne sont pas dans WorkerPrime (Orphelines) ---
        # NEW LOGIC: Use Global Primes + Worker Links
        
        # 1. Fetch Employer Primes
        global_primes = db.query(models.Prime).filter(models.Prime.employer_id == employer.id, models.Prime.is_active == True).all()
        
        # 2. Fetch Worker Links (Associations / Exclusions)
        worker_links = db.query(models.WorkerPrimeLink).filter(models.WorkerPrimeLink.worker_id == worker_id).all()
        link_map = {l.prime_id: l.is_active for l in worker_links}
        
        # 3. Construct "Effective Primes" list
        effective_primes = []
        
        class StartPrime:
            def __init__(self, p_model):
                self.label = p_model.label
                self.formula_nombre = p_model.formula_nombre
                self.formula_base = p_model.formula_base
                self.formula_taux = p_model.formula_taux
                self.operation_1 = getattr(p_model, "operation_1", "*")
                self.operation_2 = getattr(p_model, "operation_2", "*")
                self.is_active = True
                self.id = getattr(p_model, "id", None)
        
        # --- FUZZY MATCHING LOGIC ---
        # Normalize imported keys for lookup
        # Map normalized_key -> original_key (to retrieve data)
        imported_keys_map = {k.lower().strip(): k for k in primes_overrides_data.keys()}
        
        for gp in global_primes:
            # Check explicit link status
            is_active_for_worker = link_map.get(gp.id, True)
            
            # Check for data presence (Fuzzy)
            gp_label_norm = gp.label.lower().strip()
            original_key = imported_keys_map.get(gp_label_norm)
            
            has_data = original_key is not None
            
            # Fix Override Key Mismatch:
            # If we found data under a fuzzy key, but specific key doesn't exist in overrides,
            # we must inject the correct key so compute_preview finds it.
            if has_data and original_key != gp.label:
                # Add an alias in the overrides dict
                primes_overrides_data[gp.label] = primes_overrides_data[original_key]

            if is_active_for_worker or has_data:
                effective_primes.append(StartPrime(gp))

        # Add Legacy WorkerPrimes (if not already covered by Global Primes)
        # Use fuzzy check to avoid duplicates
        global_labels_norm = {gp.label.lower().strip() for gp in effective_primes}
        
        for wp in explicit_primes:
             if wp.label.lower().strip() not in global_labels_norm:
                  effective_primes.append(wp)
                  
        # Legacy Injection for purely imported primes (Orphans) that match NOTHING
        # Check against normalized effective labels
        effective_labels_norm = {p.label.lower().strip() for p in effective_primes}
        
        known_legacy_norm = set() 
        # ... logic for Prime 1..10 ... (simplified check)
        
        class FakeRow:
            def __init__(self, label):
                self.label = label
                self.formula_nombre = None
                self.formula_base = None
                self.formula_taux = None
                self.operation_1 = "*"
                self.operation_2 = "*"
                self.is_active = True

        for p_label in primes_overrides_data.keys():
             p_label_norm = p_label.lower().strip()
             if p_label_norm not in effective_labels_norm:
                  # This is truly an orphan (matches no Global nor Legacy)
                  effective_primes.append(SimplePrime(FakeRow(p_label)))

        # --- LOGIQUE DEBAUCHE / RUPTURE ---
        termination_data = None
        if worker.date_debauche:
            d_deb = worker.date_debauche
            period_date = datetime.strptime(period, "%Y-%m").date()
            
            # Calcul des indemnitÃ©s uniquement si le mois de dÃ©bauche correspond au mois de paie
            if d_deb.year == period_date.year and d_deb.month == period_date.month:
                from ..leave_logic import calculate_leave_balance
                # REMOVED: from dateutil.relativedelta import relativedelta (Package not installed)
                
                # 1. Solde de congÃ©s
                lb = calculate_leave_balance(db, worker_id, period)
                balance_days = lb.get("balance", 0.0)
                
                # 2. Historique des salaires bruts (12 derniers mois) for IndemnitÃ©s
                # On doit recomposer les bruts passÃ©s.
                # Attention : ceci est coÃ»teux, on le fait seulement pour un worker en cours de dÃ©part.
                
                past_bruts = []
                
                # On remonte 12 mois en arriÃ¨re (hors mois courant)
                # Logic sans dateutil
                curr_y = period_date.year
                curr_m = period_date.month
                
                # Go back 1 month first
                if curr_m == 1:
                    curr_y -= 1
                    curr_m = 12
                else:
                    curr_m -= 1
                
                current_loop_date = date(curr_y, curr_m, 1)
                
                # Loop 12 months back
                # Check Embauche to avoid counting pre-employment months as full salary (or 0)
                d_emb = worker.date_embauche
                
                for _ in range(12):
                    # If this loop month is strictly before embauche month, skip
                    # (On compare mois/annÃ©e)
                    loop_date_start = date(current_loop_date.year, current_loop_date.month, 1)
                    
                    # Simplification: si loop_year/month < emb_year/month, on ignore
                    if d_emb:
                        if (current_loop_date.year < d_emb.year) or \
                           (current_loop_date.year == d_emb.year and current_loop_date.month < d_emb.month):
                             # Go to previous month and continue
                             if current_loop_date.month == 1:
                                current_loop_date = date(current_loop_date.year - 1, 12, 1)
                             else:
                                current_loop_date = date(current_loop_date.year, current_loop_date.month - 1, 1)
                             continue

                    loop_period = current_loop_date.strftime("%Y-%m")
                    
                    brut_hist = 0.0
                    
                    # SYSTEME D : Reconstruction du brut (Approximation amÃ©liorÃ©e)
                    # Brut ~ Base Salary + Avantages + HS/HM + Primes
                    
                    # 1. Base Salary (On suppose constant car pas d'historique)
                    brut_hist += (worker.salaire_base or 0.0)

                    # 2. HS/HM (Amounts from PayrollHsHm)
                    # On cherche si un calcul HS HM enregistrÃ© existe
                    try:
                         hs_record = db.query(models.PayrollHsHm).join(models.PayrollRun).filter(
                             models.PayrollRun.period == loop_period,
                             models.PayrollHsHm.worker_id == worker_id
                         ).first()
                         
                         if hs_record:
                              total_hs_hm = (
                                  (hs_record.hsni_130_montant or 0) + 
                                  (hs_record.hsi_130_montant or 0) + 
                                  (hs_record.hsni_150_montant or 0) + 
                                  (hs_record.hsi_150_montant or 0) + 
                                  (hs_record.hmnh_montant or 0) + 
                                  (hs_record.hmno_montant or 0) + 
                                  (hs_record.hmd_montant or 0) + 
                                  (hs_record.hmjf_montant or 0)
                              )
                              brut_hist += float(total_hs_hm)
                    except Exception: 
                        pass 
                    
                    # 3. Primes & Avantages (from PayVar)
                    pvar_hist = db.query(models.PayVar).filter(
                        models.PayVar.worker_id == worker_id,
                        models.PayVar.period == loop_period
                    ).first()

                    if pvar_hist:
                         # Primes simples
                         brut_hist += (pvar_hist.prime_fixe or 0.0)
                         brut_hist += (pvar_hist.prime_variable or 0.0)
                         brut_hist += (pvar_hist.prime_13 or 0.0)
                         brut_hist += (pvar_hist.alloc_familiale or 0.0)

                         # Primes 1..10
                         for i in range(1, 11):
                             val = getattr(pvar_hist, f"prime{i}", 0.0)
                             if val: brut_hist += float(val)
                        
                         # Avantages en nature
                         av_veh = (pvar_hist.avantage_vehicule or 0.0)
                         if av_veh == 0: av_veh = (worker.avantage_vehicule or 0.0)
                         
                         av_log = (pvar_hist.avantage_logement or 0.0)
                         if av_log == 0: av_log = (worker.avantage_logement or 0.0)

                         av_tel = (pvar_hist.avantage_telephone or 0.0)
                         if av_tel == 0: av_tel = (worker.avantage_telephone or 0.0)

                         av_aut = (pvar_hist.avantage_autres or 0.0)
                         if av_aut == 0: av_aut = (worker.avantage_autres or 0.0)
                         
                         brut_hist += (av_veh + av_log + av_tel + av_aut)
                    
                    else:
                        # Fallback Avantages Worker Defaults
                         brut_hist += (worker.avantage_vehicule or 0.0)
                         brut_hist += (worker.avantage_logement or 0.0)
                         brut_hist += (worker.avantage_telephone or 0.0)
                         brut_hist += (worker.avantage_autres or 0.0)

                    past_bruts.append(brut_hist)
                    
                    # Previous Month Logic
                    if current_loop_date.month == 1:
                        current_loop_date = date(current_loop_date.year - 1, 12, 1)
                    else:
                        current_loop_date = date(current_loop_date.year, current_loop_date.month - 1, 1)
                
                # Moyennes
                count_12 = len(past_bruts)
                avg_12 = sum(past_bruts) / count_12 if count_12 > 0 else worker.salaire_base
                
                # 2 derniers mois
                # past_bruts[0] est M-1, past_bruts[1] est M-2...
                # Si count < 2, on prend ce qu'on a
                relevant_2 = past_bruts[:2]
                count_2 = len(relevant_2)
                avg_2 = sum(relevant_2) / count_2 if count_2 > 0 else worker.salaire_base
                
                termination_data = {
                    "avg_gross_12": avg_12,
                    "avg_gross_2": avg_2,
                    "leave_balance": balance_days,
                    "date_debauche": d_deb,
                    "type_sortie": getattr(worker, "type_sortie", "L"),
                    "groupe_preavis": getattr(worker, "groupe_preavis", 1),
                    "jours_deja_faits": getattr(worker, "jours_preavis_deja_faits", 0),
                    "nature_contrat": getattr(worker, "nature_contrat", "CDI")
                }

        lines, totals, debug_csts = compute_preview(
            employer, worker, payvar, period, 
            custom_primes_override=effective_primes, 
            hs_hm_dict=hs_hm_data,
            absence_dict=absence_data,
            avance_dict=avance_data,
            primes_overrides=primes_overrides_data,
            termination_data=termination_data
        )

        
        # Fetch leave and permission summaries
        leave_summary = get_leave_summary_for_period(db, worker_id, period)
        permission_summary = get_permission_summary_for_period(db, worker_id, period)

        # RÃ©cupÃ©rer les noms des structures organisationnelles
        etablissement_name = None
        departement_name = None
        service_name = None
        unite_name = None
        
        if worker.etablissement:
            try:
                etab_id = int(worker.etablissement)
                etab_node = db.query(models.OrganizationalNode).filter(
                    models.OrganizationalNode.id == etab_id
                ).first()
                if etab_node:
                    etablissement_name = etab_node.name
            except (ValueError, TypeError):
                pass
        
        if worker.departement:
            try:
                dept_id = int(worker.departement)
                dept_node = db.query(models.OrganizationalNode).filter(
                    models.OrganizationalNode.id == dept_id
                ).first()
                if dept_node:
                    departement_name = dept_node.name
            except (ValueError, TypeError):
                pass
        
        if worker.service:
            try:
                serv_id = int(worker.service)
                serv_node = db.query(models.OrganizationalNode).filter(
                    models.OrganizationalNode.id == serv_id
                ).first()
                if serv_node:
                    service_name = serv_node.name
            except (ValueError, TypeError):
                pass
        
        if worker.unite:
            try:
                unite_id = int(worker.unite)
                unite_node = db.query(models.OrganizationalNode).filter(
                    models.OrganizationalNode.id == unite_id
                ).first()
                if unite_node:
                    unite_name = unite_node.name
            except (ValueError, TypeError):
                pass
        
        result = {
            "employer": {
                "id": employer.id,
                "raison_sociale": employer.raison_sociale,
                "adresse": employer.adresse,
                "ville": employer.ville,
                "nif": employer.nif,
                "stat": employer.stat,
                "cnaps": employer.cnaps_num,
                "logo_path": employer.logo_path
            },
            "worker": {
                "id": worker.id,
                "matricule": worker.matricule,
                "nom": worker.nom,
                "prenom": worker.prenom,
                "adresse": worker.adresse,
                "poste": worker.poste,
                "categorie_prof": worker.categorie_prof,
                "date_embauche": worker.date_embauche,
                "cnaps": worker.cnaps_num,
                "secteur": worker.secteur,
                "mode_paiement": worker.mode_paiement,
                "etablissement": worker.etablissement,
                "departement": worker.departement,
                "service": worker.service,
                "unite": worker.unite,
                "etablissement_name": etablissement_name,
                "departement_name": departement_name,
                "service_name": service_name,
                "unite_name": unite_name,
            },
            "period": period,
            "lines": lines,
            "totaux": totals,
            "hs_hm": hs_hm_data,
            "leave": leave_summary,
            "permission": permission_summary
        }
        return result
    except Exception as e:
        raise HTTPException(500, f"Internal Server Error: {str(e)}")

