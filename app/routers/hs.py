from datetime import date, time, timedelta, datetime
from typing import List, Literal, Optional, Dict, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config.config import get_db
from ..models import HSCalculationHS
from ..schemas import HSCalculationReadHS


router = APIRouter(
    prefix="/hs",
    tags=["Heures Supplémentaires HS"],
)


@router.get("/all", response_model=List[HSCalculationReadHS])
def get_all_hs_calculations_HS(
    db: Session = Depends(get_db),
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
    return calculs_HS



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

        # Pause auto : 1h si sortie > 12h
        pause_td_HS = timedelta(hours=1) if sortie_td_HS > midi_td_HS else timedelta(0)

        # Dimanche ?
        is_sunday_HS = iso_dow_HS == 7

        # Durée de base (colonne F)
        if is_sunday_HS:
            # Dimanche : F = D - C - E (mais servira surtout pour HMD)
            duree_base_td_HS = sortie_td_HS - entree_td_HS - pause_td_HS
        else:
            # Autres jours : F = MIN(D,22h) - C - E
            sortie_limitee_td_HS = min(sortie_td_HS, limite_22h_HS)
            duree_base_td_HS = sortie_limitee_td_HS - entree_td_HS - pause_td_HS

        if duree_base_td_HS < timedelta(0):
            duree_base_td_HS = timedelta(0)

        # Heures de nuit après 22h (L et M)
        hmnh_td_jour_HS = timedelta(0)
        hmno_td_jour_HS = timedelta(0)
        if jour_HS.type_jour_HS != "JF" and sortie_td_HS > limite_22h_HS:
            duree_nuit_td_HS = sortie_td_HS - limite_22h_HS
            if jour_HS.type_nuit_HS == "H":
                hmnh_td_jour_HS = duree_nuit_td_HS
            elif jour_HS.type_nuit_HS == "O":
                hmno_td_jour_HS = duree_nuit_td_HS

        # Heures majorées jour férié (Q)
        if jour_HS.type_jour_HS == "JF":
            hmjf_td_jour_HS = sortie_td_HS - entree_td_HS - pause_td_HS
            if hmjf_td_jour_HS < timedelta(0):
                hmjf_td_jour_HS = timedelta(0)
        else:
            hmjf_td_jour_HS = timedelta(0)

        # Heures majorées dimanche (O)
        hmd_td_jour_HS = timedelta(0)
        if is_sunday_HS and jour_HS.type_jour_HS != "JF":
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

        # ⛔ IMPORTANT : on n'ajoute au total hebdo HS que les jours normaux
        # (hors dimanche et hors jours fériés)
        if (not is_sunday_HS) and (jour_HS.type_jour_HS != "JF"):
            agg_HS.duree_sans_nuit_HS += duree_base_td_HS
            agg_HS.hmnh_HS += hmnh_td_jour_HS
            agg_HS.hmno_HS += hmno_td_jour_HS

    # --- Étape 2 : HS 130% / 150% par semaine (Hxx / Ixx) ---

    total_H_130_td_HS = timedelta(0)
    total_H_150_td_HS = timedelta(0)

    for agg_HS in semaines_HS.values():
        # Total semaine pour HS = jours normaux seulement
        total_hebdo_td_HS = agg_HS.duree_sans_nuit_HS + agg_HS.hmnh_HS + agg_HS.hmno_HS

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

    # --- Étape 3 : Répartition NI / Imposable sur le mois (S61,T61,U61,V61) ---

    seuil_20h_td_HS = timedelta(hours=20)
    H61_td_HS = total_H_130_td_HS  # total HS 130
    I61_td_HS = total_H_150_td_HS  # total HS 150

    # S61 : HSNI 130
    HSNI_130_td_HS = min(H61_td_HS, seuil_20h_td_HS)

    # T61 : HSI 130
    HSI_130_td_HS = H61_td_HS - HSNI_130_td_HS

    # U61 : HSNI 150
    if HSNI_130_td_HS <= seuil_20h_td_HS:
        if H61_td_HS + I61_td_HS < seuil_20h_td_HS:
            HSNI_150_td_HS = I61_td_HS
        else:
            HSNI_150_td_HS = seuil_20h_td_HS - HSNI_130_td_HS
    else:
        HSNI_150_td_HS = timedelta(0)

    # V61 : HSI 150
    if HSNI_130_td_HS == seuil_20h_td_HS:
        HSI_150_td_HS = I61_td_HS
    else:
        reste_td_HS = I61_td_HS - HSNI_150_td_HS
        HSI_150_td_HS = reste_td_HS if reste_td_HS > timedelta(0) else timedelta(0)

    # --- Retour du résultat en heures décimales ---

    return HSCalculationResultHS(
        worker_id_HS=req_HS.worker_id_HS,
        mois_HS=req_HS.mois_HS,
        total_HSNI_130_heures_HS=_td_to_hours_HS(HSNI_130_td_HS),
        total_HSI_130_heures_HS=_td_to_hours_HS(HSI_130_td_HS),
        total_HSNI_150_heures_HS=_td_to_hours_HS(HSNI_150_td_HS),
        total_HSI_150_heures_HS=_td_to_hours_HS(HSI_150_td_HS),
        total_HMNH_30_heures_HS=_td_to_hours_HS(total_HMNH_td_HS),
        total_HMNO_50_heures_HS=_td_to_hours_HS(total_HMNO_td_HS),
        total_HMD_40_heures_HS=_td_to_hours_HS(total_HMD_td_HS),
        total_HMJF_50_heures_HS=_td_to_hours_HS(total_HMJF_td_HS),
    )


# --------- 🚀 Endpoints FastAPI ---------


@router.post("/calculate", response_model=HSCalculationResultHS)
def calculate_hs_endpoint_HS(payload_HS: HSCalculationRequestHS) -> HSCalculationResultHS:
    """
    Endpoint API :
    POST /hs/calculate
    -> calcule les HS mais ne sauvegarde pas en base
    """
    return calculer_heures_supplementaires_et_majorations_HS(payload_HS)


@router.post("/calculate-and-save", response_model=HSCalculationReadHS)
def calculate_and_save_hs_endpoint_HS(
    payload_HS: HSCalculationRequestHS,
    db: Session = Depends(get_db),
) -> HSCalculationReadHS:
    """
    Endpoint API :
    POST /hs/calculate-and-save

    1. Calcule les HS (comme /hs/calculate)
    2. Sauvegarde le résumé mensuel dans hs_calculations_HS
    3. Retourne l'enregistrement sauvegardé (avec id_HS)
    """
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
