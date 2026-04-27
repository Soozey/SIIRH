import unittest
from datetime import date, time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.routers.hs import (
    HSCalculationRequestHS,
    HSJourInputHS,
    calculate_and_save_hs_endpoint_HS,
    calculer_heures_supplementaires_et_majorations_HS,
)


class HSEngineGuardrailsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="Demo HS Employer")
        self.db.add(self.employer)
        self.db.flush()

        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="MAT-HS-001",
            nom="Rakoto",
            prenom="Aina",
            cin="101010101010",
            date_naissance=date(1995, 1, 1),
            adresse="Antananarivo",
            date_embauche=date(2026, 1, 1),
            nature_contrat="CDI",
            poste="Agent",
            categorie_prof="Employe",
            indice="A1",
            salaire_base=800000,
        )
        self.db.add(self.worker)
        self.db.flush()

        self.user = models.AppUser(
            username="rh_hs",
            password_hash="hash",
            role_code="rh",
            employer_id=self.employer.id,
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_closed_day_type_f_is_ignored(self):
        payload = HSCalculationRequestHS(
            worker_id_HS=self.worker.id,
            mois_HS="2026-01",
            base_hebdo_heures_HS=40.0,
            jours_HS=[
                HSJourInputHS(
                    date_HS=date(2026, 1, 5),
                    type_jour_HS="N",
                    entree_HS=time(8, 0),
                    sortie_HS=time(17, 0),
                    duree_pause_minutes_HS=60,
                ),
                HSJourInputHS(
                    date_HS=date(2026, 1, 6),
                    type_jour_HS="F",
                    entree_HS=time(8, 0),
                    sortie_HS=time(22, 0),
                    duree_pause_minutes_HS=0,
                ),
            ],
        )
        result = calculer_heures_supplementaires_et_majorations_HS(payload)
        self.assertEqual(result.total_HMJF_50_heures_HS, 0.0)
        self.assertEqual(result.total_HMD_40_heures_HS, 0.0)
        self.assertEqual(result.total_HSNI_130_heures_HS, 0.0)
        self.assertEqual(result.total_HSNI_150_heures_HS, 0.0)

    def test_calendar_off_day_is_treated_as_holiday(self):
        self.db.add(
            models.CalendarDay(
                employer_id=self.employer.id,
                date=date(2026, 1, 7),
                is_worked=False,
            )
        )
        self.db.commit()

        payload = HSCalculationRequestHS(
            worker_id_HS=self.worker.id,
            mois_HS="2026-01",
            employer_id_HS=self.employer.id,
            base_hebdo_heures_HS=40.0,
            jours_HS=[
                HSJourInputHS(
                    date_HS=date(2026, 1, 7),
                    type_jour_HS="N",
                    entree_HS=time(8, 0),
                    sortie_HS=time(17, 0),
                    duree_pause_minutes_HS=60,
                )
            ],
        )

        result = calculer_heures_supplementaires_et_majorations_HS(payload, self.db)
        self.assertAlmostEqual(result.total_HMJF_50_heures_HS, 8.0, places=2)
        self.assertEqual(result.total_HMD_40_heures_HS, 0.0)

    def test_calculate_and_save_is_upsert_per_worker_month(self):
        payload_1 = HSCalculationRequestHS(
            worker_id_HS=self.worker.id,
            mois_HS="2026-02",
            base_hebdo_heures_HS=40.0,
            jours_HS=[
                HSJourInputHS(
                    date_HS=date(2026, 2, 2),
                    type_jour_HS="N",
                    entree_HS=time(8, 0),
                    sortie_HS=time(17, 0),
                    duree_pause_minutes_HS=60,
                )
            ],
        )
        created = calculate_and_save_hs_endpoint_HS(payload_1, db=self.db, user=self.user)

        payload_2 = HSCalculationRequestHS(
            worker_id_HS=self.worker.id,
            mois_HS="2026-02",
            base_hebdo_heures_HS=35.0,
            jours_HS=[
                HSJourInputHS(
                    date_HS=date(2026, 2, 2),
                    type_jour_HS="N",
                    entree_HS=time(8, 0),
                    sortie_HS=time(18, 0),
                    duree_pause_minutes_HS=60,
                )
            ],
        )
        updated = calculate_and_save_hs_endpoint_HS(payload_2, db=self.db, user=self.user)

        self.assertEqual(created.id_HS, updated.id_HS)
        self.assertEqual(updated.base_hebdo_heures_HS, 35.0)
        count = (
            self.db.query(models.HSCalculationHS)
            .filter(
                models.HSCalculationHS.worker_id_HS == self.worker.id,
                models.HSCalculationHS.mois_HS == "2026-02",
            )
            .count()
        )
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
