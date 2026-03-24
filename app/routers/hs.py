from datetime import date, time, timedelta, datetime
from typing import List, Literal, Optional, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config.config import get_db
from .. import models
from ..models import HSCalculationHS
from ..schemas import HSCalculationReadHS
from ..security import PAYROLL_WRITE_ROLES, READ_PAYROLL_ROLES, can_access_worker, require_roles


router = APIRouter(
    prefix="/hs",
    tags=["Heures Supplémentaires HS"],
)


def _filter_hs_for_user(db: Session, user: models.AppUser, rows: List[HSCalculationHS]) -> List[HSCalculationHS]:
    worker_cache = {}
    allowed = []
    for row in rows:
        worker_id = row.worker_id_HS
        if worker_id not in worker_cache:
            worker_cache[worker_id] = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        worker = worker_cache[worker_id]
        if worker and can_access_worker(db, user, worker):
            allowed.append(row)
    return allowed


@router.get("/all", response_model=List[HSCalculationReadHS])
def get_all_hs_calculations_HS(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
) -> List[HSCalculationReadHS]:
    """
    Endpoint API :
    GET /hs/all

    -> renvoie TOUS les enregistrements hs_calculations_HS
       (triés du plus récent au plus ancien).
    """
    calculs_HS = (
        db.query(HSCalculationHS)
        .order_by(HSCalculationHS.created_at_HS.desc())
        .all()
    )
    return _filter_hs_for_user(db, user, calculs_HS)


@router.get("/all", response_model=List[HSCalculationReadHS])
def get_all_hs_calculations_HS(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
) -> List[HSCalculationReadHS]:
    """
    Endpoint API :
    GET /hs/all

    -> renvoie TOUS les enregistrements hs_calculations_HS
       triés du plus récent au plus ancien (created_at_HS desc).
    """
    calculs_HS = (
        db.query(HSCalculationHS)
        .order_by(HSCalculationHS.created_at_HS.desc())
        .all()
    )
    return _filter_hs_for_user(db, user, calculs_HS)


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

    db.delete(calc_HS)
    db.commit()
    # 204 -> pas de contenu à retourner
    return



# --------- 📌 Modèles Pydantic (avec suffixe HS) ---------


class HSJourInputHS(BaseModel):
    """Données d'une journée de travail pour le calcul des HS."""

    date_HS: date = Field(..., description="Date de la journée")
    type_jour_HS: Literal["N", "JF"] = Field(
        "N", description="Type de jour: N = Normal, JF = Jour Férié"
    )
    entree_HS: time = Field(..., description="Heure d'entrée")
    sortie_HS: time = Field(..., description="Heure de sortie")
    type_nuit_HS: Optional[Literal["H", "O"]] = Field(
        None,
        description=(
            "Type de nuit après 22h : "
            "H = Nuit habituelle, O = Nuit occasionnelle. "
            "Laisser vide si pas de nuit."
        ),
    )
    duree_pause_minutes_HS: int = Field(
        60,
        description="Durée de la pause en minutes (par défaut 60 = 1h)"
    )



class HSCalculationRequestHS(BaseModel):
    """
    Requête pour calculer les heures sup / majorations sur un mois.

    On laisse volontairement simple (sans Field()) pour éviter
    les soucis de compatibilité Pydantic.
    """

    # Identifiant du salarié
    worker_id_HS: int

    # Mois de paie, ex: "2025-07"
    mois_HS: str

    # Durée hebdomadaire contractuelle en heures (par ex. 40 ou 48)
    base_hebdo_heures_HS: float = 40.0

    # Liste des jours à traiter pour le calcul HS
    jours_HS: List[HSJourInputHS]


class HSCalculationResultHS(BaseModel):
    """Résultat global mensuel en heures décimales."""

    worker_id_HS: int
    mois_HS: str

    # HS NI / I
    total_HSNI_130_heures_HS: float
    total_HSI_130_heures_HS: float
    total_HSNI_150_heures_HS: float
    total_HSI_150_heures_HS: float

    # Heures majorées
    total_HMNH_30_heures_HS: float
    total_HMNO_50_heures_HS: float
    total_HMD_40_heures_HS: float
    total_HMJF_50_heures_HS: float


# --------- 🔧 Fonctions internes (conversion temps) ---------


def _time_to_td_HS(t: time) -> timedelta:
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


def _td_to_hours_HS(td: timedelta) -> float:
    return td.total_seconds() / 3600.0


class _WeekAggHS:
    """Accumulation par semaine (interne)."""

    def __init__(self) -> None:
        # Durée des jours normaux (hors dimanche & JF) jusqu'à 22h
        self.duree_sans_nuit_HS = timedelta(0)
        # Heures de nuit habituelles (jours normaux uniquement)
        self.hmnh_HS = timedelta(0)
        # Heures de nuit occasionnelles (jours normaux uniquement)
        self.hmno_HS = timedelta(0)


# --------- 🧠 Coeur du calcul : traduction des formules Excel ---------


def calculer_heures_supplementaires_et_majorations_HS(
    req_HS: HSCalculationRequestHS,
) -> HSCalculationResultHS:
    """
    Reproduit la logique du fichier Excel HS-MAJORATION.xlsx en Python.

    PRINCIPALE CORRECTION :
    -----------------------
    Les heures du DIMANCHE et des JOURS FÉRIÉS ne sont PAS incluses
    dans le total hebdomadaire utilisé pour déterminer les HS 130/150%.

    Elles sont rémunérées à part :
      - Dimanche non férié -> HMD 40%
      - Jour férié -> HMJF 50%

    Si on les incluait en plus dans le total semaine, on paierait deux fois.
    """

    base_hebdo_td_HS = timedelta(hours=req_HS.base_hebdo_heures_HS)
    limite_22h_HS = _time_to_td_HS(time(22, 0))
    midi_td_HS = _time_to_td_HS(time(12, 0))

    # Accumulateurs globaux (mois)
    total_HMNH_td_HS = timedelta(0)
    total_HMNO_td_HS = timedelta(0)
    total_HMD_td_HS = timedelta(0)
    total_HMJF_td_HS = timedelta(0)

    # Accumulateurs hebdomadaires (clé = (année ISO, semaine ISO))
    semaines_HS: Dict[Tuple[int, int], _WeekAggHS] = {}

    for jour_HS in req_HS.jours_HS:
        # (année, semaine ISO, jour_semaine) – lundi=1, dimanche=7
        iso_year_HS, iso_week_HS, iso_dow_HS = jour_HS.date_HS.isocalendar()
        semaine_key_HS = (iso_year_HS, iso_week_HS)

        if semaine_key_HS not in semaines_HS:
            semaines_HS[semaine_key_HS] = _WeekAggHS()
        agg_HS = semaines_HS[semaine_key_HS]



        entree_td_HS = _time_to_td_HS(jour_HS.entree_HS)
        sortie_td_HS = _time_to_td_HS(jour_HS.sortie_HS)

        # 🌙 Détection du passage de minuit
        # Si sortie < entrée, cela signifie qu'on a travaillé jusqu'au lendemain
        # Exemple: 08:00 → 01:00 signifie 08:00 → 25:00 (01:00 le lendemain)
        if sortie_td_HS < entree_td_HS:
            sortie_td_HS += timedelta(hours=24)

        # Pause configurable (en minutes, converti en timedelta)
        pause_td_HS = timedelta(minutes=jour_HS.duree_pause_minutes_HS)


        # Dimanche ?
        is_sunday_HS = iso_dow_HS == 7

        # Durée de base (colonne F)
        # ⚠️ PAUSE: Ne pas déduire la pause si sortie <= 12h (travail se termine le matin)
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

        # Heures de nuit après 22h (L et M)
        # Excel: SI(D>=TEMPS(22;0;0);D-TEMPS(22;0;0);0)
        hmnh_td_jour_HS = timedelta(0)
        hmno_td_jour_HS = timedelta(0)
        if jour_HS.type_jour_HS != "JF" and sortie_td_HS >= limite_22h_HS:  # Changed > to >=
            duree_nuit_td_HS = sortie_td_HS - limite_22h_HS
            if jour_HS.type_nuit_HS == "H":
                hmnh_td_jour_HS = duree_nuit_td_HS
            elif jour_HS.type_nuit_HS == "O":
                hmno_td_jour_HS = duree_nuit_td_HS

        # Heures majorées jour férié (Q)
        if jour_HS.type_jour_HS == "JF":
            # Même logique : pas de pause si sortie <= midi
            if sortie_td_HS <= midi_td_HS:
                hmjf_td_jour_HS = sortie_td_HS - entree_td_HS
            else:
                hmjf_td_jour_HS = sortie_td_HS - entree_td_HS - pause_td_HS
            if hmjf_td_jour_HS < timedelta(0):
                hmjf_td_jour_HS = timedelta(0)
        else:
            hmjf_td_jour_HS = timedelta(0)

        # Heures majorées dimanche (O)
        hmd_td_jour_HS = timedelta(0)
        if is_sunday_HS and jour_HS.type_jour_HS != "JF":
            # Même logique de pause que pour duree_base : pas de pause si sortie <= midi
            if sortie_td_HS <= midi_td_HS:
                duree_totale_jour_td_HS = sortie_td_HS - entree_td_HS  # Pas de pause
            else:
                duree_totale_jour_td_HS = sortie_td_HS - entree_td_HS - pause_td_HS
            
            if duree_totale_jour_td_HS < timedelta(0):
                duree_totale_jour_td_HS = timedelta(0)
            # O = (D - C - E) - M (on enlève déjà les 50% nuit occasionnelle)
            hmd_td_jour_HS = duree_totale_jour_td_HS - hmno_td_jour_HS

        # Accumulation globale (mois)
        total_HMNH_td_HS += hmnh_td_jour_HS
        total_HMNO_td_HS += hmno_td_jour_HS
        total_HMJF_td_HS += hmjf_td_jour_HS
        total_HMD_td_HS += hmd_td_jour_HS

        # ⛔ RÈGLE CRITIQUE du prompt :
        # "On ne compte pas parmi les heures supplémentaires les heures de travail 
        # effectuées pendant les heures de nuit, heures de dimanches, heures pendant les jours fériés"
        # 
        # Donc pour le calcul des HS, on n'ajoute QUE les jours normaux (hors dimanche, hors JF)
        # ET on n'ajoute QUE la durée AVANT 22h (duree_sans_nuit_HS)
        if (not is_sunday_HS) and (jour_HS.type_jour_HS != "JF"):
            # UNIQUEMENT la durée de base (avant 22h) compte pour les HS
            # Les heures de nuit (hmnh_HS et hmno_HS) NE comptent PAS pour les HS
            agg_HS.duree_sans_nuit_HS += duree_base_td_HS
            # On garde les heures de nuit séparément pour les majorations
            agg_HS.hmnh_HS += hmnh_td_jour_HS
            agg_HS.hmno_HS += hmno_td_jour_HS

    # --- Étape 2 : HS 130% / 150% par semaine (Hxx / Ixx) ---

    total_H_130_td_HS = timedelta(0)
    total_H_150_td_HS = timedelta(0)

    for agg_HS in semaines_HS.values():
        # ⛔ RÈGLE CRITIQUE : Les heures de nuit NE comptent PAS pour les HS
        # Total semaine pour HS = UNIQUEMENT duree_sans_nuit_HS (avant 22h)
        # On N'ajoute PAS hmnh_HS ni hmno_HS ici !
        total_hebdo_td_HS = agg_HS.duree_sans_nuit_HS  # SANS les heures de nuit !

        if total_hebdo_td_HS <= base_hebdo_td_HS:
            hs_brut_td_HS = timedelta(0)
        else:
            hs_brut_td_HS = total_hebdo_td_HS - base_hebdo_td_HS

        # Gxx : HS hebdo plafonnées à 20h
        hs_plafonne_td_HS = min(hs_brut_td_HS, timedelta(hours=20))

        # Hxx : 8 premières heures à 130%
        hs_130_semaine_td_HS = min(hs_plafonne_td_HS, timedelta(hours=8))

        # Ixx : le reste (jusqu'à 20h) à 150%
        hs_150_semaine_td_HS = hs_plafonne_td_HS - hs_130_semaine_td_HS

        total_H_130_td_HS += hs_130_semaine_td_HS
        total_H_150_td_HS += hs_150_semaine_td_HS

    # --- Étape 3 : Répartition NI / Imposable sur le mois (ligne 61 Excel) ---
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

    # --- Retour du résultat en heures décimales ---

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


# --------- 🚀 Endpoints FastAPI ---------


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
    return calculer_heures_supplementaires_et_majorations_HS(payload_HS)


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
    2. Sauvegarde le résumé mensuel dans hs_calculations_HS
    3. Retourne l'enregistrement sauvegardé (avec id_HS)
    """
    worker = db.query(models.Worker).filter(models.Worker.id == payload_HS.worker_id_HS).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    result_HS = calculer_heures_supplementaires_et_majorations_HS(payload_HS)

    now_HS = datetime.utcnow()

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
        payroll_run_id_HS=None,  # tu pourras le renseigner plus tard
        created_at_HS=now_HS,
        updated_at_HS=now_HS,
    )

    db.add(calc_db_HS)
    db.commit()
    db.refresh(calc_db_HS)

    return calc_db_HS
