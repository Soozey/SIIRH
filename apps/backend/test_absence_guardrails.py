import unittest

from app.services.absence_service import calculate_absence_retentions
from app.schemas import AbsenceInput


class AbsenceGuardrailTests(unittest.TestCase):
    def test_calculate_absences_uses_expected_daily_divisor(self):
        payload = AbsenceInput(
            worker_id=1,
            salaire_base=216700.0,
            salaire_horaire=1250.0,
            ABSNR_J=1.0,
        )

        result = calculate_absence_retentions(payload)

        self.assertEqual(round(result.salaire_journalier, 2), 10000.0)
        self.assertEqual(round(result.total_retenues_absence, 2), -10000.0)

    def test_total_retenues_excludes_informative_maladie_lines(self):
        payload = AbsenceInput(
            worker_id=1,
            salaire_base=325050.0,
            salaire_horaire=1875.0,
            ABSM_J=3.0,
            ABSM_H=4.0,
            ABSNR_J=2.0,
            ABSNR_H=1.5,
            ABS1_J=1.0,
            ABS2_H=2.0,
        )

        result = calculate_absence_retentions(payload)

        salaire_journalier = 325050.0 / 21.67
        expected = (
            -(2.0 * salaire_journalier)
            -(1.5 * 1875.0)
            -(1.0 * salaire_journalier)
            -(2.0 * 1875.0)
        )
        self.assertEqual(round(result.total_retenues_absence, 2), round(expected, 2))
        maladie_lines = [line for line in result.rubriques if line.code in {"ABSM_J", "ABSM_H"}]
        self.assertTrue(all(line.montant_salarial == 0 for line in maladie_lines))


if __name__ == "__main__":
    unittest.main(verbosity=2)
