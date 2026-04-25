from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime, date, time
import re


PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _validate_period(value: str) -> str:
    if not PERIOD_PATTERN.match(value or ""):
        raise ValueError("Period must use YYYY-MM format")
    return value


# ==========================
#  TYPE RÃ‰GIME
# ==========================
class TypeRegimeIn(BaseModel):
    code: str            # "agricole" | "non_agricole"
    label: str           # ex: "RÃ©gime Agricole"
    vhm: float           # Valeur Horaire Mensuelle moyenne (ex: 200.0 ou 173.33)


class TypeRegimeOut(TypeRegimeIn):
    id: int

    model_config = ConfigDict(from_attributes=True)

# ==========================
#  STRUCTURE ORGANISATIONNELLE HIÃ‰RARCHIQUE EN CASCADE
# ==========================

class OrganizationalNodeCreate(BaseModel):
    """SchÃ©ma pour crÃ©er un nouveau nÅ“ud organisationnel"""
    parent_id: Optional[int] = None
    level: Literal['etablissement', 'departement', 'service', 'unite'] = Field(..., description="Niveau hiÃ©rarchique")
    name: str = Field(..., min_length=1, max_length=255, description="Nom du nÅ“ud organisationnel")
    code: Optional[str] = Field(None, max_length=50, description="Code optionnel du nÅ“ud")
    description: Optional[str] = None
    sort_order: int = Field(0, description="Ordre de tri")


class OrganizationalNodeUpdate(BaseModel):
    """SchÃ©ma pour mettre Ã  jour un nÅ“ud organisationnel"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class OrganizationalNodeOut(BaseModel):
    """SchÃ©ma de sortie pour un nÅ“ud organisationnel"""
    id: int
    employer_id: int
    parent_id: Optional[int]
    level: str
    name: str
    code: Optional[str]
    description: Optional[str]
    path: Optional[str]
    sort_order: int
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    children: Optional[List['OrganizationalNodeOut']] = []

    model_config = ConfigDict(from_attributes=True)

class OrganizationalTreeOut(BaseModel):
    """SchÃ©ma pour l'arbre hiÃ©rarchique complet"""
    nodes: List[OrganizationalNodeOut]
    total_count: int


class CascadingOptionsOut(BaseModel):
    """SchÃ©ma pour les options de filtrage en cascade"""
    id: int
    name: str
    code: Optional[str]
    level: str
    parent_id: Optional[int]
    path: Optional[str]


class OrganizationalPathValidation(BaseModel):
    """SchÃ©ma pour valider un chemin organisationnel"""
    etablissement_id: Optional[int] = None
    departement_id: Optional[int] = None
    service_id: Optional[int] = None
    unite_id: Optional[int] = None


class OrganizationalPathValidationResult(BaseModel):
    """RÃ©sultat de validation d'un chemin organisationnel"""
    is_valid: bool
    errors: List[str] = []


class OrganizationalMoveRequest(BaseModel):
    """SchÃ©ma pour dÃ©placer un nÅ“ud"""
    new_parent_id: Optional[int] = None


class OrganizationalTreeNode(BaseModel):
    """NÅ“ud d'arbre hiÃ©rarchique avec enfants"""
    id: int
    parent_id: Optional[int]
    level: int
    name: str
    code: Optional[str]
    description: Optional[str]
    is_active: bool
    level_name: str
    children: List['OrganizationalTreeNode'] = []
    worker_count: int = 0


class CascadingOptionsResponse(BaseModel):
    """RÃ©ponse pour les options de filtrage en cascade"""
    level: int
    parent_id: Optional[int]
    options: List[Dict[str, Any]]


class HierarchicalValidationResult(BaseModel):
    """RÃ©sultat de validation hiÃ©rarchique"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class OrganizationalMigrationAnalysis(BaseModel):
    """RÃ©sultat d'analyse de migration organisationnelle"""
    total_combinations: int
    total_workers_affected: int
    combinations: List[Dict[str, Any]]
    hierarchy_analysis: Dict[str, Any]
    migration_strategy: str
    estimated_duration: str
    risk_level: str


class OrganizationalMigrationResult(BaseModel):
    """RÃ©sultat d'exÃ©cution de migration"""
    etablissements_created: int
    departements_created: int
    services_created: int
    unites_created: int
    workers_updated: int
    conflicts: List[str] = []


# ==========================
#  STRUCTURE ORGANISATIONNELLE (ANCIEN SYSTÃˆME)
# ==========================
class OrganizationalUnitCreate(BaseModel):
    level: Literal['etablissement', 'departement', 'service', 'unite']
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    parent_id: Optional[int] = None
    description: Optional[str] = None


class CreateOrganizationalUnitRequest(BaseModel):
    """Request schema for creating organizational units"""
    employer_id: int
    level: Literal['etablissement', 'departement', 'service', 'unite']
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    parent_id: Optional[int] = None
    description: Optional[str] = None


class OrganizationalUnitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateOrganizationalUnitRequest(BaseModel):
    """Request schema for updating organizational units"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationalUnitOut(BaseModel):
    id: int
    employer_id: int
    parent_id: Optional[int]
    level: str
    level_order: int
    code: str
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ValidationResult(BaseModel):
    """Result of validation operations"""
    is_valid: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class OrganizationalTreeResponse(BaseModel):
    """Response schema for organizational tree"""
    employer_id: int
    tree: List[Dict[str, Any]]
    total_units: int
    levels_present: List[str]


class CascadingChoicesResponse(BaseModel):
    """Response schema for cascading organizational choices"""
    level: str
    parent_id: Optional[int]
    choices: List[Dict[str, Any]]


class WorkerAssignment(BaseModel):
    worker_id: int
    organizational_unit_id: Optional[int] = None


class OrganizationTreeNode(BaseModel):
    id: int
    name: str
    code: str
    level: str
    level_order: int
    description: Optional[str]
    direct_workers: List[Dict[str, Any]]
    children: List['OrganizationTreeNode']
    total_workers: int


class OrganizationTree(BaseModel):
    employer_id: int
    root_units: List[OrganizationTreeNode]
    orphan_workers: List[Dict[str, Any]]
    total_workers: int


class MigrationResult(BaseModel):
    migrated_count: int
    message: str


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

    # ReprÃ©sentant avancÃ©
    rep_date_naissance: Optional[date] = None
    rep_cin_num: Optional[str] = None
    rep_cin_date: Optional[date] = None
    rep_cin_lieu: Optional[str] = None
    rep_adresse: Optional[str] = None
    rep_fonction: Optional[str] = None

    # Champs supplÃ©mentaires alignÃ©s avec models.Employer
    rcs: Optional[str] = None
    ostie_num: Optional[str] = None
    smie_num: Optional[str] = None
    ville: Optional[str] = None
    contact_rh: Optional[str] = None

    sm_embauche: Optional[float] = 0.0
    type_etab: str = "general"              # "general" | "scolaire"
    taux_pat_cnaps: float = 13.0            # auto 13% si "general", 8% si "scolaire"
    taux_pat_smie: float = 0.0

    # Lien vers le type de rÃ©gime (FK)
    type_regime_id: Optional[int] = None

    # ParamÃ¨tres de contributions
    taux_sal_cnaps: float = 1.0             # part salariÃ© CNaPS (%)
    plafond_cnaps_base: float = 0.0         # 0 = pas de plafond
    taux_pat_fmfp: float = 1.0              # part employeur FMFP (%)

    taux_sal_smie: float = 0.0              # part salariÃ© SMIE (%)
    smie_forfait_sal: float = 0.0           # forfait salariÃ© SMIE (montant)
    smie_forfait_pat: float = 0.0           # forfait employeur SMIE (montant)
    plafond_smie: float = 0.0               # Plafond manuel pour le SMIE
    logo_path: Optional[str] = None         # Chemin vers le logo
    
    # Labels des Primes 1..5
    label_prime1: Optional[str] = "Prime 1"
    label_prime2: Optional[str] = "Prime 2"
    label_prime3: Optional[str] = "Prime 3"
    label_prime4: Optional[str] = "Prime 4"
    label_prime5: Optional[str] = "Prime 5"
    
    # ðŸ”¹ NOUVELLES LISTES ORGANISATIONNELLES
    etablissements: Optional[List[str]] = Field(default_factory=list)
    departements: Optional[List[str]] = Field(default_factory=list)
    services: Optional[List[str]] = Field(default_factory=list)
    unites: Optional[List[str]] = Field(default_factory=list)

    @field_validator("raison_sociale")
    @classmethod
    def validate_raison_sociale(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("raison_sociale is required")
        return value



class WorkerPrimeIn(BaseModel):
    label: str
    formula_nombre: Optional[str] = None
    formula_base: Optional[str] = None
    formula_taux: Optional[str] = None
    operation_1: str = "*"
    operation_2: str = "*"
    is_active: bool = True


class WorkerPrimeOut(WorkerPrimeIn):
    id: int
    worker_id: int

    model_config = ConfigDict(from_attributes=True)

class EmployerOut(EmployerIn):
    id: int
    type_regime: Optional[TypeRegimeOut] = None
    # primes removed

    model_config = ConfigDict(from_attributes=True)

# ==========================
#  SALARIÃ‰
# ==========================
class WorkerIn(BaseModel):
    employer_id: int
    matricule: str
    nom: str
    prenom: str
    sexe: Optional[str] = None
    situation_familiale: Optional[str] = None
    date_naissance: Optional[date] = None
    adresse: Optional[str] = None  # ChangÃ© de str Ã  Optional[str]
    telephone: Optional[str] = None
    email: Optional[str] = None
    cin: Optional[str] = None
    cin_delivre_le: Optional[date] = None
    cin_lieu: Optional[str] = None
    cnaps_num: Optional[str] = None
    nombre_enfant: Optional[int] = 0
    date_embauche: Optional[date] = None
    type_regime_id: Optional[int] = None  # ChangÃ© de int Ã  Optional[int]                               # "agricole" | "non_agricole"
    salaire_base: float
    salaire_horaire: float
    vhm: float
    horaire_hebdo: float
    nature_contrat: Optional[str] = "CDI" # CDI / CDD
    duree_essai_jours: Optional[int] = 0
    date_fin_essai: Optional[date] = None
    etablissement: Optional[str] = None
    departement: Optional[str] = None
    service: Optional[str] = None
    unite: Optional[str] = None
    indice: Optional[str] = None
    valeur_point: Optional[float] = 0.0
    secteur: Optional[str] = None 
    mode_paiement: Optional[str] = "Virement"
    rib: Optional[str] = None
    code_banque: Optional[str] = None
    code_guichet: Optional[str] = None
    compte_num: Optional[str] = None
    cle_rib: Optional[str] = None
    banque: Optional[str] = None
    nom_guichet: Optional[str] = None
    bic: Optional[str] = None
    categorie_prof: Optional[str] = None
    poste: Optional[str] = None
    solde_conge_initial: Optional[float] = 0.0
    
    # DÃ©bauche / Rupture
    date_debauche: Optional[date] = None
    type_sortie: Optional[str] = None      # "L" | "D"
    groupe_preavis: Optional[int] = None   # 1..5
    jours_preavis_deja_faits: Optional[int] = 0
    
    # Avantages (valeurs fixes)
    avantage_vehicule: Optional[float] = 0.0
    avantage_logement: Optional[float] = 0.0
    avantage_telephone: Optional[float] = 0.0
    avantage_autres: Optional[float] = 0.0

    # Contribution rate overrides (optional)
    taux_sal_cnaps_override: Optional[float] = None
    taux_sal_smie_override: Optional[float] = None
    taux_pat_cnaps_override: Optional[float] = None
    taux_pat_smie_override: Optional[float] = None
    taux_pat_fmfp_override: Optional[float] = None

    # Structure organisationnelle (optionnelle)
    organizational_unit_id: Optional[int] = None

    @field_validator("matricule", "nom", "prenom")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("field is required")
        return value

    @field_validator("salaire_base", "salaire_horaire", "vhm", "horaire_hebdo")
    @classmethod
    def validate_positive_numbers(cls, value: float) -> float:
        if value is None or value < 0:
            raise ValueError("value must be non-negative")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.date_fin_essai and self.date_embauche and self.date_fin_essai < self.date_embauche:
            raise ValueError("date_fin_essai cannot be before date_embauche")
        if self.date_debauche and self.date_embauche and self.date_debauche < self.date_embauche:
            raise ValueError("date_debauche cannot be before date_embauche")
        return self



# ==========================
#  HISTORIQUE DES POSTES
# ==========================
class WorkerPositionHistoryBase(BaseModel):
    poste: str
    categorie_prof: Optional[str] = None
    indice: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None

class WorkerPositionHistoryIn(WorkerPositionHistoryBase):
    pass

class WorkerPositionHistoryOut(WorkerPositionHistoryBase):
    id: int
    worker_id: int

    model_config = ConfigDict(from_attributes=True)

class WorkerOut(WorkerIn):
    id: int
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    primes: List[WorkerPrimeOut] = []
    position_history: List[WorkerPositionHistoryOut] = []

    model_config = ConfigDict(from_attributes=True)


class OrgUnitEventOut(BaseModel):
    id: int
    employer_id: int
    org_unit_id: Optional[int] = None
    event_type: str
    payload_json: Dict[str, Any] = Field(default_factory=dict)
    triggered_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkerListDelete(BaseModel):
    ids: List[int]


class WorkerResetRequest(BaseModel):
    employer_id: Optional[int] = None
    mode: Literal["soft", "hard"] = "soft"
    confirmation_text: Optional[str] = None


class WorkerResetResult(BaseModel):
    ok: bool = True
    mode: str
    count: int
    message: str


# ==========================
#  VARIABLES DE PAIE (PayVar)
# ==========================
class PayVarBase(BaseModel):
    worker_id: int
    period: str  # format "YYYY-MM"

    # === HEURES SUPPLÃ‰MENTAIRES (totaux mois) ===
    hsni_130: float = 0.0   # HS non imposables 130%
    hsi_130: float = 0.0    # HS imposables 130%
    hsni_150: float = 0.0   # HS non imposables 150%
    hsi_150: float = 0.0    # HS imposables 150%
    hmn_30: float = 0.0     # Heures majorÃ©es nuit 30%

    # === ANCIEN CHAMP RÃ‰SUMÃ‰ (compatibilitÃ©) ===
    absences_non_remu: float = 0.0

    # === ABSENCES DÃ‰TAILLÃ‰ES ===
    abs_non_remu_j: float = 0.0   # Absences non rÃ©munÃ©rÃ©es (jours)
    abs_maladie_j: float = 0.0    # Absence maladie (jours)
    mise_a_pied_j: float = 0.0    # Mise Ã  pied (jours)
    abs_non_remu_h: float = 0.0   # Absences non rÃ©munÃ©rÃ©es (heures)

    # === PRIMES SIMPLES ===
    prime_fixe: float = 0.0
    prime_variable: float = 0.0

    # === PRIMES DÃ‰TAILLÃ‰ES 1..10 ===
    prime1: float = 0.0
    prime2: float = 0.0
    prime3: float = 0.0
    prime4: float = 0.0
    prime5: float = 0.0
    prime6: float = 0.0
    prime7: float = 0.0
    prime8: float = 0.0
    prime9: float = 0.0
    prime10: float = 0.0
    prime_13: float = 0.0  # 13Ã¨me Mois

    # === AVANTAGES EN NATURE ===
    avantage_vehicule: float = 0.0
    avantage_logement: float = 0.0
    avantage_telephone: float = 0.0
    avantage_autres: float = 0.0

    # === ALLOCATION FAMILIALE ===
    alloc_familiale: float = 0.0

    # === AVANCES & DÃ‰DUCTIONS ===
    avance_salaire: float = 0.0
    avance_quinzaine: float = 0.0
    avance_speciale_rembfixe: float = 0.0

    autre_ded1: float = 0.0
    autre_ded2: float = 0.0
    autre_ded3: float = 0.0
    autre_ded4: float = 0.0

    autres_gains: float = 0.0
    autres_retenues: float = 0.0


class PayVarIn(PayVarBase):
    """DonnÃ©es reÃ§ues depuis le front pour crÃ©er / mettre Ã  jour les variables de paie."""
    pass


class PayVarOut(PayVarBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ==========================
#   SCHEMAS HS (Heures SupplÃ©mentaires)
#   Suffixe HS pour tout ce qui concerne ce module
# ==========================


class HSJourBaseHS(BaseModel):
    """
    DonnÃ©es d'une journÃ©e HS (cÃ´tÃ© API / lecture).
    Correspond Ã  une ligne de la table hs_jours_HS.
    """

    date_HS: date
    type_jour_HS: str  # 'N' ou 'JF'
    entree_HS: time
    sortie_HS: time
    type_nuit_HS: Optional[str] = None  # None, 'H' ou 'O'

    # Champs calculÃ©s (en heures dÃ©cimales)
    duree_travail_totale_heures_HS: Optional[float] = None
    duree_base_heures_HS: Optional[float] = None
    hmnh_30_heures_HS: Optional[float] = None
    hmno_50_heures_HS: Optional[float] = None
    hmd_40_heures_HS: Optional[float] = None
    hmjf_50_heures_HS: Optional[float] = None

    # Semaine ISO (pour recontrÃ´le)
    iso_year_HS: Optional[int] = None
    iso_week_HS: Optional[int] = None

    commentaire_HS: Optional[str] = None


class HSJourCreateHS(HSJourBaseHS):
    """
    SchÃ©ma utilisÃ© si un jour HS est crÃ©Ã© cÃ´tÃ© API.
    En pratique, on crÃ©era surtout ces lignes en backend
    Ã  partir de la requÃªte de calcul HS.
    """

    calculation_id_HS: int


class PayrollRunOut(BaseModel):
    id: int
    employer_id: int
    period: str
    generated_at: Optional[date]
    employer_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class HSJourReadHS(HSJourBaseHS):
    """
    SchÃ©ma de lecture d'une ligne hs_jours_HS.
    """

    id_HS: int
    calculation_id_HS: int

    model_config = ConfigDict(from_attributes=True)

class HSCalculationBaseHS(BaseModel):
    """
    Champs communs pour un calcul HS mensuel.
    Correspond Ã  la table hs_calculations_HS.
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
    SchÃ©ma pour crÃ©er un calcul HS en BDD.
    On peut Ã©ventuellement l'enrichir avec des paramÃ¨tres supplÃ©mentaires.
    """

    payroll_run_id_HS: Optional[int] = None


class HSCalculationReadHS(HSCalculationBaseHS):
    """
    SchÃ©ma de lecture d'un calcul HS (rÃ©sumÃ© mensuel),
    avec Ã©ventuellement les jours HS associÃ©s.
    """

    id_HS: int
    payroll_run_id_HS: Optional[int] = None
    worker_matricule_HS: Optional[str] = None
    worker_nom_HS: Optional[str] = None
    worker_prenom_HS: Optional[str] = None
    worker_display_name_HS: Optional[str] = None

    created_at_HS: datetime
    updated_at_HS: datetime

    # Liste des jours HS rattachÃ©s Ã  ce calcul
    jours_HS: List[HSJourReadHS] = []

    model_config = ConfigDict(from_attributes=True)

class AbsenceInput(BaseModel):
    worker_id: int | None = Field(
        default=None,
        description="ID du salariÃ© (worker) concernÃ© par ces absences"
    )
    salaire_base: float = Field(..., description="Salaire de base mensuel")
    salaire_horaire: float = Field(..., description="Salaire horaire de rÃ©fÃ©rence")

    ABSM_J: float = 0.0   # Absence maladie en jours (informatif)
    ABSM_H: float = 0.0   # Absence maladie en heures (informatif)
    ABSNR_J: float = 0.0  # Absence non rÃ©munÃ©rÃ©e en jours
    ABSNR_H: float = 0.0  # Absence non rÃ©munÃ©rÃ©e en heures
    ABSMP: float = 0.0    # Mise Ã  pied (jours)
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


# ==========================
#  PAYROLL HS/HM
# ==========================

class PayrollHsHmBase(BaseModel):
    """Base schema for HS/HM data"""
    hsni_130_heures: float = Field(0.0, ge=0, description="HSNI 130% (heures)")
    hsi_130_heures: float = Field(0.0, ge=0, description="HSI 130% (heures)")
    hsni_150_heures: float = Field(0.0, ge=0, description="HSNI 150% (heures)")
    hsi_150_heures: float = Field(0.0, ge=0, description="HSI 150% (heures)")
    hmnh_heures: float = Field(0.0, ge=0, description="HMNH 30% (heures)")
    hmno_heures: float = Field(0.0, ge=0, description="HMNO 50% (heures)")
    hmd_heures: float = Field(0.0, ge=0, description="HMD 40% (heures)")
    hmjf_heures: float = Field(0.0, ge=0, description="HMJF 200% (heures)")

    # === ABSENCES ===
    ABSM_J: float = Field(0.0, ge=0, description="Absence Maladie (jours)")
    ABSM_H: float = Field(0.0, ge=0, description="Absence Maladie (heures)")
    ABSNR_J: float = Field(0.0, ge=0, description="Absence Non RÃ©munÃ©rÃ©e (jours)")
    ABSNR_H: float = Field(0.0, ge=0, description="Absence Non RÃ©munÃ©rÃ©e (heures)")
    ABSMP: float = Field(0.0, ge=0, description="Mise Ã  pied (jours)")
    ABS1_J: float = Field(0.0, ge=0, description="Autre Absence 1 (jours)")
    ABS1_H: float = Field(0.0, ge=0, description="Autre Absence 1 (heures)")
    ABS2_J: float = Field(0.0, ge=0, description="Autre Absence 2 (jours)")
    ABS2_H: float = Field(0.0, ge=0, description="Autre Absence 2 (heures)")

    # === AVANCE ===
    avance: float = Field(0.0, description="Avance (Montant)")

    # === AUTRES DÃ‰DUCTIONS (PayVar) ===
    autre_ded1: float = Field(0.0, description="Autre DÃ©duction 1")
    autre_ded2: float = Field(0.0, description="Autre DÃ©duction 2")
    autre_ded3: float = Field(0.0, description="Autre DÃ©duction 3")
    autre_ded4: float = Field(0.0, description="Autre DÃ©duction 4")

    # === AVANTAGES EN NATURE (PayVar Override) ===
    avantage_vehicule: float = Field(0.0, description="Avantage VÃ©hicule")
    avantage_logement: float = Field(0.0, description="Avantage Logement")
    avantage_telephone: float = Field(0.0, description="Avantage TÃ©lÃ©phone")
    avantage_autres: float = Field(0.0, description="Avantage Autres")

    # Primes & 13th Month removed from this view



class PayrollHsHmCreate(PayrollHsHmBase):
    """Schema for creating HS/HM entry"""
    payroll_run_id: int
    worker_id: int
    source_type: Literal["MANUAL", "IMPORT"]
    hs_calculation_id: Optional[int] = None
    import_file_name: Optional[str] = None


class PayrollHsHmOut(PayrollHsHmBase):
    """Schema for reading HS/HM entry with calculated amounts"""
    id: int
    payroll_run_id: int
    worker_id: int
    source_type: str
    hs_calculation_id: Optional[int]
    import_file_name: Optional[str]
    
    # Montants calculÃ©s (en Ariary)
    hsni_130_montant: float
    hsi_130_montant: float
    hsni_150_montant: float
    hsi_150_montant: float
    hmnh_montant: float
    hmno_montant: float
    hmd_montant: float
    hmjf_montant: float
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class LinkHsCalculationRequest(BaseModel):
    """Request to link a manual HS calculation to payroll"""
    hs_calculation_id: int


class ExcelImportRow(BaseModel):
    """Schema for one row of Excel import"""
    matricule: str = Field(..., description="Worker matricule")
    hsni_130_heures: float = Field(0.0, ge=0)
    hsi_130_heures: float = Field(0.0, ge=0)
    hsni_150_heures: float = Field(0.0, ge=0)
    hsi_150_heures: float = Field(0.0, ge=0)
    hmnh_heures: float = Field(0.0, ge=0)
    hmno_heures: float = Field(0.0, ge=0)
    hmd_heures: float = Field(0.0, ge=0)
    hmjf_heures: float = Field(0.0, ge=0)


class ExcelImportSummary(BaseModel):
    """Summary of Excel import results"""
    total_rows: int
    successful: int
    failed: int
    errors: List[str] = []


class ImportIssue(BaseModel):
    row_number: int
    code: str
    message: str
    column: Optional[str] = None
    value: Optional[str] = None


class TabularImportReport(BaseModel):
    mode: Literal["create", "update", "mixed"] = "mixed"
    total_rows: int = 0
    processed_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    unknown_columns: List[str] = Field(default_factory=list)
    missing_columns: List[str] = Field(default_factory=list)
    issues: List[ImportIssue] = Field(default_factory=list)
    error_report_csv: Optional[str] = None


class SystemImportOptions(BaseModel):
    update_existing: bool = True
    skip_exact_duplicates: bool = True
    continue_on_error: bool = True
    strict_mode: bool = False
    selected_modules: List[str] = Field(default_factory=list)


class SystemImportManifestSummary(BaseModel):
    source_system: Optional[str] = None
    package_version: Optional[str] = None
    export_version: Optional[str] = None
    modules_detected: List[str] = Field(default_factory=list)
    modules_requested: List[str] = Field(default_factory=list)
    expected_records: Dict[str, int] = Field(default_factory=dict)
    detected_records: Dict[str, int] = Field(default_factory=dict)
    compatibility_warnings: List[str] = Field(default_factory=list)


class SystemImportModuleReport(BaseModel):
    module: str
    expected_records: Optional[int] = None
    detected_records: int = 0
    processed_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    conflicts: int = 0
    unmapped_fields: List[str] = Field(default_factory=list)
    issues: List[ImportIssue] = Field(default_factory=list)


class SystemDataImportReport(BaseModel):
    dry_run: bool = False
    started_at: datetime
    finished_at: Optional[datetime] = None
    options: SystemImportOptions = Field(default_factory=SystemImportOptions)
    manifest: SystemImportManifestSummary = Field(default_factory=SystemImportManifestSummary)
    modules: List[SystemImportModuleReport] = Field(default_factory=list)
    total_processed_rows: int = 0
    total_created: int = 0
    total_updated: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    total_conflicts: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class SystemDataImportExecuteResponse(BaseModel):
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    conflicts: int = 0
    report: SystemDataImportReport


class SystemExportOptions(BaseModel):
    selected_modules: List[str] = Field(default_factory=list)
    employer_id: Optional[int] = None
    include_inactive: bool = True
    include_document_content: bool = False


class SystemExportManifestSummary(BaseModel):
    source_system: Optional[str] = None
    package_version: Optional[str] = None
    export_version: Optional[str] = None
    modules_requested: List[str] = Field(default_factory=list)
    modules_exported: List[str] = Field(default_factory=list)
    detected_records: Dict[str, int] = Field(default_factory=dict)
    compatibility_warnings: List[str] = Field(default_factory=list)


class SystemDataExportPreview(BaseModel):
    generated_at: datetime
    options: SystemExportOptions = Field(default_factory=SystemExportOptions)
    manifest: SystemExportManifestSummary = Field(default_factory=SystemExportManifestSummary)
    total_records: int = 0
    warnings: List[str] = Field(default_factory=list)


class SystemUpdateTarget(BaseModel):
    source: str
    destination: str


class SystemUpdateManifest(BaseModel):
    version: str
    package_sha256: str
    payload_root: str = "payload"
    targets: List[SystemUpdateTarget] = Field(default_factory=list)
    requires_migration: bool = True
    migration_command: Optional[str] = None
    notes: Optional[str] = None


class SystemUpdateJobStatus(BaseModel):
    job_id: str
    status: str
    stage: str
    progress: int = 0
    environment_mode: str = "unknown"
    package_filename: str
    package_sha256: Optional[str] = None
    package_version: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    backup_path: Optional[str] = None
    rollback_performed: bool = False
    logs: List[str] = Field(default_factory=list)
    error: Optional[str] = None


# ============================================================
# LEAVE & PERMISSION SCHEMAS
# ============================================================

class LeaveBase(BaseModel):
    worker_id: int
    period: str  # "2025-01" format
    start_date: date
    end_date: date
    days_taken: float
    notes: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        return _validate_period(value)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        if self.days_taken < 0:
            raise ValueError("days_taken must be non-negative")
        return self


class LeaveCreate(LeaveBase):
    pass


class LeaveOut(LeaveBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PermissionBase(BaseModel):
    worker_id: int
    period: str  # "2025-01" format
    start_date: date
    end_date: date
    days_taken: float
    notes: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        return _validate_period(value)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        if self.days_taken < 0:
            raise ValueError("days_taken must be non-negative")
        return self


class PermissionCreate(PermissionBase):
    pass


class PermissionOut(PermissionBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ==========================
#  REPORTING
# ==========================

class ReportField(BaseModel):
    id: str           # ex: "matricule", "brut"
    label: str        # LibellÃ© lisible
    category: str     # CatÃ©gorie (IdentitÃ©, Base, Gains, Retenues, RÃ©sultats, etc.)

class ReportMetadataOut(BaseModel):
    fields: List[ReportField]

class ReportRequest(BaseModel):
    employer_id: int
    start_period: str # "YYYY-MM"
    end_period: str   # "YYYY-MM"
    columns: List[str] # Liste des IDs des colonnes souhaitÃ©es
    etablissement: Optional[int] = None  # ChangÃ© de str Ã  int
    departement: Optional[int] = None    # ChangÃ© de str Ã  int
    service: Optional[int] = None        # ChangÃ© de str Ã  int
    unite: Optional[int] = None          # ChangÃ© de str Ã  int

    @field_validator("start_period", "end_period")
    @classmethod
    def validate_period_fields(cls, value: str) -> str:
        return _validate_period(value)

    @model_validator(mode="after")
    def validate_period_order(self):
        if self.end_period < self.start_period:
            raise ValueError("end_period cannot be before start_period")
        return self


# ==========================
#  CONTRATS PERSONNALISÃ‰S
# ==========================

class CustomContractIn(BaseModel):
    worker_id: int
    employer_id: int
    title: str = "Contrat de Travail"
    content: str
    template_type: str = "employment_contract"
    is_default: bool = False
    validation_status: str = "active_non_validated"
    inspection_status: str = "pending_review"
    inspection_comment: Optional[str] = None


class CustomContractOut(CustomContractIn):
    id: int
    active_version_number: int = 1
    last_published_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CustomContractUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_default: Optional[bool] = None
    validation_status: Optional[str] = None
    inspection_status: Optional[str] = None
    inspection_comment: Optional[str] = None


# ==========================
#  TEMPLATES DE DOCUMENTS
# ==========================

class DocumentTemplateIn(BaseModel):
    employer_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    template_type: str  # 'contract', 'certificate', 'attestation'
    content: str
    is_active: bool = True


class DocumentTemplateOut(DocumentTemplateIn):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


class UserLoginIn(BaseModel):
    username: str
    password: str


class PublicRegistrationRoleOut(BaseModel):
    code: str
    label: str
    scope: str


class PublicRegistrationConfigOut(BaseModel):
    enabled: bool = True
    password_policy: str
    allowed_roles: List[PublicRegistrationRoleOut] = Field(default_factory=list)


class PublicRegisterIn(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role_code: str = "salarie_agent"
    worker_matricule: str


class PublicRegisterOut(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str] = None
    role_code: str
    account_status: str = "PENDING_APPROVAL"
    employer_id: Optional[int] = None
    worker_id: int
    created_at: datetime


class PublicDemoAccountOut(BaseModel):
    label: str
    role_code: str
    username: str


class LabourLegalAlertOut(BaseModel):
    code: str
    severity: str
    title: str
    message: str
    due_at: Optional[datetime] = None


class LabourCaseLegalSummaryOut(BaseModel):
    requires_inspection_before_court: bool = False
    employment_relationship_active: bool = False
    convocation_count: int = 0
    no_show_convocation_count: int = 0
    pv_due_at: Optional[datetime] = None
    last_pv_delivered_at: Optional[datetime] = None
    eligible_pv_types: List[str] = Field(default_factory=list)
    alerts: List[LabourLegalAlertOut] = Field(default_factory=list)


class UserSessionOut(BaseModel):
    token: str
    user_id: int
    username: str
    full_name: Optional[str] = None
    role_code: str
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    effective_role_code: Optional[str] = None
    role_label: Optional[str] = None
    role_scope: Optional[str] = None
    module_permissions: Dict[str, List[str]] = Field(default_factory=dict)
    assigned_role_codes: List[str] = Field(default_factory=list)
    account_status: str = "ACTIVE"
    must_change_password: bool = False


class UserAccessProfileOut(BaseModel):
    role_code: str
    effective_role_code: str
    role_label: str
    role_scope: str
    module_permissions: Dict[str, List[str]] = Field(default_factory=dict)
    assigned_role_codes: List[str] = Field(default_factory=list)


class AppUserLightOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role_code: str
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    is_active: bool = True
    account_status: str = "ACTIVE"
    must_change_password: bool = False

    model_config = ConfigDict(from_attributes=True)

class RoleCatalogItemOut(BaseModel):
    code: str
    label: str
    scope: str
    base_role_code: Optional[str] = None
    modules: Dict[str, List[str]]
    is_active: bool = True


class RoleCatalogPublicItemOut(BaseModel):
    code: str
    label: str
    scope: str
    base_role_code: Optional[str] = None
    is_active: bool = True


class IamPermissionCatalogItemOut(BaseModel):
    code: str
    module: str
    action: str
    label: str
    sensitivity: str = "base"


class IamRoleActivationOut(BaseModel):
    role_code: str
    is_enabled: bool


class IamRoleActivationUpdateIn(BaseModel):
    is_enabled: bool


class IamRolePermissionsUpdateIn(BaseModel):
    modules: Dict[str, List[str]] = Field(default_factory=dict)


class IamRolePermissionsOut(BaseModel):
    role_code: str
    modules: Dict[str, List[str]] = Field(default_factory=dict)


class IamUserRoleAssignmentIn(BaseModel):
    role_code: str
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class IamUserRoleAssignmentOut(IamUserRoleAssignmentIn):
    id: int
    user_id: int
    delegated_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IamUserRoleAssignmentSetIn(BaseModel):
    assignments: List[IamUserRoleAssignmentIn] = Field(default_factory=list)


class IamUserPermissionOverrideIn(BaseModel):
    permission_code: str
    is_allowed: bool
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None


class IamUserPermissionOverrideOut(IamUserPermissionOverrideIn):
    id: int
    user_id: int
    updated_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IamUserPermissionOverrideSetIn(BaseModel):
    overrides: List[IamUserPermissionOverrideIn] = Field(default_factory=list)


class AppUserCreateIn(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role_code: str
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    is_active: bool = True
    account_status: Optional[str] = None
    must_change_password: bool = False


class AppUserUpdateIn(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    role_code: Optional[str] = None
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    is_active: Optional[bool] = None
    account_status: Optional[str] = None
    must_change_password: Optional[bool] = None


class AppUserDeleteIn(BaseModel):
    current_password: str


class AppUserOut(AppUserLightOut):
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[int] = None
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AppUserStatusUpdateIn(BaseModel):
    status: str


class AppUserRejectIn(BaseModel):
    reason: Optional[str] = None


class AppUserResetPasswordIn(BaseModel):
    temporary_password: str
    must_change_password: bool = True


class AppUserChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class IamSummaryOut(BaseModel):
    total_users: int = 0
    pending_users: int = 0
    active_users: int = 0
    suspended_users: int = 0
    rejected_users: int = 0
    password_reset_required_users: int = 0
    roles_count: int = 0
    permissions_count: int = 0


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_role: Optional[str] = None
    actor_username: Optional[str] = None
    actor_full_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    route: Optional[str] = None
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    before: Dict[str, Any] = Field(default_factory=dict)
    after: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class ReviewWorkflowIn(BaseModel):
    approved: bool
    comment: Optional[str] = None


class RequestWorkflowOut(BaseModel):
    id: int
    request_type: str
    request_id: int
    overall_status: str
    manager_status: str
    rh_status: str
    manager_comment: Optional[str] = None
    rh_comment: Optional[str] = None
    manager_actor_user_id: Optional[int] = None
    rh_actor_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveTypeRuleIn(BaseModel):
    employer_id: Optional[int] = None
    code: str
    label: str
    category: str = "leave"
    description: Optional[str] = None
    deduct_from_annual_balance: bool = False
    validation_required: bool = True
    justification_required: bool = False
    payroll_impact: str = "none"
    attendance_impact: str = "absence"
    payroll_code: Optional[str] = None
    visibility_scope: str = "all"
    allow_requalification: bool = True
    supports_hour_range: bool = False
    max_days_per_request: Optional[float] = None
    active: bool = True


class LeaveTypeRuleOut(LeaveTypeRuleIn):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveApprovalRuleStepIn(BaseModel):
    step_order: int = 1
    parallel_group: int = 1
    approver_kind: str = "manager"
    approver_role_code: Optional[str] = None
    approver_user_id: Optional[int] = None
    is_required: bool = True
    label: Optional[str] = None


class LeaveApprovalRuleStepOut(LeaveApprovalRuleStepIn):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveApprovalRuleIn(BaseModel):
    employer_id: Optional[int] = None
    leave_type_code: str
    worker_category: Optional[str] = None
    organizational_unit_id: Optional[int] = None
    approval_mode: str = "sequential"
    fallback_on_reject: str = "reject"
    active: bool = True
    steps: List[LeaveApprovalRuleStepIn] = Field(default_factory=list)


class LeaveApprovalRuleOut(LeaveApprovalRuleIn):
    id: int
    created_at: datetime
    updated_at: datetime
    steps: List[LeaveApprovalRuleStepOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LeaveRequestCreate(BaseModel):
    worker_id: int
    leave_type_code: str
    start_date: date
    end_date: date
    duration_days: Optional[float] = None
    duration_hours: float = 0.0
    partial_day_mode: Optional[str] = None
    subject: str
    reason: Optional[str] = None
    comment: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    submit_now: bool = True

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class LeaveRequestDecisionIn(BaseModel):
    action: str
    comment: Optional[str] = None


class LeaveRequestRequalifyIn(BaseModel):
    new_leave_type_code: str
    comment: str


class LeavePlanningCycleIn(BaseModel):
    employer_id: int
    title: str
    planning_year: int
    start_date: date
    end_date: date
    status: str = "draft"
    max_absent_per_unit: int = 1
    blackout_periods: List[Dict[str, Any]] = Field(default_factory=list)
    family_priority_enabled: bool = True
    notes: Optional[str] = None


class LeavePlanningCycleOut(LeavePlanningCycleIn):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeavePlanningProposalOut(BaseModel):
    id: int
    cycle_id: int
    worker_id: int
    worker_name: str
    leave_type_code: str
    start_date: date
    end_date: date
    score: float
    rationale: List[Dict[str, Any]] = Field(default_factory=list)
    status: str


class LeaveRequestApprovalOut(BaseModel):
    id: int
    step_order: int
    parallel_group: int
    approver_kind: str
    approver_user_id: Optional[int] = None
    approver_role_code: Optional[str] = None
    approver_label: Optional[str] = None
    label: Optional[str] = None
    is_required: bool = True
    status: str
    acted_at: Optional[datetime] = None
    comment: Optional[str] = None


class LeaveRequestHistoryOut(BaseModel):
    id: int
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    comment: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class LeaveRequestOut(BaseModel):
    id: int
    employer_id: int
    worker_id: int
    request_ref: str
    leave_type_code: str
    initial_leave_type_code: str
    final_leave_type_code: str
    status: str
    approval_mode: str
    fallback_on_reject: str
    current_step_order: Optional[int] = None
    period: str
    start_date: date
    end_date: date
    duration_days: float
    duration_hours: float
    partial_day_mode: Optional[str] = None
    subject: str
    reason: Optional[str] = None
    comment: Optional[str] = None
    attachment_required: bool = False
    attachment_count: int = 0
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_balance_delta: float = 0.0
    estimated_payroll_impact: str = "none"
    estimated_attendance_impact: str = "absence"
    legacy_request_type: Optional[str] = None
    legacy_request_id: Optional[int] = None
    requested_by_user_id: Optional[int] = None
    requested_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    integrated_at: Optional[datetime] = None
    requalified_at: Optional[datetime] = None
    validations_remaining: List[str] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    approvals: List[LeaveRequestApprovalOut] = Field(default_factory=list)
    history: List[LeaveRequestHistoryOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class LeaveDashboardOut(BaseModel):
    worker_id: int
    employer_id: int
    period: str
    balances: Dict[str, float] = Field(default_factory=dict)
    requests: List[LeaveRequestOut] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    notifications: List[Dict[str, Any]] = Field(default_factory=list)
    calendar: List[Dict[str, Any]] = Field(default_factory=list)


class LeaveValidatorDashboardOut(BaseModel):
    metrics: Dict[str, int] = Field(default_factory=dict)
    pending_requests: List[LeaveRequestOut] = Field(default_factory=list)
    urgent_requests: List[LeaveRequestOut] = Field(default_factory=list)
    conflicts: List[LeaveRequestOut] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)


class AttendanceLeaveReconciliationOut(BaseModel):
    id: int
    leave_request_id: int
    employer_id: int
    worker_id: int
    worker_name: Optional[str] = None
    request_ref: Optional[str] = None
    leave_type_code: Optional[str] = None
    subject: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    period: str
    status: str
    discrepancy_level: str
    attendance_payload: Dict[str, Any] = Field(default_factory=dict)
    leave_payload: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    resolved_by_user_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class PaginatedWorkersOut(BaseModel):
    items: List[WorkerOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedEmployersOut(BaseModel):
    items: List[EmployerOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportRequestValidated(BaseModel):
    employer_id: int
    start_period: str
    end_period: str
    columns: List[str]
    etablissement: Optional[str] = None
    departement: Optional[str] = None
    service: Optional[str] = None
    unite: Optional[str] = None
    matricule_search: Optional[str] = None
    worker_name_search: Optional[str] = None
    include_matricule: bool = False
    group_by_matricule: bool = False

    @field_validator("start_period", "end_period")
    @classmethod
    def validate_report_period_fields(cls, value: str) -> str:
        return _validate_period(value)

    @field_validator(
        "etablissement",
        "departement",
        "service",
        "unite",
        "matricule_search",
        "worker_name_search",
        mode="before",
    )
    @classmethod
    def normalize_report_optional_text_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @model_validator(mode="after")
    def validate_report_period_order(self):
        if self.end_period < self.start_period:
            raise ValueError("end_period cannot be before start_period")
        return self


ReportRequest = ReportRequestValidated


class RecruitmentJobPostingBase(BaseModel):
    employer_id: int
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    contract_type: str = "CDI"
    status: str = "draft"
    salary_range: Optional[str] = None
    description: Optional[str] = None
    skills_required: Optional[str] = None
    publish_channels: List[str] = Field(default_factory=list)
    publish_status: str = "draft"
    publish_logs: List[Dict[str, Any]] = Field(default_factory=list)


class RecruitmentJobPostingCreate(RecruitmentJobPostingBase):
    pass


class RecruitmentJobPostingUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    status: Optional[str] = None
    salary_range: Optional[str] = None
    description: Optional[str] = None
    skills_required: Optional[str] = None
    publish_channels: Optional[List[str]] = None
    publish_status: Optional[str] = None
    publish_logs: Optional[List[Dict[str, Any]]] = None


class RecruitmentJobPostingOut(RecruitmentJobPostingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentCandidateBase(BaseModel):
    employer_id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    education_level: Optional[str] = None
    experience_years: float = 0.0
    source: Optional[str] = None
    status: str = "new"
    summary: Optional[str] = None
    cv_file_path: Optional[str] = None


class RecruitmentCandidateCreate(RecruitmentCandidateBase):
    pass


class RecruitmentCandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education_level: Optional[str] = None
    experience_years: Optional[float] = None
    source: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    cv_file_path: Optional[str] = None


class RecruitmentCandidateOut(RecruitmentCandidateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentApplicationBase(BaseModel):
    job_posting_id: int
    candidate_id: int
    stage: str = "applied"
    score: Optional[float] = None
    notes: Optional[str] = None


class RecruitmentApplicationCreate(RecruitmentApplicationBase):
    pass


class RecruitmentApplicationUpdate(BaseModel):
    stage: Optional[str] = None
    score: Optional[float] = None
    notes: Optional[str] = None


class RecruitmentApplicationOut(RecruitmentApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentLibraryItemBase(BaseModel):
    employer_id: Optional[int] = None
    category: str
    label: str
    description: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class RecruitmentLibraryItemCreate(RecruitmentLibraryItemBase):
    pass


class RecruitmentLibraryItemUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class RecruitmentLibraryItemOut(RecruitmentLibraryItemBase):
    id: int
    normalized_key: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentJobAssistantRequest(BaseModel):
    employer_id: Optional[int] = None
    title: str = ""
    department: str = ""
    description: str = ""
    contract_type: str = ""
    sector: str = ""
    mode: str = "generate"
    version: str = "long"
    focus_block: Optional[str] = None


class RecruitmentContractTypeSuggestionOut(BaseModel):
    code: str
    label: str
    description: str
    recommended: bool = False


class RecruitmentJobAssistantOut(BaseModel):
    probable_title: str
    probable_department: str
    detected_job_family: str = "autre"
    generated_context: str = ""
    mission_summary: str
    main_activities: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    behavioral_skills: List[str] = Field(default_factory=list)
    education_level: str = ""
    experience_required: str = ""
    languages: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    interview_criteria: List[str] = Field(default_factory=list)
    suggestion_sources: List[str] = Field(default_factory=list)
    classification: str = ""
    contract_type_suggestions: List[RecruitmentContractTypeSuggestionOut] = Field(default_factory=list)


class RecruitmentJobProfileBase(BaseModel):
    manager_title: Optional[str] = None
    mission_summary: Optional[str] = None
    main_activities: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    behavioral_skills: List[str] = Field(default_factory=list)
    education_level: Optional[str] = None
    experience_required: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    working_hours: Optional[str] = None
    working_days: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    desired_start_date: Optional[date] = None
    application_deadline: Optional[date] = None
    publication_channels: List[str] = Field(default_factory=list)
    classification: Optional[str] = None
    workflow_status: str = "draft"
    validation_comment: Optional[str] = None
    assistant_source: Dict[str, Any] = Field(default_factory=dict)
    interview_criteria: List[str] = Field(default_factory=list)
    announcement_title: Optional[str] = None
    announcement_body: Optional[str] = None
    announcement_status: str = "draft"
    announcement_share_pack: Dict[str, Any] = Field(default_factory=dict)
    submission_attachments: List[Dict[str, Any]] = Field(default_factory=list)
    workforce_job_profile_id: Optional[int] = None
    contract_guidance: Dict[str, Any] = Field(default_factory=dict)
    publication_mode: Optional[str] = None
    publication_url: Optional[str] = None
    submitted_to_inspection_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None


class RecruitmentJobProfileUpsert(RecruitmentJobProfileBase):
    pass


class RecruitmentJobProfileOut(RecruitmentJobProfileBase):
    id: int
    job_posting_id: int
    announcement_slug: Optional[str] = None
    validated_by_user_id: Optional[int] = None
    validated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentValidationIn(BaseModel):
    approved: bool
    comment: Optional[str] = None


class RecruitmentInspectorDecisionIn(BaseModel):
    action: str
    comment: Optional[str] = None
    publication_mode: Optional[str] = None
    publication_url: Optional[str] = None


class RecruitmentAnnouncementOut(BaseModel):
    title: str
    slug: str
    public_url: str
    web_body: str
    email_subject: str
    email_body: str
    facebook_text: str
    linkedin_text: str
    whatsapp_text: str
    copy_text: str


class RecruitmentPublicationChannelConfigUpdate(BaseModel):
    access_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    organization_id: Optional[str] = None
    sender_email: Optional[str] = None
    audience_emails: List[str] = Field(default_factory=list)
    webhook_url: Optional[str] = None
    publish_url: Optional[str] = None
    endpoint_path: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecruitmentPublicationChannelBase(BaseModel):
    company_id: int
    channel_type: str
    is_active: bool = False
    default_publish: bool = False


class RecruitmentPublicationChannelUpsert(RecruitmentPublicationChannelBase):
    config: RecruitmentPublicationChannelConfigUpdate = Field(default_factory=RecruitmentPublicationChannelConfigUpdate)


class RecruitmentPublicationChannelOut(RecruitmentPublicationChannelBase):
    id: int
    config: Dict[str, Any] = Field(default_factory=dict)
    secret_fields_configured: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecruitmentPublicationLogOut(BaseModel):
    id: int
    job_id: int
    channel: str
    status: str
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    triggered_by_user_id: Optional[int] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class RecruitmentPublishRequest(BaseModel):
    channels: List[str] = Field(default_factory=list)


class RecruitmentPublishRetryRequest(BaseModel):
    channel: str


class RecruitmentPublishResultOut(BaseModel):
    job: RecruitmentJobPostingOut
    profile: RecruitmentJobProfileOut
    channel_results: List[RecruitmentPublicationLogOut] = Field(default_factory=list)


class RecruitmentContractGuidanceOut(BaseModel):
    suggested_primary_type: str
    available_types: List[str] = Field(default_factory=list)
    language_options: List[str] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    suggested_defaults: Dict[str, Any] = Field(default_factory=dict)


class RecruitmentCandidateAssetOut(BaseModel):
    id: int
    candidate_id: int
    resume_original_name: Optional[str] = None
    resume_storage_path: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    raw_extract_text: Optional[str] = None
    parsed_profile: Dict[str, Any] = Field(default_factory=dict)
    parsing_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentCandidateUploadOut(BaseModel):
    candidate: RecruitmentCandidateOut
    asset: RecruitmentCandidateAssetOut
    application_id: Optional[int] = None


class RecruitmentInterviewBase(BaseModel):
    round_number: int = 1
    round_label: str = "Tour 1"
    interview_type: str = "entretien"
    scheduled_at: Optional[datetime] = None
    interviewer_user_id: Optional[int] = None
    interviewer_name: Optional[str] = None
    status: str = "scheduled"
    score_total: Optional[float] = None
    scorecard: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    recommendation: Optional[str] = None


class RecruitmentInterviewCreate(RecruitmentInterviewBase):
    pass


class RecruitmentInterviewUpdate(BaseModel):
    round_number: Optional[int] = None
    round_label: Optional[str] = None
    interview_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    interviewer_user_id: Optional[int] = None
    interviewer_name: Optional[str] = None
    status: Optional[str] = None
    score_total: Optional[float] = None
    scorecard: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    recommendation: Optional[str] = None


class RecruitmentInterviewOut(RecruitmentInterviewBase):
    id: int
    application_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentDecisionIn(BaseModel):
    shortlist_rank: Optional[int] = None
    decision_status: str = "pending"
    decision_comment: Optional[str] = None


class RecruitmentDecisionOut(RecruitmentDecisionIn):
    id: int
    application_id: int
    decided_by_user_id: Optional[int] = None
    decided_at: Optional[datetime] = None
    converted_worker_id: Optional[int] = None
    contract_draft_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentActivityOut(BaseModel):
    id: int
    employer_id: int
    job_posting_id: Optional[int] = None
    candidate_id: Optional[int] = None
    application_id: Optional[int] = None
    interview_id: Optional[int] = None
    actor_user_id: Optional[int] = None
    event_type: str
    visibility: str
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecruitmentConversionOut(BaseModel):
    worker_id: int
    contract_draft_id: Optional[int] = None
    decision_id: int


class ContractVersionCreate(BaseModel):
    contract_id: int
    status: str = "generated"
    source_module: str = "contracts"
    effective_date: Optional[date] = None
    salary_amount: Optional[float] = None
    classification_index: Optional[str] = None


class ContractVersionOut(BaseModel):
    id: int
    contract_id: int
    worker_id: int
    employer_id: int
    version_number: int
    source_module: str
    status: str
    effective_date: Optional[date] = None
    salary_amount: Optional[float] = None
    classification_index: Optional[str] = None
    snapshot_json: str
    created_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ComplianceReviewCreate(BaseModel):
    contract_id: Optional[int] = None
    contract_version_id: Optional[int] = None
    worker_id: Optional[int] = None
    employer_id: int
    review_type: str = "contract_control"
    review_stage: str = "pre_signature"
    status: str = "draft"
    due_at: Optional[datetime] = None
    requested_documents: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class ComplianceReviewStatusUpdate(BaseModel):
    status: str
    review_stage: Optional[str] = None
    note: Optional[str] = None


class ComplianceReviewOut(BaseModel):
    id: int
    employer_id: int
    worker_id: Optional[int] = None
    contract_id: Optional[int] = None
    contract_version_id: Optional[int] = None
    review_type: str
    review_stage: str
    status: str
    source_module: str
    checklist: List[Dict[str, Any]] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    requested_documents: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    due_at: Optional[datetime] = None
    submitted_to_inspector_at: Optional[datetime] = None
    reviewed_by_user_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class InspectorObservationCreate(BaseModel):
    visibility: str = "restricted"
    observation_type: str = "general"
    status_marker: str = "observation"
    message: str
    structured_payload: Dict[str, Any] = Field(default_factory=dict)


class InspectorObservationOut(BaseModel):
    id: int
    review_id: int
    employer_id: int
    author_user_id: Optional[int] = None
    visibility: str
    observation_type: str
    status_marker: str
    message: str
    structured_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ComplianceVisitCreate(BaseModel):
    employer_id: int
    review_id: Optional[int] = None
    visit_type: str = "inspection"
    status: str = "scheduled"
    inspector_name: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class ComplianceVisitOut(BaseModel):
    id: int
    employer_id: int
    review_id: Optional[int] = None
    visit_type: str
    status: str
    inspector_name: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    occurred_at: Optional[datetime] = None
    notes: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EmployerRegisterEntryOut(BaseModel):
    id: int
    employer_id: int
    worker_id: Optional[int] = None
    contract_id: Optional[int] = None
    contract_version_id: Optional[int] = None
    entry_type: str
    registry_label: str
    status: str
    effective_date: Optional[date] = None
    archived_at: Optional[datetime] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class IntegrityIssueOut(BaseModel):
    severity: str
    issue_type: str
    entity_type: str
    entity_id: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class EmployeeFlowOut(BaseModel):
    worker: Dict[str, Any]
    candidate: Dict[str, Any] = Field(default_factory=dict)
    job_posting: Dict[str, Any] = Field(default_factory=dict)
    job_profile: Dict[str, Any] = Field(default_factory=dict)
    workforce_job_profile: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)
    contract: Dict[str, Any] = Field(default_factory=dict)
    contract_versions: List[Dict[str, Any]] = Field(default_factory=list)
    declarations: List[Dict[str, Any]] = Field(default_factory=list)
    integrity_issues: List[IntegrityIssueOut] = Field(default_factory=list)


class MasterDataSectionOut(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)
    canonical_hash: Optional[str] = None
    source_status: Optional[str] = None
    updated_at: Optional[datetime] = None


class MasterDataWorkerViewOut(BaseModel):
    worker: Dict[str, Any] = Field(default_factory=dict)
    identity: MasterDataSectionOut
    employment: MasterDataSectionOut
    compensation: MasterDataSectionOut
    organization: MasterDataSectionOut
    recruitment: Dict[str, Any] = Field(default_factory=dict)
    contract: Dict[str, Any] = Field(default_factory=dict)
    contract_versions: List[Dict[str, Any]] = Field(default_factory=list)
    declarations: List[Dict[str, Any]] = Field(default_factory=list)
    integrity_issues: List[IntegrityIssueOut] = Field(default_factory=list)


class HrDossierDocumentVersionOut(BaseModel):
    id: str
    version_number: int
    original_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
    created_by_user_id: Optional[int] = None


class HrDossierDocumentOut(BaseModel):
    id: str
    title: str
    section_code: str
    document_type: str
    status: str
    source_module: str
    source_record_type: Optional[str] = None
    source_record_id: Optional[int] = None
    document_date: Optional[str] = None
    expiration_date: Optional[str] = None
    is_expired: bool = False
    comment: Optional[str] = None
    visibility_scope: str = "hr_only"
    can_preview: bool = False
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    current_version_number: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)
    versions: List[HrDossierDocumentVersionOut] = Field(default_factory=list)


class HrDossierTimelineEventOut(BaseModel):
    id: str
    section_code: str
    event_type: str
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    event_date: Optional[str] = None
    source_module: Optional[str] = None
    source_record_type: Optional[str] = None
    source_record_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class HrDossierAlertOut(BaseModel):
    code: str
    severity: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class HrDossierCompletenessOut(BaseModel):
    score: int = 0
    completed_items: int = 0
    total_items: int = 0
    missing_items: List[str] = Field(default_factory=list)


class HrDossierSectionOut(BaseModel):
    key: str
    title: str
    source: str
    data: Dict[str, Any] = Field(default_factory=dict)


class HrDossierViewOut(BaseModel):
    worker: Dict[str, Any] = Field(default_factory=dict)
    access_scope: str
    summary: Dict[str, Any] = Field(default_factory=dict)
    completeness: HrDossierCompletenessOut
    alerts: List[HrDossierAlertOut] = Field(default_factory=list)
    sections: Dict[str, HrDossierSectionOut] = Field(default_factory=dict)
    documents: List[HrDossierDocumentOut] = Field(default_factory=list)
    timeline: List[HrDossierTimelineEventOut] = Field(default_factory=list)


class HrDossierSectionUpdateIn(BaseModel):
    section_key: str
    data: Dict[str, Any] = Field(default_factory=dict)


class HrDossierDocumentUploadMetaIn(BaseModel):
    title: Optional[str] = None
    section_code: str = "documents"
    document_type: str = "other"
    document_date: Optional[date] = None
    expiration_date: Optional[date] = None
    comment: Optional[str] = None
    visibility_scope: str = "hr_only"
    visible_to_employee: bool = False
    visible_to_manager: bool = False
    visible_to_payroll: bool = False


class HrDossierReportRowOut(BaseModel):
    worker_id: int
    employer_id: int
    matricule: Optional[str] = None
    full_name: str
    completeness_score: int
    missing_contract_document: bool = False
    missing_medical_visit: bool = False
    missing_cnaps_number: bool = False
    expired_document_count: int = 0
    missing_items: List[str] = Field(default_factory=list)


class HrDossierReportOut(BaseModel):
    employer_id: int
    total_workers: int
    incomplete_workers: int
    missing_contract_document_workers: int
    missing_medical_visit_workers: int
    missing_cnaps_number_workers: int
    workers_with_expired_documents: int
    rows: List[HrDossierReportRowOut] = Field(default_factory=list)


class ComplianceDashboardOut(BaseModel):
    review_counts: Dict[str, int] = Field(default_factory=dict)
    contract_queue: List[Dict[str, Any]] = Field(default_factory=list)
    integrity_issues: List[IntegrityIssueOut] = Field(default_factory=list)
    pending_declarations: List[Dict[str, Any]] = Field(default_factory=list)
    upcoming_visits: List[ComplianceVisitOut] = Field(default_factory=list)


class ExportTemplateOut(BaseModel):
    id: int
    code: str
    type_document: str
    version: str
    format: str
    mapping: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StatutoryExportPreviewRequest(BaseModel):
    employer_id: int
    template_code: str
    start_period: str
    end_period: str

    @field_validator("start_period", "end_period")
    @classmethod
    def validate_period_fields(cls, value: str) -> str:
        return _validate_period(value)

    @model_validator(mode="after")
    def validate_period_order(self):
        if self.end_period < self.start_period:
            raise ValueError("end_period cannot be before start_period")
        return self


class StatutoryExportPreviewOut(BaseModel):
    template_code: str
    document_type: str
    format: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    issues: List[IntegrityIssueOut] = Field(default_factory=list)


class ExportJobOut(BaseModel):
    id: int
    employer_id: int
    template_id: Optional[int] = None
    snapshot_id: Optional[int] = None
    requested_by_user_id: Optional[int] = None
    document_type: str
    start_period: str
    end_period: str
    status: str
    file_path: Optional[str] = None
    checksum: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class StatutoryDeclarationOut(BaseModel):
    id: int
    employer_id: int
    export_job_id: Optional[int] = None
    channel: str
    period_label: str
    status: str
    reference_number: Optional[str] = None
    receipt_path: Optional[str] = None
    totals: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeclarationSubmissionOut(BaseModel):
    declaration: StatutoryDeclarationOut
    download_url: Optional[str] = None


class TalentSkillBase(BaseModel):
    employer_id: int
    code: str
    name: str
    description: Optional[str] = None
    scale_max: int = 5
    is_active: bool = True


class TalentSkillCreate(TalentSkillBase):
    pass


class TalentSkillUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    scale_max: Optional[int] = None
    is_active: Optional[bool] = None


class TalentSkillOut(TalentSkillBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TalentEmployeeSkillBase(BaseModel):
    worker_id: int
    skill_id: int
    level: int = 1
    source: str = "manager"


class TalentEmployeeSkillCreate(TalentEmployeeSkillBase):
    pass


class TalentEmployeeSkillUpdate(BaseModel):
    level: Optional[int] = None
    source: Optional[str] = None


class TalentEmployeeSkillOut(TalentEmployeeSkillBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TalentTrainingBase(BaseModel):
    employer_id: int
    title: str
    provider: Optional[str] = None
    duration_hours: float = 0.0
    mode: Optional[str] = None
    price: float = 0.0
    objectives: Optional[str] = None
    status: str = "draft"


class TalentTrainingCreate(TalentTrainingBase):
    pass


class TalentTrainingUpdate(BaseModel):
    title: Optional[str] = None
    provider: Optional[str] = None
    duration_hours: Optional[float] = None
    mode: Optional[str] = None
    price: Optional[float] = None
    objectives: Optional[str] = None
    status: Optional[str] = None


class TalentTrainingOut(TalentTrainingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TalentTrainingSessionBase(BaseModel):
    training_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    site: Optional[str] = None
    trainer: Optional[str] = None
    capacity: Optional[int] = None
    status: str = "planned"


class TalentTrainingSessionCreate(TalentTrainingSessionBase):
    pass


class TalentTrainingSessionUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    site: Optional[str] = None
    trainer: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None


class TalentTrainingSessionOut(TalentTrainingSessionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SstIncidentBase(BaseModel):
    employer_id: int
    worker_id: Optional[int] = None
    incident_type: str
    severity: str = "medium"
    status: str = "open"
    occurred_at: datetime
    location: Optional[str] = None
    description: str
    action_taken: Optional[str] = None
    witnesses: Optional[str] = None


class SstIncidentCreate(SstIncidentBase):
    pass


class SstIncidentUpdate(BaseModel):
    worker_id: Optional[int] = None
    incident_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    occurred_at: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    action_taken: Optional[str] = None
    witnesses: Optional[str] = None


class SstIncidentOut(SstIncidentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EmployeePortalRequestBase(BaseModel):
    employer_id: int
    worker_id: Optional[int] = None
    request_type: str
    destination: str = "rh"
    title: str
    description: str
    priority: str = "normal"
    confidentiality: str = "standard"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class EmployeePortalRequestCreate(EmployeePortalRequestBase):
    pass


class EmployeePortalRequestStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class EmployeePortalRequestOut(EmployeePortalRequestBase):
    id: int
    status: str
    case_number: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    created_by_user_id: Optional[int] = None
    assigned_to_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InspectorCaseBase(BaseModel):
    employer_id: int
    worker_id: Optional[int] = None
    contract_id: Optional[int] = None
    portal_request_id: Optional[int] = None
    case_type: str = "general_claim"
    sub_type: Optional[str] = None
    source_party: str = "employee"
    subject: str
    description: str
    category: Optional[str] = None
    district: Optional[str] = None
    urgency: str = "normal"
    confidentiality: str = "standard"
    amicable_attempt_status: str = "not_started"
    current_stage: str = "filing"
    outcome_summary: Optional[str] = None
    resolution_type: Optional[str] = None
    due_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    is_sensitive: bool = False
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class InspectorCaseCreate(InspectorCaseBase):
    pass


class InspectorCaseStatusUpdate(BaseModel):
    status: str
    current_stage: Optional[str] = None
    note: Optional[str] = None
    outcome_summary: Optional[str] = None
    resolution_type: Optional[str] = None


class InspectorCaseOut(InspectorCaseBase):
    id: int
    case_number: str
    status: str
    receipt_reference: Optional[str] = None
    assigned_inspector_user_id: Optional[int] = None
    filed_by_user_id: Optional[int] = None
    last_response_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InspectorMessageCreate(BaseModel):
    sender_role: str = "employee"
    direction: str = "employee_to_inspector"
    message_type: str = "message"
    visibility: str = "case_parties"
    body: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class InspectorMessageOut(BaseModel):
    id: int
    case_id: int
    employer_id: int
    author_user_id: Optional[int] = None
    sender_role: str
    direction: str
    message_type: str
    visibility: str
    body: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InspectorCaseAssignmentCreate(BaseModel):
    inspector_user_id: int
    scope: str = "lead"
    notes: Optional[str] = None


class InspectorCaseAssignmentUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class InspectorCaseAssignmentOut(BaseModel):
    id: int
    case_id: int
    inspector_user_id: int
    assigned_by_user_id: Optional[int] = None
    scope: str
    status: str
    notes: Optional[str] = None
    assigned_at: datetime
    revoked_at: Optional[datetime] = None
    inspector: Optional[AppUserLightOut] = None

    model_config = ConfigDict(from_attributes=True)

class InspectionDocumentVersionOut(BaseModel):
    id: int
    document_id: int
    case_id: int
    employer_id: int
    version_number: int
    file_name: str
    original_name: str
    storage_path: str
    download_url: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    notes: Optional[str] = None
    uploaded_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InspectionDocumentOut(BaseModel):
    id: int
    case_id: int
    employer_id: int
    uploaded_by_user_id: Optional[int] = None
    document_type: str
    title: str
    description: Optional[str] = None
    visibility: str
    confidentiality: str
    status: str
    current_version_number: int
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    versions: List[InspectionDocumentVersionOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class InspectionDocumentAccessLogOut(BaseModel):
    id: int
    document_id: int
    version_id: Optional[int] = None
    case_id: int
    user_id: Optional[int] = None
    action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabourCaseClaimCreate(BaseModel):
    claim_type: str
    claimant_party: str = "employee"
    factual_basis: str
    amount_requested: Optional[float] = None
    status: str = "submitted"
    conciliation_outcome: Optional[str] = None
    inspector_observations: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LabourCaseClaimOut(LabourCaseClaimCreate):
    id: int
    case_id: int
    employer_id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabourCaseEventCreate(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None
    status: str = "planned"
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    participants: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LabourCaseEventOut(LabourCaseEventCreate):
    id: int
    case_id: int
    employer_id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabourPVCreate(BaseModel):
    pv_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    status: str = "draft"
    measures_to_execute: Optional[str] = None
    execution_deadline: Optional[datetime] = None
    delivered_to_parties_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LabourPVOut(BaseModel):
    id: int
    case_id: int
    employer_id: int
    generated_by_user_id: Optional[int] = None
    pv_number: str
    pv_type: str
    title: str
    content: str
    status: str
    version_number: int
    measures_to_execute: Optional[str] = None
    execution_deadline: Optional[datetime] = None
    delivered_to_parties_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabourChatbotRequest(BaseModel):
    role_context: str = "inspecteur"
    intent: str = "general"
    prompt: str
    include_case_summary: bool = True


class LabourChatbotOut(BaseModel):
    id: int
    case_id: Optional[int] = None
    employer_id: Optional[int] = None
    role_context: str
    intent: str
    response: Dict[str, Any] = Field(default_factory=dict)
    fallback_used: bool = True
    created_at: datetime


class LabourCaseWorkspaceOut(BaseModel):
    case: InspectorCaseOut
    claims: List[LabourCaseClaimOut] = Field(default_factory=list)
    events: List[LabourCaseEventOut] = Field(default_factory=list)
    pv_records: List[LabourPVOut] = Field(default_factory=list)
    messages: List[InspectorMessageOut] = Field(default_factory=list)
    documents: List[InspectionDocumentOut] = Field(default_factory=list)
    document_access_logs: List[InspectionDocumentAccessLogOut] = Field(default_factory=list)
    related: Dict[str, Any] = Field(default_factory=dict)
    help_topics: List[Dict[str, Any]] = Field(default_factory=list)
    legal_summary: LabourCaseLegalSummaryOut = Field(default_factory=LabourCaseLegalSummaryOut)

class EmployeePortalDashboardOut(BaseModel):
    worker: Dict[str, Any] = Field(default_factory=dict)
    requests: List[EmployeePortalRequestOut] = Field(default_factory=list)
    inspector_cases: List[InspectorCaseOut] = Field(default_factory=list)
    contracts: List[Dict[str, Any]] = Field(default_factory=list)
    performance_reviews: List[Dict[str, Any]] = Field(default_factory=list)
    training_plan_items: List[Dict[str, Any]] = Field(default_factory=list)
    notifications: List[Dict[str, Any]] = Field(default_factory=list)


class InternalMessageChannelCreate(BaseModel):
    employer_id: int
    title: str
    description: Optional[str] = None
    channel_type: str = "group"
    visibility: str = "internal"
    ack_required: bool = False
    member_user_ids: List[int] = Field(default_factory=list)


class InternalMessageChannelMemberCreate(BaseModel):
    user_id: int
    member_role: str = "member"


class InternalMessageChannelMemberOut(BaseModel):
    id: int
    channel_id: int
    user_id: int
    member_role: str
    is_active: bool
    last_read_at: Optional[datetime] = None
    joined_at: datetime
    user: Optional[AppUserLightOut] = None

    model_config = ConfigDict(from_attributes=True)

class InternalMessageCreate(BaseModel):
    message_type: str = "message"
    body: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class InternalMessageOut(BaseModel):
    id: int
    channel_id: int
    employer_id: int
    author_user_id: Optional[int] = None
    message_type: str
    body: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    status: str
    created_at: datetime
    updated_at: datetime
    author: Optional[AppUserLightOut] = None
    receipt_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class InternalMessageChannelOut(BaseModel):
    id: int
    channel_code: str
    employer_id: int
    created_by_user_id: Optional[int] = None
    channel_type: str
    title: str
    description: Optional[str] = None
    visibility: str
    ack_required: bool
    status: str
    member_count: int = 0
    unread_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InternalNoticeCreate(BaseModel):
    employer_id: int
    title: str
    body: str
    notice_type: str = "service_note"
    audience_role: Optional[str] = None
    ack_required: bool = False
    expires_at: Optional[datetime] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class InternalNoticeOut(BaseModel):
    id: int
    employer_id: int
    created_by_user_id: Optional[int] = None
    title: str
    body: str
    notice_type: str
    audience_role: Optional[str] = None
    status: str
    ack_required: bool
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    acknowledged_by_current_user: bool = False

    model_config = ConfigDict(from_attributes=True)

class InternalMessagesDashboardOut(BaseModel):
    online_users: int = 0
    active_channels: int = 0
    unread_messages: int = 0
    pending_acknowledgements: int = 0
    notices: List[InternalNoticeOut] = Field(default_factory=list)
    channels: List[InternalMessageChannelOut] = Field(default_factory=list)


class LabourInspectorAssignmentCreate(BaseModel):
    employer_id: int
    inspector_user_id: int
    assignment_scope: str = "portfolio"
    circonscription: Optional[str] = None
    sector_filter: Optional[str] = None
    notes: Optional[str] = None


class LabourInspectorAssignmentOut(BaseModel):
    id: int
    employer_id: int
    inspector_user_id: int
    assigned_by_user_id: Optional[int] = None
    assignment_scope: str
    circonscription: Optional[str] = None
    sector_filter: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    inspector: Optional[AppUserLightOut] = None

    model_config = ConfigDict(from_attributes=True)


class LabourFormalMessageRecipientIn(BaseModel):
    employer_id: Optional[int] = None
    user_id: Optional[int] = None
    recipient_type: str = "employer"

    @model_validator(mode="after")
    def validate_target(self):
        if self.employer_id is None and self.user_id is None:
            raise ValueError("A recipient employer_id or user_id is required")
        return self


class LabourFormalMessageCreate(BaseModel):
    subject: str
    body: str
    message_scope: str = "individual"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    recipients: List[LabourFormalMessageRecipientIn] = Field(default_factory=list)
    send_now: bool = False

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("subject is required")
        return normalized

    @model_validator(mode="after")
    def validate_recipients(self):
        if not self.recipients:
            raise ValueError("At least one recipient is required")
        return self


class LabourFormalMessageRecipientOut(BaseModel):
    id: int
    employer_id: Optional[int] = None
    user_id: Optional[int] = None
    recipient_type: str
    status: str
    read_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabourFormalMessageOut(BaseModel):
    id: int
    reference_number: str
    thread_key: Optional[str] = None
    sender_user_id: Optional[int] = None
    sender_employer_id: Optional[int] = None
    sender_role: Optional[str] = None
    subject: str
    body: str
    message_scope: str
    status: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    recipients: List[LabourFormalMessageRecipientOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InspectorEmployerSummaryOut(BaseModel):
    id: int
    raison_sociale: str
    nif: Optional[str] = None
    stat: Optional[str] = None
    rccm: Optional[str] = None
    adresse: Optional[str] = None
    secteur: Optional[str] = None
    contact_rh: Optional[str] = None
    company_size: int = 0
    open_cases: int = 0
    pending_job_offers: int = 0
    pending_reviews: int = 0
    unread_messages: int = 0
    latest_activity_at: Optional[datetime] = None


class InspectorEmployerDetailOut(BaseModel):
    employer: Dict[str, Any] = Field(default_factory=dict)
    compliance_status: Dict[str, Any] = Field(default_factory=dict)
    contacts: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[InspectionDocumentOut] = Field(default_factory=list)
    cases: List[InspectorCaseOut] = Field(default_factory=list)
    job_offers: List[Dict[str, Any]] = Field(default_factory=list)
    formal_messages: List[LabourFormalMessageOut] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class InspectorDashboardOut(BaseModel):
    scope: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, int] = Field(default_factory=dict)
    recent_companies: List[InspectorEmployerSummaryOut] = Field(default_factory=list)
    recent_cases: List[InspectorCaseOut] = Field(default_factory=list)
    recent_messages: List[LabourFormalMessageOut] = Field(default_factory=list)
    pending_job_offers: List[Dict[str, Any]] = Field(default_factory=list)
    pending_documents: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)


class WorkforceJobProfileBase(BaseModel):
    employer_id: int
    title: str
    department: Optional[str] = None
    category_prof: Optional[str] = None
    classification_index: Optional[str] = None
    criticality: str = "medium"
    target_headcount: Optional[int] = None
    required_skills: List[Dict[str, Any]] = Field(default_factory=list)
    mobility_paths: List[str] = Field(default_factory=list)
    succession_candidates: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class WorkforceJobProfileCreate(WorkforceJobProfileBase):
    pass


class WorkforceJobProfileUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    category_prof: Optional[str] = None
    classification_index: Optional[str] = None
    criticality: Optional[str] = None
    target_headcount: Optional[int] = None
    required_skills: Optional[List[Dict[str, Any]]] = None
    mobility_paths: Optional[List[str]] = None
    succession_candidates: Optional[List[str]] = None
    notes: Optional[str] = None


class WorkforceJobProfileOut(WorkforceJobProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PerformanceCycleBase(BaseModel):
    employer_id: int
    name: str
    cycle_type: str = "annual"
    start_date: date
    end_date: date
    status: str = "draft"
    objectives: List[Dict[str, Any]] = Field(default_factory=list)


class PerformanceCycleCreate(PerformanceCycleBase):
    pass


class PerformanceCycleOut(PerformanceCycleBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PerformanceReviewBase(BaseModel):
    cycle_id: int
    employer_id: int
    worker_id: int
    status: str = "draft"
    overall_score: Optional[float] = None
    self_assessment: Optional[str] = None
    manager_comment: Optional[str] = None
    hr_comment: Optional[str] = None
    objectives: List[Dict[str, Any]] = Field(default_factory=list)
    competencies: List[Dict[str, Any]] = Field(default_factory=list)
    development_actions: List[Dict[str, Any]] = Field(default_factory=list)
    promotion_recommendation: Optional[str] = None


class PerformanceReviewCreate(PerformanceReviewBase):
    reviewer_user_id: Optional[int] = None
    manager_user_id: Optional[int] = None


class PerformanceReviewStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class PerformanceReviewOut(PerformanceReviewBase):
    id: int
    reviewer_user_id: Optional[int] = None
    manager_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkforcePlanningBase(BaseModel):
    employer_id: int
    planning_year: int
    title: str
    job_profile_id: Optional[int] = None
    current_headcount: int = 0
    target_headcount: int = 0
    recruitment_need: int = 0
    mobility_need: int = 0
    criticality: str = "medium"
    status: str = "draft"
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None


class WorkforcePlanningCreate(WorkforcePlanningBase):
    pass


class WorkforcePlanningOut(WorkforcePlanningBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrainingNeedBase(BaseModel):
    employer_id: int
    worker_id: Optional[int] = None
    review_id: Optional[int] = None
    job_profile_id: Optional[int] = None
    source: str = "gpec"
    priority: str = "medium"
    title: str
    description: Optional[str] = None
    target_skill: Optional[str] = None
    gap_level: Optional[int] = None
    recommended_training_id: Optional[int] = None
    status: str = "identified"
    due_date: Optional[date] = None


class TrainingNeedCreate(TrainingNeedBase):
    pass


class TrainingNeedStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class TrainingNeedOut(TrainingNeedBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrainingPlanBase(BaseModel):
    employer_id: int
    name: str
    plan_year: int
    budget_amount: float = 0.0
    status: str = "draft"
    objectives: List[Dict[str, Any]] = Field(default_factory=list)
    fmfp_tracking: Dict[str, Any] = Field(default_factory=dict)


class TrainingPlanCreate(TrainingPlanBase):
    pass


class TrainingPlanOut(TrainingPlanBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrainingPlanItemBase(BaseModel):
    training_plan_id: int
    need_id: Optional[int] = None
    training_id: Optional[int] = None
    training_session_id: Optional[int] = None
    worker_id: Optional[int] = None
    status: str = "planned"
    estimated_cost: float = 0.0
    funding_source: Optional[str] = None
    fmfp_eligible: bool = False
    scheduled_start: Optional[date] = None
    scheduled_end: Optional[date] = None
    notes: Optional[str] = None


class TrainingPlanItemCreate(TrainingPlanItemBase):
    pass


class TrainingPlanItemOut(TrainingPlanItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrainingEvaluationBase(BaseModel):
    employer_id: int
    training_session_id: Optional[int] = None
    worker_id: int
    evaluation_type: str = "hot"
    score: Optional[float] = None
    impact_level: Optional[str] = None
    comments: Optional[str] = None


class TrainingEvaluationCreate(TrainingEvaluationBase):
    pass


class TrainingEvaluationOut(TrainingEvaluationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DisciplinaryCaseBase(BaseModel):
    employer_id: int
    worker_id: int
    inspection_case_id: Optional[int] = None
    case_type: str = "warning"
    severity: str = "medium"
    status: str = "draft"
    subject: str
    description: str
    happened_at: Optional[datetime] = None
    hearing_at: Optional[datetime] = None
    defense_notes: Optional[str] = None
    sanction_type: Optional[str] = None
    monetary_sanction_flag: bool = False
    documents: List[Dict[str, Any]] = Field(default_factory=list)


class DisciplinaryCaseCreate(DisciplinaryCaseBase):
    pass


class DisciplinaryCaseStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class DisciplinaryCaseOut(DisciplinaryCaseBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TerminationWorkflowBase(BaseModel):
    employer_id: int
    worker_id: int
    contract_id: Optional[int] = None
    inspection_case_id: Optional[int] = None
    termination_type: str = "resignation"
    motif: str
    status: str = "draft"
    effective_date: Optional[date] = None
    notification_sent_at: Optional[datetime] = None
    notification_received_at: Optional[datetime] = None
    pre_hearing_notice_sent_at: Optional[datetime] = None
    pre_hearing_scheduled_at: Optional[datetime] = None
    preavis_start_date: Optional[date] = None
    economic_consultation_started_at: Optional[date] = None
    economic_inspection_referral_at: Optional[date] = None
    technical_layoff_declared_at: Optional[date] = None
    technical_layoff_end_at: Optional[date] = None
    sensitive_case: bool = False
    handover_required: bool = False
    inspection_required: bool = False
    legal_risk_level: str = "normal"
    checklist: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    legal_metadata: Dict[str, Any] = Field(default_factory=dict)
    readonly_stc: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class TerminationWorkflowCreate(TerminationWorkflowBase):
    pass


class TerminationWorkflowStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class TerminationWorkflowOut(TerminationWorkflowBase):
    id: int
    created_by_user_id: Optional[int] = None
    validated_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DuerEntryBase(BaseModel):
    employer_id: int
    site_name: str
    risk_family: str
    hazard: str
    exposure_population: Optional[str] = None
    probability: int = 1
    severity: int = 1
    existing_controls: Optional[str] = None
    residual_risk: Optional[int] = None
    owner_name: Optional[str] = None
    status: str = "open"
    last_reviewed_at: Optional[date] = None


class DuerEntryCreate(DuerEntryBase):
    pass


class DuerEntryOut(DuerEntryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PreventionActionBase(BaseModel):
    employer_id: int
    duer_entry_id: Optional[int] = None
    action_title: str
    action_type: str = "pap"
    owner_name: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "planned"
    measure_details: Optional[str] = None
    inspection_follow_up: bool = False


class PreventionActionCreate(PreventionActionBase):
    pass


class PreventionActionStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class PreventionActionOut(PreventionActionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HrDashboardOut(BaseModel):
    workforce: Dict[str, Any] = Field(default_factory=dict)
    performance: Dict[str, Any] = Field(default_factory=dict)
    training: Dict[str, Any] = Field(default_factory=dict)
    discipline: Dict[str, Any] = Field(default_factory=dict)
    safety: Dict[str, Any] = Field(default_factory=dict)
    legal_status: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)


class LegalModulesStatusOut(BaseModel):
    modules_implemented: int
    procedures_created: int
    pv_generated: int
    test_cases: int
    employers: List[Dict[str, Any]] = Field(default_factory=list)
    highlights: List[Dict[str, Any]] = Field(default_factory=list)
    role_coverage: List[str] = Field(default_factory=list)


class DebugExecutionItemOut(BaseModel):
    label: str
    value: str
    at: Optional[datetime] = None


class DebugExecutionPanelOut(BaseModel):
    last_migrations_executed: List[DebugExecutionItemOut] = Field(default_factory=list)
    last_seed_executed: List[DebugExecutionItemOut] = Field(default_factory=list)
    last_errors: List[DebugExecutionItemOut] = Field(default_factory=list)
    modules_created: List[DebugExecutionItemOut] = Field(default_factory=list)


