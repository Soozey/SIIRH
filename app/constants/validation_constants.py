"""
Constantes pour la validation et les listes déroulantes
"""
from typing import Dict, List, Any

# Options pour les listes déroulantes
DROPDOWN_OPTIONS = {
    "sexe": [
        {"value": "M", "label": "Masculin"},
        {"value": "F", "label": "Féminin"}
    ],
    
    "situation_familiale": [
        {"value": "celibataire", "label": "Célibataire"},
        {"value": "marie", "label": "Marié(e)"},
        {"value": "divorce", "label": "Divorcé(e)"},
        {"value": "veuf", "label": "Veuf(ve)"},
        {"value": "concubinage", "label": "Concubinage"},
        {"value": "pacs", "label": "PACS"}
    ],
    
    "nature_contrat": [
        {"value": "CDI", "label": "Contrat à Durée Indéterminée"},
        {"value": "CDD", "label": "Contrat à Durée Déterminée"}
    ],
    
    "type_regime": [
        {"value": "agricole", "label": "Régime Agricole"},
        {"value": "non_agricole", "label": "Régime Non Agricole"}
    ],
    
    "mode_paiement": [
        {"value": "virement", "label": "Virement bancaire"},
        {"value": "especes", "label": "Espèces"},
        {"value": "cheque", "label": "Chèque"}
    ],
    
    "groupe_preavis": [
        {"value": 1, "label": "Groupe 1 (15 jours)"},
        {"value": 2, "label": "Groupe 2 (30 jours)"},
        {"value": 3, "label": "Groupe 3 (45 jours)"},
        {"value": 4, "label": "Groupe 4 (60 jours)"},
        {"value": 5, "label": "Groupe 5 (90 jours)"}
    ],
    
    "categorie_professionnelle": [
        {"value": "M1", "label": "Manœuvre 1"},
        {"value": "M2", "label": "Manœuvre 2"},
        {"value": "OS1", "label": "Ouvrier Spécialisé 1"},
        {"value": "OS2", "label": "Ouvrier Spécialisé 2"},
        {"value": "OP1", "label": "Ouvrier Professionnel 1"},
        {"value": "OP2", "label": "Ouvrier Professionnel 2"},
        {"value": "EM1", "label": "Employé 1"},
        {"value": "EM2", "label": "Employé 2"},
        {"value": "AM", "label": "Agent de Maîtrise"},
        {"value": "CAD", "label": "Cadre"}
    ],
    
    "type_etablissement": [
        {"value": "general", "label": "Établissement Général"},
        {"value": "scolaire", "label": "Établissement Scolaire"}
    ]
}

# Règles de validation
VALIDATION_RULES = {
    "matricule": {
        "required": True,
        "type": "string",
        "min_length": 1,
        "max_length": 20,
        "pattern": r"^[A-Z0-9]+$",
        "message": "Le matricule doit contenir uniquement des lettres majuscules et des chiffres"
    },
    
    "nom": {
        "required": True,
        "type": "string",
        "min_length": 2,
        "max_length": 50,
        "pattern": r"^[A-ZÀ-ÿ\s\-']+$",
        "message": "Le nom doit contenir uniquement des lettres, espaces, tirets et apostrophes"
    },
    
    "prenom": {
        "required": True,
        "type": "string", 
        "min_length": 2,
        "max_length": 50,
        "pattern": r"^[A-ZÀ-ÿ\s\-']+$",
        "message": "Le prénom doit contenir uniquement des lettres, espaces, tirets et apostrophes"
    },
    
    "cin": {
        "required": True,
        "type": "string",
        "length": 12,
        "pattern": r"^\d{12}$",
        "message": "Le CIN doit contenir exactement 12 chiffres"
    },
    
    "cnaps": {
        "required": False,
        "type": "string",
        "length": 11,
        "pattern": r"^\d{10}[A-Z]$",
        "message": "Le numéro CNaPS doit contenir 10 chiffres suivis d'une lettre"
    },
    
    "email": {
        "required": False,
        "type": "email",
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "message": "Format d'email invalide"
    },
    
    "telephone": {
        "required": False,
        "type": "string",
        "pattern": r"^(\+261|0)[0-9]{9}$",
        "message": "Format de téléphone invalide (ex: 0340000000 ou +261340000000)"
    },
    
    "salaire_base": {
        "required": True,
        "type": "number",
        "min": 0,
        "max": 100000000,
        "message": "Le salaire de base doit être un montant positif"
    },
    
    "nombre_enfant": {
        "required": False,
        "type": "integer",
        "min": 0,
        "max": 20,
        "message": "Le nombre d'enfants doit être entre 0 et 20"
    },
    
    "code_banque": {
        "required": False,
        "type": "string",
        "length": 5,
        "pattern": r"^\d{5}$",
        "message": "Le code banque doit contenir exactement 5 chiffres"
    },
    
    "code_guichet": {
        "required": False,
        "type": "string",
        "length": 5,
        "pattern": r"^\d{5}$",
        "message": "Le code guichet doit contenir exactement 5 chiffres"
    },
    
    "numero_compte": {
        "required": False,
        "type": "string",
        "min_length": 10,
        "max_length": 11,
        "pattern": r"^\d{10,11}$",
        "message": "Le numéro de compte doit contenir 10 ou 11 chiffres"
    }
}

# Messages d'erreur personnalisés
ERROR_MESSAGES = {
    "required": "Ce champ est obligatoire",
    "invalid_format": "Format invalide",
    "too_short": "Trop court (minimum {min} caractères)",
    "too_long": "Trop long (maximum {max} caractères)",
    "invalid_email": "Adresse email invalide",
    "invalid_phone": "Numéro de téléphone invalide",
    "invalid_number": "Doit être un nombre valide",
    "out_of_range": "Valeur hors limites ({min} - {max})",
    "duplicate": "Cette valeur existe déjà",
    "not_found": "Élément non trouvé"
}

# Configuration des champs obligatoires par contexte
REQUIRED_FIELDS = {
    "worker_creation": [
        "matricule", "nom", "prenom", "sexe", "date_naissance",
        "date_embauche", "salaire_base", "employer_id"
    ],
    
    "worker_import": [
        "matricule", "nom", "prenom", "date_embauche", "salaire_base"
    ],
    
    "employer_creation": [
        "raison_sociale", "representant", "nif", "stat"
    ],
    
    "payroll_generation": [
        "worker_id", "period", "salaire_base"
    ],
    
    "document_generation": [
        "worker_id", "template_type"
    ]
}

# Formats d'affichage
DISPLAY_FORMATS = {
    "date": "dd/MM/yyyy",
    "datetime": "dd/MM/yyyy HH:mm",
    "currency": "0,0 Ar",
    "percentage": "0.00%",
    "number": "0,0",
    "decimal": "0,0.00"
}

# Constantes de validation regroupées
VALIDATION_CONSTANTS = {
    "dropdowns": DROPDOWN_OPTIONS,
    "rules": VALIDATION_RULES,
    "messages": ERROR_MESSAGES,
    "required": REQUIRED_FIELDS,
    "formats": DISPLAY_FORMATS
}