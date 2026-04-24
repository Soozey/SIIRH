from typing import Literal

from ..constants.payroll_constants import CALCULATION_CONSTANTS
from ..schemas import AbsenceCalculationResult, AbsenceInput, AbsenceRubriqueResult

ABSENCE_RULES: tuple[tuple[str, str, Literal["jour", "heure"], bool], ...] = (
    ("ABSM_J", "Absence Maladie (en jour)", "jour", True),
    ("ABSM_H", "Absence Maladie (en heure)", "heure", True),
    ("ABSNR_J", "Absence non rémunérée (en jour)", "jour", False),
    ("ABSNR_H", "Absence non rémunérée (en heure)", "heure", False),
    ("ABSMP", "Absence mis à pied", "jour", False),
    ("ABS1_J", "Autre absence 1 (en jour)", "jour", False),
    ("ABS1_H", "Autre absence 1 (en heure)", "heure", False),
    ("ABS2_J", "Autre absence 2 (en jour)", "jour", False),
    ("ABS2_H", "Autre absence 2 (en heure)", "heure", False),
)


def _resolve_daily_salary(salaire_base: float) -> float:
    abs_divisor = float(CALCULATION_CONSTANTS["abs_divisor"])
    if abs_divisor <= 0:
        return 0.0
    return salaire_base / abs_divisor


def _build_absence_rubrique(
    code: str,
    label: str,
    unit: Literal["jour", "heure"],
    quantity: float,
    salary_daily: float,
    salary_hourly: float,
    informative_only: bool,
) -> AbsenceRubriqueResult:
    if informative_only:
        base = 0.0
        amount = 0.0
    elif unit == "jour":
        base = salary_daily
        amount = -quantity * base
    else:
        base = salary_hourly
        amount = -quantity * base

    return AbsenceRubriqueResult(
        code=code,
        label=label,
        unite=unit,
        nombre=quantity,
        base=base,
        montant_salarial=amount,
    )


def calculate_absence_retentions(absence_input: AbsenceInput) -> AbsenceCalculationResult:
    salary_daily = _resolve_daily_salary(absence_input.salaire_base)
    salary_hourly = absence_input.salaire_horaire

    rubriques: list[AbsenceRubriqueResult] = []
    for code, label, unit, informative_only in ABSENCE_RULES:
        quantity = float(getattr(absence_input, code, 0.0) or 0.0)
        rubriques.append(
            _build_absence_rubrique(
                code=code,
                label=label,
                unit=unit,
                quantity=quantity,
                salary_daily=salary_daily,
                salary_hourly=salary_hourly,
                informative_only=informative_only,
            )
        )

    total_retenues = sum(r.montant_salarial for r in rubriques if r.montant_salarial < 0)

    return AbsenceCalculationResult(
        salaire_journalier=salary_daily,
        salaire_horaire=salary_hourly,
        rubriques=rubriques,
        total_retenues_absence=total_retenues,
    )
