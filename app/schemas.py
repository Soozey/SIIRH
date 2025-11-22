# backend/app/schemas.py
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime, date, time


# ==========================
#  TYPE RÉGIME
# ==========================
class TypeRegimeIn(BaseModel):
    code: str            # "agricole" | "non_agricole"
    label: str           # ex: "Régime Agricole"
    vhm: float           # Valeur Horaire Mensuelle moyenne (ex: 200.0 ou 173.33)


class TypeRegimeOut(TypeRegimeIn):
    id: int

    class Config:
        from_attributes = True


# ==========================
#  EMPLOYEUR
# ==========================
class EmployerIn(BaseModel):
    raison_sociale: str
    adresse: Optional[str] = None
    pays: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    activite: Optional[str] = None
    representant: Optional[str] = None
    nif: Optional[str] = None
    stat: Optional[str] = None
    lieu_fiscal: Optional[str] = None
    cnaps_num: Optional[str] = None

    # Champs supplémentaires alignés avec models.Employer
    rcs: Optional[str] = None
    ostie_num: Optional[str] = None
    smie_num: Optional[str] = None
    ville: Optional[str] = None
    contact_rh: Optional[str] = None

    sm_embauche: Optional[float] = 0.0
    type_etab: str = "general"              # "general" | "scolaire"
    taux_pat_cnaps: float = 13.0            # auto 13% si "general", 8% si "scolaire"
    taux_pat_smie: float = 0.0

    # Lien vers le type de régime (FK)
    type_regime_id: Optional[int] = None

    # Paramètres de contributions
    taux_sal_cnaps: float = 1.0             # part salarié CNaPS (%)
    plafond_cnaps_base: float = 0.0         # 0 = pas de plafond
    taux_pat_fmfp: float = 1.0              # part employeur FMFP (%)

    taux_sal_smie: float = 0.0              # part salarié SMIE (%)
    smie_forfait_sal: float = 0.0           # forfait salarié SMIE (montant)
    smie_forfait_pat: float = 0.0           # forfait employeur SMIE (montant)


class EmployerOut(EmployerIn):
    id: int
    type_regime: Optional[TypeRegimeOut] = None

    class Config:
        from_attributes = True


# ==========================
#  SALARIÉ
# ==========================
class WorkerIn(BaseModel):
    employer_id: int
    matricule: str
    nom: str
    prenom: str
    adresse: str
    nombre_enfant: int
    type_regime_id: int                               # "agricole" | "non_agricole" (libre si tu préfères)
    salaire_base: float
    salaire_horaire: float
    vhm: float
    horaire_hebdo: float


class WorkerOut(WorkerIn):
    id: int

    class Config:
        from_attributes = True


# ==========================
#  VARIABLES DE PAIE (PayVar)
# ==========================
class PayVarIn(BaseModel):
    worker_id: int
    period: str  # format "AAAA-MM"

    # congés / absences
    conge_pris_j: float = 0.0
    conge_restant_j: float = 0.0
    conge_valeur: float = 0.0
    abs_maladie_j: float = 0.0
    abs_non_remu_h: float = 0.0
    abs_non_remu_j: float = 0.0
    mise_a_pied_j: float = 0.0

    # heures supplémentaires
    hsni_130_h: float = 0.0
    hsi_130_h: float = 0.0
    hsni_150_h: float = 0.0
    hsi_150_h: float = 0.0

    # majorations
    dimanche_h: float = 0.0
    nuit_hab_h: float = 0.0
    nuit_occ_h: float = 0.0
    ferie_jour_h: float = 0.0

    # primes (ajoute prime3..prime10 plus tard si besoin)
    prime1: float = 0.0
    prime2: float = 0.0

    # avantages en nature
    avantage_logement: float = 0.0
    avantage_vehicule: float = 0.0
    avantage_telephone: float = 0.0
    avantage_autres: float = 0.0

    # avances et autres déductions
    avance_quinzaine: float = 0.0
    avance_speciale_total: float = 0.0
    avance_speciale_rembfixe: float = 0.0
    avance_speciale_restant_prec: float = 0.0
    autre_ded1: float = 0.0
    autre_ded2: float = 0.0
    autre_ded3: float = 0.0
    autre_ded4: float = 0.0

    # allocations familiales
    alloc_familiale: float = 0.0


class PayVarOut(PayVarIn):
    id: int

    class Config:
        from_attributes = True


# ==========================
#   SCHEMAS HS (Heures Supplémentaires)
#   Suffixe HS pour tout ce qui concerne ce module
# ==========================


class HSJourBaseHS(BaseModel):
  """
  Données d'une journée HS (côté API / lecture).
  Correspond à une ligne de la table hs_jours_HS.
  """

  date_HS: date
  type_jour_HS: str  # 'N' ou 'JF'
  entree_HS: time
  sortie_HS: time
  type_nuit_HS: Optional[str] = None  # None, 'H' ou 'O'

  # Champs calculés (en heures décimales)
  duree_travail_totale_heures_HS: Optional[float] = None
  duree_base_heures_HS: Optional[float] = None
  hmnh_30_heures_HS: Optional[float] = None
  hmno_50_heures_HS: Optional[float] = None
  hmd_40_heures_HS: Optional[float] = None
  hmjf_50_heures_HS: Optional[float] = None

  # Semaine ISO (pour recontrôle)
  iso_year_HS: Optional[int] = None
  iso_week_HS: Optional[int] = None

  commentaire_HS: Optional[str] = None


class HSJourCreateHS(HSJourBaseHS):
  """
  Schéma utilisé si un jour HS est créé côté API.
  En pratique, on créera surtout ces lignes en backend
  à partir de la requête de calcul HS.
  """

  calculation_id_HS: int


class HSJourReadHS(HSJourBaseHS):
  """
  Schéma de lecture d'une ligne hs_jours_HS.
  """

  id_HS: int
  calculation_id_HS: int

  class Config:
    orm_mode = True


class HSCalculationBaseHS(BaseModel):
  """
  Champs communs pour un calcul HS mensuel.
  Correspond à la table hs_calculations_HS.
  """

  worker_id_HS: int
  mois_HS: str  # 'YYYY-MM'
  base_hebdo_heures_HS: float

  total_HSNI_130_heures_HS: float
  total_HSI_130_heures_HS: float
  total_HSNI_150_heures_HS: float
  total_HSI_150_heures_HS: float

  total_HMNH_30_heures_HS: float
  total_HMNO_50_heures_HS: float
  total_HMD_40_heures_HS: float
  total_HMJF_50_heures_HS: float


class HSCalculationCreateHS(HSCalculationBaseHS):
  """
  Schéma pour créer un calcul HS en BDD.
  On peut éventuellement l'enrichir avec des paramètres supplémentaires.
  """

  payroll_run_id_HS: Optional[int] = None


class HSCalculationReadHS(HSCalculationBaseHS):
  """
  Schéma de lecture d'un calcul HS (résumé mensuel),
  avec éventuellement les jours HS associés.
  """

  id_HS: int
  payroll_run_id_HS: Optional[int] = None

  created_at_HS: datetime
  updated_at_HS: datetime

  # Liste des jours HS rattachés à ce calcul
  jours_HS: List[HSJourReadHS] = []

  class Config:
    orm_mode = True


class AbsenceInput(BaseModel):
    salaire_base: float = Field(..., description="Salaire de base mensuel")
    salaire_horaire: float = Field(..., description="Salaire horaire de référence")

    ABSM_J: float = 0.0   # Absence maladie en jours (informatif)
    ABSM_H: float = 0.0   # Absence maladie en heures (informatif)
    ABSNR_J: float = 0.0  # Absence non rémunérée en jours
    ABSNR_H: float = 0.0  # Absence non rémunérée en heures
    ABSMP: float = 0.0    # Mise à pied (jours)
    ABS1_J: float = 0.0   # Autre absence 1 (jours)
    ABS1_H: float = 0.0   # Autre absence 1 (heures)
    ABS2_J: float = 0.0   # Autre absence 2 (jours)
    ABS2_H: float = 0.0   # Autre absence 2 (heures)


class AbsenceRubriqueResult(BaseModel):
    code: str
    label: str
    unite: Literal["jour", "heure"]
    nombre: float
    base: float
    montant_salarial: float


class AbsenceCalculationResult(BaseModel):
    salaire_journalier: float
    salaire_horaire: float
    rubriques: List[AbsenceRubriqueResult]
    total_retenues_absence: float