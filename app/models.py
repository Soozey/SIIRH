from sqlalchemy import Column, Integer, String, Text, Time, Float, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .config.config import Base
from datetime import datetime, date, time


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
    plafond_cnaps_base = Column(Float, default=0.0)
    taux_pat_fmfp = Column(Float, default=1.0)
    taux_sal_smie = Column(Float, default=0.0)
    smie_forfait_sal = Column(Float, default=0.0)
    smie_forfait_pat = Column(Float, default=0.0)
    
    
    # 🔹 RELATION avec TypeRegime (N:1)
    type_regime_id = Column(Integer, ForeignKey("type_regimes.id", ondelete="SET NULL"), nullable=True)
    type_regime = relationship("TypeRegime", back_populates="employers")
    #TypeRegime.employers = relationship("Employer", back_populates="type_regime")

    workers = relationship("Worker", back_populates="employer")


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
    date_embauche = Column(Date)
    nature_contrat = Column(String)   # CDI / CDD
    duree_essai_jours = Column(Integer, default=0)
    mode_paiement = Column(String)    # banque | espece | ...
    rib = Column(String)
    banque = Column(String)
    bic = Column(String)
    cnaps_num = Column(String)
    smie_agence = Column(String)
    smie_carte_num = Column(String)
    etablissement = Column(String)
    departement = Column(String)
    service = Column(String)
    poste = Column(String)
    categorie_prof = Column(String)
    indice = Column(String)
    valeur_point = Column(Float)
    groupe_preavis = Column(Integer)  # 1..5
    type_sortie = Column(String)      # L/D
    jours_preavis_deja_faits = Column(Integer, default=0)
    anciennete_jours = Column(Integer, default=0)
    secteur = Column(String)          # agricole / non_agricole
    salaire_base = Column(Float, default=0.0)
    salaire_horaire = Column(Float, default=0.0)
    vhm = Column(Float, default=0.0)              # 173.33 ou 200
    horaire_hebdo = Column(Float, default=0.0)    # 40 ou 46

    employer = relationship("Employer", back_populates="workers")
    variables = relationship("PayVar", back_populates="worker")
    absences = relationship("Absence", back_populates="worker")

class PayVar(Base):
    __tablename__ = "payvars"

    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    period = Column(String, index=True)  # format AAAA-MM
    # congés / absences / HS / primes / avantages / avances
    conge_pris_j = Column(Float, default=0.0)
    conge_restant_j = Column(Float, default=0.0)
    conge_valeur = Column(Float, default=0.0)
    abs_maladie_j = Column(Float, default=0.0)
    abs_non_remu_h = Column(Float, default=0.0)
    abs_non_remu_j = Column(Float, default=0.0)
    mise_a_pied_j = Column(Float, default=0.0)
    # HS
    hsni_130_h = Column(Float, default=0.0)
    hsi_130_h  = Column(Float, default=0.0)
    hsni_150_h = Column(Float, default=0.0)
    hsi_150_h  = Column(Float, default=0.0)
    # majorations
    dimanche_h = Column(Float, default=0.0)
    nuit_hab_h = Column(Float, default=0.0)
    nuit_occ_h = Column(Float, default=0.0)
    ferie_jour_h = Column(Float, default=0.0)
    # primes
    prime1 = Column(Float, default=0.0)
    prime2 = Column(Float, default=0.0)
    # ... prime10
    avantage_logement = Column(Float, default=0.0)
    avantage_vehicule = Column(Float, default=0.0)
    avantage_telephone = Column(Float, default=0.0)
    avantage_autres = Column(Float, default=0.0)
    avance_quinzaine = Column(Float, default=0.0)
    avance_speciale_total = Column(Float, default=0.0)
    avance_speciale_rembfixe = Column(Float, default=0.0)
    avance_speciale_restant_prec = Column(Float, default=0.0)
    autre_ded1 = Column(Float, default=0.0)
    autre_ded2 = Column(Float, default=0.0)
    autre_ded3 = Column(Float, default=0.0)
    autre_ded4 = Column(Float, default=0.0)
    alloc_familiale = Column(Float, default=0.0)

    worker = relationship("Worker", back_populates="variables")


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
        