from datetime import date, time, timedelta, datetime, timezone
from typing import List, Literal, Optional, Dict, Tuple
from decimal import Decimal
from io import BytesIO
import unicodedata
import pandas as pd

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ..config.config import get_db
from .. import models
from ..models import HSCalculationHS, PayrollHsHm, PayrollRun, CalendarDay
from ..schemas import HSCalculationReadHS
from ..security import PAYROLL_WRITE_ROLES, READ_PAYROLL_ROLES, can_access_worker, require_roles


router = APIRouter(
    prefix="/hs",
    tags=["Heures SupplÃ©mentaires HS"],
)


def _filter_hs_for_user(db: Session, user: models.AppUser, rows: List[HSCalculationHS]) -> List[HSCalculationHS]:
    worker_cache = {}
    allowed = []
    for row in rows:
        worker_id = row.worker_id_HS
        worker = row.worker
        if worker is None and worker_id not in worker_cache:
            worker_cache[worker_id] = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        worker = worker or worker_cache.get(worker_id)
        if worker and can_access_worker(db, user, worker):
            allowed.append(row)
    return allowed


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/all", response_model=List[HSCalculationReadHS])
def get_all_hs_calculations_HS(
    worker_id: Optional[int] = Query(None),
    mois: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
) -> List[HSCalculationReadHS]:
    """
    Endpoint API :
    GET /hs/all

    -> renvoie TOUS les enregistrements hs_calculations_HS
       (triÃ©s du plus rÃ©cent au plus ancien).
    """
    query = db.query(HSCalculationHS).options(joinedload(HSCalculationHS.worker))
    if worker_id is not None:
        query = query.filter(HSCalculationHS.worker_id_HS == worker_id)
    if mois:
        query = query.filter(HSCalculationHS.mois_HS == mois)
    calculs_HS = query.order_by(HSCalculationHS.created_at_HS.desc()).all()
    return _filter_hs_for_user(db, user, calculs_HS)


class HSUpdateRequestHS(BaseModel):
    total_HSNI_130_heures_HS: Optional[float] = None
    total_HSI_130_heures_HS: Optional[float] = None
    total_HSNI_150_heures_HS: Optional[float] = None
    total_HSI_150_heures_HS: Optional[float] = None
    total_HMNH_30_heures_HS: Optional[float] = None
    total_HMNO_50_heures_HS: Optional[float] = None
    total_HMD_40_heures_HS: Optional[float] = None
    total_HMJF_50_heures_HS: Optional[float] = None


@router.put("/{hs_id}", response_model=HSCalculationReadHS)
def update_hs_calculation_HS(
    hs_id: int,
    body: HSUpdateRequestHS,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
) -> HSCalculationReadHS:
    calc_db_HS = db.query(HSCalculationHS).filter(HSCalculationHS.id_HS == hs_id).first()
    if not calc_db_HS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calcul HS id_HS={hs_id} introuvable.",
        )
    worker = db.query(models.Worker).filter(models.Worker.id == calc_db_HS.worker_id_HS).first()
    if not worker or not can_access_worker(db, user, worker):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    fields = [
        "total_HSNI_130_heures_HS",
        "total_HSI_130_heures_HS",
        "total_HSNI_150_heures_HS",
        "total_HSI_150_heures_HS",
        "total_HMNH_30_heures_HS",
        "total_HMNO_50_heures_HS",
        "total_HMD_40_heures_HS",
        "total_HMJF_50_heures_HS",
    ]
    for field in fields:
        val = getattr(body, field)
        if val is not None:
            setattr(calc_db_HS, field, val)

    calc_db_HS.updated_at_HS = _utcnow()
    db.commit()
    db.refresh(calc_db_HS)
    return calc_db_HS


@router.delete("/{hs_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hs_calculation_HS(
    hs_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
) -> None:
    """
    Endpoint API :
    DELETE /hs/{hs_id}

    -> supprime un enregistrement hs_calculations_HS par son id_HS.
    Retourne 204 NO CONTENT si tout se passe bien.
    """

    calc_HS = (
        db.query(HSCalculationHS)
        .filter(HSCalculationHS.id_HS == hs_id)
        .first()
    )

    if calc_HS is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calcul HS id_HS={hs_id} introuvable.",
        )
    worker = db.query(models.Worker).filter(models.Worker.id == calc_HS.worker_id_HS).first()
    if not worker or not can_access_worker(db, user, worker):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        db.query(PayrollHsHm).filter(PayrollHsHm.hs_calculation_id == hs_id).delete(synchronize_session=False)
        db.delete(calc_HS)
        db.commit()
    except Exception:
        db.rollback()
        raise
    # 204 -> pas de contenu Ã  retourner
    return



# --------- ðŸ“Œ ModÃ¨les Pydantic (avec suffixe HS) ---------


class HSJourInputHS(BaseModel):
    """DonnÃ©es d'une journÃ©e de travail pour le calcul des HS."""

    date_HS: date = Field(..., description="Date de la journÃ©e")
    type_jour_HS: Literal["N", "JF", "F"] = Field(
        "N", description="Type de jour: N = Normal, JF = Jour FÃ©riÃ©, F = FermÃ©"
    )
    entree_HS: time = Field(..., description="Heure d'entrÃ©e")
    sortie_HS: time = Field(..., description="Heure de sortie")
    type_nuit_HS: Optional[Literal["H", "O"]] = Field(
        None,
        description=(
            "Type de nuit aprÃ¨s 22h : "
            "H = Nuit habituelle, O = Nuit occasionnelle. "
            "Laisser vide si pas de nuit."
        ),
    )
    duree_pause_minutes_HS: int = Field(
        60,
        description="DurÃ©e de la pause en minutes (par dÃ©faut 60 = 1h)"
    )



class HSCalculationRequestHS(BaseModel):
    """
    RequÃªte pour calculer les heures sup / majorations sur un mois.

    On laisse volontairement simple (sans Field()) pour Ã©viter
    les soucis de compatibilitÃ© Pydantic.
    """

    # Identifiant du salariÃ©
    worker_id_HS: int

    # Mois de paie, ex: "2025-07"
    mois_HS: str

    # DurÃ©e hebdomadaire contractuelle en heures (par ex. 40 ou 48)
    base_hebdo_heures_HS: float = 40.0

    # Liste des jours Ã  traiter pour le calcul HS
    jours_HS: List[HSJourInputHS]
    mode_nuit_HS: Optional[Literal["H", "O"]] = None
    employer_id_HS: Optional[int] = None


class HSCalculationResultHS(BaseModel):
    """RÃ©sultat global mensuel en heures dÃ©cimales."""

    worker_id_HS: int
    mois_HS: str

    # HS NI / I
    total_HSNI_130_heures_HS: float
    total_HSI_130_heures_HS: float
    total_HSNI_150_heures_HS: float
    total_HSI_150_heures_HS: float

    # Heures majorÃ©es
    total_HMNH_30_heures_HS: float
    total_HMNO_50_heures_HS: float
    total_HMD_40_heures_HS: float
    total_HMJF_50_heures_HS: float


class HSImportPreviewRowHS(BaseModel):
    worker_id_HS: Optional[int] = None
    matricule: str
    nom: str
    date_HS: str
    type_jour_HS: Literal["N", "JF", "F"] = "N"
    entree_HS: str
    sortie_HS: str
    type_nuit_HS: Optional[Literal["H", "O"]] = None
    duree_pause_minutes_HS: int = 60


class HSImportPreviewResponseHS(BaseModel):
    success: bool
    message: str
    rows_imported: int
    data: List[HSImportPreviewRowHS]
    errors: List[str] = []


def _normalize_column_name_hs_import(value: str) -> str:
    base = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(base.strip().lower().replace("_", " ").split())


def _canonicalize_hs_import_columns(columns: List[str]) -> Dict[str, str]:
    alias_to_target = {
        "matricule": "Matricule",
        "nom": "Nom",
        "date": "Date",
        "heure entree": "Heure entree",
        "heure d entree": "Heure entree",
        "heure sortie": "Heure sortie",
        "pause": "Pause",
        "pause min": "Pause",
        "pause minutes": "Pause",
        "type jour": "Type jour",
        "type de jour": "Type jour",
        "type nuit": "Type nuit",
    }
    mapping: Dict[str, str] = {}
    for original in columns:
        normalized = _normalize_column_name_hs_import(str(original))
        target = alias_to_target.get(normalized)
        if target:
            mapping[str(original)] = target
    return mapping


def _parse_time_string_hs_import(value: object) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if isinstance(value, (int, float)):
        total_seconds = float(value) * 24 * 3600
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return f"{hours:02d}:{minutes:02d}"
        return None

    text = str(value).strip().lower()
    if not text:
        return None
    text = text.replace("h", ":")
    if text.count(":") == 2:
        text = ":".join(text.split(":")[:2])
    if ":" not in text:
        try:
            only_hour = int(float(text))
            if 0 <= only_hour <= 23:
                return f"{only_hour:02d}:00"
        except ValueError:
            return None
    parts = text.split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(float(parts[0]))
        minute = int(float(parts[1]))
    except ValueError:
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return None


def _parse_date_string_hs_import(value: object) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()
    if not text:
        return None
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            parsed = datetime.strptime(text, date_format)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# --------- ðŸ”§ Fonctions internes (conversion temps) ---------


def _time_to_td_HS(t: time) -> timedelta:
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


def _td_to_hours_HS(td: timedelta) -> float:
    return td.total_seconds() / 3600.0


class _WeekAggHS:
    """Accumulation par semaine (interne)."""

    def __init__(self) -> None:
        # DurÃ©e des jours normaux (hors dimanche & JF) jusqu'Ã  22h
        self.duree_sans_nuit_HS = timedelta(0)
        # Heures de nuit habituelles (jours normaux uniquement)
        self.hmnh_HS = timedelta(0)
        # Heures de nuit occasionnelles (jours normaux uniquement)
        self.hmno_HS = timedelta(0)


# --------- ðŸ§  Coeur du calcul : traduction des formules Excel ---------


def calculer_heures_supplementaires_et_majorations_HS(
    req_HS: HSCalculationRequestHS,
    db: Optional[Session] = None,
) -> HSCalculationResultHS:
    """
    Reproduit la logique du fichier Excel HS-MAJORATION.xlsx en Python.

    PRINCIPALE CORRECTION :
    -----------------------
    Les heures du DIMANCHE et des JOURS FÃ‰RIÃ‰S ne sont PAS incluses
    dans le total hebdomadaire utilisÃ© pour dÃ©terminer les HS 130/150%.

    Elles sont rÃ©munÃ©rÃ©es Ã  part :
      - Dimanche non fÃ©riÃ© -> HMD 40%
      - Jour fÃ©riÃ© -> HMJF 50%

    Si on les incluait en plus dans le total semaine, on paierait deux fois.
    """

    calendar_status_map: Dict[date, str] = {}
    if db and req_HS.employer_id_HS:
        try:
            year_HS, month_HS = map(int, req_HS.mois_HS.split("-"))
            month_start_HS = date(year_HS, month_HS, 1)
            month_end_HS = date(year_HS + (1 if month_HS == 12 else 0), (month_HS % 12) + 1, 1)
            calendar_days = (
                db.query(CalendarDay)
                .filter(
                    CalendarDay.employer_id == req_HS.employer_id_HS,
                    CalendarDay.date >= month_start_HS,
                    CalendarDay.date < month_end_HS,
                )
                .all()
            )
            for cal_day in calendar_days:
                if getattr(cal_day, "status", None):
                    calendar_status_map[cal_day.date] = cal_day.status
                else:
                    calendar_status_map[cal_day.date] = "worked" if getattr(cal_day, "is_worked", True) else "off"
        except Exception:
            calendar_status_map = {}

    base_hebdo_td_HS = timedelta(hours=req_HS.base_hebdo_heures_HS)
    limite_22h_HS = _time_to_td_HS(time(22, 0))
    midi_td_HS = _time_to_td_HS(time(12, 0))

    # Accumulateurs globaux (mois)
    total_HMNH_td_HS = timedelta(0)
    total_HMNO_td_HS = timedelta(0)
    total_HMD_td_HS = timedelta(0)
    total_HMJF_td_HS = timedelta(0)

    # Accumulateurs hebdomadaires (clÃ© = (annÃ©e ISO, semaine ISO))
    semaines_HS: Dict[Tuple[int, int], _WeekAggHS] = {}

    for jour_HS in req_HS.jours_HS:
        effective_type_jour_HS = jour_HS.type_jour_HS
        calendar_status_HS = calendar_status_map.get(jour_HS.date_HS)

        if calendar_status_HS == "closed":
            continue
        if calendar_status_HS in {"off", "holiday"} and effective_type_jour_HS == "N":
            effective_type_jour_HS = "JF"

        if effective_type_jour_HS == "F":
            continue
        # (annÃ©e, semaine ISO, jour_semaine) â€“ lundi=1, dimanche=7
        iso_year_HS, iso_week_HS, iso_dow_HS = jour_HS.date_HS.isocalendar()
        semaine_key_HS = (iso_year_HS, iso_week_HS)

        if semaine_key_HS not in semaines_HS:
            semaines_HS[semaine_key_HS] = _WeekAggHS()
        agg_HS = semaines_HS[semaine_key_HS]



        entree_td_HS = _time_to_td_HS(jour_HS.entree_HS)
        sortie_td_HS = _time_to_td_HS(jour_HS.sortie_HS)

        # ðŸŒ™ DÃ©tection du passage de minuit
        # Si sortie < entrÃ©e, cela signifie qu'on a travaillÃ© jusqu'au lendemain
        # Exemple: 08:00 â†’ 01:00 signifie 08:00 â†’ 25:00 (01:00 le lendemain)
        if sortie_td_HS < entree_td_HS:
            sortie_td_HS += timedelta(hours=24)

        # Pause configurable (en minutes, converti en timedelta)
        pause_td_HS = timedelta(minutes=jour_HS.duree_pause_minutes_HS)


        # Dimanche ?
        is_sunday_HS = iso_dow_HS == 7

        # DurÃ©e de base (colonne F)
        # âš ï¸ PAUSE: Ne pas dÃ©duire la pause si sortie <= 12h (travail se termine le matin)
        if is_sunday_HS:
            # Dimanche : F = D - C - E, mais pas de pause si sortie <= midi
            if sortie_td_HS <= midi_td_HS:
                duree_base_td_HS = sortie_td_HS - entree_td_HS  # Pas de pause
            else:
                duree_base_td_HS = sortie_td_HS - entree_td_HS - pause_td_HS
        else:
            # Autres jours : F = MIN(D,22h) - C - E
            sortie_limitee_td_HS = min(sortie_td_HS, limite_22h_HS)
            if sortie_td_HS <= midi_td_HS:
                duree_base_td_HS = sortie_limitee_td_HS - entree_td_HS  # Pas de pause
            else:
                duree_base_td_HS = sortie_limitee_td_HS - entree_td_HS - pause_td_HS

        if duree_base_td_HS < timedelta(0):
            duree_base_td_HS = timedelta(0)

        # Heures de nuit entre 22h et 05h (L et M)
        hmnh_td_jour_HS = timedelta(0)
        hmno_td_jour_HS = timedelta(0)
        if effective_type_jour_HS != "JF":
            limite_5h_lendemain_HS = timedelta(hours=29)
            if sortie_td_HS <= limite_22h_HS:
                duree_nuit_td_HS = timedelta(0)
            elif entree_td_HS < limite_22h_HS and sortie_td_HS > limite_22h_HS:
                fin_nuit_HS = min(sortie_td_HS, limite_5h_lendemain_HS)
                duree_nuit_td_HS = max(fin_nuit_HS - limite_22h_HS, timedelta(0))
            elif entree_td_HS >= timedelta(hours=24) and entree_td_HS < limite_5h_lendemain_HS:
                fin_nuit_HS = min(sortie_td_HS, limite_5h_lendemain_HS)
                duree_nuit_td_HS = max(fin_nuit_HS - entree_td_HS, timedelta(0))
            else:
                duree_nuit_td_HS = timedelta(0)
            effective_type_nuit_HS = jour_HS.type_nuit_HS or req_HS.mode_nuit_HS
            if effective_type_nuit_HS == "H":
                hmnh_td_jour_HS = duree_nuit_td_HS
            elif effective_type_nuit_HS == "O":
                hmno_td_jour_HS = duree_nuit_td_HS

        # Heures majorÃ©es jour fÃ©riÃ© (Q)
        if effective_type_jour_HS == "JF":
            # MÃªme logique : pas de pause si sortie <= midi
            if sortie_td_HS <= midi_td_HS:
                hmjf_td_jour_HS = sortie_td_HS - entree_td_HS
            else:
                hmjf_td_jour_HS = sortie_td_HS - entree_td_HS - pause_td_HS
            if hmjf_td_jour_HS < timedelta(0):
                hmjf_td_jour_HS = timedelta(0)
        else:
            hmjf_td_jour_HS = timedelta(0)

        # Heures majorÃ©es dimanche (O)
        hmd_td_jour_HS = timedelta(0)
        if is_sunday_HS and effective_type_jour_HS != "JF":
            # MÃªme logique de pause que pour duree_base : pas de pause si sortie <= midi
            if sortie_td_HS <= midi_td_HS:
                duree_totale_jour_td_HS = sortie_td_HS - entree_td_HS  # Pas de pause
            else:
                duree_totale_jour_td_HS = sortie_td_HS - entree_td_HS - pause_td_HS
            
            if duree_totale_jour_td_HS < timedelta(0):
                duree_totale_jour_td_HS = timedelta(0)
            # O = (D - C - E) - M (on enlÃ¨ve dÃ©jÃ  les 50% nuit occasionnelle)
            hmd_td_jour_HS = duree_totale_jour_td_HS - hmno_td_jour_HS

        # Accumulation globale (mois)
        total_HMNH_td_HS += hmnh_td_jour_HS
        total_HMNO_td_HS += hmno_td_jour_HS
        total_HMJF_td_HS += hmjf_td_jour_HS
        total_HMD_td_HS += hmd_td_jour_HS

        # â›” RÃˆGLE CRITIQUE du prompt :
        # "On ne compte pas parmi les heures supplÃ©mentaires les heures de travail 
        # effectuÃ©es pendant les heures de nuit, heures de dimanches, heures pendant les jours fÃ©riÃ©s"
        # 
        # Donc pour le calcul des HS, on n'ajoute QUE les jours normaux (hors dimanche, hors JF)
        # ET on n'ajoute QUE la durÃ©e AVANT 22h (duree_sans_nuit_HS)
        if (not is_sunday_HS) and (effective_type_jour_HS != "JF"):
            # UNIQUEMENT la durÃ©e de base (avant 22h) compte pour les HS
            # Les heures de nuit (hmnh_HS et hmno_HS) NE comptent PAS pour les HS
            agg_HS.duree_sans_nuit_HS += duree_base_td_HS
            # On garde les heures de nuit sÃ©parÃ©ment pour les majorations
            agg_HS.hmnh_HS += hmnh_td_jour_HS
            agg_HS.hmno_HS += hmno_td_jour_HS

    # --- Ã‰tape 2 : HS 130% / 150% par semaine (Hxx / Ixx) ---

    total_H_130_td_HS = timedelta(0)
    total_H_150_td_HS = timedelta(0)

    for agg_HS in semaines_HS.values():
        # â›” RÃˆGLE CRITIQUE : Les heures de nuit NE comptent PAS pour les HS
        # Total semaine pour HS = UNIQUEMENT duree_sans_nuit_HS (avant 22h)
        # On N'ajoute PAS hmnh_HS ni hmno_HS ici !
        total_hebdo_td_HS = agg_HS.duree_sans_nuit_HS  # SANS les heures de nuit !

        if total_hebdo_td_HS <= base_hebdo_td_HS:
            hs_brut_td_HS = timedelta(0)
        else:
            hs_brut_td_HS = total_hebdo_td_HS - base_hebdo_td_HS

        # Gxx : HS hebdo plafonnÃ©es Ã  20h
        hs_plafonne_td_HS = min(hs_brut_td_HS, timedelta(hours=20))

        # Hxx : 8 premiÃ¨res heures Ã  130%
        hs_130_semaine_td_HS = min(hs_plafonne_td_HS, timedelta(hours=8))

        # Ixx : le reste (jusqu'Ã  20h) Ã  150%
        hs_150_semaine_td_HS = hs_plafonne_td_HS - hs_130_semaine_td_HS

        total_H_130_td_HS += hs_130_semaine_td_HS
        total_H_150_td_HS += hs_150_semaine_td_HS

    # --- Ã‰tape 3 : RÃ©partition NI / Imposable sur le mois (ligne 61 Excel) ---
    # Formules Excel exactes :
    # H61 = somme des HS 130% de toutes les semaines
    # I61 = somme des HS 150% de toutes les semaines
    # S61 (HSNI 130%) = SI(H61>=20h; 20h; H61)
    # T61 (HSI 130%) = H61 - S61
    # U61 (HSNI 150%) = SI(S61<=20h; SI(H61+I61<20h; I61; 20h-S61); 0h)
    # V61 (HSI 150%) = SI(S61=20h; I61; SI((I61-U61)<=0; 0; I61-U61))

    seuil_20h_td_HS = timedelta(hours=20)
    H61_td_HS = total_H_130_td_HS  # total mensuel HS 130%
    I61_td_HS = total_H_150_td_HS  # total mensuel HS 150%

    # S61 : HSNI 130% = SI(H61>=20h; 20h; H61)
    if H61_td_HS >= seuil_20h_td_HS:
        S61_HSNI_130_td_HS = seuil_20h_td_HS
    else:
        S61_HSNI_130_td_HS = H61_td_HS

    # T61 : HSI 130% = H61 - S61
    T61_HSI_130_td_HS = H61_td_HS - S61_HSNI_130_td_HS

    # U61 : HSNI 150% = SI(S61<=20h; SI(H61+I61<20h; I61; 20h-S61); 0h)
    # CORRECTION: Utiliser <= au lieu de < pour le test H61+I61
    if S61_HSNI_130_td_HS <= seuil_20h_td_HS:
        if H61_td_HS + I61_td_HS <= seuil_20h_td_HS:  # Changed < to <=
            U61_HSNI_150_td_HS = I61_td_HS
        else:
            U61_HSNI_150_td_HS = seuil_20h_td_HS - S61_HSNI_130_td_HS
    else:
        U61_HSNI_150_td_HS = timedelta(0)

    # V61 : HSI 150% = SI(S61=20h; I61; SI((I61-U61)<=0; 0; I61-U61))
    if S61_HSNI_130_td_HS == seuil_20h_td_HS:
        V61_HSI_150_td_HS = I61_td_HS
    else:
        reste_150 = I61_td_HS - U61_HSNI_150_td_HS
        if reste_150 <= timedelta(0):
            V61_HSI_150_td_HS = timedelta(0)
        else:
            V61_HSI_150_td_HS = reste_150

    # --- Retour du rÃ©sultat en heures dÃ©cimales ---

    return HSCalculationResultHS(
        worker_id_HS=req_HS.worker_id_HS,
        mois_HS=req_HS.mois_HS,
        total_HSNI_130_heures_HS=_td_to_hours_HS(S61_HSNI_130_td_HS),
        total_HSI_130_heures_HS=_td_to_hours_HS(T61_HSI_130_td_HS),
        total_HSNI_150_heures_HS=_td_to_hours_HS(U61_HSNI_150_td_HS),
        total_HSI_150_heures_HS=_td_to_hours_HS(V61_HSI_150_td_HS),
        total_HMNH_30_heures_HS=_td_to_hours_HS(total_HMNH_td_HS),
        total_HMNO_50_heures_HS=_td_to_hours_HS(total_HMNO_td_HS),
        total_HMD_40_heures_HS=_td_to_hours_HS(total_HMD_td_HS),
        total_HMJF_50_heures_HS=_td_to_hours_HS(total_HMJF_td_HS),
    )


# --------- ðŸš€ Endpoints FastAPI ---------


@router.get("/import/template")
def download_hs_import_template(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    workers_query = db.query(models.Worker)
    if employer_id is not None:
        workers_query = workers_query.filter(models.Worker.employer_id == employer_id)
    workers = workers_query.order_by(models.Worker.matricule.asc()).all()
    accessible_workers = [worker for worker in workers if can_access_worker(db, user, worker)]

    if not accessible_workers:
        worker_rows = [
            {"matricule": "MAT001", "nom": "EXEMPLE", "prenom": "SALARIE"},
        ]
    else:
        worker_rows = [
            {
                "matricule": worker.matricule or "",
                "nom": worker.nom or "",
                "prenom": worker.prenom or "",
            }
            for worker in accessible_workers
            if (worker.matricule or "").strip()
        ]

    rows = []
    for worker in worker_rows:
        full_name = f"{worker['nom']} {worker['prenom']}".strip()
        for current_day in week_dates:
            rows.append(
                {
                    "Matricule": worker["matricule"],
                    "Nom": full_name,
                    "Date": current_day.strftime("%Y-%m-%d"),
                    "Heure entree": "08:00",
                    "Heure sortie": "17:00",
                    "Pause": 60,
                    "Type jour": "N",
                    "Type nuit": "",
                }
            )

    instructions = pd.DataFrame(
        [
            {"Champ": "Type jour", "Valeurs": "N / JF / F", "Description": "Normal, ferie, ferme"},
            {"Champ": "Type nuit", "Valeurs": "H / O / vide", "Description": "H = habituelle, O = occasionnelle"},
            {"Champ": "Pause", "Valeurs": "entier", "Description": "Duree pause en minutes"},
            {"Champ": "Heure entree/sortie", "Valeurs": "HH:MM", "Description": "Format 24h"},
        ]
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="Planning HS")
        instructions.to_excel(writer, index=False, sheet_name="Instructions")
    output.seek(0)

    filename = f"template_planning_hs_{monday.strftime('%Y%m%d')}_{week_dates[-1].strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import/preview", response_model=HSImportPreviewResponseHS)
async def preview_hs_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    filename = file.filename or ""
    lower = filename.lower()
    if not lower.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Le fichier doit etre au format Excel ou CSV.")

    content = await file.read()
    try:
        if lower.endswith(".csv"):
            frame = pd.read_csv(BytesIO(content))
        else:
            frame = pd.read_excel(BytesIO(content))
    except Exception as exc:  # pragma: no cover - defensive parsing guard
        raise HTTPException(status_code=400, detail=f"Lecture du fichier impossible: {exc}") from exc

    frame = frame.rename(columns=_canonicalize_hs_import_columns(list(frame.columns)))
    required_columns = ["Matricule", "Date", "Heure entree", "Heure sortie"]
    missing_columns = [name for name in required_columns if name not in frame.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Colonnes manquantes: {', '.join(missing_columns)}",
        )

    rows: List[HSImportPreviewRowHS] = []
    errors: List[str] = []
    worker_cache: Dict[str, Optional[models.Worker]] = {}

    for index, item in frame.iterrows():
        row_number = index + 2
        matricule = str(item.get("Matricule", "")).strip()
        if not matricule:
            continue

        parsed_date = _parse_date_string_hs_import(item.get("Date"))
        if not parsed_date:
            errors.append(f"Ligne {row_number}: date invalide")
            continue

        entree = _parse_time_string_hs_import(item.get("Heure entree"))
        sortie = _parse_time_string_hs_import(item.get("Heure sortie"))
        if not entree or not sortie:
            errors.append(f"Ligne {row_number}: heure entree/sortie invalide")
            continue

        pause_raw = item.get("Pause", 60)
        try:
            pause_minutes = int(float(pause_raw))
        except (TypeError, ValueError):
            pause_minutes = 60

        type_jour = str(item.get("Type jour", "N")).strip().upper() or "N"
        if type_jour not in {"N", "JF", "F"}:
            type_jour = "N"

        type_nuit_raw = str(item.get("Type nuit", "")).strip().upper()
        type_nuit = type_nuit_raw if type_nuit_raw in {"H", "O"} else None

        if matricule not in worker_cache:
            worker_cache[matricule] = (
                db.query(models.Worker)
                .filter(models.Worker.matricule == matricule)
                .first()
            )
        worker = worker_cache[matricule]
        worker_id = worker.id if worker else None
        if worker and not can_access_worker(db, user, worker):
            errors.append(f"Ligne {row_number}: acces refuse au matricule {matricule}")
            continue

        if worker:
            fallback_name = " ".join(part for part in [worker.nom or "", worker.prenom or ""] if part).strip()
        else:
            fallback_name = ""
        row_name = str(item.get("Nom", "")).strip() or fallback_name or matricule

        rows.append(
            HSImportPreviewRowHS(
                worker_id_HS=worker_id,
                matricule=matricule,
                nom=row_name,
                date_HS=parsed_date,
                type_jour_HS=type_jour,  # type: ignore[arg-type]
                entree_HS=entree,
                sortie_HS=sortie,
                type_nuit_HS=type_nuit,  # type: ignore[arg-type]
                duree_pause_minutes_HS=max(0, pause_minutes),
            )
        )

    if not rows and errors:
        raise HTTPException(status_code=400, detail=f"Aucune ligne valide. {errors[0]}")

    return HSImportPreviewResponseHS(
        success=True,
        message=f"{len(rows)} ligne(s) HS valide(s) detectee(s)",
        rows_imported=len(rows),
        data=rows,
        errors=errors,
    )


@router.post("/calculate", response_model=HSCalculationResultHS)
def calculate_hs_endpoint_HS(
    payload_HS: HSCalculationRequestHS,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
) -> HSCalculationResultHS:
    """
    Endpoint API :
    POST /hs/calculate
    -> calcule les HS mais ne sauvegarde pas en base
    """
    worker = db.query(models.Worker).filter(models.Worker.id == payload_HS.worker_id_HS).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    return calculer_heures_supplementaires_et_majorations_HS(payload_HS, db)


@router.post("/calculate-and-save", response_model=HSCalculationReadHS)
def calculate_and_save_hs_endpoint_HS(
    payload_HS: HSCalculationRequestHS,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
) -> HSCalculationReadHS:
    """
    Endpoint API :
    POST /hs/calculate-and-save

    1. Calcule les HS (comme /hs/calculate)
    2. Sauvegarde le rÃ©sumÃ© mensuel dans hs_calculations_HS
    3. Retourne l'enregistrement sauvegardÃ© (avec id_HS)
    """
    worker = db.query(models.Worker).filter(models.Worker.id == payload_HS.worker_id_HS).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    result_HS = calculer_heures_supplementaires_et_majorations_HS(payload_HS, db)

    now_HS = _utcnow()

    calc_db_HS = db.query(HSCalculationHS).filter(
        HSCalculationHS.worker_id_HS == payload_HS.worker_id_HS,
        HSCalculationHS.mois_HS == payload_HS.mois_HS,
    ).first()

    if calc_db_HS:
        calc_db_HS.base_hebdo_heures_HS = payload_HS.base_hebdo_heures_HS
        calc_db_HS.total_HSNI_130_heures_HS = result_HS.total_HSNI_130_heures_HS
        calc_db_HS.total_HSI_130_heures_HS = result_HS.total_HSI_130_heures_HS
        calc_db_HS.total_HSNI_150_heures_HS = result_HS.total_HSNI_150_heures_HS
        calc_db_HS.total_HSI_150_heures_HS = result_HS.total_HSI_150_heures_HS
        calc_db_HS.total_HMNH_30_heures_HS = result_HS.total_HMNH_30_heures_HS
        calc_db_HS.total_HMNO_50_heures_HS = result_HS.total_HMNO_50_heures_HS
        calc_db_HS.total_HMD_40_heures_HS = result_HS.total_HMD_40_heures_HS
        calc_db_HS.total_HMJF_50_heures_HS = result_HS.total_HMJF_50_heures_HS
        calc_db_HS.updated_at_HS = now_HS
    else:
        calc_db_HS = HSCalculationHS(
            worker_id_HS=payload_HS.worker_id_HS,
            mois_HS=payload_HS.mois_HS,
            base_hebdo_heures_HS=payload_HS.base_hebdo_heures_HS,
            total_HSNI_130_heures_HS=result_HS.total_HSNI_130_heures_HS,
            total_HSI_130_heures_HS=result_HS.total_HSI_130_heures_HS,
            total_HSNI_150_heures_HS=result_HS.total_HSNI_150_heures_HS,
            total_HSI_150_heures_HS=result_HS.total_HSI_150_heures_HS,
            total_HMNH_30_heures_HS=result_HS.total_HMNH_30_heures_HS,
            total_HMNO_50_heures_HS=result_HS.total_HMNO_50_heures_HS,
            total_HMD_40_heures_HS=result_HS.total_HMD_40_heures_HS,
            total_HMJF_50_heures_HS=result_HS.total_HMJF_50_heures_HS,
            payroll_run_id_HS=None,
            created_at_HS=now_HS,
            updated_at_HS=now_HS,
        )
        db.add(calc_db_HS)
    db.commit()
    db.refresh(calc_db_HS)

    return calc_db_HS


class HSExportTauxHS(BaseModel):
    taux_hs130: Optional[float] = None
    taux_hs150: Optional[float] = None
    taux_hmnh: Optional[float] = None
    taux_hmno: Optional[float] = None
    taux_hmd: Optional[float] = None
    taux_hmjf: Optional[float] = None


@router.post("/{hs_id}/export-to-payroll")
def export_hs_to_payroll(
    hs_id: int,
    payroll_run_id: int,
    taux: Optional[HSExportTauxHS] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
):
    hs_calc = db.query(HSCalculationHS).filter(HSCalculationHS.id_HS == hs_id).first()
    if not hs_calc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calcul HS id_HS={hs_id} introuvable.",
        )
    worker = db.query(models.Worker).filter(models.Worker.id == hs_calc.worker_id_HS).first()
    if not worker or not can_access_worker(db, user, worker):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payroll run id={payroll_run_id} introuvable.",
        )

    salaire_horaire = float(worker.salaire_horaire or 0.0)
    rates = taux or HSExportTauxHS()
    r_hs130 = float((rates.taux_hs130 if rates.taux_hs130 is not None else 130.0) / 100.0)
    r_hs150 = float((rates.taux_hs150 if rates.taux_hs150 is not None else 150.0) / 100.0)
    r_hmnh = float((rates.taux_hmnh if rates.taux_hmnh is not None else 30.0) / 100.0)
    r_hmno = float((rates.taux_hmno if rates.taux_hmno is not None else 50.0) / 100.0)
    r_hmd = float((rates.taux_hmd if rates.taux_hmd is not None else 40.0) / 100.0)
    r_hmjf = float((rates.taux_hmjf if rates.taux_hmjf is not None else 50.0) / 100.0)

    def calc_montant(heures: float, coef: float) -> Decimal:
        return Decimal(str(salaire_horaire * float(heures) * coef))

    montants = {
        "hsni_130_montant": calc_montant(hs_calc.total_HSNI_130_heures_HS, r_hs130),
        "hsi_130_montant": calc_montant(hs_calc.total_HSI_130_heures_HS, r_hs130),
        "hsni_150_montant": calc_montant(hs_calc.total_HSNI_150_heures_HS, r_hs150),
        "hsi_150_montant": calc_montant(hs_calc.total_HSI_150_heures_HS, r_hs150),
        "hmnh_montant": calc_montant(hs_calc.total_HMNH_30_heures_HS, r_hmnh),
        "hmno_montant": calc_montant(hs_calc.total_HMNO_50_heures_HS, r_hmno),
        "hmd_montant": calc_montant(hs_calc.total_HMD_40_heures_HS, r_hmd),
        "hmjf_montant": calc_montant(hs_calc.total_HMJF_50_heures_HS, r_hmjf),
    }

    existing = db.query(PayrollHsHm).filter(
        PayrollHsHm.payroll_run_id == payroll_run_id,
        PayrollHsHm.worker_id == hs_calc.worker_id_HS,
    ).first()

    if existing:
        existing.source_type = "MANUAL"
        existing.hs_calculation_id = hs_id
        existing.import_file_name = None
        existing.hsni_130_heures = Decimal(str(hs_calc.total_HSNI_130_heures_HS))
        existing.hsi_130_heures = Decimal(str(hs_calc.total_HSI_130_heures_HS))
        existing.hsni_150_heures = Decimal(str(hs_calc.total_HSNI_150_heures_HS))
        existing.hsi_150_heures = Decimal(str(hs_calc.total_HSI_150_heures_HS))
        existing.hmnh_heures = Decimal(str(hs_calc.total_HMNH_30_heures_HS))
        existing.hmno_heures = Decimal(str(hs_calc.total_HMNO_50_heures_HS))
        existing.hmd_heures = Decimal(str(hs_calc.total_HMD_40_heures_HS))
        existing.hmjf_heures = Decimal(str(hs_calc.total_HMJF_50_heures_HS))
        for key, value in montants.items():
            setattr(existing, key, value)
        existing.updated_at = _utcnow()
        db.commit()
        db.refresh(existing)
        return {
            "success": True,
            "message": "Calcul HS exporte avec succes (mise a jour)",
            "payroll_hs_hm_id": existing.id,
            "action": "updated",
        }

    payroll_hs_hm = PayrollHsHm(
        payroll_run_id=payroll_run_id,
        worker_id=hs_calc.worker_id_HS,
        source_type="MANUAL",
        hs_calculation_id=hs_id,
        import_file_name=None,
        hsni_130_heures=Decimal(str(hs_calc.total_HSNI_130_heures_HS)),
        hsi_130_heures=Decimal(str(hs_calc.total_HSI_130_heures_HS)),
        hsni_150_heures=Decimal(str(hs_calc.total_HSNI_150_heures_HS)),
        hsi_150_heures=Decimal(str(hs_calc.total_HSI_150_heures_HS)),
        hmnh_heures=Decimal(str(hs_calc.total_HMNH_30_heures_HS)),
        hmno_heures=Decimal(str(hs_calc.total_HMNO_50_heures_HS)),
        hmd_heures=Decimal(str(hs_calc.total_HMD_40_heures_HS)),
        hmjf_heures=Decimal(str(hs_calc.total_HMJF_50_heures_HS)),
        **montants,
    )
    db.add(payroll_hs_hm)
    db.commit()
    db.refresh(payroll_hs_hm)
    return {
        "success": True,
        "message": "Calcul HS exporte avec succes (creation)",
        "payroll_hs_hm_id": payroll_hs_hm.id,
        "action": "created",
    }
