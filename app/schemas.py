from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, date, time
import re


PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _validate_period(value: str) -> str:
    if not PERIOD_PATTERN.match(value or ""):
        raise ValueError("Period must use YYYY-MM format")
    return value


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
#  STRUCTURE ORGANISATIONNELLE HIÉRARCHIQUE EN CASCADE
# ==========================

class OrganizationalNodeCreate(BaseModel):
    """Schéma pour créer un nouveau nœud organisationnel"""
    parent_id: Optional[int] = None
    level: Literal['etablissement', 'departement', 'service', 'unite'] = Field(..., description="Niveau hiérarchique")
    name: str = Field(..., min_length=1, max_length=255, description="Nom du nœud organisationnel")
    code: Optional[str] = Field(None, max_length=50, description="Code optionnel du nœud")
    description: Optional[str] = None
    sort_order: int = Field(0, description="Ordre de tri")


class OrganizationalNodeUpdate(BaseModel):
    """Schéma pour mettre à jour un nœud organisationnel"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class OrganizationalNodeOut(BaseModel):
    """Schéma de sortie pour un nœud organisationnel"""
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

    class Config:
        from_attributes = True


class OrganizationalTreeOut(BaseModel):
    """Schéma pour l'arbre hiérarchique complet"""
    nodes: List[OrganizationalNodeOut]
    total_count: int


class CascadingOptionsOut(BaseModel):
    """Schéma pour les options de filtrage en cascade"""
    id: int
    name: str
    code: Optional[str]
    level: str
    parent_id: Optional[int]
    path: Optional[str]


class OrganizationalPathValidation(BaseModel):
    """Schéma pour valider un chemin organisationnel"""
    etablissement_id: Optional[int] = None
    departement_id: Optional[int] = None
    service_id: Optional[int] = None
    unite_id: Optional[int] = None


class OrganizationalPathValidationResult(BaseModel):
    """Résultat de validation d'un chemin organisationnel"""
    is_valid: bool
    errors: List[str] = []


class OrganizationalMoveRequest(BaseModel):
    """Schéma pour déplacer un nœud"""
    new_parent_id: Optional[int] = None


class OrganizationalTreeNode(BaseModel):
    """Nœud d'arbre hiérarchique avec enfants"""
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
    """Réponse pour les options de filtrage en cascade"""
    level: int
    parent_id: Optional[int]
    options: List[Dict[str, Any]]


class HierarchicalValidationResult(BaseModel):
    """Résultat de validation hiérarchique"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class OrganizationalMigrationAnalysis(BaseModel):
    """Résultat d'analyse de migration organisationnelle"""
    total_combinations: int
    total_workers_affected: int
    combinations: List[Dict[str, Any]]
    hierarchy_analysis: Dict[str, Any]
    migration_strategy: str
    estimated_duration: str
    risk_level: str


class OrganizationalMigrationResult(BaseModel):
    """Résultat d'exécution de migration"""
    etablissements_created: int
    departements_created: int
    services_created: int
    unites_created: int
    workers_updated: int
    conflicts: List[str] = []


# ==========================
#  STRUCTURE ORGANISATIONNELLE (ANCIEN SYSTÈME)
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

    class Config:
        from_attributes = True


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

    # Représentant avancé
    rep_date_naissance: Optional[date] = None
    rep_cin_num: Optional[str] = None
    rep_cin_date: Optional[date] = None
    rep_cin_lieu: Optional[str] = None
    rep_adresse: Optional[str] = None
    rep_fonction: Optional[str] = None

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
    plafond_smie: float = 0.0               # Plafond manuel pour le SMIE
    logo_path: Optional[str] = None         # Chemin vers le logo
    
    # Labels des Primes 1..5
    label_prime1: Optional[str] = "Prime 1"
    label_prime2: Optional[str] = "Prime 2"
    label_prime3: Optional[str] = "Prime 3"
    label_prime4: Optional[str] = "Prime 4"
    label_prime5: Optional[str] = "Prime 5"
    
    # 🔹 NOUVELLES LISTES ORGANISATIONNELLES
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

    class Config:
        from_attributes = True


class EmployerOut(EmployerIn):
    id: int
    type_regime: Optional[TypeRegimeOut] = None
    # primes removed

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
    sexe: Optional[str] = None
    situation_familiale: Optional[str] = None
    date_naissance: Optional[date] = None
    adresse: Optional[str] = None  # Changé de str à Optional[str]
    telephone: Optional[str] = None
    email: Optional[str] = None
    cin: Optional[str] = None
    cin_delivre_le: Optional[date] = None
    cin_lieu: Optional[str] = None
    cnaps_num: Optional[str] = None
    nombre_enfant: Optional[int] = 0
    date_embauche: Optional[date] = None
    type_regime_id: Optional[int] = None  # Changé de int à Optional[int]                               # "agricole" | "non_agricole"
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
    
    # Débauche / Rupture
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

    class Config:
        from_attributes = True


class WorkerOut(WorkerIn):
    id: int
    primes: List[WorkerPrimeOut] = []
    position_history: List[WorkerPositionHistoryOut] = []

    class Config:
        from_attributes = True


class WorkerListDelete(BaseModel):
    ids: List[int]


# ==========================
#  VARIABLES DE PAIE (PayVar)
# ==========================
class PayVarBase(BaseModel):
    worker_id: int
    period: str  # format "YYYY-MM"

    # === HEURES SUPPLÉMENTAIRES (totaux mois) ===
    hsni_130: float = 0.0   # HS non imposables 130%
    hsi_130: float = 0.0    # HS imposables 130%
    hsni_150: float = 0.0   # HS non imposables 150%
    hsi_150: float = 0.0    # HS imposables 150%
    hmn_30: float = 0.0     # Heures majorées nuit 30%

    # === ANCIEN CHAMP RÉSUMÉ (compatibilité) ===
    absences_non_remu: float = 0.0

    # === ABSENCES DÉTAILLÉES ===
    abs_non_remu_j: float = 0.0   # Absences non rémunérées (jours)
    abs_maladie_j: float = 0.0    # Absence maladie (jours)
    mise_a_pied_j: float = 0.0    # Mise à pied (jours)
    abs_non_remu_h: float = 0.0   # Absences non rémunérées (heures)

    # === PRIMES SIMPLES ===
    prime_fixe: float = 0.0
    prime_variable: float = 0.0

    # === PRIMES DÉTAILLÉES 1..10 ===
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
    prime_13: float = 0.0  # 13ème Mois

    # === AVANTAGES EN NATURE ===
    avantage_vehicule: float = 0.0
    avantage_logement: float = 0.0
    avantage_telephone: float = 0.0
    avantage_autres: float = 0.0

    # === ALLOCATION FAMILIALE ===
    alloc_familiale: float = 0.0

    # === AVANCES & DÉDUCTIONS ===
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
    """Données reçues depuis le front pour créer / mettre à jour les variables de paie."""
    pass


class PayVarOut(PayVarBase):
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


class PayrollRunOut(BaseModel):
    id: int
    employer_id: int
    period: str
    generated_at: Optional[date]
    employer_name: Optional[str] = None

    class Config:
        from_attributes = True


class HSJourReadHS(HSJourBaseHS):
    """
    Schéma de lecture d'une ligne hs_jours_HS.
    """

    id_HS: int
    calculation_id_HS: int

    class Config:
        from_attributes = True


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
        from_attributes = True


class AbsenceInput(BaseModel):
    worker_id: int | None = Field(
        default=None,
        description="ID du salarié (worker) concerné par ces absences"
    )
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
    ABSNR_J: float = Field(0.0, ge=0, description="Absence Non Rémunérée (jours)")
    ABSNR_H: float = Field(0.0, ge=0, description="Absence Non Rémunérée (heures)")
    ABSMP: float = Field(0.0, ge=0, description="Mise à pied (jours)")
    ABS1_J: float = Field(0.0, ge=0, description="Autre Absence 1 (jours)")
    ABS1_H: float = Field(0.0, ge=0, description="Autre Absence 1 (heures)")
    ABS2_J: float = Field(0.0, ge=0, description="Autre Absence 2 (jours)")
    ABS2_H: float = Field(0.0, ge=0, description="Autre Absence 2 (heures)")

    # === AVANCE ===
    avance: float = Field(0.0, description="Avance (Montant)")

    # === AUTRES DÉDUCTIONS (PayVar) ===
    autre_ded1: float = Field(0.0, description="Autre Déduction 1")
    autre_ded2: float = Field(0.0, description="Autre Déduction 2")
    autre_ded3: float = Field(0.0, description="Autre Déduction 3")
    autre_ded4: float = Field(0.0, description="Autre Déduction 4")

    # === AVANTAGES EN NATURE (PayVar Override) ===
    avantage_vehicule: float = Field(0.0, description="Avantage Véhicule")
    avantage_logement: float = Field(0.0, description="Avantage Logement")
    avantage_telephone: float = Field(0.0, description="Avantage Téléphone")
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
    
    # Montants calculés (en Ariary)
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
    
    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


# ==========================
#  REPORTING
# ==========================

class ReportField(BaseModel):
    id: str           # ex: "matricule", "brut"
    label: str        # Libellé lisible
    category: str     # Catégorie (Identité, Base, Gains, Retenues, Résultats, etc.)

class ReportMetadataOut(BaseModel):
    fields: List[ReportField]

class ReportRequest(BaseModel):
    employer_id: int
    start_period: str # "YYYY-MM"
    end_period: str   # "YYYY-MM"
    columns: List[str] # Liste des IDs des colonnes souhaitées
    etablissement: Optional[int] = None  # Changé de str à int
    departement: Optional[int] = None    # Changé de str à int
    service: Optional[int] = None        # Changé de str à int
    unite: Optional[int] = None          # Changé de str à int

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
#  CONTRATS PERSONNALISÉS
# ==========================

class CustomContractIn(BaseModel):
    worker_id: int
    employer_id: int
    title: str = "Contrat de Travail"
    content: str
    template_type: str = "employment_contract"
    is_default: bool = False


class CustomContractOut(CustomContractIn):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomContractUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_default: Optional[bool] = None


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

    class Config:
        from_attributes = True


class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


class UserLoginIn(BaseModel):
    username: str
    password: str


class UserSessionOut(BaseModel):
    token: str
    user_id: int
    username: str
    full_name: Optional[str] = None
    role_code: str
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None


class AppUserLightOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role_code: str
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class RoleCatalogItemOut(BaseModel):
    code: str
    label: str
    scope: str
    modules: Dict[str, List[str]]


class AppUserCreateIn(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role_code: str
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    is_active: bool = True


class AppUserUpdateIn(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    role_code: Optional[str] = None
    employer_id: Optional[int] = None
    worker_id: Optional[int] = None
    is_active: Optional[bool] = None


class AppUserOut(AppUserLightOut):
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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


class RecruitmentJobPostingOut(RecruitmentJobPostingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class RecruitmentJobAssistantRequest(BaseModel):
    employer_id: Optional[int] = None
    title: str = ""
    department: str = ""
    description: str = ""


class RecruitmentJobAssistantOut(BaseModel):
    probable_title: str
    probable_department: str
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

    class Config:
        from_attributes = True


class RecruitmentValidationIn(BaseModel):
    approved: bool
    comment: Optional[str] = None


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class InspectorCaseBase(BaseModel):
    employer_id: int
    worker_id: Optional[int] = None
    contract_id: Optional[int] = None
    portal_request_id: Optional[int] = None
    case_type: str = "general_claim"
    source_party: str = "employee"
    subject: str
    description: str
    confidentiality: str = "standard"
    amicable_attempt_status: str = "not_started"
    current_stage: str = "filing"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class InspectorCaseCreate(InspectorCaseBase):
    pass


class InspectorCaseStatusUpdate(BaseModel):
    status: str
    current_stage: Optional[str] = None
    note: Optional[str] = None


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class InspectionDocumentAccessLogOut(BaseModel):
    id: int
    document_id: int
    version_id: Optional[int] = None
    case_id: int
    user_id: Optional[int] = None
    action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class InternalMessagesDashboardOut(BaseModel):
    online_users: int = 0
    active_channels: int = 0
    unread_messages: int = 0
    pending_acknowledgements: int = 0
    notices: List[InternalNoticeOut] = Field(default_factory=list)
    channels: List[InternalMessageChannelOut] = Field(default_factory=list)


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


class WorkforceJobProfileOut(WorkforceJobProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class TerminationWorkflowBase(BaseModel):
    employer_id: int
    worker_id: int
    contract_id: Optional[int] = None
    inspection_case_id: Optional[int] = None
    termination_type: str = "resignation"
    motif: str
    status: str = "draft"
    effective_date: Optional[date] = None
    sensitive_case: bool = False
    inspection_required: bool = False
    checklist: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class HrDashboardOut(BaseModel):
    workforce: Dict[str, Any] = Field(default_factory=dict)
    performance: Dict[str, Any] = Field(default_factory=dict)
    training: Dict[str, Any] = Field(default_factory=dict)
    discipline: Dict[str, Any] = Field(default_factory=dict)
    safety: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
