from sqlalchemy import Column, Integer, String, Text, Time, Float, Date, DateTime, Boolean, ForeignKey, func, Index, CheckConstraint
from sqlalchemy.orm import relationship
from .config.config import Base
from datetime import datetime, date, time
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

    employer = relationship("Employer", back_populates="primes")
    
    # Liens
    worker_links = relationship("WorkerPrimeLink", back_populates="prime", cascade="all, delete-orphan")


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
    
    worker = relationship("Worker", back_populates="prime_links")
    prime = relationship("Prime", back_populates="worker_links")

    __table_args__ = (
        UniqueConstraint('worker_id', 'prime_id', name='uq_worker_prime_link'),
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
    created_at_HS = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at_HS = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relation avec les lignes journalières HS
    jours_HS = relationship(
        "HSJourHS",
        back_populates="calculation_HS",
        cascade="all, delete-orphan",
    )

    worker = relationship("Worker", back_populates="hs_calculations")

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

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
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

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
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


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role_code = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employer = relationship("Employer")
    worker = relationship("Worker")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    actor = relationship("AppUser")


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("request_type", "request_id", name="uq_request_workflow_request"),
        CheckConstraint(
            "request_type IN ('leave', 'permission')",
            name="chk_request_workflow_type"
        ),
    )

    manager_actor = relationship("AppUser", foreign_keys=[manager_actor_user_id])
    rh_actor = relationship("AppUser", foreign_keys=[rh_actor_user_id])


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employer = relationship("Employer", backref="recruitment_candidates")


class RecruitmentApplication(Base):
    __tablename__ = "recruitment_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(Integer, ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("recruitment_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), nullable=False, default="applied", index=True)
    score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    training = relationship("TalentTraining", backref="sessions")


class SstIncident(Base):
    __tablename__ = "sst_incidents"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True, index=True)
    incident_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False, default="medium", index=True)
    status = Column(String(50), nullable=False, default="open", index=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=True)
    witnesses = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    job_posting = relationship("RecruitmentJobPosting", backref="job_profile")
    validated_by = relationship("AppUser")


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    employer = relationship("Employer")
    job_posting = relationship("RecruitmentJobPosting")
    candidate = relationship("RecruitmentCandidate")
    application = relationship("RecruitmentApplication")
    interview = relationship("RecruitmentInterview")
    actor = relationship("AppUser")
