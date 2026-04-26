# backend/app/routers/payroll.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from ..config.config import get_db, settings
from .. import models
from .. import schemas as models_schemas
from ..payroll_logic import compute_preview
from ..leave_logic import get_leave_summary_for_period, get_permission_summary_for_period
from ..security import READ_PAYROLL_ROLES, can_access_worker, require_roles, user_has_any_role
from ..services.organizational_filters import apply_worker_hierarchy_filters
from ..services.payroll_period_service import (
    close_payroll_period,
    ensure_payroll_period_open,
    format_period,
    get_or_create_payroll_period,
    payroll_period_write_guard,
    reopen_payroll_period,
)
from datetime import datetime, date

router = APIRouter(prefix="/payroll", tags=["payroll"])
PAYROLL_BULK_ROLES = {"admin", "rh", "comptable", "employeur", "manager"}


def _parse_node_id(raw_value) -> int | None:
    if raw_value is None:
        return None
    text_value = str(raw_value).strip()
    if not text_value:
        return None
    try:
        return int(text_value)
    except (TypeError, ValueError):
        return None


def _collect_worker_node_ids(db: Session, employer_id: int, worker) -> set[int]:
    node_ids = {
        _parse_node_id(getattr(worker, "etablissement", None)),
        _parse_node_id(getattr(worker, "departement", None)),
        _parse_node_id(getattr(worker, "service", None)),
        _parse_node_id(getattr(worker, "unite", None)),
    }
    seed_ids = {node_id for node_id in node_ids if node_id is not None}
    if not seed_ids:
        return set()

    nodes = db.query(models.OrganizationalNode).filter(
        models.OrganizationalNode.id.in_(seed_ids),
        models.OrganizationalNode.employer_id == employer_id,
    ).all()
    by_id = {node.id: node for node in nodes}

    collected: set[int] = set()
    for node_id in seed_ids:
        current = by_id.get(node_id)
        visited: set[int] = set()
        while current is not None and current.id not in visited:
            collected.add(current.id)
            visited.add(current.id)
            parent_id = current.parent_id
            current = by_id.get(parent_id)
            if current is None and parent_id is not None:
                current = db.query(models.OrganizationalNode).filter(
                    models.OrganizationalNode.id == parent_id,
                    models.OrganizationalNode.employer_id == employer_id,
                ).first()
                if current is not None:
                    by_id[current.id] = current
    return collected


def _collect_worker_unit_ids(db: Session, employer_id: int, worker) -> set[int]:
    seed_id = getattr(worker, "organizational_unit_id", None)
    if not seed_id:
        return set()

    current = db.query(models.OrganizationalUnit).filter(
        models.OrganizationalUnit.id == seed_id,
        models.OrganizationalUnit.employer_id == employer_id,
        models.OrganizationalUnit.is_active == True,
    ).first()
    collected: set[int] = set()
    visited: set[int] = set()
    while current is not None and current.id not in visited:
        collected.add(current.id)
        visited.add(current.id)
        current = current.parent
    return collected


def _is_prime_applicable_to_worker(
    db: Session,
    employer_id: int,
    prime,
    worker,
    link_map: dict[int, tuple[bool, str]],
    target_node_ids: set[int],
    target_unit_ids: set[int],
) -> bool:
    link_state = link_map.get(getattr(prime, "id", None))
    link_is_active = link_state[0] if link_state else True
    link_type = link_state[1] if link_state else "include"
    if not link_is_active:
        return False

    target_mode = getattr(prime, "target_mode", "global") or "global"
    if target_mode == "individual":
        return link_type == "include" and link_state is not None

    if link_type == "exclude":
        return False

    if target_mode == "segment":
        worker_node_ids = _collect_worker_node_ids(db, employer_id, worker)
        worker_unit_ids = _collect_worker_unit_ids(db, employer_id, worker)
        return bool(worker_node_ids.intersection(target_node_ids) or worker_unit_ids.intersection(target_unit_ids))

    return True


def _filter_runs_for_user(query, db: Session, user: models.AppUser):
    if user_has_any_role(db, user, "admin", "rh", "comptable", "audit"):
        return query
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        return query.filter(models.PayrollRun.employer_id == user.employer_id)
    if user.worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        if worker:
            return query.filter(models.PayrollRun.employer_id == worker.employer_id)
    return query.filter(models.PayrollRun.id == -1)

@router.post("/get-or-create-run", response_model=models_schemas.PayrollRunOut)
@payroll_period_write_guard
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
    if user_has_any_role(db, user, "employeur") and user.employer_id != employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if user_has_any_role(db, user, "manager"):
        manager_worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        if not manager_worker or manager_worker.employer_id != employer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    ensure_payroll_period_open(db, employer_id, period=period)

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


@router.get("/periods/{employer_id}/{year}/{month}", response_model=models_schemas.PayrollPeriodOut)
def get_payroll_period_status(
    employer_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_BULK_ROLES)),
):
    if user_has_any_role(db, user, "employeur") and user.employer_id != employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_or_create_payroll_period(db, employer_id, month, year)


@router.post("/periods/{employer_id}/{year}/{month}/close", response_model=models_schemas.PayrollPeriodCloseOut)
def close_payroll_period_endpoint(
    employer_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "drh", "rh", "comptable", "employeur")),
):
    if user_has_any_role(db, user, "employeur") and user.employer_id != employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    period, archived_count = close_payroll_period(db, employer_id, month, year, closed_by_user_id=user.id)
    return models_schemas.PayrollPeriodCloseOut(period=period, archived_count=archived_count)


@router.post("/periods/{employer_id}/{year}/{month}/reopen", response_model=models_schemas.PayrollPeriodOut)
def reopen_payroll_period_endpoint(
    employer_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "drh", "rh")),
):
    if user_has_any_role(db, user, "employeur") and user.employer_id != employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return reopen_payroll_period(db, employer_id, month, year, reopened_by_user_id=user.id)


@router.get("/archives/{employer_id}/{year}/{month}", response_model=list[models_schemas.PayrollArchiveOut])
def get_payroll_archives(
    employer_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    if user_has_any_role(db, user, "employeur") and user.employer_id != employer_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    period_text = format_period(month, year)
    return (
        db.query(models.PayrollArchive)
        .filter(models.PayrollArchive.employer_id == employer_id, models.PayrollArchive.period == period_text)
        .order_by(models.PayrollArchive.worker_matricule.asc(), models.PayrollArchive.id.asc())
        .all()
    )

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


@router.get("/reverse-calculate")
def reverse_calculate_salary(
    worker_id: int = Query(...),
    period: str = Query(...),
    target_net: float = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Calcule le salaire de base nécessaire pour approcher un net cible.
    Ne persiste aucune modification dans la base.
    """
    if target_net <= 0:
        raise HTTPException(status_code=400, detail="target_net must be > 0")

    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    original_salary = float(worker.salaire_base or 0.0)
    original_hourly = float(worker.salaire_horaire or 0.0)

    min_salary = max(0.0, target_net * 0.5)
    max_salary = max(min_salary + 1.0, target_net * 2.0)
    tolerance = 1.0
    max_iterations = 60

    best_salary = original_salary if original_salary > 0 else (min_salary + max_salary) / 2.0
    best_net: Optional[float] = None
    best_preview = None

    def _evaluate(test_salary: float):
        worker.salaire_base = float(test_salary)
        if worker.vhm and float(worker.vhm) > 0:
            worker.salaire_horaire = float(test_salary) / float(worker.vhm)
        else:
            worker.salaire_horaire = original_hourly

        with db.no_autoflush:
            preview = generate_preview_data(worker_id, period, db)
        net_value = float(preview.get("totaux", {}).get("net", 0.0) or 0.0)
        return net_value, preview

    iteration_count = 0
    try:
        for idx in range(max_iterations):
            iteration_count = idx + 1
            test_salary = (min_salary + max_salary) / 2.0
            calculated_net, preview = _evaluate(test_salary)

            if best_net is None or abs(calculated_net - target_net) < abs(best_net - target_net):
                best_salary = test_salary
                best_net = calculated_net
                best_preview = preview

            if abs(calculated_net - target_net) <= tolerance:
                break

            if calculated_net < target_net:
                min_salary = test_salary
            else:
                max_salary = test_salary

        final_net, final_preview = _evaluate(best_salary)
        if best_net is None or abs(final_net - target_net) <= abs(best_net - target_net):
            best_net = final_net
            best_preview = final_preview

        return {
            "target_net": round(target_net, 2),
            "calculated_base_salary": round(best_salary, 2),
            "actual_net": round(best_net or 0.0, 2),
            "difference": round((best_net or 0.0) - target_net, 2),
            "original_base_salary": round(original_salary, 2),
            "iterations": iteration_count,
            "preview": best_preview,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul inverse: {exc}")
    finally:
        worker.salaire_base = original_salary
        worker.salaire_horaire = original_hourly
        db.rollback()


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
    if user_has_any_role(db, user, "employeur") and user.employer_id != employer_id:
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
        link_map = {
            l.prime_id: (l.is_active, (l.link_type or "include"))
            for l in worker_links
        }
        prime_target_rows = db.query(models.PrimeOrganizationalTarget).join(
            models.Prime,
            models.Prime.id == models.PrimeOrganizationalTarget.prime_id,
        ).filter(models.Prime.employer_id == employer.id).all()
        target_unit_map: dict[int, set[int]] = {}
        for row in prime_target_rows:
            target_unit_map.setdefault(row.prime_id, set()).add(row.node_id)

        prime_unit_target_rows = db.query(models.PrimeOrganizationalUnitTarget).join(
            models.Prime,
            models.Prime.id == models.PrimeOrganizationalUnitTarget.prime_id,
        ).filter(models.Prime.employer_id == employer.id).all()
        target_organizational_unit_map: dict[int, set[int]] = {}
        for row in prime_unit_target_rows:
            target_organizational_unit_map.setdefault(row.prime_id, set()).add(row.organizational_unit_id)
        
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
            is_active_for_worker = _is_prime_applicable_to_worker(
                db,
                employer.id,
                gp,
                worker,
                link_map,
                target_unit_map.get(gp.id, set()),
                target_organizational_unit_map.get(gp.id, set()),
            )
            
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

        def _resolve_node_name(raw_value):
            if not raw_value:
                return None
            text_value = str(raw_value).strip()
            if not text_value:
                return None
            try:
                node_id = int(text_value)
            except (TypeError, ValueError):
                return text_value

            node = db.query(models.OrganizationalNode).filter(
                models.OrganizationalNode.id == node_id
            ).first()
            if node:
                return node.name
            return text_value

        effective_etablissement = worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement
        effective_departement = worker.effective_departement if hasattr(worker, "effective_departement") else worker.departement
        effective_service = worker.effective_service if hasattr(worker, "effective_service") else worker.service
        effective_unite = worker.effective_unite if hasattr(worker, "effective_unite") else worker.unite

        etablissement_name = _resolve_node_name(effective_etablissement)
        departement_name = _resolve_node_name(effective_departement)
        service_name = _resolve_node_name(effective_service)
        unite_name = _resolve_node_name(effective_unite)
        
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
                "etablissement": effective_etablissement,
                "departement": effective_departement,
                "service": effective_service,
                "unite": effective_unite,
                "etablissement_name": etablissement_name,
                "departement_name": departement_name,
                "service_name": service_name,
                "unite_name": unite_name,
            },
            "period": period,
            "lines": lines,
            "totaux": totals,
            "debug_constants": debug_csts,
            "hs_hm": hs_hm_data,
            "leave": leave_summary,
            "permission": permission_summary
        }
        return result
    except Exception as e:
        raise HTTPException(500, f"Internal Server Error: {str(e)}")

