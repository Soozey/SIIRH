"""
Utility functions for calculating HS/HM amounts in Ariary
"""

from decimal import Decimal
from typing import Dict


def calculate_hs_hm_amounts(
    hours: Dict[str, float],
    salaire_horaire: float
) -> Dict[str, float]:
    """
    Calculate HS/HM amounts in Ariary based on hourly wage.
    
    Formules:
    - HSNI 130% = heures × salaire_horaire × 1.30
    - HSI 130% = heures × salaire_horaire × 1.30
    - HSNI 150% = heures × salaire_horaire × 1.50
    - HSI 150% = heures × salaire_horaire × 1.50
    - HMNH 30% = heures × salaire_horaire × 0.30
    - HMNO 50% = heures × salaire_horaire × 0.50
    - HMD 40% = heures × salaire_horaire × 0.40
    - HMJF 200% = heures × salaire_horaire × 2.00
    
    Args:
        hours: Dict with keys like 'hsni_130_heures', 'hsi_130_heures', etc.
        salaire_horaire: Hourly wage in Ariary
    
    Returns:
        Dict with calculated amounts for each type
    """
    # Coefficients multiplicateurs
    coefficients = {
        'hsni_130': 1.30,
        'hsi_130': 1.30,
        'hsni_150': 1.50,
        'hsi_150': 1.50,
        'hmnh': 0.30,
        'hmno': 0.50,
        'hmd': 0.40,
        'hmjf': 2.00,
    }
    
    amounts = {}
    
    for key_base, coef in coefficients.items():
        hours_key = f"{key_base}_heures"
        amount_key = f"{key_base}_montant"
        
        # Get hours (default 0.0 if not present)
        h = hours.get(hours_key, 0.0)
        
        # Calculate amount: hours × hourly_wage × coefficient
        # Round to 2 decimals for Ariary
        amount = round(float(h) * salaire_horaire * coef, 2)
        
        amounts[amount_key] = amount
    
    return amounts


def get_non_taxable_amount(amounts: Dict[str, float]) -> float:
    """
    Calculate total non-taxable amount from HS/HM.
    
    HSNI 130% and HSNI 150% are NON-TAXABLE.
    All others are taxable.
    
    Args:
        amounts: Dict with calculated amounts
    
    Returns:
        Total non-taxable amount in Ariary
    """
    non_taxable = (
        amounts.get('hsni_130_montant', 0.0) +
        amounts.get('hsni_150_montant', 0.0)
    )
    return round(non_taxable, 2)


def get_taxable_amount(amounts: Dict[str, float]) -> float:
    """
    Calculate total taxable amount from HS/HM.
    
    HSI 130%, HSI 150%, and all HM are taxable.
    
    Args:
        amounts: Dict with calculated amounts
    
    Returns:
        Total taxable amount in Ariary
    """
    taxable = (
        amounts.get('hsi_130_montant', 0.0) +
        amounts.get('hsi_150_montant', 0.0) +
        amounts.get('hmnh_montant', 0.0) +
        amounts.get('hmno_montant', 0.0) +
        amounts.get('hmd_montant', 0.0) +
        amounts.get('hmjf_montant', 0.0)
    )
    return round(taxable, 2)


def get_total_hs_hm_amount(amounts: Dict[str, float]) -> float:
    """
    Calculate total HS/HM amount (taxable + non-taxable).
    
    Args:
        amounts: Dict with calculated amounts
    
    Returns:
        Total amount in Ariary
    """
    total = sum(amounts.values())
    return round(total, 2)
