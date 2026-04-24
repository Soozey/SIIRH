import unittest
from datetime import date
from typing import Optional

from app.payroll_logic import (
    _apply_plafond,
    calculate_constants,
    compute_cnaps,
    compute_smie,
    evaluate_formula,
)


class FakeCalendarDay:
    def __init__(self, year: int, month: int, day: int, is_worked: bool, status: Optional[str] = None):
        self.date = date(year, month, day)
        self.is_worked = is_worked
        self.status = status


class FakeEmployer:
    def __init__(self, sm_embauche: float = 250000.0, calendar_days=None):
        self.sm_embauche = sm_embauche
        self.calendar_days = calendar_days or []


class FakeWorker:
    def __init__(self):
        self.date_embauche = date(2024, 1, 15)
        self.nombre_enfant = 2
        self.employer = FakeEmployer(
            calendar_days=[
                FakeCalendarDay(2025, 1, 1, False),
                FakeCalendarDay(2025, 1, 2, True),
                FakeCalendarDay(2025, 1, 3, True),
            ]
        )


class FakePayVar:
    def __init__(self, period: str):
        self.period = period


class PayrollGuardrailTests(unittest.TestCase):
    def test_apply_plafond_keeps_smallest_value(self):
        self.assertEqual(_apply_plafond(500000, 350000), 350000.0)
        self.assertEqual(_apply_plafond(500000, 0), 500000.0)

    def test_compute_cnaps_uses_plafond_before_rates(self):
        base_cot, sal, pat = compute_cnaps(500000, 1.0, 13.0, 350000)
        self.assertEqual(base_cot, 350000.0)
        self.assertEqual(sal, 3500.0)
        self.assertEqual(pat, 45500.0)

    def test_compute_smie_adds_forfait_after_rate(self):
        base_cot, sal, pat = compute_smie(400000, 1.0, 5.0, 500, 1000, 300000)
        self.assertEqual(base_cot, 300000.0)
        self.assertEqual(sal, 3500.0)
        self.assertEqual(pat, 16000.0)

    def test_evaluate_formula_reuses_known_constants_only(self):
        result = evaluate_formula("SALDBASE + (NOMBRENF * 1000)", {"SALDBASE": 250000.0, "NOMBRENF": 2.0})
        self.assertEqual(result, 252000.0)
        self.assertEqual(evaluate_formula("UNSAFE()", {"SALDBASE": 250000.0}), 0.0)

    def test_calculate_constants_exposes_expected_payroll_inputs(self):
        worker = FakeWorker()
        payvar = FakePayVar("2025-01")

        constants = calculate_constants(
            worker=worker,
            payvar=payvar,
            brut_numeraire_courant=275000.0,
            salaire_base=250000.0,
            salaire_horaire=1442.31,
            salaire_journalier=11536.64,
            period="2025-01",
        )

        self.assertEqual(constants["NOMBRENF"], 2.0)
        self.assertEqual(constants["SME"], 250000.0)
        self.assertEqual(constants["SALDBASE"], 250000.0)
        self.assertEqual(constants["SOMMBRUT"], 275000.0)
        self.assertGreater(constants["ANCIENJR"], 0.0)
        self.assertGreater(constants["DAYSWORK"], 0.0)

    def test_calculate_constants_dayswork_supports_status_three_states(self):
        worker = FakeWorker()
        worker.employer.calendar_days = [
            FakeCalendarDay(2025, 1, 2, True, status="off"),
            FakeCalendarDay(2025, 1, 3, True, status="closed"),
            FakeCalendarDay(2025, 1, 4, False, status="worked"),
        ]
        payvar = FakePayVar("2025-01")

        constants = calculate_constants(
            worker=worker,
            payvar=payvar,
            brut_numeraire_courant=275000.0,
            salaire_base=250000.0,
            salaire_horaire=1442.31,
            salaire_journalier=11536.64,
            period="2025-01",
        )

        self.assertEqual(constants["DAYSWORK"], 22.0)

    def test_calculate_constants_dayswork_uses_period_even_without_payvar(self):
        worker = FakeWorker()

        constants = calculate_constants(
            worker=worker,
            payvar=None,
            brut_numeraire_courant=275000.0,
            salaire_base=250000.0,
            salaire_horaire=1442.31,
            salaire_journalier=11536.64,
            period="2025-01",
        )

        self.assertEqual(constants["DAYSWORK"], 22.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
