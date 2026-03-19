"""
Router pour gÃ©rer l'importation et la liaison des HS/HM aux paies
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import openpyxl
from io import BytesIO

from ..config.config import get_db
from ..models import PayrollHsHm, Worker, PayrollRun, HSCalculationHS, Absence, Avance, PayVar
from ..schemas import (
    PayrollHsHmCreate,
    PayrollHsHmOut,
    PayrollHsHmBase,
    LinkHsCalculationRequest,
    ExcelImportSummary
)
from ..utils.hs_hm_calculations import calculate_hs_hm_amounts
from fastapi.responses import FileResponse
import os
from ..schemas import (
    PayrollHsHmCreate,
    PayrollHsHmOut,
    PayrollHsHmBase,
    LinkHsCalculationRequest,
    ExcelImportSummary
)
from ..utils.hs_hm_calculations import calculate_hs_hm_amounts
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/payroll-hs-hm", tags=["Payroll HS/HM"])


@router.get("/template")
def get_hs_hm_template(
    payroll_run_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Télécharge le modèle Excel pour l'import HS/HM.
    Dynamique : toujours nettoyer les exemples (EMP001) et remplir avec les salariés si ID fourni.
    """
    
    payroll_run = None
    if payroll_run_id:
        payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()

    try:
        # Create NEW workbook from scratch (No file dependency)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Import Paie"
        
        # Define headers manually (guaranteed correct)
        headers = [
            'Matricule',      # 1
            'HSNI_130',       # 2
            'HSI_130',        # 3
            'HSNI_150',       # 4
            'HSI_150',        # 5
            'HMNH',           # 6
            'HMNO',           # 7
            'HMD',            # 8
            'HMJF',           # 9
            'ABSM_J',         # 10
            'ABSM_H',         # 11
            'ABSNR_J',        # 12
            'ABSNR_H',        # 13
            'ABSMP',          # 14
            'ABS1_J',         # 15
            'ABS1_H',         # 16
            'ABS2_J',         # 17
            'ABS2_H',         # 18
            'Avance',          # 19
            'Autre déduction 1', # 20
            'Autre déduction 2', # 21
            'Autre déduction 3', # 22
            'Avantage Véhicule', # 23
            'Avantage Logement', # 24
            'Avantage Téléphone', # 25
            'Autres Avantages'   # 26
        ]
        ws.append(headers)
        
        # Style headers
        from openpyxl.styles import Font, PatternFill, Alignment
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            cell.alignment = Alignment(horizontal='center')

        # If we have a payroll_run_id, populate with workers
        if payroll_run:
            print(f"Generating template for PayrollRun ID: {payroll_run_id}")
            workers = db.query(Worker).filter(
                Worker.employer_id == payroll_run.employer_id
            ).order_by(Worker.matricule).all()
            
            print(f"Found {len(workers)} workers for employer {payroll_run.employer_id}")

            from openpyxl.comments import Comment
            # Start at row 2 (row 1 is header)
            for idx, w in enumerate(workers, start=2):
                cell = ws.cell(row=idx, column=1, value=w.matricule)
                comment_text = f"{w.nom} {w.prenom}"
                cell.comment = Comment(comment_text, "SIIRH")
        else:
            print("No payroll_run_id provided or not found, returning empty template")

        # Set column widths
        ws.column_dimensions['A'].width = 15  # Matricule
        ws.column_dimensions['B'].width = 10
        ws.column_dimensions['C'].width = 10
        # ... others default is fine

        # Save to memory and serve
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Determine filename
        filename = "Modele_Import_Paie.xlsx"
        if payroll_run:
            from ..models import Employer
            employer = db.query(Employer).filter(Employer.id == payroll_run.employer_id).first()
            # Fix: Employer model uses raison_sociale
            emp_name = getattr(employer, "raison_sociale", f"EMP{payroll_run.employer_id}") if employer else f"EMP{payroll_run.employer_id}"
            
            safe_emp_name = "".join([c for c in emp_name if c.isalnum() or c in (' ','-','_')]).strip()
            filename = f"Import_Paie_{safe_emp_name}_{payroll_run.period}.xlsx"
        
        from fastapi.responses import StreamingResponse
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        print(f"CRITICAL ERROR generating template: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating template: {str(e)}")


@router.post("/{payroll_run_id}/link-manual/{worker_id}", response_model=PayrollHsHmOut)
def link_manual_hs_calculation(
    payroll_run_id: int,
    worker_id: int,
    request: LinkHsCalculationRequest,
    db: Session = Depends(get_db)
):
    """
    Lie un calcul HS manuel (from HeuresSupplementairesPageHS) Ã  une paie.
    RÃ©cupÃ¨re les heures depuis hs_calculations_HS et calcule les montants.
    """
    # Verify payroll run exists
    payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    # Verify worker exists
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Verify HS calculation exists
    hs_calc = db.query(HSCalculationHS).filter(
        HSCalculationHS.id_HS == request.hs_calculation_id
    ).first()
    if not hs_calc:
        raise HTTPException(status_code=404, detail="HS calculation not found")
    
    # Check if HS/HM already exists for this payroll + worker
    existing = db.query(PayrollHsHm).filter(
        PayrollHsHm.payroll_run_id == payroll_run_id,
        PayrollHsHm.worker_id == worker_id
    ).first()
    
    if existing:
        # Update existing
        db.delete(existing)
        db.commit()
    
    # Prepare hours dict
    hours = {
        'hsni_130_heures': float(hs_calc.total_HSNI_130_heures_HS),
        'hsi_130_heures': float(hs_calc.total_HSI_130_heures_HS),
        'hsni_150_heures': float(hs_calc.total_HSNI_150_heures_HS),
        'hsi_150_heures': float(hs_calc.total_HSI_150_heures_HS),
        'hmnh_heures': float(hs_calc.total_HMNH_30_heures_HS),
        'hmno_heures': float(hs_calc.total_HMNO_50_heures_HS),
        'hmd_heures': float(hs_calc.total_HMD_40_heures_HS),
        'hmjf_heures': float(hs_calc.total_HMJF_50_heures_HS),
    }
    
    # Calculate amounts in Ariary
    amounts = calculate_hs_hm_amounts(hours, worker.salaire_horaire)
    
    # Create new PayrollHsHm
    payroll_hs_hm = PayrollHsHm(
        payroll_run_id=payroll_run_id,
        worker_id=worker_id,
        source_type="MANUAL",
        hs_calculation_id=hs_calc.id_HS,
        **hours,
        **amounts
    )
    
    db.add(payroll_hs_hm)
    db.commit()
    db.refresh(payroll_hs_hm)
    
    return payroll_hs_hm


@router.post("/{payroll_run_id}/import-excel", response_model=ExcelImportSummary)
async def import_hs_hm_from_excel(
    payroll_run_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import HS/HM, Absences, and Avances data from Excel file.
    Expected format: Matricule, HSNI_130, HSI_130, HSNI_150, HSI_150, HMNH, HMNO, HMD, HMJF,
                     ABSM_J, ABSM_H, ABSNR_J, ABSNR_H, ABSMP, ABS1_J, ABS1_H, ABS2_J, ABS2_H, Avance
    """
    # Verify payroll run exists
    payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    # Read Excel file
    try:
        contents = await file.read()
        workbook = openpyxl.load_workbook(BytesIO(contents))
        sheet = workbook.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {str(e)}")
    
    total_rows = 0
    successful = 0
    failed = 0
    errors = []
    
    # Skip header row, start from row 2
    for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not row[0]:  # Skip empty rows
            continue
        
        total_rows += 1
        
        try:
            # Parse row
            matricule = str(row[0]).strip()
            
            # Find worker by matricule
            worker = db.query(Worker).filter(Worker.matricule == matricule).first()
            if not worker:
                errors.append(f"Row {row_idx}: Worker '{matricule}' not found")
                failed += 1
                continue
            
            # Parse hours (default 0.0 if empty)
            hours = {
                'hsni_130_heures': float(row[1] or 0.0),
                'hsi_130_heures': float(row[2] or 0.0),
                'hsni_150_heures': float(row[3] or 0.0),
                'hsi_150_heures': float(row[4] or 0.0),
                'hmnh_heures': float(row[5] or 0.0),
                'hmno_heures': float(row[6] or 0.0),
                'hmd_heures': float(row[7] or 0.0),
                'hmjf_heures': float(row[8] or 0.0),
            }
            
            # Parse absences (colonnes 9-17)
            absences_data = {
                'ABSM_J': float(row[9] or 0.0),
                'ABSM_H': float(row[10] or 0.0),
                'ABSNR_J': float(row[11] or 0.0),
                'ABSNR_H': float(row[12] or 0.0),
                'ABSMP': float(row[13] or 0.0),
                'ABS1_J': float(row[14] or 0.0),
                'ABS1_H': float(row[15] or 0.0),
                'ABS2_J': float(row[16] or 0.0),
                'ABS2_H': float(row[17] or 0.0),
            }
            
            # Parse avance (colonne 18)
            avance_montant = float(row[18] or 0.0) if len(row) > 18 else 0.0
            
            # Validate all hours >= 0
            if any(h < 0 for h in hours.values()):
                errors.append(f"Row {row_idx}: Negative hours not allowed")
                failed += 1
                continue
            
            # Validate absences >= 0
            if any(v < 0 for v in absences_data.values()):
                errors.append(f"Row {row_idx}: Negative absence values not allowed")
                failed += 1
                continue
            
            # Calculate HS/HM amounts
            amounts = calculate_hs_hm_amounts(hours, worker.salaire_horaire)
            
            # === HS/HM ===
            # Check if already exists
            existing = db.query(PayrollHsHm).filter(
                PayrollHsHm.payroll_run_id == payroll_run_id,
                PayrollHsHm.worker_id == worker.id
            ).first()
            
            if existing:
                # Update
                for key, value in hours.items():
                    setattr(existing, key, value)
                for key, value in amounts.items():
                    setattr(existing, key, value)
                existing.source_type = "IMPORT"
                existing.import_file_name = file.filename
                existing.hs_calculation_id = None
            else:
                # Create new
                payroll_hs_hm = PayrollHsHm(
                    payroll_run_id=payroll_run_id,
                    worker_id=worker.id,
                    source_type="IMPORT",
                    import_file_name=file.filename,
                    **hours,
                    **amounts
                )
                db.add(payroll_hs_hm)
            
            # === ABSENCES ===
            # Get period from payroll_run
            period = payroll_run.period  # Format YYYY-MM
            
            existing_absence = db.query(Absence).filter(
                Absence.worker_id == worker.id,
                Absence.mois == period
            ).first()
            
            if existing_absence:
                # Update
                for key, value in absences_data.items():
                    setattr(existing_absence, key, value)
            else:
                # Create new
                absence = Absence(
                    worker_id=worker.id,
                    mois=period,
                    **absences_data
                )
                db.add(absence)
            
            # === AVANCES ===
            if avance_montant > 0:
                existing_avance = db.query(Avance).filter(
                    Avance.worker_id == worker.id,
                    Avance.periode == period
                ).first()
                
                if existing_avance:
                    existing_avance.montant = avance_montant
                else:
                    avance = Avance(
                        worker_id=worker.id,
                        periode=period,
                        montant=avance_montant
                    )
                    db.add(avance)

            # === PAYVAR (Autres Déductions & Avantages Override) ===
            # Columns 19..25 (0-indexed in row): 19=AutreDed1 ... 25=AutreAv
            # Row indices: 
            # 19: Autre Ded 1
            # 20: Autre Ded 2
            # 21: Autre Ded 3
            # 22: Avantage Véhicule
            # 23: Avantage Logement
            # 24: Avantage Téléphone
            # 25: Autres Avantages

            autre_ded1 = float(row[19] or 0.0) if len(row) > 19 else 0.0
            autre_ded2 = float(row[20] or 0.0) if len(row) > 20 else 0.0
            autre_ded3 = float(row[21] or 0.0) if len(row) > 21 else 0.0
            
            av_vehicule = float(row[22] or 0.0) if len(row) > 22 else 0.0
            av_logement = float(row[23] or 0.0) if len(row) > 23 else 0.0
            av_telephone = float(row[24] or 0.0) if len(row) > 24 else 0.0
            av_autres = float(row[25] or 0.0) if len(row) > 25 else 0.0

            # Check if we have ANY data to save in PayVar
            if any([autre_ded1, autre_ded2, autre_ded3, av_vehicule, av_logement, av_telephone, av_autres]):
                # Get or Create PayVar
                payvar_entry = db.query(PayVar).filter(
                    PayVar.worker_id == worker.id,
                    PayVar.period == period
                ).first()

                if not payvar_entry:
                    payvar_entry = PayVar(worker_id=worker.id, period=period)
                    db.add(payvar_entry)
                
                # Update fields
                if len(row) > 19: payvar_entry.autre_ded1 = autre_ded1
                if len(row) > 20: payvar_entry.autre_ded2 = autre_ded2
                if len(row) > 21: payvar_entry.autre_ded3 = autre_ded3
                
                if len(row) > 22: payvar_entry.avantage_vehicule = av_vehicule
                if len(row) > 23: payvar_entry.avantage_logement = av_logement
                if len(row) > 24: payvar_entry.avantage_telephone = av_telephone
                if len(row) > 25: payvar_entry.avantage_autres = av_autres

            successful += 1
            
        except Exception as e:
            errors.append(f"Row {row_idx}: {str(e)}")
            failed += 1
            continue
    
    db.commit()
    
    return ExcelImportSummary(
        total_rows=total_rows,
        successful=successful,
        failed=failed,
        errors=errors
    )


@router.get("/{payroll_run_id}/all", response_model=List[PayrollHsHmOut])
def get_all_hs_hm_for_payroll(
    payroll_run_id: int,
    db: Session = Depends(get_db)
):
    """Get all HS/HM data for a payroll run, merged with Absences"""
    
    # 1. Get PayrollRun to determine period
    payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        return []
        
    period = payroll_run.period
    
    # 2. Get all HS/HM
    hs_hms = db.query(PayrollHsHm).filter(
        PayrollHsHm.payroll_run_id == payroll_run_id
    ).all()
    
    # 3. Get all Absences
    absences = db.query(Absence).filter(
        Absence.mois == period
    ).all()
    
    # 4. Get all Avances
    avances = db.query(Avance).filter(
        Avance.periode == period
    ).all()

    # 5. Get all PayVars (Advantages & Deductions)
    payvars = db.query(PayVar).filter(
        PayVar.period == period
    ).all()
    
    # Merge Data
    hs_map = {hs.worker_id: hs for hs in hs_hms}
    abs_map = {a.worker_id: a for a in absences}
    av_map = {a.worker_id: a for a in avances}
    pv_map = {p.worker_id: p for p in payvars}
    
    all_worker_ids = set(hs_map.keys()) | set(abs_map.keys()) | set(av_map.keys()) | set(pv_map.keys())
    
    result = []
    
    for wid in all_worker_ids:
        hs_entry = hs_map.get(wid)
        abs_entry = abs_map.get(wid)
        av_entry = av_map.get(wid)
        pv_entry = pv_map.get(wid)
        
        # Base dict
        if hs_entry:
            out_dict = {c.name: getattr(hs_entry, c.name) for c in PayrollHsHm.__table__.columns}
        else:
            out_dict = {
                "id": None, # Should be None for new entries on frontend logic usually, check types? schema says int, let's put 0
                "payroll_run_id": payroll_run_id,
                "worker_id": wid,
                "source_type": "MANUAL",
                "hs_calculation_id": None,
                "import_file_name": None,
                "hsni_130_heures": 0.0, "hsi_130_heures": 0.0,
                "hsni_150_heures": 0.0, "hsi_150_heures": 0.0,
                "hmnh_heures": 0.0, "hmno_heures": 0.0,
                "hmd_heures": 0.0, "hmjf_heures": 0.0,
                "hsni_130_montant": 0.0, "hsi_130_montant": 0.0,
                "hsni_150_montant": 0.0, "hsi_150_montant": 0.0,
                "hmnh_montant": 0.0, "hmno_montant": 0.0,
                "hmd_montant": 0.0, "hmjf_montant": 0.0,
                "created_at": None, "updated_at": None,
                "id": 0 # Default ID 0
            }

        # Inject Absence Data
        if abs_entry:
            out_dict["ABSM_J"] = abs_entry.ABSM_J
            out_dict["ABSM_H"] = abs_entry.ABSM_H
            out_dict["ABSNR_J"] = abs_entry.ABSNR_J
            out_dict["ABSNR_H"] = abs_entry.ABSNR_H
            out_dict["ABSMP"] = abs_entry.ABSMP
            out_dict["ABS1_J"] = abs_entry.ABS1_J
            out_dict["ABS1_H"] = abs_entry.ABS1_H
            out_dict["ABS2_J"] = abs_entry.ABS2_J
            out_dict["ABS2_H"] = abs_entry.ABS2_H
        else:
            out_dict["ABSM_J"] = 0.0
            out_dict["ABSM_H"] = 0.0
            out_dict["ABSNR_J"] = 0.0
            out_dict["ABSNR_H"] = 0.0
            out_dict["ABSMP"] = 0.0
            out_dict["ABS1_J"] = 0.0
            out_dict["ABS1_H"] = 0.0
            out_dict["ABS2_J"] = 0.0
            out_dict["ABS2_H"] = 0.0
            
        # Inject Avance Data
        if av_entry:
            out_dict["avance"] = av_entry.montant
        else:
            out_dict["avance"] = 0.0

        # Inject PayVar Data (Advantages & Deductions)
        if pv_entry:
            out_dict["autre_ded1"] = pv_entry.autre_ded1
            out_dict["autre_ded2"] = pv_entry.autre_ded2
            out_dict["autre_ded3"] = pv_entry.autre_ded3
            out_dict["autre_ded4"] = pv_entry.autre_ded4
            out_dict["avantage_vehicule"] = pv_entry.avantage_vehicule
            out_dict["avantage_logement"] = pv_entry.avantage_logement
            out_dict["avantage_telephone"] = pv_entry.avantage_telephone
            out_dict["avantage_autres"] = pv_entry.avantage_autres
        else:
            out_dict["autre_ded1"] = 0.0
            out_dict["autre_ded2"] = 0.0
            out_dict["autre_ded3"] = 0.0
            out_dict["autre_ded4"] = 0.0
            out_dict["avantage_vehicule"] = 0.0
            out_dict["avantage_logement"] = 0.0
            out_dict["avantage_telephone"] = 0.0
            out_dict["avantage_autres"] = 0.0
            
        # Primes Data Removed from Schema

            
        result.append(out_dict)
        
    return result


@router.put("/{payroll_run_id}/{worker_id}", response_model=PayrollHsHmOut)
def update_worker_hs_hm(
    payroll_run_id: int,
    worker_id: int,
    payload: PayrollHsHmBase,
    db: Session = Depends(get_db)
):
    """
    Update HS/HM AND Absences for a specific worker.
    """
    # 1. Verify Worker & PayrollRun
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    period = payroll_run.period

    # 2. Separate Payload
    data = payload.dict()
    
    hs_keys = [
        "hsni_130_heures", "hsi_130_heures",
        "hsni_150_heures", "hsi_150_heures",
        "hmnh_heures", "hmno_heures",
        "hmd_heures", "hmjf_heures"
    ]
    abs_keys = [
        "ABSM_J", "ABSM_H", 
        "ABSNR_J", "ABSNR_H", 
        "ABSMP", 
        "ABS1_J", "ABS1_H", 
        "ABS2_J", "ABS2_H"
    ]

    # prime_keys removed
    
    hs_data = {k: v for k, v in data.items() if k in hs_keys}
    abs_data = {k: v for k, v in data.items() if k in abs_keys}
    avance_val = data.get("avance", 0.0)

    payvar_keys = [
        "autre_ded1", "autre_ded2", "autre_ded3", "autre_ded4",
        "avantage_vehicule", "avantage_logement", "avantage_telephone", "avantage_autres"
    ]
    pv_data = {k: v for k, v in data.items() if k in payvar_keys}
    
    # 3. Update/Create HS/HM (PayrollHsHm)
    amounts = calculate_hs_hm_amounts(hs_data, worker.salaire_horaire)
    
    hs_hm = db.query(PayrollHsHm).filter(
        PayrollHsHm.payroll_run_id == payroll_run_id,
        PayrollHsHm.worker_id == worker_id
    ).first()
    
    if hs_hm:
        for as_key, as_val in hs_data.items():
            setattr(hs_hm, as_key, as_val)
        for amt_key, amt_val in amounts.items():
            setattr(hs_hm, amt_key, amt_val)
        hs_hm.source_type = "MANUAL"
    else:
        hs_hm = PayrollHsHm(
            payroll_run_id=payroll_run_id,
            worker_id=worker_id,
            source_type="MANUAL",
            **hs_data,
            **amounts
        )
        db.add(hs_hm)
    
    # 4. Update/Create Absence
    absence = db.query(Absence).filter(
        Absence.worker_id == worker_id,
        Absence.mois == period
    ).first()
    
    if absence:
        for k, v in abs_data.items():
            setattr(absence, k, v)
    else:
        absence = Absence(
            worker_id=worker_id,
            mois=period,
            **abs_data
        )
        db.add(absence)

    # 5. Update/Create Avance
    avance_obj = db.query(Avance).filter(
        Avance.worker_id == worker_id,
        Avance.periode == period
    ).first()
    
    if avance_obj:
        avance_obj.montant = avance_val
    elif avance_val > 0:
        # Only create if > 0
        avance_obj = Avance(
            worker_id=worker_id,
            periode=period,
            montant=avance_val
        )
        db.add(avance_obj)

    # 6. Update PayVar (Advantages & Deductions)
    payvar_entry = db.query(PayVar).filter(
        PayVar.worker_id == worker_id,
        PayVar.period == period
    ).first()

    should_create_pv = any(v != 0 for v in pv_data.values())
    
    if not payvar_entry and should_create_pv:
        payvar_entry = PayVar(worker_id=worker_id, period=period)
        db.add(payvar_entry)
        
    if payvar_entry:
        for k, v in pv_data.items():
            setattr(payvar_entry, k, v)


    db.commit()
    db.refresh(hs_hm)
    
    # 6. Build Response
    out_dict = {c.name: getattr(hs_hm, c.name) for c in PayrollHsHm.__table__.columns}
    
    for k in abs_keys:
        out_dict[k] = abs_data.get(k, 0.0)
    
    out_dict["avance"] = avance_val

    for k in payvar_keys:
        out_dict[k] = pv_data.get(k, 0.0)


    return out_dict 

@router.delete("/{payroll_run_id}/{worker_id}", status_code=204)
def delete_worker_hs_hm(
    payroll_run_id: int,
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Supprime les HS/HM et les Absences pour un salariÃ© et une paie donnÃ©e.
    Remet effectivement Ã  zÃ©ro les compteurs.
    """
    # 1. Get PayrollRun to find period
    payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
        
    period = payroll_run.period

    # 2. Delete HS/HM
    hs_hm = db.query(PayrollHsHm).filter(
        PayrollHsHm.payroll_run_id == payroll_run_id,
        PayrollHsHm.worker_id == worker_id
    ).first()
    
    if hs_hm:
        db.delete(hs_hm)
        
    # 3. Delete Absences (same period)
    absence = db.query(Absence).filter(
        Absence.worker_id == worker_id,
        Absence.mois == period
    ).first()
    
    if absence:
        db.delete(absence)
        
    # 4. Delete Avance
    avance = db.query(Avance).filter(
        Avance.worker_id == worker_id,
        Avance.periode == period
    ).first()
    
    if avance:
        db.delete(avance)

    # 5. Delete PayVar (Advantages & Deductions)
    payvar = db.query(PayVar).filter(
        PayVar.worker_id == worker_id,
        PayVar.period == period
    ).first()
    
    if payvar:
        db.delete(payvar)
        
    db.commit()
    return None

@router.post("/{payroll_run_id}/reset-bulk", status_code=204)
def reset_bulk_hs_hm(
    payroll_run_id: int,
    worker_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Supprime HS/HM et Absences pour une liste de salariÃ©s (Bulk Reset).
    """
    # 1. Get PayrollRun
    payroll_run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
        
    period = payroll_run.period
    
    # 2. Bulk Delete PayrollHsHm
    db.query(PayrollHsHm).filter(
        PayrollHsHm.payroll_run_id == payroll_run_id,
        PayrollHsHm.worker_id.in_(worker_ids)
    ).delete(synchronize_session=False)
    
    # 3. Bulk Delete Absences
    db.query(Absence).filter(
        Absence.mois == period,
        Absence.worker_id.in_(worker_ids)
    ).delete(synchronize_session=False)

    # 4. Bulk Delete Avances
    db.query(Avance).filter(
        Avance.periode == period,
        Avance.worker_id.in_(worker_ids)
    ).delete(synchronize_session=False)

    # 5. Bulk Delete PayVar
    db.query(PayVar).filter(
        PayVar.period == period,
        PayVar.worker_id.in_(worker_ids)
    ).delete(synchronize_session=False)
    
    db.commit()
    return None
