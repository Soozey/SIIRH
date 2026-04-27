from sqlalchemy import Column, Integer, String, Text, Time, Float, Date, DateTime, Boolean, ForeignKey, func, Index, CheckConstraint
from sqlalchemy.orm import relationship
from .config.config import Base
from datetime import datetime, date, time, timezone
from typing import List, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    ForeignKey,
    Boolean,
    UniqueConstraint,
    Numeric,  # Pour les champs décimaux précis
    Text,  # Pour les textes longs
    CheckConstraint,  # Pour les contraintes de validation
)



def utcnow():
    """UTC timestamp compatible with Python 3.12+ deprecation of timezone.utcnow."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TypeRegime(Base):
    __tablename__ = "type_regimes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)   # "agricole" | "non_agricole"
    label = Column(String, nullable=False)               # ex: "Régime Agricole"
    vhm = Column(Float, nullable=False)                  # Valeur Horaire Mensuelle moyenne

    # Employeurs ayant ce régime
    employers = relationship("Employer", back_populates="type_regime")


class Employer(Base):
    __tablename__ = "employers"

    id = Column(Integer, primary_key=True, index=True)
    raison_sociale = Column(String, nullable=False)
    adresse = Column(String)
    pays = Column(String)
    telephone = Column(String)
    email = Column(String)
    activite = Column(String)
    representant = Column(String)
    rep_date_naissance = Column(Date)
    rep_cin_num = Column(String)
    rep_cin_date = Column(Date)
    rep_cin_lieu = Column(String)
    rep_adresse = Column(String)
    rep_fonction = Column(String)
    nif = Column(String)
    stat = Column(String)
    lieu_fiscal = Column(String)
    cnaps_num = Column(String)
    sm_embauche = Column(Float)
    type_etab = Column(String, default="general")   # general | scolaire
    taux_pat_cnaps = Column(Float, default=13.0)    # 13% general / 8% scolaire
    taux_pat_smie = Column(Float, default=0.0)
    taux_sal_cnaps = Column(Float, default=1.0)     # part salarié CNaPS (%)

    # 🔹 Paramètres employeur supplémentaires
    rcs = Column(String)
    ostie_num = Column(String)
    smie_num = Column(String)
    ville = Column(String)
    contact_rh = Column(String)
    logo_path = Column(String)  # Chemin vers le logo
    plafond_cnaps_base = Column(Float, default=0.0)
    taux_pat_fmfp = Column(Float, default=1.0)
    taux_sal_smie = Column(Float, default=0.0)
    smie_forfait_sal = Column(Float, default=0.0)
    smie_forfait_pat = Column(Float, default=0.0)
    plafond_smie = Column(Float, default=0.0)
    
    # Primes personnalisées (Labels 1 à 5)
    label_prime1 = Column(String, default="Prime 1")
    label_prime2 = Column(String, default="Prime 2")
    label_prime3 = Column(String, default="Prime 3")
    label_prime4 = Column(String, default="Prime 4")
    label_prime5 = Column(String, default="Prime 5")
    
    # 🔹 NOUVELLES LISTES ORGANISATIONNELLES (JSON)
    etablissements = Column(Text, default="[]")  # JSON array: ["Établissement 1", "Établissement 2"]
    departements = Column(Text, default="[]")    # JSON array: ["Département A", "Département B"]
    services = Column(Text, default="[]")        # JSON array: ["Service X", "Service Y"]
    unites = Column(Text, default="[]")          # JSON array: ["Unité Alpha", "Unité Beta"]
    
    # RELATION avec TypeRegime (N:1)
    type_regime_id = Column(Integer, ForeignKey("type_regimes.id", ondelete="SET NULL"), nullable=True)
    type_regime = relationship("TypeRegime", back_populates="employers")

    # Global Primes (Types de primes définis par l'employeur)
    primes = relationship("Prime", back_populates="employer", cascade="all, delete-orphan")

    workers = relationship("Worker", back_populates="employer")
    
    # Relation avec la hiérarchie organisationnelle
    organizational_nodes = relationship("OrganizationalNode", back_populates="employer", cascade="all, delete-orphan")
    
    # Relation avec le calendrier
    calendar_days = relationship("CalendarDay", back_populates="employer", cascade="all, delete-orphan")


class OrganizationalNode(Base):
    """
    Modèle pour la hiérarchie organisationnelle en cascade.
    Remplace les listes JSON par une vraie structure hiérarchique.
    """
    __tablename__ = "organizational_nodes"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("organizational_nodes.id", ondelete="CASCADE"), nullable=True)
    level = Column(String(20), nullable=False)  # 'etablissement', 'departement', 'service', 'unite'
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)  # Code optionnel pour le nœud
    description = Column(Text, nullable=True)  # Description optionnelle
    path = Column(Text)  # Chemin hiérarchique complet calculé automatiquement
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relations
    employer = relationship("Employer", back_populates="organizational_nodes")
    parent = relationship("OrganizationalNode", remote_side=[id], back_populates="children")
    children = relationship("OrganizationalNode", back_populates="parent", cascade="all, delete-orphan")

    # Contraintes
    __table_args__ = (
        CheckConstraint(
            "level IN ('etablissement', 'departement', 'service', 'unite')",
            name="chk_valid_level"
        ),
        CheckConstraint(
            "(level = 'etablissement' AND parent_id IS NULL) OR "
            "(level IN ('departement', 'service', 'unite') AND parent_id IS NOT NULL)",
            name="chk_level_hierarchy"
        ),
        UniqueConstraint('employer_id', 'parent_id', 'name', name='uq_employer_parent_name'),
        Index('idx_organizational_nodes_employer', 'employer_id'),
        Index('idx_organizational_nodes_parent', 'parent_id'),
        Index('idx_organizational_nodes_level', 'level'),
        Index('idx_organizational_nodes_path', 'path'),
        Index('idx_organizational_nodes_active', 'is_active'),
    )


class CalendarDay(Base):
    __tablename__ = "calendar_days"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    is_worked = Column(Boolean, default=True)
    status = Column(String(20), nullable=True)
    note = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('employer_id', 'date', name='uq_employer_date'),
    )

    employer = relationship("Employer", back_populates="calendar_days")


class Prime(Base):
    """
    Définition globale d'une prime pour un employeur.
    Les formules sont définies ici et appliquées à tous les travailleurs qui ont cette prime activée.
    """
    __tablename__ = "primes"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False)
    
    label = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # Formules globales
    formula_nombre = Column(String, nullable=True)
    formula_base = Column(String, nullable=True)
    formula_taux = Column(String, nullable=True)
    
    operation_1 = Column(String, default="*")
    operation_2 = Column(String, default="*")

    # Options
    is_active = Column(Boolean, default=True)
    is_cotisable = Column(Boolean, default=True)
    is_imposable = Column(Boolean, default=True)
    target_mode = Column(String(20), default="global", nullable=False)

    employer = relationship("Employer", back_populates="primes")
    
    # Liens
    worker_links = relationship("WorkerPrimeLink", back_populates="prime", cascade="all, delete-orphan")
    organizational_targets = relationship("PrimeOrganizationalTarget", back_populates="prime", cascade="all, delete-orphan")
    organizational_unit_targets = relationship("PrimeOrganizationalUnitTarget", back_populates="prime", cascade="all, delete-orphan")


class WorkerPrimeLink(Base):
    """
    Association entre un travailleur et une prime globale.
    Permet d'activer/désactiver la prime pour ce travailleur spécifique.
    """
    __tablename__ = "worker_prime_links"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    prime_id = Column(Integer, ForeignKey("primes.id"), nullable=False)
    
    is_active = Column(Boolean, default=True)
    link_type = Column(String(20), default="include", nullable=False)
    
    worker = relationship("Worker", back_populates="prime_links")
    prime = relationship("Prime", back_populates="worker_links")

    __table_args__ = (
        UniqueConstraint('worker_id', 'prime_id', name='uq_worker_prime_link'),
    )


class PrimeOrganizationalTarget(Base):
    """
    Cible organisationnelle d'une prime globale.
    Permet d'appliquer une prime a un ou plusieurs segments RH.
    """
    __tablename__ = "prime_organizational_targets"

    id = Column(Integer, primary_key=True, index=True)
    prime_id = Column(Integer, ForeignKey("primes.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(Integer, ForeignKey("organizational_nodes.id", ondelete="CASCADE"), nullable=False)

    prime = relationship("Prime", back_populates="organizational_targets")
    node = relationship("OrganizationalNode")

    __table_args__ = (
        UniqueConstraint("prime_id", "node_id", name="uq_prime_organizational_target"),
    )


class PrimeOrganizationalUnitTarget(Base):
    """
    Cible organisationnelle d'une prime basee sur la page Organisation.
    Utilise organizational_units, qui porte les affectations visibles des salaries.
    """
    __tablename__ = "prime_organizational_unit_targets"

    id = Column(Integer, primary_key=True, index=True)
    prime_id = Column(Integer, ForeignKey("primes.id", ondelete="CASCADE"), nullable=False)
    organizational_unit_id = Column(Integer, ForeignKey("organizational_units.id", ondelete="CASCADE"), nullable=False)

    prime = relationship("Prime", back_populates="organizational_unit_targets")
    organizational_unit = relationship("OrganizationalUnit")

    __table_args__ = (
        UniqueConstraint("prime_id", "organizational_unit_id", name="uq_prime_organizational_unit_target"),
    )



class WorkerPrime(Base):
    __tablename__ = "worker_primes"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    
    label = Column(String, nullable=False)           # ex: "Prime d'ancienneté"
    
    # Formules (stockées sous forme de string, ex: "ANCIENAN * 0.05 * SALDBASE")
    formula_nombre = Column(String, nullable=True)   # Formule pour la colonne Nombre
    formula_base = Column(String, nullable=True)     # Formule pour la colonne Base
    formula_taux = Column(String, nullable=True)     # Formule pour la colonne Taux

    operation_1 = Column(String, default="*")        # Opérateur entre Nb et Base (*, +, -, /)
    operation_2 = Column(String, default="*")        # Opérateur entre (Nb op1 Base) et Taux (*, +, -, /)
    
    is_active = Column(Boolean, default=True)
    
    worker = relationship("Worker", back_populates="primes")


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False)
    matricule = Column(String, unique=True, index=True)
    nom = Column(String)
    prenom = Column(String)
    sexe = Column(String)
    situation_familiale = Column(String)
    adresse = Column(String)
    telephone = Column(String)
    type_regime_id = Column(Integer)
    email = Column(String)
    cin = Column(String)
    cin_delivre_le = Column(Date)
    cin_lieu = Column(String)
    nombre_enfant = Column(Integer)
    date_naissance = Column(Date)
    lieu_naissance = Column(String)  # Lieu de naissance
    date_embauche = Column(Date)
    nature_contrat = Column(String)   # CDI / CDD
    duree_essai_jours = Column(Integer, default=0)
    date_fin_essai = Column(Date, nullable=True)  # Date de fin d'essai
    mode_paiement = Column(String)    # banque | espece | ...
    rib = Column(String)
    code_banque = Column(String)
    code_guichet = Column(String)
    compte_num = Column(String)
    cle_rib = Column(String)
    banque = Column(String)
    nom_guichet = Column(String)
    bic = Column(String)
    cnaps_num = Column(String)
    smie_agence = Column(String)
    smie_carte_num = Column(String)
    etablissement = Column(String)
    departement = Column(String)
    service = Column(String)
    unite = Column(String)
    poste = Column(String)
    categorie_prof = Column(String)
    indice = Column(String)
    valeur_point = Column(Float)
    groupe_preavis = Column(Integer)  # 1..5
    type_sortie = Column(String)      # L/D = type_rupture
    date_debauche = Column(Date, nullable=True) # Date de débauche
    jours_preavis_deja_faits = Column(Integer, default=0)
    anciennete_jours = Column(Integer, default=0)
    secteur = Column(String)          # agricole / non_agricole
    salaire_base = Column(Float, default=0.0)
    salaire_horaire = Column(Float, default=0.0)
    vhm = Column(Float, default=0.0)              # 173.33 ou 200
    horaire_hebdo = Column(Float, default=0.0)    # 40 ou 46
    solde_conge_initial = Column(Float, default=0.0) # Reprise de solde / Ajustement
    
    # === AVANTAGES EN NATURE (VALEURS FIXES) ===
    avantage_vehicule = Column(Float, default=0.0)
    avantage_logement = Column(Float, default=0.0)
    avantage_telephone = Column(Float, default=0.0)
    avantage_autres = Column(Float, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)

    # === CONTRIBUTION RATE OVERRIDES (OPTIONAL) ===
    taux_sal_cnaps_override = Column(Float, nullable=True)  # Override employer CNaPS rate
    taux_sal_smie_override = Column(Float, nullable=True)   # Override employer SMIE rate
    taux_pat_cnaps_override = Column(Float, nullable=True)  # Override employer CNaPS patronal rate
    taux_pat_smie_override = Column(Float, nullable=True)   # Override employer SMIE patronal rate
    taux_pat_fmfp_override = Column(Float, nullable=True)   # Override employer FMFP patronal rate

    employer = relationship("Employer", back_populates="workers")
    variables = relationship("PayVar", back_populates="worker", cascade="all, delete-orphan")
    # Relations
    prime_links = relationship("WorkerPrimeLink", back_populates="worker", cascade="all, delete-orphan")
    primes = relationship("WorkerPrime", back_populates="worker", cascade="all, delete-orphan")
    absences = relationship("Absence", back_populates="worker", cascade="all, delete-orphan")
    avances = relationship("Avance", back_populates="worker", cascade="all, delete-orphan")
    leaves = relationship("Leave", back_populates="worker", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="worker", cascade="all, delete-orphan")
    position_history = relationship("WorkerPositionHistory", back_populates="worker", cascade="all, delete-orphan")
    
    # Cascades pour tables de paie additionnelles
    hs_calculations = relationship("HSCalculationHS", back_populates="worker", cascade="all, delete-orphan")
    payroll_hs_hm = relationship("PayrollHsHm", back_populates="worker", cascade="all, delete-orphan")
    payroll_primes = relationship("PayrollPrime", back_populates="worker", cascade="all, delete-orphan")
    
    # ✅ NOUVELLE LIAISON ORGANISATIONNELLE (OPTIONNELLE)
    organizational_unit_id = Column(Integer, ForeignKey("organizational_units.id"), nullable=True, index=True)
    organizational_unit = relationship("OrganizationalUnit", backref="workers")
    deleted_by = relationship("AppUser", foreign_keys=[deleted_by_user_id])
    
    # ✅ PROPRIÉTÉS CALCULÉES POUR RÉTROCOMPATIBILITÉ
    @property
    def effective_etablissement(self):
        """Retourne l'établissement via la nouvelle structure ou l'ancien champ"""
        if self.organizational_unit:
            ancestor = self.organizational_unit.get_ancestor_by_level('etablissement')
            return ancestor.name if ancestor else None
        return self.etablissement
    
    @property
    def effective_departement(self):
        """Retourne le département via la nouvelle structure ou l'ancien champ"""
        if self.organizational_unit:
            ancestor = self.organizational_unit.get_ancestor_by_level('departement')
            return ancestor.name if ancestor else None
        return self.departement
    
    @property
    def effective_service(self):
        """Retourne le service via la nouvelle structure ou l'ancien champ"""
        if self.organizational_unit:
            ancestor = self.organizational_unit.get_ancestor_by_level('service')
            return ancestor.name if ancestor else None
        return self.service
    
    @property
    def effective_unite(self):
        """Retourne l'unité via la nouvelle structure ou None"""
        if self.organizational_unit and self.organizational_unit.level == 'unite':
            return self.organizational_unit.name
        return None


class WorkerPositionHistory(Base):
    __tablename__ = "worker_position_history"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    
    poste = Column(String, nullable=False)
    categorie_prof = Column(String, nullable=True)
    indice = Column(String, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    worker = relationship("Worker", back_populates="position_history")


class PayVar(Base):
    __tablename__ = "payvars"

    id = Column(Integer, primary_key=True, index=True)

    # 🔗 Lien avec le salarié
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)

    # 📅 Période de paie (ex : "2025-11")
    period = Column(String, nullable=False, index=True)

    # === HEURES SUPPLÉMENTAIRES (totaux mois) ===
    hsni_130 = Column(Float, default=0.0)   # HS non imposables 130%
    hsi_130 = Column(Float, default=0.0)    # HS imposables 130%
    hsni_150 = Column(Float, default=0.0)   # HS non imposables 150%
    hsi_150 = Column(Float, default=0.0)    # HS imposables 150%
    hmn_30 = Column(Float, default=0.0)     # Heures majorées nuit 30%

    # Ancien champ résumé (on le garde pour compatibilité)
    absences_non_remu = Column(Float, default=0.0)

    # === ABSENCES DÉTAILLÉES ===
    # 👉 utilisés dans payroll_logic.compute_preview
    abs_non_remu_j = Column(Float, default=0.0)   # Absences non rémunérées (jours)
    abs_maladie_j = Column(Float, default=0.0)    # Absence maladie (jours)
    mise_a_pied_j = Column(Float, default=0.0)    # Mise à pied (jours)
    abs_non_remu_h = Column(Float, default=0.0)   # Absences non rémunérées (heures)

    # === PRIMES SIMPLES ===
    prime_fixe = Column(Float, default=0.0)
    prime_variable = Column(Float, default=0.0)

    # === PRIMES DÉTAILLÉES 1..10 (pour l’avenir) ===
    prime1 = Column(Float, default=0.0)
    prime2 = Column(Float, default=0.0)
    prime3 = Column(Float, default=0.0)
    prime4 = Column(Float, default=0.0)
    prime5 = Column(Float, default=0.0)
    prime6 = Column(Float, default=0.0)
    prime7 = Column(Float, default=0.0)
    prime8 = Column(Float, default=0.0)
    prime9 = Column(Float, default=0.0)
    prime10 = Column(Float, default=0.0)
    
    # 13ème Mois
    prime_13 = Column(Float, default=0.0)

    # === AVANTAGES EN NATURE ===
    # 👉 utilisés dans la formule "Somme des avantages en nature taxables"
    avantage_vehicule = Column(Float, default=0.0)
    avantage_logement = Column(Float, default=0.0)
    avantage_telephone = Column(Float, default=0.0)
    avantage_autres = Column(Float, default=0.0)

    # === ALLOCATION FAMILIALE ===
    alloc_familiale = Column(Float, default=0.0)

    # === AVANCES & DÉDUCTIONS ===
    avance_salaire = Column(Float, default=0.0)      # Ancien champ, on le garde
    avance_quinzaine = Column(Float, default=0.0)
    avance_speciale_rembfixe = Column(Float, default=0.0)

    autre_ded1 = Column(Float, default=0.0)
    autre_ded2 = Column(Float, default=0.0)
    autre_ded3 = Column(Float, default=0.0)
    autre_ded4 = Column(Float, default=0.0)

    autres_gains = Column(Float, default=0.0)
    autres_retenues = Column(Float, default=0.0)

    # 🔁 Relation ORM vers le salarié
    worker = relationship("Worker", back_populates="variables")

    # 🔒 Un seul enregistrement par salarié et par période
    __table_args__ = (
        UniqueConstraint("worker_id", "period", name="uq_payvars_worker_period"),
    )


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True)
    employer_id = Column(Integer, ForeignKey("employers.id"))
    period = Column(String, index=True)
    generated_at = Column(Date)


class PayrollPeriod(Base):
    __tablename__ = "payroll_periods"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    is_closed = Column(Boolean, nullable=False, default=False, index=True)
    closed_at = Column(DateTime, nullable=True)
    reopened_at = Column(DateTime, nullable=True)
    closed_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    reopened_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    closed_by = relationship("AppUser", foreign_keys=[closed_by_user_id])
    reopened_by = relationship("AppUser", foreign_keys=[reopened_by_user_id])

    __table_args__ = (
        UniqueConstraint("employer_id", "month", "year", name="uq_payroll_period_employer_month_year"),
        CheckConstraint("month >= 1 AND month <= 12", name="chk_payroll_period_month"),
        Index("ix_payroll_periods_employer_year_month", "employer_id", "year", "month"),
    )


class PayrollArchive(Base):
    __tablename__ = "payroll_archives"

    id = Column(Integer, primary_key=True, index=True)
    payroll_period_id = Column(Integer, ForeignKey("payroll_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    period = Column(String(7), nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    worker_matricule = Column(String(100), nullable=True)
    worker_full_name = Column(String(255), nullable=True)
    brut = Column(Float, nullable=False, default=0.0)
    cotisations_salariales = Column(Float, nullable=False, default=0.0)
    cotisations_patronales = Column(Float, nullable=False, default=0.0)
    irsa = Column(Float, nullable=False, default=0.0)
    net = Column(Float, nullable=False, default=0.0)
    totals_json = Column(Text, nullable=False, default="{}")
    lines_json = Column(Text, nullable=False, default="[]")
    archived_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    payroll_period = relationship("PayrollPeriod")
    employer = relationship("Employer")
    worker = relationship("Worker")

    __table_args__ = (
        UniqueConstraint("payroll_period_id", "worker_id", name="uq_payroll_archive_period_worker"),
        Index("ix_payroll_archives_employer_period", "employer_id", "period"),
    )


class HSCalculationHS(Base):
    """
    Résumé mensuel des heures supplémentaires pour un salarié.
    Correspond à la table hs_calculations_HS.
    """

    __tablename__ = "hs_calculations_HS"

    id_HS = Column(Integer, primary_key=True, index=True)

    # Salarié concerné
    worker_id_HS = Column(Integer, ForeignKey("workers.id"), nullable=False)

    # Mois de paie : 'YYYY-MM'
    mois_HS = Column(String(7), nullable=False)

    # Base hebdomadaire utilisée pour le calcul (ex: 40, 44, 48)
    base_hebdo_heures_HS = Column(Float, nullable=False, default=40.0)

    # Totaux HS NI / I
    total_HSNI_130_heures_HS = Column(Float, nullable=False, default=0.0)
    total_HSI_130_heures_HS = Column(Float, nullable=False, default=0.0)
    total_HSNI_150_heures_HS = Column(Float, nullable=False, default=0.0)
    total_HSI_150_heures_HS = Column(Float, nullable=False, default=0.0)

    # Totaux majorations
    total_HMNH_30_heures_HS = Column(Float, nullable=False, default=0.0)
    total_HMNO_50_heures_HS = Column(Float, nullable=False, default=0.0)
    total_HMD_40_heures_HS = Column(Float, nullable=False, default=0.0)
    total_HMJF_50_heures_HS = Column(Float, nullable=False, default=0.0)

    # Lien éventuel avec un traitement de paie (run de paie)
    payroll_run_id_HS = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)

    # Audit
    created_at_HS = Column(DateTime, default=utcnow, nullable=False)
    updated_at_HS = Column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relation avec les lignes journalières HS
    jours_HS = relationship(
        "HSJourHS",
        back_populates="calculation_HS",
        cascade="all, delete-orphan",
    )

    worker = relationship("Worker", back_populates="hs_calculations")

    @property
    def worker_matricule_HS(self):
        return self.worker.matricule if self.worker else None

    @property
    def worker_nom_HS(self):
        return self.worker.nom if self.worker else None

    @property
    def worker_prenom_HS(self):
        return self.worker.prenom if self.worker else None

    @property
    def worker_display_name_HS(self):
        if not self.worker:
            return None
        return " ".join(part for part in [self.worker.nom, self.worker.prenom] if part).strip() or None

    def __repr__(self) -> str:
        return (
            f"<HSCalculationHS id={self.id_HS} worker={self.worker_id_HS} "
            f"mois={self.mois_HS}>"
        )


class HSJourHS(Base):
    """
    Détail jour par jour pour un calcul HS donné.
    Correspond à la table hs_jours_HS.
    """

    __tablename__ = "hs_jours_HS"

    id_HS = Column(Integer, primary_key=True, index=True)

    # Référence au calcul HS mensuel
    calculation_id_HS = Column(
        Integer,
        ForeignKey("hs_calculations_HS.id_HS"),
        nullable=False,
        index=True,
    )

    # Données d'entrée
    date_HS = Column(Date, nullable=False)
    type_jour_HS = Column(String(2), nullable=False)  # 'N' ou 'JF'
    entree_HS = Column(Time, nullable=False)
    sortie_HS = Column(Time, nullable=False)
    type_nuit_HS = Column(String(1), nullable=True)  # None, 'H', 'O'

    # Données calculées (en heures décimales)
    duree_travail_totale_heures_HS = Column(Float, nullable=True)
    duree_base_heures_HS = Column(Float, nullable=True)
    hmnh_30_heures_HS = Column(Float, nullable=True)
    hmno_50_heures_HS = Column(Float, nullable=True)
    hmd_40_heures_HS = Column(Float, nullable=True)
    hmjf_50_heures_HS = Column(Float, nullable=True)

    # Semaine ISO, utile pour recontrôler la logique HS
    iso_year_HS = Column(Integer, nullable=True)
    iso_week_HS = Column(Integer, nullable=True)

    # Commentaire libre (optionnel)
    commentaire_HS = Column(Text, nullable=True)

    # Relation vers le calcul mensuel
    calculation_HS = relationship("HSCalculationHS", back_populates="jours_HS")

    def __repr__(self) -> str:
        return (
            f"<HSJourHS id={self.id_HS} calc={self.calculation_id_HS} "
            f"date={self.date_HS}>"
        )
        
        
class Absence(Base):
    __tablename__ = "absences"

    id = Column(Integer, primary_key=True, index=True)

    # 🔹 Lien avec le salarié (adapte le nom si ton modèle Worker s'appelle autrement)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)

    # Exemple : mois au format "2025-10"
    mois = Column(String, nullable=False)

    # 🔹 Champs d'absences, mêmes codes que dans le calcul
    ABSM_J = Column(Float, default=0.0)   # Absence maladie (jours) – info
    ABSM_H = Column(Float, default=0.0)   # Absence maladie (heures) – info
    ABSNR_J = Column(Float, default=0.0)  # Absence non rémunérée (jours)
    ABSNR_H = Column(Float, default=0.0)  # Absence non rémunérée (heures)
    ABSMP   = Column(Float, default=0.0)  # Mise à pied (jours)
    ABS1_J  = Column(Float, default=0.0)  # Autre absence 1 (jours)
    ABS1_H  = Column(Float, default=0.0)  # Autre absence 1 (heures)
    ABS2_J  = Column(Float, default=0.0)  # Autre absence 2 (jours)
    ABS2_H  = Column(Float, default=0.0)  # Autre absence 2 (heures)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow
    )

    # Relation vers le modèle Worker (si tu en as un)
    worker = relationship("Worker", back_populates="absences")


class Avance(Base):
    __tablename__ = "avances"

    id = Column(Integer, primary_key=True, index=True)

    # Lien avec le salarié
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)

    # Période (YYYY-MM) pour lier à une paie spécifique
    periode = Column(String, nullable=False)

    # Montant de l'avance
    montant = Column(Float, default=0.0)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow
    )

    # Relations
    worker = relationship("Worker", back_populates="avances")


# ============================================================
# LEAVE & PERMISSION MODELS
# ============================================================

class Leave(Base):
    """Leave (Congé) tracking for workers"""
    __tablename__ = "leaves"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(String, nullable=False, index=True)  # "2025-01" format
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_taken = Column(Float, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    worker = relationship("Worker", back_populates="leaves")


class Permission(Base):
    """Exceptional Permission tracking for workers"""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(String, nullable=False, index=True)  # "2025-01" format
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_taken = Column(Float, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    worker = relationship("Worker", back_populates="permissions")



class PayrollHsHm(Base):
    """
    Heures Supplémentaires et Heures Majorées pour une paie.
    Peut provenir soit d'un calcul manuel (hs_calculations_HS) soit d'une importation Excel.
    """
    __tablename__ = "payroll_hs_hm"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    
    # Source des données
    source_type = Column(String(20), nullable=False)  # 'MANUAL' ou 'IMPORT'
    hs_calculation_id = Column(Integer, ForeignKey("hs_calculations_HS.id_HS"), nullable=True)  # Si source = MANUAL
    import_file_name = Column(String(255), nullable=True)  # Si source = IMPORT
    
    # Heures (valeurs brutes en heures décimales)
    hsni_130_heures = Column(Numeric(10, 2), default=0)
    hsi_130_heures = Column(Numeric(10, 2), default=0)
    hsni_150_heures = Column(Numeric(10, 2), default=0)
    hsi_150_heures = Column(Numeric(10, 2), default=0)
    hmnh_heures = Column(Numeric(10, 2), default=0)
    hmno_heures = Column(Numeric(10, 2), default=0)
    hmd_heures = Column(Numeric(10, 2), default=0)
    hmjf_heures = Column(Numeric(10, 2), default=0)
    
    # Montants calculés (en Ariary)
    hsni_130_montant = Column(Numeric(15, 2), default=0)
    hsi_130_montant = Column(Numeric(15, 2), default=0)
    hsni_150_montant = Column(Numeric(15, 2), default=0)
    hsi_150_montant = Column(Numeric(15, 2), default=0)
    hmnh_montant = Column(Numeric(15, 2), default=0)
    hmno_montant = Column(Numeric(15, 2), default=0)
    hmd_montant = Column(Numeric(15, 2), default=0)
    hmjf_montant = Column(Numeric(15, 2), default=0)
    
    # Métadonnées
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    # Relations
    payroll_run = relationship("PayrollRun")
    worker = relationship("Worker", back_populates="payroll_hs_hm")
    hs_calculation = relationship("HSCalculationHS")
    
    # Contrainte unique : un seul enregistrement par (payroll_run_id, worker_id)
    __table_args__ = (
        UniqueConstraint('payroll_run_id', 'worker_id', name='uq_payroll_worker_hs_hm'),
    )


class PayrollPrime(Base):
    """
    Valeurs variables importées pour les primes (Nombre et Base) pour une période donnée.
    Utilisé pour surcharger les formules lors du calcul de paie.
    """
    __tablename__ = "payroll_primes"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    period = Column(String, nullable=False, index=True)
    
    prime_label = Column(String, nullable=False) # Le nom de la prime (ex: "Prime de Panier")
    
    # Valeurs importées (remplacent le résultat de la formule si non-null)
    nombre = Column(Float, nullable=True)
    base = Column(Float, nullable=True)
    taux = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    worker = relationship("Worker", back_populates="payroll_primes")

    __table_args__ = (
        UniqueConstraint('worker_id', 'period', 'prime_label', name='uq_payroll_prime_worker_period_label'),
    )


class CustomContract(Base):
    """
    Contrats personnalisés sauvegardés par les utilisateurs
    """
    __tablename__ = "custom_contracts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    
    # Contenu du contrat
    title = Column(String, nullable=False, default="Contrat de Travail")
    content = Column(Text, nullable=False)  # Contenu HTML du contrat personnalisé
    
    # Métadonnées
    template_type = Column(String, default="employment_contract")  # Type de template
    is_default = Column(Boolean, default=False)  # Si c'est le template par défaut pour ce travailleur
    validation_status = Column(String(50), nullable=False, default="active_non_validated", index=True)
    inspection_status = Column(String(50), nullable=False, default="pending_review", index=True)
    inspection_comment = Column(Text, nullable=True)
    active_version_number = Column(Integer, nullable=False, default=1)
    last_published_at = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relations
    worker = relationship("Worker", backref="custom_contracts")
    employer = relationship("Employer", backref="custom_contracts")

    def __repr__(self):
        return f"<CustomContract(id={self.id}, worker_id={self.worker_id}, title='{self.title}')>"


class DocumentTemplate(Base):
    """
    Templates de documents réutilisables (certificats, attestations, etc.)
    """
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)  # Null = template global
    
    # Contenu du template
    name = Column(String, nullable=False)
    description = Column(String)
    template_type = Column(String, nullable=False)  # 'contract', 'certificate', 'attestation'
    content = Column(Text, nullable=False)  # Contenu HTML avec placeholders
    
    # Métadonnées
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # Template système (non modifiable)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relations
    employer = relationship("Employer", backref="document_templates")

    def __repr__(self):
        return f"<DocumentTemplate(id={self.id}, name='{self.name}', type='{self.template_type}')>"


# Constantes pour les niveaux organisationnels
ORGANIZATIONAL_LEVELS = {
    'etablissement': 1,
    'departement': 2, 
    'service': 3,
    'unite': 4
}


class OrganizationalUnit(Base):
    """
    Structure organisationnelle hiérarchique avec ordre strict :
    Employeur → Établissement → Département → Service → Unité
    """
    __tablename__ = "organizational_units"
    
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    
    # Hiérarchie avec ordre strict
    parent_id = Column(Integer, ForeignKey("organizational_units.id"), nullable=True, index=True)
    level = Column(String, nullable=False, index=True)  # 'etablissement', 'departement', 'service', 'unite'
    level_order = Column(Integer, nullable=False, index=True)  # 1=etablissement, 2=departement, 3=service, 4=unite
    
    # Informations
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # Métadonnées
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    # Relations
    employer = relationship("Employer", backref="organizational_units")
    parent = relationship("OrganizationalUnit", remote_side=[id], backref="children")
    
    # Contraintes pour garantir l'ordre hiérarchique et l'unicité
    __table_args__ = (
        Index('idx_org_unit_employer_level', 'employer_id', 'level'),
        Index('idx_org_unit_parent', 'parent_id'),
        UniqueConstraint('employer_id', 'parent_id', 'code', name='uq_org_unit_code'),
    )
    
    def get_ancestor_by_level(self, target_level: str):
        """Récupère l'ancêtre d'un niveau donné"""
        current = self
        while current:
            if current.level == target_level:
                return current
            current = current.parent
        return None
    
    def get_hierarchy_path(self):
        """Retourne le chemin hiérarchique complet"""
        path = []
        current = self
        while current:
            path.insert(0, current)
            current = current.parent
        return path
    
    def __repr__(self):
        return f"<OrganizationalUnit(id={self.id}, level='{self.level}', name='{self.name}')>"


class OrganizationalAudit(Base):
    """
    Table d'audit pour tracer toutes les modifications hiérarchiques.
    Maintient un historique complet des changements pour la conformité et le débogage.
    """
    __tablename__ = "organizational_audit"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("organizational_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Type d'action
    action = Column(String(20), nullable=False, index=True)  # CREATE, UPDATE, DELETE, MOVE
    
    # Données de l'audit
    old_values = Column(Text, nullable=True)  # JSON des anciennes valeurs
    new_values = Column(Text, nullable=True)  # JSON des nouvelles valeurs
    
    # Métadonnées
    user_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)
    reason = Column(Text, nullable=True)
    
    # Relations
    node = relationship("OrganizationalNode", backref="audit_entries")
    
    # Contraintes
    __table_args__ = (
        CheckConstraint(
            "action IN ('CREATE', 'UPDATE', 'DELETE', 'MOVE')",
            name="valid_action"
        ),
        Index('idx_org_audit_node_timestamp', 'node_id', 'timestamp'),
        Index('idx_org_audit_action', 'action'),
    )
    
    def __repr__(self):
        return f"<OrganizationalAudit(id={self.id}, node_id={self.node_id}, action='{self.action}', timestamp={self.timestamp})>"


class OrgUnitEvent(Base):
    __tablename__ = "org_unit_events"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    org_unit_id = Column(Integer, ForeignKey("organizational_units.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    triggered_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    org_unit = relationship("OrganizationalUnit")
    triggered_by = relationship("AppUser")


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role_code = Column(String(80), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    account_status = Column(String(40), default="ACTIVE", nullable=False, index=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker", foreign_keys=[worker_id])
    approved_by_user = relationship("AppUser", remote_side=[id], foreign_keys=[approved_by])
    rejected_by_user = relationship("AppUser", remote_side=[id], foreign_keys=[rejected_by])
    role_assignments = relationship(
        "IamUserRole",
        foreign_keys="IamUserRole.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    permission_overrides = relationship(
        "IamUserPermissionOverride",
        foreign_keys="IamUserPermissionOverride.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    role_activation_updates = relationship(
        "IamRoleActivation",
        foreign_keys="IamRoleActivation.updated_by_user_id",
        back_populates="updated_by",
    )


class IamRole(Base):
    __tablename__ = "iam_roles"

    code = Column(String(80), primary_key=True)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(String(80), nullable=False, default="company")
    base_role_code = Column(String(80), nullable=False)
    is_system = Column(Boolean, nullable=False, default=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    permissions = relationship("IamRolePermission", back_populates="role", cascade="all, delete-orphan")
    user_assignments = relationship("IamUserRole", back_populates="role", cascade="all, delete-orphan")
    activations = relationship("IamRoleActivation", back_populates="role", cascade="all, delete-orphan")


class IamPermission(Base):
    __tablename__ = "iam_permissions"

    code = Column(String(120), primary_key=True)
    module = Column(String(80), nullable=False, index=True)
    action = Column(String(30), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    sensitivity = Column(String(80), nullable=False, default="base")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    role_links = relationship("IamRolePermission", back_populates="permission", cascade="all, delete-orphan")
    user_overrides = relationship("IamUserPermissionOverride", back_populates="permission", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "action IN ('read', 'create', 'write', 'validate', 'approve', 'close', 'export', 'print', 'document', 'delete', 'admin')",
            name="chk_iam_permission_action",
        ),
    )


class IamRolePermission(Base):
    __tablename__ = "iam_role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_code = Column(String(80), ForeignKey("iam_roles.code", ondelete="CASCADE"), nullable=False, index=True)
    permission_code = Column(String(120), ForeignKey("iam_permissions.code", ondelete="CASCADE"), nullable=False, index=True)
    is_granted = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    role = relationship("IamRole", back_populates="permissions")
    permission = relationship("IamPermission", back_populates="role_links")

    __table_args__ = (
        UniqueConstraint("role_code", "permission_code", name="uq_iam_role_permission"),
        Index("ix_iam_role_permissions_role_grant", "role_code", "is_granted"),
    )


class IamRoleActivation(Base):
    __tablename__ = "iam_role_activations"

    id = Column(Integer, primary_key=True, index=True)
    scope_key = Column(String(100), nullable=False, default="installation", index=True)
    role_code = Column(String(80), ForeignKey("iam_roles.code", ondelete="CASCADE"), nullable=False, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    updated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    role = relationship("IamRole", back_populates="activations")
    updated_by = relationship("AppUser", foreign_keys=[updated_by_user_id], back_populates="role_activation_updates")

    __table_args__ = (
        UniqueConstraint("scope_key", "role_code", name="uq_iam_role_activation_scope"),
    )


class IamUserRole(Base):
    __tablename__ = "iam_user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_code = Column(String(80), ForeignKey("iam_roles.code", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True, index=True)
    delegated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("AppUser", foreign_keys=[user_id], back_populates="role_assignments")
    role = relationship("IamRole", back_populates="user_assignments")
    employer = relationship("Employer")
    worker = relationship("Worker")
    delegated_by = relationship("AppUser", foreign_keys=[delegated_by_user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "role_code", "employer_id", "worker_id", name="uq_iam_user_role_scope"),
        Index("ix_iam_user_roles_user_active", "user_id", "is_active", "valid_until"),
    )


class IamUserPermissionOverride(Base):
    __tablename__ = "iam_user_permission_overrides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_code = Column(String(120), ForeignKey("iam_permissions.code", ondelete="CASCADE"), nullable=False, index=True)
    is_allowed = Column(Boolean, nullable=False, default=True)
    reason = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    updated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("AppUser", foreign_keys=[user_id], back_populates="permission_overrides")
    permission = relationship("IamPermission", back_populates="user_overrides")
    updated_by = relationship("AppUser", foreign_keys=[updated_by_user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "permission_code", name="uq_iam_user_permission_override"),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_seen_at = Column(DateTime, default=utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("AppUser")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    actor_role = Column(String(50), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    route = Column(String(255), nullable=True)
    employer_id = Column(Integer, nullable=True, index=True)
    worker_id = Column(Integer, nullable=True, index=True)
    before_json = Column(Text, nullable=True)
    after_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    actor = relationship("AppUser")


class LabourInspectorAssignment(Base):
    __tablename__ = "labour_inspector_assignments"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=False, index=True)
    inspector_user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    assignment_scope = Column(String(50), nullable=False, default="portfolio", index=True)
    circonscription = Column(String(255), nullable=True, index=True)
    sector_filter = Column(String(255), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    inspector = relationship("AppUser", foreign_keys=[inspector_user_id])
    assigned_by = relationship("AppUser", foreign_keys=[assigned_by_user_id])

    __table_args__ = (
        UniqueConstraint("employer_id", "inspector_user_id", name="uq_labour_inspector_assignment"),
        Index("ix_labour_inspector_assignments_scope", "inspector_user_id", "status", "circonscription"),
    )


class LabourFormalMessage(Base):
    __tablename__ = "labour_formal_messages"

    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String(100), nullable=False, unique=True, index=True)
    thread_key = Column(String(100), nullable=True, index=True)
    sender_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    sender_employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)
    sender_role = Column(String(50), nullable=True, index=True)
    subject = Column(String(255), nullable=False, index=True)
    body = Column(Text, nullable=False)
    message_scope = Column(String(50), nullable=False, default="individual", index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    related_entity_type = Column(String(100), nullable=True, index=True)
    related_entity_id = Column(String(100), nullable=True, index=True)
    attachments_json = Column(Text, nullable=False, default="[]")
    metadata_json = Column(Text, nullable=False, default="{}")
    sent_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    sender = relationship("AppUser")
    sender_employer = relationship("Employer")

    __table_args__ = (
        Index("ix_labour_formal_messages_scope", "status", "message_scope", "sent_at"),
    )


class LabourFormalMessageRecipient(Base):
    __tablename__ = "labour_formal_message_recipients"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("labour_formal_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_type = Column(String(50), nullable=False, default="employer", index=True)
    status = Column(String(50), nullable=False, default="sent", index=True)
    read_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    message = relationship("LabourFormalMessage", backref="recipients")
    employer = relationship("Employer")
    user = relationship("AppUser")

    __table_args__ = (
        Index("ix_labour_formal_message_recipients_target", "employer_id", "user_id", "status"),
    )


class RequestWorkflow(Base):
    __tablename__ = "request_workflows"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(30), nullable=False, index=True)
    request_id = Column(Integer, nullable=False, index=True)
    overall_status = Column(String(30), nullable=False, default="pending_manager", index=True)
    manager_status = Column(String(30), nullable=False, default="pending")
    rh_status = Column(String(30), nullable=False, default="pending")
    manager_comment = Column(Text, nullable=True)
    rh_comment = Column(Text, nullable=True)
    manager_actor_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    rh_actor_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("request_type", "request_id", name="uq_request_workflow_request"),
        CheckConstraint(
            "request_type IN ('leave', 'permission')",
            name="chk_request_workflow_type"
        ),
    )

    manager_actor = relationship("AppUser", foreign_keys=[manager_actor_user_id])
    rh_actor = relationship("AppUser", foreign_keys=[rh_actor_user_id])


class LeaveTypeRule(Base):
    __tablename__ = "leave_type_rules"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)
    code = Column(String(100), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default="leave", index=True)
    description = Column(Text, nullable=True)
    deduct_from_annual_balance = Column(Boolean, nullable=False, default=False)
    validation_required = Column(Boolean, nullable=False, default=True)
    justification_required = Column(Boolean, nullable=False, default=False)
    payroll_impact = Column(String(50), nullable=False, default="none")
    attendance_impact = Column(String(50), nullable=False, default="absence")
    payroll_code = Column(String(30), nullable=True)
    visibility_scope = Column(String(30), nullable=False, default="all")
    allow_requalification = Column(Boolean, nullable=False, default=True)
    supports_hour_range = Column(Boolean, nullable=False, default=False)
    max_days_per_request = Column(Float, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")

    __table_args__ = (
        UniqueConstraint("employer_id", "code", name="uq_leave_type_rules_scope_code"),
    )


class LeaveApprovalRule(Base):
    __tablename__ = "leave_approval_rules"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)
    leave_type_code = Column(String(100), nullable=False, index=True)
    worker_category = Column(String(255), nullable=True, index=True)
    organizational_unit_id = Column(Integer, ForeignKey("organizational_units.id"), nullable=True, index=True)
    approval_mode = Column(String(30), nullable=False, default="sequential")
    fallback_on_reject = Column(String(30), nullable=False, default="reject")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    organizational_unit = relationship("OrganizationalUnit")


class LeaveApprovalRuleStep(Base):
    __tablename__ = "leave_approval_rule_steps"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("leave_approval_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False, default=1)
    parallel_group = Column(Integer, nullable=False, default=1)
    approver_kind = Column(String(50), nullable=False, default="manager")
    approver_role_code = Column(String(50), nullable=True)
    approver_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    is_required = Column(Boolean, nullable=False, default=True)
    label = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    rule = relationship("LeaveApprovalRule", backref="steps")
    approver_user = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("rule_id", "step_order", "parallel_group", "approver_kind", "approver_user_id", name="uq_leave_approval_rule_step"),
    )


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    request_ref = Column(String(50), nullable=False, unique=True, index=True)
    leave_type_code = Column(String(100), nullable=False, index=True)
    initial_leave_type_code = Column(String(100), nullable=False, index=True)
    final_leave_type_code = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    approval_mode = Column(String(30), nullable=False, default="sequential")
    fallback_on_reject = Column(String(30), nullable=False, default="reject")
    current_step_order = Column(Integer, nullable=True)
    period = Column(String(7), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    duration_days = Column(Float, nullable=False, default=0.0)
    duration_hours = Column(Float, nullable=False, default=0.0)
    partial_day_mode = Column(String(30), nullable=True)
    subject = Column(String(255), nullable=False)
    reason = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    attachment_required = Column(Boolean, nullable=False, default=False)
    attachment_count = Column(Integer, nullable=False, default=0)
    attachments_json = Column(Text, nullable=False, default="[]")
    estimated_balance_delta = Column(Float, nullable=False, default=0.0)
    estimated_payroll_impact = Column(String(50), nullable=False, default="none")
    estimated_attendance_impact = Column(String(50), nullable=False, default="absence")
    legacy_request_type = Column(String(30), nullable=True)
    legacy_request_id = Column(Integer, nullable=True, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    integrated_at = Column(DateTime, nullable=True)
    requalified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    requested_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_leave_requests_worker_status", "worker_id", "status", "start_date"),
    )


class LeaveRequestApproval(Base):
    __tablename__ = "leave_request_approvals"

    id = Column(Integer, primary_key=True, index=True)
    leave_request_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False, default=1)
    parallel_group = Column(Integer, nullable=False, default=1)
    approver_kind = Column(String(50), nullable=False, default="manager")
    approver_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    approver_role_code = Column(String(50), nullable=True)
    label = Column(String(255), nullable=True)
    is_required = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    acted_at = Column(DateTime, nullable=True)
    comment = Column(Text, nullable=True)
    delegated_from_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    leave_request = relationship("LeaveRequest", backref="approvals")
    approver_user = relationship("AppUser", foreign_keys=[approver_user_id])
    delegated_from_user = relationship("AppUser", foreign_keys=[delegated_from_user_id])

    __table_args__ = (
        Index("ix_leave_request_approvals_queue", "approver_user_id", "status", "step_order"),
    )


class LeaveRequestHistory(Base):
    __tablename__ = "leave_request_history"

    id = Column(Integer, primary_key=True, index=True)
    leave_request_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    comment = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    leave_request = relationship("LeaveRequest", backref="history")
    actor = relationship("AppUser")


class LeavePlanningCycle(Base):
    __tablename__ = "leave_planning_cycles"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    planning_year = Column(Integer, nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default="draft", index=True)
    max_absent_per_unit = Column(Integer, nullable=False, default=1)
    blackout_periods_json = Column(Text, nullable=False, default="[]")
    family_priority_enabled = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    created_by = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("employer_id", "planning_year", "title", name="uq_leave_planning_cycle_scope"),
    )


class LeavePlanningProposal(Base):
    __tablename__ = "leave_planning_proposals"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("leave_planning_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    leave_type_code = Column(String(100), nullable=False, default="CONGE_ANNUEL")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    score = Column(Float, nullable=False, default=0.0, index=True)
    rationale_json = Column(Text, nullable=False, default="[]")
    status = Column(String(50), nullable=False, default="proposed", index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    cycle = relationship("LeavePlanningCycle", backref="proposals")
    worker = relationship("Worker")
    created_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_leave_planning_proposals_cycle_score", "cycle_id", "score", "status"),
    )


class AttendanceLeaveReconciliation(Base):
    __tablename__ = "attendance_leave_reconciliation"

    id = Column(Integer, primary_key=True, index=True)
    leave_request_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    period = Column(String(7), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="validated_request_reference", index=True)
    discrepancy_level = Column(String(50), nullable=False, default="none", index=True)
    attendance_payload_json = Column(Text, nullable=False, default="{}")
    leave_payload_json = Column(Text, nullable=False, default="{}")
    notes = Column(Text, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    leave_request = relationship("LeaveRequest")
    employer = relationship("Employer")
    worker = relationship("Worker")
    resolved_by = relationship("AppUser")


class RecruitmentJobPosting(Base):
    __tablename__ = "recruitment_job_postings"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    contract_type = Column(String(50), nullable=False, default="CDI")
    status = Column(String(50), nullable=False, default="draft", index=True)
    salary_range = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    skills_required = Column(Text, nullable=True)
    publish_channels_json = Column(Text, nullable=False, default="[]")
    publish_status = Column(String(50), nullable=False, default="draft", index=True)
    publish_logs_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer", backref="recruitment_job_postings")


class RecruitmentCandidate(Base):
    __tablename__ = "recruitment_candidates"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(100), nullable=True)
    education_level = Column(String(120), nullable=True)
    experience_years = Column(Float, nullable=False, default=0.0)
    source = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="new", index=True)
    summary = Column(Text, nullable=True)
    cv_file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer", backref="recruitment_candidates")


class RecruitmentApplication(Base):
    __tablename__ = "recruitment_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(Integer, ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("recruitment_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), nullable=False, default="applied", index=True)
    score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    job_posting = relationship("RecruitmentJobPosting", backref="applications")
    candidate = relationship("RecruitmentCandidate", backref="applications")

    __table_args__ = (
        UniqueConstraint("job_posting_id", "candidate_id", name="uq_recruitment_job_candidate"),
    )


class TalentSkill(Base):
    __tablename__ = "talent_skills"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scale_max = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer", backref="talent_skills")

    __table_args__ = (
        UniqueConstraint("employer_id", "code", name="uq_talent_skill_code"),
    )


class TalentEmployeeSkill(Base):
    __tablename__ = "talent_employee_skills"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("talent_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(Integer, nullable=False, default=1)
    source = Column(String(100), nullable=False, default="manager")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    worker = relationship("Worker", backref="talent_skill_levels")
    skill = relationship("TalentSkill", backref="worker_levels")

    __table_args__ = (
        UniqueConstraint("worker_id", "skill_id", name="uq_talent_worker_skill"),
    )


class TalentTraining(Base):
    __tablename__ = "talent_trainings"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=True)
    duration_hours = Column(Float, nullable=False, default=0.0)
    mode = Column(String(100), nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    objectives = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer", backref="talent_trainings")


class TalentTrainingSession(Base):
    __tablename__ = "talent_training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("talent_trainings.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    site = Column(String(255), nullable=True)
    trainer = Column(String(255), nullable=True)
    capacity = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="planned", index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    training = relationship("TalentTraining", backref="sessions")


class SstIncident(Base):
    __tablename__ = "sst_incidents"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    incident_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False, default="medium", index=True)
    status = Column(String(50), nullable=False, default="open", index=True)
    occurred_at = Column(DateTime, nullable=False, default=utcnow)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=True)
    witnesses = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer", backref="sst_incidents")
    worker = relationship("Worker", backref="sst_incidents")


class RecruitmentLibraryItem(Base):
    __tablename__ = "recruitment_library_items"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    normalized_key = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer", backref="recruitment_library_items")

    __table_args__ = (
        UniqueConstraint("employer_id", "category", "normalized_key", name="uq_recruitment_library_scope_key"),
    )


class RecruitmentJobProfile(Base):
    __tablename__ = "recruitment_job_profiles"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(
        Integer,
        ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    manager_title = Column(String(255), nullable=True)
    mission_summary = Column(Text, nullable=True)
    main_activities_json = Column(Text, nullable=False, default="[]")
    technical_skills_json = Column(Text, nullable=False, default="[]")
    behavioral_skills_json = Column(Text, nullable=False, default="[]")
    education_level = Column(String(255), nullable=True)
    experience_required = Column(String(255), nullable=True)
    languages_json = Column(Text, nullable=False, default="[]")
    tools_json = Column(Text, nullable=False, default="[]")
    certifications_json = Column(Text, nullable=False, default="[]")
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    working_hours = Column(String(255), nullable=True)
    working_days_json = Column(Text, nullable=False, default="[]")
    benefits_json = Column(Text, nullable=False, default="[]")
    desired_start_date = Column(Date, nullable=True)
    application_deadline = Column(Date, nullable=True)
    publication_channels_json = Column(Text, nullable=False, default="[]")
    classification = Column(String(255), nullable=True)
    workflow_status = Column(String(50), nullable=False, default="draft", index=True)
    validation_comment = Column(Text, nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    assistant_source_json = Column(Text, nullable=False, default="{}")
    interview_criteria_json = Column(Text, nullable=False, default="[]")
    announcement_title = Column(String(255), nullable=True)
    announcement_body = Column(Text, nullable=True)
    announcement_status = Column(String(50), nullable=False, default="draft", index=True)
    announcement_slug = Column(String(255), nullable=True)
    announcement_share_pack_json = Column(Text, nullable=False, default="{}")
    submission_attachments_json = Column(Text, nullable=False, default="[]")
    workforce_job_profile_id = Column(Integer, ForeignKey("workforce_job_profiles.id"), nullable=True, index=True)
    contract_guidance_json = Column(Text, nullable=False, default="{}")
    publication_mode = Column(String(50), nullable=True)
    publication_url = Column(String(500), nullable=True)
    submitted_to_inspection_at = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    job_posting = relationship("RecruitmentJobPosting", backref="job_profile")
    validated_by = relationship("AppUser")
    workforce_job_profile = relationship("WorkforceJobProfile")


class RecruitmentPublicationChannel(Base):
    __tablename__ = "recruitment_publication_channels"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_type = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    config_json = Column(Text, nullable=False, default="{}")
    default_publish = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer", backref="recruitment_publication_channels")

    __table_args__ = (
        UniqueConstraint("company_id", "channel_type", name="uq_recruitment_publication_channel_company_type"),
    )


class RecruitmentPublicationLog(Base):
    __tablename__ = "recruitment_publication_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    message = Column(Text, nullable=True)
    details_json = Column(Text, nullable=False, default="{}")
    triggered_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)

    job_posting = relationship("RecruitmentJobPosting", backref="publication_logs")
    triggered_by = relationship("AppUser")


class RecruitmentCandidateAsset(Base):
    __tablename__ = "recruitment_candidate_assets"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("recruitment_candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    resume_original_name = Column(String(255), nullable=True)
    resume_storage_path = Column(String(500), nullable=True)
    attachments_json = Column(Text, nullable=False, default="[]")
    raw_extract_text = Column(Text, nullable=True)
    parsed_profile_json = Column(Text, nullable=False, default="{}")
    parsing_status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    candidate = relationship("RecruitmentCandidate", backref="candidate_asset")


class RecruitmentInterview(Base):
    __tablename__ = "recruitment_interviews"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(
        Integer,
        ForeignKey("recruitment_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number = Column(Integer, nullable=False, default=1)
    round_label = Column(String(100), nullable=False, default="Tour 1")
    interview_type = Column(String(100), nullable=False, default="entretien")
    scheduled_at = Column(DateTime, nullable=True, index=True)
    interviewer_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    interviewer_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="scheduled", index=True)
    score_total = Column(Float, nullable=True)
    scorecard_json = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=True)
    recommendation = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    application = relationship("RecruitmentApplication", backref="interviews")
    interviewer = relationship("AppUser")


class RecruitmentDecision(Base):
    __tablename__ = "recruitment_decisions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(
        Integer,
        ForeignKey("recruitment_applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    shortlist_rank = Column(Integer, nullable=True, index=True)
    decision_status = Column(String(50), nullable=False, default="pending", index=True)
    decision_comment = Column(Text, nullable=True)
    decided_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    converted_worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    contract_draft_id = Column(Integer, ForeignKey("custom_contracts.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    application = relationship("RecruitmentApplication", backref="decision")
    decided_by = relationship("AppUser")
    converted_worker = relationship("Worker")
    contract_draft = relationship("CustomContract")


class RecruitmentActivity(Base):
    __tablename__ = "recruitment_activities"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    job_posting_id = Column(Integer, ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"), nullable=True, index=True)
    candidate_id = Column(Integer, ForeignKey("recruitment_candidates.id", ondelete="CASCADE"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("recruitment_applications.id", ondelete="CASCADE"), nullable=True, index=True)
    interview_id = Column(Integer, ForeignKey("recruitment_interviews.id", ondelete="CASCADE"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    visibility = Column(String(50), nullable=False, default="internal", index=True)
    message = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    job_posting = relationship("RecruitmentJobPosting")
    candidate = relationship("RecruitmentCandidate")
    application = relationship("RecruitmentApplication")
    interview = relationship("RecruitmentInterview")
    actor = relationship("AppUser")


class ContractVersion(Base):
    __tablename__ = "contract_versions"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("custom_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    source_module = Column(String(50), nullable=False, default="contracts", index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    effective_date = Column(Date, nullable=True)
    salary_amount = Column(Float, nullable=True)
    classification_index = Column(String(100), nullable=True)
    snapshot_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("contract_id", "version_number", name="uq_contract_versions_contract_version"),
    )

    contract = relationship("CustomContract", backref="versions")
    worker = relationship("Worker")
    employer = relationship("Employer")
    created_by = relationship("AppUser")


class ComplianceReview(Base):
    __tablename__ = "compliance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("custom_contracts.id"), nullable=True, index=True)
    contract_version_id = Column(Integer, ForeignKey("contract_versions.id"), nullable=True, index=True)
    review_type = Column(String(50), nullable=False, default="contract_control", index=True)
    review_stage = Column(String(50), nullable=False, default="pre_signature", index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    source_module = Column(String(50), nullable=False, default="contracts", index=True)
    checklist_json = Column(Text, nullable=False, default="[]")
    observations_json = Column(Text, nullable=False, default="[]")
    requested_documents_json = Column(Text, nullable=False, default="[]")
    tags_json = Column(Text, nullable=False, default="[]")
    due_at = Column(DateTime, nullable=True, index=True)
    submitted_to_inspector_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    worker = relationship("Worker")
    contract = relationship("CustomContract")
    contract_version = relationship("ContractVersion")
    reviewed_by = relationship("AppUser", foreign_keys=[reviewed_by_user_id])
    created_by = relationship("AppUser", foreign_keys=[created_by_user_id])


class InspectorObservation(Base):
    __tablename__ = "inspector_observations"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("compliance_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    visibility = Column(String(50), nullable=False, default="restricted", index=True)
    observation_type = Column(String(50), nullable=False, default="general", index=True)
    status_marker = Column(String(50), nullable=False, default="observation", index=True)
    message = Column(Text, nullable=False)
    structured_payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    review = relationship("ComplianceReview", backref="inspector_observations")
    employer = relationship("Employer")
    author = relationship("AppUser")


class ComplianceVisit(Base):
    __tablename__ = "compliance_visits"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    review_id = Column(Integer, ForeignKey("compliance_reviews.id"), nullable=True, index=True)
    visit_type = Column(String(50), nullable=False, default="inspection", index=True)
    status = Column(String(50), nullable=False, default="scheduled", index=True)
    inspector_name = Column(String(255), nullable=True)
    scheduled_at = Column(DateTime, nullable=True, index=True)
    occurred_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    attachments_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    review = relationship("ComplianceReview", backref="visits")


class EmployerRegisterEntry(Base):
    __tablename__ = "employer_register_entries"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("custom_contracts.id"), nullable=True, index=True)
    contract_version_id = Column(Integer, ForeignKey("contract_versions.id"), nullable=True, index=True)
    entry_type = Column(String(50), nullable=False, default="employer_register", index=True)
    registry_label = Column(String(255), nullable=False, default="Registre employeur")
    status = Column(String(50), nullable=False, default="active", index=True)
    effective_date = Column(Date, nullable=True, index=True)
    archived_at = Column(DateTime, nullable=True)
    details_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    contract = relationship("CustomContract")
    contract_version = relationship("ContractVersion")

    __table_args__ = (
        UniqueConstraint("employer_id", "entry_type", "worker_id", "contract_id", name="uq_employer_register_entry_scope"),
    )


class ExportTemplate(Base):
    __tablename__ = "export_templates"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    type_document = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False, default="1.0")
    format = Column(String(20), nullable=False, default="xlsx")
    mapping_json = Column(Text, nullable=False, default="{}")
    options_json = Column(Text, nullable=False, default="{}")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ReportingSnapshot(Base):
    __tablename__ = "reporting_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    snapshot_type = Column(String(100), nullable=False, index=True)
    start_period = Column(String(7), nullable=False, index=True)
    end_period = Column(String(7), nullable=False, index=True)
    source_hash = Column(String(128), nullable=True)
    data_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    created_by = relationship("AppUser")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("export_templates.id"), nullable=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("reporting_snapshots.id"), nullable=True, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    document_type = Column(String(100), nullable=False, index=True)
    start_period = Column(String(7), nullable=False, index=True)
    end_period = Column(String(7), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    file_path = Column(String(500), nullable=True)
    checksum = Column(String(128), nullable=True)
    logs_json = Column(Text, nullable=False, default="[]")
    errors_json = Column(Text, nullable=False, default="[]")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    template = relationship("ExportTemplate")
    snapshot = relationship("ReportingSnapshot")
    requested_by = relationship("AppUser")


class StatutoryDeclaration(Base):
    __tablename__ = "statutory_declarations"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    export_job_id = Column(Integer, ForeignKey("export_jobs.id"), nullable=True, index=True)
    channel = Column(String(50), nullable=False, index=True)
    period_label = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="generated", index=True)
    reference_number = Column(String(255), nullable=True)
    receipt_path = Column(String(500), nullable=True)
    totals_json = Column(Text, nullable=False, default="{}")
    metadata_json = Column(Text, nullable=False, default="{}")
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    export_job = relationship("ExportJob", backref="declarations")


class EmployeePortalRequest(Base):
    __tablename__ = "employee_portal_requests"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    assigned_to_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    request_type = Column(String(50), nullable=False, index=True)
    destination = Column(String(50), nullable=False, default="rh", index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="submitted", index=True)
    priority = Column(String(20), nullable=False, default="normal", index=True)
    confidentiality = Column(String(50), nullable=False, default="standard", index=True)
    case_number = Column(String(100), nullable=True, unique=True, index=True)
    attachments_json = Column(Text, nullable=False, default="[]")
    history_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    worker = relationship("Worker")
    created_by = relationship("AppUser", foreign_keys=[created_by_user_id])
    assigned_to = relationship("AppUser", foreign_keys=[assigned_to_user_id])

    __table_args__ = (
        Index("ix_employee_portal_requests_queue", "employer_id", "destination", "status", "priority"),
    )


class InspectorCase(Base):
    __tablename__ = "inspector_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(100), nullable=False, unique=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("custom_contracts.id"), nullable=True, index=True)
    portal_request_id = Column(Integer, ForeignKey("employee_portal_requests.id"), nullable=True, index=True)
    filed_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    assigned_inspector_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    case_type = Column(String(50), nullable=False, default="general_claim", index=True)
    sub_type = Column(String(100), nullable=True, index=True)
    source_party = Column(String(50), nullable=False, default="employee", index=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="received", index=True)
    confidentiality = Column(String(50), nullable=False, default="standard", index=True)
    amicable_attempt_status = Column(String(50), nullable=False, default="not_started", index=True)
    current_stage = Column(String(50), nullable=False, default="filing", index=True)
    receipt_reference = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    district = Column(String(255), nullable=True, index=True)
    urgency = Column(String(50), nullable=False, default="normal", index=True)
    outcome_summary = Column(Text, nullable=True)
    resolution_type = Column(String(100), nullable=True, index=True)
    due_at = Column(DateTime, nullable=True, index=True)
    received_at = Column(DateTime, nullable=True, index=True)
    is_sensitive = Column(Boolean, nullable=False, default=False, index=True)
    attachments_json = Column(Text, nullable=False, default="[]")
    tags_json = Column(Text, nullable=False, default="[]")
    last_response_at = Column(DateTime, nullable=True, index=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    worker = relationship("Worker")
    contract = relationship("CustomContract")
    portal_request = relationship("EmployeePortalRequest", backref="inspector_case")
    filed_by = relationship("AppUser", foreign_keys=[filed_by_user_id])
    assigned_inspector = relationship("AppUser", foreign_keys=[assigned_inspector_user_id])

    __table_args__ = (
        Index("ix_inspector_cases_queue", "employer_id", "status", "current_stage", "updated_at"),
    )


class InspectorMessage(Base):
    __tablename__ = "inspector_messages"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    sender_role = Column(String(50), nullable=False, default="employee", index=True)
    direction = Column(String(50), nullable=False, default="employee_to_inspector", index=True)
    message_type = Column(String(50), nullable=False, default="message", index=True)
    visibility = Column(String(50), nullable=False, default="case_parties", index=True)
    body = Column(Text, nullable=False)
    attachments_json = Column(Text, nullable=False, default="[]")
    status = Column(String(50), nullable=False, default="sent", index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    case = relationship("InspectorCase", backref="messages")
    employer = relationship("Employer")
    author = relationship("AppUser")

    __table_args__ = (
        Index("ix_inspector_messages_case_created", "case_id", "created_at"),
    )


class InspectorCaseAssignment(Base):
    __tablename__ = "inspector_case_assignments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    inspector_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    scope = Column(String(50), nullable=False, default="lead")
    status = Column(String(50), nullable=False, default="active", index=True)
    notes = Column(Text, nullable=True)
    assigned_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)

    case = relationship("InspectorCase", backref="assignments")
    inspector = relationship("AppUser", foreign_keys=[inspector_user_id])
    assigned_by = relationship("AppUser", foreign_keys=[assigned_by_user_id])

    __table_args__ = (
        UniqueConstraint("case_id", "inspector_user_id", name="uq_inspector_case_assignment"),
        Index("ix_inspector_case_assignments_scope", "inspector_user_id", "status", "assigned_at"),
    )


class InspectionDocument(Base):
    __tablename__ = "inspection_documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    document_type = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    visibility = Column(String(50), nullable=False, default="case_parties", index=True)
    confidentiality = Column(String(50), nullable=False, default="restricted", index=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    current_version_number = Column(Integer, nullable=False, default=0)
    tags_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    case = relationship("InspectorCase", backref="documents")
    employer = relationship("Employer")
    uploaded_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_inspection_documents_queue", "case_id", "status", "updated_at"),
    )


class InspectionDocumentVersion(Base):
    __tablename__ = "inspection_document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("inspection_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    static_url = Column(String(500), nullable=True)
    content_type = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    document = relationship("InspectionDocument", backref="versions")
    case = relationship("InspectorCase")
    employer = relationship("Employer")
    uploaded_by = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_inspection_document_version"),
        Index("ix_inspection_document_versions_case", "case_id", "created_at"),
    )


class InspectionDocumentAccessLog(Base):
    __tablename__ = "inspection_document_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("inspection_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("inspection_document_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False, default="view", index=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    document = relationship("InspectionDocument", backref="access_logs")
    version = relationship("InspectionDocumentVersion")
    case = relationship("InspectorCase")
    user = relationship("AppUser")

    __table_args__ = (
        Index("ix_inspection_document_access_logs_document", "document_id", "created_at"),
    )


class LabourCaseClaim(Base):
    __tablename__ = "labour_case_claims"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    claim_type = Column(String(100), nullable=False, index=True)
    claimant_party = Column(String(50), nullable=False, default="employee", index=True)
    factual_basis = Column(Text, nullable=False)
    amount_requested = Column(Numeric(14, 2), nullable=True)
    status = Column(String(50), nullable=False, default="submitted", index=True)
    conciliation_outcome = Column(String(100), nullable=True, index=True)
    inspector_observations = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    case = relationship("InspectorCase", backref="claims")
    employer = relationship("Employer")
    created_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_labour_case_claims_case_status", "case_id", "status", "claim_type"),
    )


class LabourCaseEvent(Base):
    __tablename__ = "labour_case_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="planned", index=True)
    scheduled_at = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    participants_json = Column(Text, nullable=False, default="[]")
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    case = relationship("InspectorCase", backref="events")
    employer = relationship("Employer")
    created_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_labour_case_events_case_schedule", "case_id", "event_type", "scheduled_at"),
    )


class LabourPV(Base):
    __tablename__ = "labour_pv"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    pv_number = Column(String(100), nullable=False, unique=True, index=True)
    pv_type = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="draft", index=True)
    version_number = Column(Integer, nullable=False, default=1)
    measures_to_execute = Column(Text, nullable=True)
    execution_deadline = Column(DateTime, nullable=True, index=True)
    delivered_to_parties_at = Column(DateTime, nullable=True, index=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    case = relationship("InspectorCase", backref="pv_records")
    employer = relationship("Employer")
    generated_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_labour_pv_case_type", "case_id", "pv_type", "status"),
    )


class LabourChatbotLog(Base):
    __tablename__ = "labour_chatbot_logs"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("inspector_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    role_context = Column(String(50), nullable=False, default="inspecteur", index=True)
    intent = Column(String(100), nullable=False, index=True)
    prompt_excerpt = Column(Text, nullable=True)
    response_json = Column(Text, nullable=False, default="{}")
    fallback_used = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

    case = relationship("InspectorCase", backref="chatbot_logs")
    employer = relationship("Employer")
    created_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_labour_chatbot_logs_case_role", "case_id", "role_context", "created_at"),
    )


class InternalMessageChannel(Base):
    __tablename__ = "internal_message_channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_code = Column(String(100), nullable=False, unique=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    channel_type = Column(String(50), nullable=False, default="group", index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    visibility = Column(String(50), nullable=False, default="internal", index=True)
    ack_required = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    created_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_internal_message_channels_queue", "employer_id", "status", "updated_at"),
    )


class InternalMessageChannelMember(Base):
    __tablename__ = "internal_message_channel_members"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("internal_message_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    member_role = Column(String(50), nullable=False, default="member", index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_read_at = Column(DateTime, nullable=True)
    joined_at = Column(DateTime, default=utcnow, nullable=False)

    channel = relationship("InternalMessageChannel", backref="members")
    user = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("channel_id", "user_id", name="uq_internal_message_channel_member"),
        Index("ix_internal_message_channel_members_user", "user_id", "is_active", "joined_at"),
    )


class InternalMessage(Base):
    __tablename__ = "internal_messages"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("internal_message_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    message_type = Column(String(50), nullable=False, default="message", index=True)
    body = Column(Text, nullable=False)
    attachments_json = Column(Text, nullable=False, default="[]")
    status = Column(String(50), nullable=False, default="sent", index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    channel = relationship("InternalMessageChannel", backref="messages")
    employer = relationship("Employer")
    author = relationship("AppUser")

    __table_args__ = (
        Index("ix_internal_messages_channel_created", "channel_id", "created_at"),
    )


class InternalMessageReceipt(Base):
    __tablename__ = "internal_message_receipts"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("internal_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="read", index=True)
    read_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    message = relationship("InternalMessage", backref="receipts")
    user = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_internal_message_receipt"),
        Index("ix_internal_message_receipts_user", "user_id", "status", "updated_at"),
    )


class InternalNotice(Base):
    __tablename__ = "internal_notices"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    notice_type = Column(String(50), nullable=False, default="service_note", index=True)
    audience_role = Column(String(50), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="published", index=True)
    ack_required = Column(Boolean, nullable=False, default=False)
    attachments_json = Column(Text, nullable=False, default="[]")
    published_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    created_by = relationship("AppUser")

    __table_args__ = (
        Index("ix_internal_notices_queue", "employer_id", "status", "published_at"),
    )


class InternalNoticeAcknowledgement(Base):
    __tablename__ = "internal_notice_acknowledgements"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(Integer, ForeignKey("internal_notices.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="acknowledged", index=True)
    acknowledged_at = Column(DateTime, nullable=False, default=utcnow)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    notice = relationship("InternalNotice", backref="acknowledgements")
    user = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("notice_id", "user_id", name="uq_internal_notice_acknowledgement"),
        Index("ix_internal_notice_acknowledgements_user", "user_id", "acknowledged_at"),
    )


class WorkforceJobProfile(Base):
    __tablename__ = "workforce_job_profiles"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(255), nullable=True, index=True)
    category_prof = Column(String(255), nullable=True)
    classification_index = Column(String(100), nullable=True)
    criticality = Column(String(50), nullable=False, default="medium", index=True)
    target_headcount = Column(Integer, nullable=True)
    required_skills_json = Column(Text, nullable=False, default="[]")
    mobility_paths_json = Column(Text, nullable=False, default="[]")
    succession_candidates_json = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")

    __table_args__ = (
        UniqueConstraint("employer_id", "title", "department", name="uq_workforce_job_profiles_title_department"),
    )


class PerformanceCycle(Base):
    __tablename__ = "performance_cycles"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cycle_type = Column(String(50), nullable=False, default="annual", index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    objectives_json = Column(Text, nullable=False, default="[]")
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    created_by = relationship("AppUser")


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("performance_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    reviewer_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    manager_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    overall_score = Column(Float, nullable=True)
    self_assessment = Column(Text, nullable=True)
    manager_comment = Column(Text, nullable=True)
    hr_comment = Column(Text, nullable=True)
    objectives_json = Column(Text, nullable=False, default="[]")
    competencies_json = Column(Text, nullable=False, default="[]")
    development_actions_json = Column(Text, nullable=False, default="[]")
    promotion_recommendation = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    cycle = relationship("PerformanceCycle", backref="reviews")
    employer = relationship("Employer")
    worker = relationship("Worker")
    reviewer = relationship("AppUser", foreign_keys=[reviewer_user_id])
    manager = relationship("AppUser", foreign_keys=[manager_user_id])

    __table_args__ = (
        UniqueConstraint("cycle_id", "worker_id", name="uq_performance_review_cycle_worker"),
        Index("ix_performance_reviews_queue", "employer_id", "status", "updated_at"),
    )


class WorkforcePlanning(Base):
    __tablename__ = "workforce_planning"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    job_profile_id = Column(Integer, ForeignKey("workforce_job_profiles.id"), nullable=True, index=True)
    planning_year = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    current_headcount = Column(Integer, nullable=False, default=0)
    target_headcount = Column(Integer, nullable=False, default=0)
    recruitment_need = Column(Integer, nullable=False, default=0)
    mobility_need = Column(Integer, nullable=False, default=0)
    criticality = Column(String(50), nullable=False, default="medium", index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    assumptions_json = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    job_profile = relationship("WorkforceJobProfile")


class TrainingNeed(Base):
    __tablename__ = "training_needs"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    review_id = Column(Integer, ForeignKey("performance_reviews.id"), nullable=True, index=True)
    job_profile_id = Column(Integer, ForeignKey("workforce_job_profiles.id"), nullable=True, index=True)
    source = Column(String(50), nullable=False, default="gpec", index=True)
    priority = Column(String(20), nullable=False, default="medium", index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_skill = Column(String(255), nullable=True)
    gap_level = Column(Integer, nullable=True)
    recommended_training_id = Column(Integer, ForeignKey("talent_trainings.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="identified", index=True)
    due_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    review = relationship("PerformanceReview")
    job_profile = relationship("WorkforceJobProfile")
    recommended_training = relationship("TalentTraining")


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    plan_year = Column(Integer, nullable=False, index=True)
    budget_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="draft", index=True)
    objectives_json = Column(Text, nullable=False, default="[]")
    fmfp_tracking_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    created_by = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("employer_id", "name", "plan_year", name="uq_training_plan_name_year"),
    )


class TrainingPlanItem(Base):
    __tablename__ = "training_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    training_plan_id = Column(Integer, ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    need_id = Column(Integer, ForeignKey("training_needs.id"), nullable=True, index=True)
    training_id = Column(Integer, ForeignKey("talent_trainings.id"), nullable=True, index=True)
    training_session_id = Column(Integer, ForeignKey("talent_training_sessions.id"), nullable=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="planned", index=True)
    estimated_cost = Column(Float, nullable=False, default=0.0)
    funding_source = Column(String(100), nullable=True)
    fmfp_eligible = Column(Boolean, nullable=False, default=False, index=True)
    scheduled_start = Column(Date, nullable=True)
    scheduled_end = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    training_plan = relationship("TrainingPlan", backref="items")
    need = relationship("TrainingNeed")
    training = relationship("TalentTraining")
    training_session = relationship("TalentTrainingSession")
    worker = relationship("Worker")


class TrainingEvaluation(Base):
    __tablename__ = "training_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    training_session_id = Column(Integer, ForeignKey("talent_training_sessions.id"), nullable=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    evaluation_type = Column(String(50), nullable=False, default="hot", index=True)
    score = Column(Float, nullable=True)
    impact_level = Column(String(50), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    training_session = relationship("TalentTrainingSession")
    worker = relationship("Worker")


class DisciplinaryCase(Base):
    __tablename__ = "disciplinary_cases"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    inspection_case_id = Column(Integer, ForeignKey("inspector_cases.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    case_type = Column(String(50), nullable=False, default="warning", index=True)
    severity = Column(String(50), nullable=False, default="medium", index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    happened_at = Column(DateTime, nullable=True)
    hearing_at = Column(DateTime, nullable=True)
    defense_notes = Column(Text, nullable=True)
    sanction_type = Column(String(100), nullable=True)
    monetary_sanction_flag = Column(Boolean, nullable=False, default=False)
    documents_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    inspection_case = relationship("InspectorCase")
    created_by = relationship("AppUser")


class TerminationWorkflow(Base):
    __tablename__ = "termination_workflows"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("custom_contracts.id"), nullable=True, index=True)
    inspection_case_id = Column(Integer, ForeignKey("inspector_cases.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    validated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    termination_type = Column(String(50), nullable=False, default="resignation", index=True)
    motif = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="draft", index=True)
    effective_date = Column(Date, nullable=True, index=True)
    notification_sent_at = Column(DateTime, nullable=True, index=True)
    notification_received_at = Column(DateTime, nullable=True, index=True)
    pre_hearing_notice_sent_at = Column(DateTime, nullable=True, index=True)
    pre_hearing_scheduled_at = Column(DateTime, nullable=True, index=True)
    preavis_start_date = Column(Date, nullable=True, index=True)
    economic_consultation_started_at = Column(Date, nullable=True, index=True)
    economic_inspection_referral_at = Column(Date, nullable=True, index=True)
    technical_layoff_declared_at = Column(Date, nullable=True, index=True)
    technical_layoff_end_at = Column(Date, nullable=True, index=True)
    sensitive_case = Column(Boolean, nullable=False, default=False, index=True)
    handover_required = Column(Boolean, nullable=False, default=False, index=True)
    inspection_required = Column(Boolean, nullable=False, default=False, index=True)
    legal_risk_level = Column(String(50), nullable=False, default="normal", index=True)
    checklist_json = Column(Text, nullable=False, default="[]")
    documents_json = Column(Text, nullable=False, default="[]")
    legal_metadata_json = Column(Text, nullable=False, default="{}")
    readonly_stc_json = Column(Text, nullable=False, default="{}")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    contract = relationship("CustomContract")
    inspection_case = relationship("InspectorCase")
    created_by = relationship("AppUser", foreign_keys=[created_by_user_id])
    validated_by = relationship("AppUser", foreign_keys=[validated_by_user_id])


class DuerEntry(Base):
    __tablename__ = "duer_entries"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    site_name = Column(String(255), nullable=False, index=True)
    risk_family = Column(String(255), nullable=False, index=True)
    hazard = Column(String(255), nullable=False)
    exposure_population = Column(String(255), nullable=True)
    probability = Column(Integer, nullable=False, default=1)
    severity = Column(Integer, nullable=False, default=1)
    existing_controls = Column(Text, nullable=True)
    residual_risk = Column(Integer, nullable=True)
    owner_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="open", index=True)
    last_reviewed_at = Column(Date, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")


class PreventionAction(Base):
    __tablename__ = "prevention_actions"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    duer_entry_id = Column(Integer, ForeignKey("duer_entries.id"), nullable=True, index=True)
    action_title = Column(String(255), nullable=False)
    action_type = Column(String(50), nullable=False, default="pap", index=True)
    owner_name = Column(String(255), nullable=True)
    due_date = Column(Date, nullable=True, index=True)
    status = Column(String(50), nullable=False, default="planned", index=True)
    measure_details = Column(Text, nullable=True)
    inspection_follow_up = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    duer_entry = relationship("DuerEntry", backref="actions")


class EmployeeMasterRecord(Base):
    __tablename__ = "employee_master_records"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    recruitment_candidate_id = Column(Integer, ForeignKey("recruitment_candidates.id"), nullable=True, index=True)
    recruitment_application_id = Column(Integer, ForeignKey("recruitment_applications.id"), nullable=True, index=True)
    recruitment_decision_id = Column(Integer, ForeignKey("recruitment_decisions.id"), nullable=True, index=True)
    first_name = Column(String(120), nullable=True)
    last_name = Column(String(120), nullable=True)
    full_name = Column(String(255), nullable=True, index=True)
    sex = Column(String(20), nullable=True)
    marital_status = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True, index=True)
    birth_place = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    cin_number = Column(String(255), nullable=True)
    cin_issued_at = Column(Date, nullable=True)
    cin_issued_place = Column(String(255), nullable=True)
    cnaps_number = Column(String(255), nullable=True)
    employee_number = Column(String(100), nullable=True, index=True)
    source_status = Column(String(50), nullable=False, default="synced", index=True)
    canonical_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    recruitment_candidate = relationship("RecruitmentCandidate")
    recruitment_application = relationship("RecruitmentApplication")
    recruitment_decision = relationship("RecruitmentDecision")


class EmploymentMasterRecord(Base):
    __tablename__ = "employment_master_records"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    recruitment_job_posting_id = Column(Integer, ForeignKey("recruitment_job_postings.id"), nullable=True, index=True)
    recruitment_job_profile_id = Column(Integer, ForeignKey("recruitment_job_profiles.id"), nullable=True, index=True)
    workforce_job_profile_id = Column(Integer, ForeignKey("workforce_job_profiles.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("custom_contracts.id"), nullable=True, index=True)
    contract_version_id = Column(Integer, ForeignKey("contract_versions.id"), nullable=True, index=True)
    contract_type = Column(String(100), nullable=True, index=True)
    employment_status = Column(String(50), nullable=False, default="active", index=True)
    hire_date = Column(Date, nullable=True, index=True)
    exit_date = Column(Date, nullable=True, index=True)
    trial_period_days = Column(Integer, nullable=True)
    trial_end_date = Column(Date, nullable=True)
    job_title = Column(String(255), nullable=True, index=True)
    professional_category = Column(String(255), nullable=True)
    classification_index = Column(String(100), nullable=True)
    work_location = Column(String(255), nullable=True)
    source_status = Column(String(50), nullable=False, default="synced", index=True)
    canonical_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    recruitment_job_posting = relationship("RecruitmentJobPosting")
    recruitment_job_profile = relationship("RecruitmentJobProfile")
    workforce_job_profile = relationship("WorkforceJobProfile")
    contract = relationship("CustomContract")
    contract_version = relationship("ContractVersion")


class CompensationMasterRecord(Base):
    __tablename__ = "compensation_master_records"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    contract_version_id = Column(Integer, ForeignKey("contract_versions.id"), nullable=True, index=True)
    validated_salary_amount = Column(Float, nullable=True)
    salary_base = Column(Float, nullable=True)
    hourly_rate = Column(Float, nullable=True)
    vhm = Column(Float, nullable=True)
    weekly_hours = Column(Float, nullable=True)
    payment_mode = Column(String(100), nullable=True)
    bank_name = Column(String(255), nullable=True)
    rib = Column(String(255), nullable=True)
    bic = Column(String(255), nullable=True)
    benefits_json = Column(Text, nullable=False, default="{}")
    source_status = Column(String(50), nullable=False, default="synced", index=True)
    canonical_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    contract_version = relationship("ContractVersion")


class OrganizationAssignmentRecord(Base):
    __tablename__ = "organization_assignment_records"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    organizational_unit_id = Column(Integer, ForeignKey("organizational_units.id"), nullable=True, index=True)
    establishment = Column(String(255), nullable=True, index=True)
    department = Column(String(255), nullable=True, index=True)
    service = Column(String(255), nullable=True, index=True)
    unit = Column(String(255), nullable=True, index=True)
    position_title = Column(String(255), nullable=True, index=True)
    effective_from = Column(Date, nullable=True)
    source_status = Column(String(50), nullable=False, default="synced", index=True)
    canonical_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    organizational_unit = relationship("OrganizationalUnit")


class HrEmployeeFile(Base):
    __tablename__ = "hr_employee_files"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    manual_sections_json = Column(Text, nullable=False, default="{}")
    checklist_overrides_json = Column(Text, nullable=False, default="{}")
    revision_number = Column(Integer, nullable=False, default=1)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    updated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    created_by = relationship("AppUser", foreign_keys=[created_by_user_id])
    updated_by = relationship("AppUser", foreign_keys=[updated_by_user_id])


class HrEmployeeDocument(Base):
    __tablename__ = "hr_employee_documents"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    hr_file_id = Column(Integer, ForeignKey("hr_employee_files.id", ondelete="CASCADE"), nullable=True, index=True)
    section_code = Column(String(80), nullable=False, default="documents", index=True)
    document_type = Column(String(80), nullable=False, default="other", index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    source_module = Column(String(50), nullable=False, default="hr_dossier", index=True)
    source_record_type = Column(String(80), nullable=True, index=True)
    source_record_id = Column(Integer, nullable=True, index=True)
    document_date = Column(Date, nullable=True, index=True)
    expiration_date = Column(Date, nullable=True, index=True)
    comment = Column(Text, nullable=True)
    visibility_scope = Column(String(50), nullable=False, default="hr_only", index=True)
    visible_to_employee = Column(Boolean, nullable=False, default=False, index=True)
    visible_to_manager = Column(Boolean, nullable=False, default=False, index=True)
    visible_to_payroll = Column(Boolean, nullable=False, default=False, index=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    current_version_number = Column(Integer, nullable=False, default=1)
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    updated_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    hr_file = relationship("HrEmployeeFile", backref="documents")
    created_by = relationship("AppUser", foreign_keys=[created_by_user_id])
    updated_by = relationship("AppUser", foreign_keys=[updated_by_user_id])

    __table_args__ = (
        Index("ix_hr_employee_documents_scope", "employer_id", "worker_id", "document_type"),
    )


class HrEmployeeDocumentVersion(Base):
    __tablename__ = "hr_employee_document_versions"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("hr_employee_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    storage_path = Column(String(500), nullable=False)
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(128), nullable=True, index=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    document = relationship("HrEmployeeDocument", backref="versions")
    created_by = relationship("AppUser")

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_hr_employee_document_version"),
    )


class HrEmployeeEvent(Base):
    __tablename__ = "hr_employee_events"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    hr_file_id = Column(Integer, ForeignKey("hr_employee_files.id", ondelete="CASCADE"), nullable=True, index=True)
    section_code = Column(String(80), nullable=False, default="general", index=True)
    event_type = Column(String(80), nullable=False, default="manual_update", index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="recorded", index=True)
    event_date = Column(DateTime, nullable=False, default=utcnow, index=True)
    source_module = Column(String(50), nullable=False, default="hr_dossier", index=True)
    source_record_type = Column(String(80), nullable=True, index=True)
    source_record_id = Column(Integer, nullable=True, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")
    hr_file = relationship("HrEmployeeFile", backref="events")
    created_by = relationship("AppUser")



