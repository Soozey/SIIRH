# backend/app/schemas.py
from typing import Optional, List
from pydantic import BaseModel


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
