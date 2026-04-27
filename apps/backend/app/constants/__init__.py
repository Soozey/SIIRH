# Référentiel centralisé de constantes SIIRH
from .payroll_constants import *
from .business_constants import *
from .document_constants import *
from .validation_constants import *

__all__ = [
    # Constantes de paie
    'PAYROLL_CONSTANTS',
    'CALCULATION_CONSTANTS', 
    'COTISATION_RATES',
    
    # Constantes métier
    'BUSINESS_CONSTANTS',
    'CONTRACT_TYPES',
    'PAYMENT_MODES',
    
    # Constantes de documents
    'DOCUMENT_TEMPLATES',
    'FIELD_MAPPINGS',
    
    # Constantes de validation
    'VALIDATION_RULES',
    'DROPDOWN_OPTIONS'
]