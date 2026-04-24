# Ajout à la fin de schemas.py

# ==========================
#  PAYROLL HS/HM
# ==========================

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    
    created_at: datetime
    updated_at: datetime
    
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
