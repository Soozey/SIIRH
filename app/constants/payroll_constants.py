"""
Constantes relatives aux calculs de paie
"""
from typing import Dict, Any
from decimal import Decimal

# Taux de cotisations par défaut
COTISATION_RATES = {
    "cnaps": {
        "salarial": Decimal("1.0"),  # 1%
        "patronal_general": Decimal("13.0"),  # 13% général
        "patronal_scolaire": Decimal("8.0"),   # 8% scolaire
        "plafond_base": Decimal("0.0")  # Pas de plafond par défaut
    },
    "smie": {
        "salarial": Decimal("0.0"),
        "patronal": Decimal("0.0"),
        "forfait_salarial": Decimal("0.0"),
        "forfait_patronal": Decimal("0.0"),
        "plafond": Decimal("0.0")
    },
    "fmfp": {
        "patronal": Decimal("1.0")  # 1%
    }
}

# Majorations heures supplémentaires
HS_MAJORATIONS = {
    "hs_130": {
        "taux": Decimal("30.0"),  # +30%
        "label": "HS 130%",
        "imposable": {"ni": False, "i": True}
    },
    "hs_150": {
        "taux": Decimal("50.0"),  # +50%
        "label": "HS 150%", 
        "imposable": {"ni": False, "i": True}
    },
    "hm_nuit_habituelle": {
        "taux": Decimal("30.0"),  # +30%
        "label": "HM Nuit Habituelle 30%"
    },
    "hm_nuit_occasionnelle": {
        "taux": Decimal("50.0"),  # +50%
        "label": "HM Nuit Occasionnelle 50%"
    },
    "hm_dimanche": {
        "taux": Decimal("40.0"),  # +40%
        "label": "HM Dimanche 40%"
    },
    "hm_jours_feries": {
        "taux": Decimal("50.0"),  # +50%
        "label": "HM Jours Fériés 50%"
    }
}

# Constantes de calcul
CALCULATION_CONSTANTS = {
    "abs_divisor": Decimal("21.67"),  # Diviseur pour calcul salaire journalier
    "hours_per_month": Decimal("173.33"),  # Heures moyennes par mois
    "days_per_month": Decimal("30.0"),  # Jours moyens par mois
    "working_days_per_month": Decimal("21.67"),  # Jours travaillés moyens
    "hours_per_day": Decimal("8.0"),  # Heures par jour standard
    "days_per_week": Decimal("5.0"),  # Jours travaillés par semaine
    "weeks_per_month": Decimal("4.33")  # Semaines moyennes par mois
}

# Formules de calcul prédéfinies
PREDEFINED_FORMULAS = {
    "salaire_horaire": "SALDBASE / 173.33",
    "salaire_journalier": "SALDBASE / 21.67", 
    "anciennete_prime": "SALDBASE * (ANCIENAN / 100)",
    "prime_enfant": "NOMBRENF * 25000",
    "hs_130_ni": "heures * (SALHORAI * 1.30)",
    "hs_150_ni": "heures * (SALHORAI * 1.50)",
    "hm_nuit_30": "heures * (SALHORAI * 1.30)",
    "hm_dimanche_40": "heures * (SALHORAI * 1.40)",
    "hm_jf_50": "heures * (SALHORAI * 1.50)"
}

# Variables disponibles dans les formules
FORMULA_VARIABLES = {
    "SALDBASE": "Salaire de base",
    "SALHORAI": "Salaire horaire", 
    "SALJOURN": "Salaire journalier",
    "ANCIENAN": "Ancienneté en années",
    "ANCIENMS": "Ancienneté en mois",
    "ANCIENJR": "Ancienneté en jours",
    "NOMBRENF": "Nombre d'enfants",
    "SME": "Salaire Minimum d'Embauche",
    "SOMMBRUT": "Somme brut courant",
    "DAYSWORK": "Jours travaillés du mois"
}

# Constantes globales de paie
PAYROLL_CONSTANTS = {
    "cotisations": COTISATION_RATES,
    "majorations": HS_MAJORATIONS,
    "calculs": CALCULATION_CONSTANTS,
    "formules": PREDEFINED_FORMULAS,
    "variables": FORMULA_VARIABLES
}