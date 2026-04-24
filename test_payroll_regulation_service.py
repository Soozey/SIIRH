import unittest
from types import SimpleNamespace

from app.services.payroll_regulation_service import resolve_regulatory_snapshot


def _make_employer(**overrides):
    base = {
        "plafond_cnaps_base": 0.0,
        "taux_sal_cnaps": 1.0,
        "taux_pat_cnaps": 13.0,
        "sm_embauche": 0.0,
        "plafond_smie": 0.0,
        "taux_sal_smie": 0.0,
        "taux_pat_smie": 0.0,
        "smie_forfait_sal": 0.0,
        "smie_forfait_pat": 0.0,
        "taux_pat_fmfp": 1.0,
        "type_regime": SimpleNamespace(code="non_agricole"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_worker(**overrides):
    base = {
        "taux_sal_cnaps_override": None,
        "taux_pat_cnaps_override": None,
        "taux_sal_smie_override": None,
        "taux_pat_smie_override": None,
        "taux_pat_fmfp_override": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class PayrollRegulationServiceTests(unittest.TestCase):
    def test_smie_zero_rates_remain_zero_without_forced_defaults(self):
        employer = _make_employer(taux_sal_smie=0.0, taux_pat_smie=0.0)
        worker = _make_worker()

        snapshot = resolve_regulatory_snapshot(employer, worker)

        self.assertEqual(snapshot["smie"]["taux_sal"], 0.0)
        self.assertEqual(snapshot["smie"]["taux_pat"], 0.0)

    def test_worker_overrides_have_priority(self):
        employer = _make_employer(taux_sal_cnaps=1.0, taux_pat_cnaps=13.0, taux_pat_fmfp=1.0)
        worker = _make_worker(
            taux_sal_cnaps_override=2.0,
            taux_pat_cnaps_override=11.0,
            taux_pat_fmfp_override=1.5,
        )

        snapshot = resolve_regulatory_snapshot(employer, worker)

        self.assertEqual(snapshot["cnaps"]["taux_sal"], 2.0)
        self.assertEqual(snapshot["cnaps"]["taux_pat"], 11.0)
        self.assertEqual(snapshot["fmfp"]["taux_pat"], 1.5)

    def test_cnaps_default_plafond_depends_on_regime(self):
        employer_agri = _make_employer(type_regime=SimpleNamespace(code="agricole"))
        employer_non_agri = _make_employer(type_regime=SimpleNamespace(code="non_agricole"))
        worker = _make_worker()

        agri_snapshot = resolve_regulatory_snapshot(employer_agri, worker)
        non_agri_snapshot = resolve_regulatory_snapshot(employer_non_agri, worker)

        self.assertEqual(agri_snapshot["cnaps"]["plafond"], 2_132_000.0)
        self.assertEqual(non_agri_snapshot["cnaps"]["plafond"], 2_101_440.0)

    def test_declarative_mapping_contains_required_organisms(self):
        employer = _make_employer()
        worker = _make_worker()

        snapshot = resolve_regulatory_snapshot(employer, worker)
        mapping = snapshot["declarative_mapping"]

        for key in ("cnaps", "ostie", "fmfp", "irsa"):
            self.assertIn(key, mapping)


if __name__ == "__main__":
    unittest.main(verbosity=2)
