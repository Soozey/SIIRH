"""
Constantes métier relatives aux travailleurs, employeurs et contrats
"""
from typing import Dict, List, Any

# Types de contrats
CONTRACT_TYPES = {
    "CDI": {
        "label": "Contrat à Durée Indéterminée",
        "code": "CDI",
        "duree_essai_max": 90,  # jours
        "preavis_demission": True,
        "preavis_licenciement": True
    },
    "CDD": {
        "label": "Contrat à Durée Déterminée", 
        "code": "CDD",
        "duree_essai_max": 30,  # jours
        "preavis_demission": False,
        "preavis_licenciement": False
    }
}

# Modes de paiement
PAYMENT_MODES = {
    "virement": {
        "label": "Virement bancaire",
        "code": "virement",
        "requires_bank": True,
        "icon": "credit-card"
    },
    "especes": {
        "label": "Espèces",
        "code": "especes", 
        "requires_bank": False,
        "icon": "banknotes"
    },
    "cheque": {
        "label": "Chèque",
        "code": "cheque",
        "requires_bank": False,
        "icon": "document-text"
    }
}

# Situations familiales
FAMILY_STATUS = {
    "celibataire": "Célibataire",
    "marie": "Marié(e)",
    "divorce": "Divorcé(e)",
    "veuf": "Veuf(ve)",
    "concubinage": "Concubinage",
    "pacs": "PACS"
}

# Sexes
GENDER_OPTIONS = {
    "M": "Masculin",
    "F": "Féminin"
}

# Types de régimes
REGIME_TYPES = {
    "agricole": {
        "label": "Régime Agricole",
        "code": "agricole",
        "vhm_default": 200.0,
        "taux_cnaps_patronal": 8.0
    },
    "non_agricole": {
        "label": "Régime Non Agricole", 
        "code": "non_agricole",
        "vhm_default": 173.33,
        "taux_cnaps_patronal": 13.0
    }
}

# Groupes de préavis
NOTICE_GROUPS = {
    1: {"label": "Groupe 1", "duree_jours": 15},
    2: {"label": "Groupe 2", "duree_jours": 30},
    3: {"label": "Groupe 3", "duree_jours": 45},
    4: {"label": "Groupe 4", "duree_jours": 60},
    5: {"label": "Groupe 5", "duree_jours": 90}
}

# Catégories professionnelles
PROFESSIONAL_CATEGORIES = {
    "M1": "Manœuvre 1",
    "M2": "Manœuvre 2", 
    "OS1": "Ouvrier Spécialisé 1",
    "OS2": "Ouvrier Spécialisé 2",
    "OP1": "Ouvrier Professionnel 1",
    "OP2": "Ouvrier Professionnel 2",
    "EM1": "Employé 1",
    "EM2": "Employé 2",
    "AM": "Agent de Maîtrise",
    "CAD": "Cadre"
}

# Types d'établissements
ESTABLISHMENT_TYPES = {
    "general": {
        "label": "Établissement Général",
        "taux_cnaps_patronal": 13.0,
        "taux_smie_patronal": 0.0
    },
    "scolaire": {
        "label": "Établissement Scolaire",
        "taux_cnaps_patronal": 8.0,
        "taux_smie_patronal": 0.0
    }
}

# Postes types
COMMON_POSITIONS = [
    "Directeur Général",
    "Directeur Administratif et Financier",
    "Directeur des Ressources Humaines",
    "Responsable Comptabilité",
    "Responsable Commercial",
    "Responsable Production",
    "Chef de Service",
    "Superviseur",
    "Secrétaire",
    "Comptable",
    "Commercial",
    "Technicien",
    "Ouvrier Qualifié",
    "Ouvrier",
    "Manœuvre",
    "Gardien",
    "Chauffeur",
    "Femme de ménage"
]

# Banques courantes à Madagascar
COMMON_BANKS = [
    {"nom": "BNI Madagascar", "bic": "BNIMMG", "code": "00005"},
    {"nom": "BOA Madagascar", "bic": "BMOIMGMG", "code": "00002"},
    {"nom": "BFV-SG", "bic": "SOGEMMG", "code": "00003"},
    {"nom": "MCB Madagascar", "bic": "MCBLMRMX", "code": "00006"},
    {"nom": "BMOI", "bic": "BMOIMGMG", "code": "00007"},
    {"nom": "Banky Fampandrosoana Malagasy", "bic": "BFMGMGMG", "code": "00008"},
    {"nom": "Accès Banque Madagascar", "bic": "ABMGMGMG", "code": "00009"},
    {"nom": "State Bank of Mauritius", "bic": "STMUMUMU", "code": "00010"}
]

# Constantes métier regroupées
BUSINESS_CONSTANTS = {
    "contrats": CONTRACT_TYPES,
    "paiements": PAYMENT_MODES,
    "famille": FAMILY_STATUS,
    "sexe": GENDER_OPTIONS,
    "regimes": REGIME_TYPES,
    "preavis": NOTICE_GROUPS,
    "categories": PROFESSIONAL_CATEGORIES,
    "etablissements": ESTABLISHMENT_TYPES,
    "postes": COMMON_POSITIONS,
    "banques": COMMON_BANKS
}