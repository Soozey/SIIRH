from fastapi import APIRouter, Depends
from ..schemas import (
    AbsenceInput,
    AbsenceCalculationResult,
    AbsenceRubriqueResult,
)
from .. import models
from ..security import READ_PAYROLL_ROLES, require_roles


router = APIRouter(
    prefix="/absences",
    tags=["Absences"],
)


def calculate_absences(data: AbsenceInput) -> AbsenceCalculationResult:
    """
    Logique de calcul des absences selon le document PROMPT-ABSENCE.
    """

    # Salaire journalier selon ton document
    salaire_journalier = data.salaire_base / 21.67
    salaire_horaire = data.salaire_horaire

    rubriques: list[AbsenceRubriqueResult] = []

    # 1) Absence Maladie (jours) - informatif, montant = 0
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABSM_J",
            label="Absence Maladie (en jour)",
            unite="jour",
            nombre=data.ABSM_J,
            base=0.0,
            montant_salarial=0.0,
        )
    )

    # 2) Absence Maladie (heures) - informatif, montant = 0
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABSM_H",
            label="Absence Maladie (en heure)",
            unite="heure",
            nombre=data.ABSM_H,
            base=0.0,
            montant_salarial=0.0,
        )
    )

    # 3) Absence non rémunérée en jours
    montant_absnr_j = - data.ABSNR_J * salaire_journalier
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABSNR_J",
            label="Absence non rémunérée (en jour)",
            unite="jour",
            nombre=data.ABSNR_J,
            base=salaire_journalier,
            montant_salarial=montant_absnr_j,
        )
    )

    # 4) Absence non rémunérée en heures
    montant_absnr_h = - data.ABSNR_H * salaire_horaire
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABSNR_H",
            label="Absence non rémunérée (en heure)",
            unite="heure",
            nombre=data.ABSNR_H,
            base=salaire_horaire,
            montant_salarial=montant_absnr_h,
        )
    )

    # 5) Mise à pied (jours)
    montant_absmp = - data.ABSMP * salaire_journalier
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABSMP",
            label="Absence mis à pied",
            unite="jour",
            nombre=data.ABSMP,
            base=salaire_journalier,
            montant_salarial=montant_absmp,
        )
    )

    # 6) Autre Absence 1 (jour)
    montant_abs1_j = - data.ABS1_J * salaire_journalier
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABS1_J",
            label="Autre absence 1 (en jour)",
            unite="jour",
            nombre=data.ABS1_J,
            base=salaire_journalier,
            montant_salarial=montant_abs1_j,
        )
    )

    # 7) Autre Absence 1 (heure)
    montant_abs1_h = - data.ABS1_H * salaire_horaire
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABS1_H",
            label="Autre absence 1 (en heure)",
            unite="heure",
            nombre=data.ABS1_H,
            base=salaire_horaire,
            montant_salarial=montant_abs1_h,
        )
    )

    # 8) Autre Absence 2 (jour)
    montant_abs2_j = - data.ABS2_J * salaire_journalier
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABS2_J",
            label="Autre absence 2 (en jour)",
            unite="jour",
            nombre=data.ABS2_J,
            base=salaire_journalier,
            montant_salarial=montant_abs2_j,
        )
    )

    # 9) Autre Absence 2 (heure)
    montant_abs2_h = - data.ABS2_H * salaire_horaire
    rubriques.append(
        AbsenceRubriqueResult(
            code="ABS2_H",
            label="Autre absence 2 (en heure)",
            unite="heure",
            nombre=data.ABS2_H,
            base=salaire_horaire,
            montant_salarial=montant_abs2_h,
        )
    )

    # Total des retenues (uniquement lignes négatives)
    total_retenues = sum(
        r.montant_salarial for r in rubriques if r.montant_salarial < 0
    )

    return AbsenceCalculationResult(
        salaire_journalier=salaire_journalier,
        salaire_horaire=salaire_horaire,
        rubriques=rubriques,
        total_retenues_absence=total_retenues,
    )


@router.post("/calcul", response_model=AbsenceCalculationResult)
def calculer_absences(
    payload: AbsenceInput,
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Endpoint pour calculer les retenues liées aux absences.
    """
    return calculate_absences(payload)
