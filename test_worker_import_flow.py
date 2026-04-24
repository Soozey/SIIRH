import unittest

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.routers.workers_import import WORKER_TEMPLATE_COLUMNS, _import_workers_dataframe


class WorkerImportFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.regime = models.TypeRegime(code="non_agricole", label="Régime non agricole", vhm=200)
        self.db.add(self.regime)
        self.employer = models.Employer(raison_sociale="Karibo Services")
        self.db.add(self.employer)
        self.db.flush()
        self.user = models.AppUser(
            username="rh-import@example.com",
            password_hash="hash",
            role_code="rh",
            employer_id=self.employer.id,
            is_active=True,
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _row(self, **overrides):
        row = {column: "" for column in WORKER_TEMPLATE_COLUMNS}
        row.update(
            {
                "Raison Sociale": self.employer.raison_sociale,
                "Matricule": "EMP-001",
                "Nom": "Rakoto",
                "Prenom": "Jean",
                "Telephone": "0340011223",
                "Email": "jean.rakoto@example.com",
                "CIN": "101234567890",
                "Date Embauche (JJ/MM/AAAA)": "01/01/2024",
                "Nature du Contrat": "CDI",
                "Type Regime (Agricole/Non Agricole)": "Non Agricole",
                "Horaire Hebdo": 40,
                "Salaire Base": 250000,
            }
        )
        row.update(overrides)
        return row

    def test_import_workers_dataframe_imports_valid_rows(self):
        df = pd.DataFrame([self._row()])

        report, created, updated, skipped = _import_workers_dataframe(
            df=df,
            update_existing=False,
            db=self.db,
            user=self.user,
            dry_run=False,
        )
        self.db.commit()

        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        self.assertEqual(skipped, 0)
        self.assertEqual(report.failed, 0)
        worker = self.db.query(models.Worker).filter(models.Worker.matricule == "EMP-001").first()
        self.assertIsNotNone(worker)
        self.assertEqual(worker.email, "jean.rakoto@example.com")

    def test_import_workers_dataframe_accepts_partial_import_and_reports_rejected_rows(self):
        existing = models.Worker(
            employer_id=self.employer.id,
            type_regime_id=self.regime.id,
            matricule="EMP-EXIST",
            nom="Existing",
            prenom="Worker",
            email="existing@example.com",
            cin="999999",
            salaire_base=100000,
        )
        self.db.add(existing)
        self.db.commit()

        df = pd.DataFrame(
            [
                self._row(Matricule="EMP-101", Email="valid.one@example.com", CIN="123456789"),
                self._row(Matricule="EMP-102", Email="bad-email", CIN="223456789"),
                self._row(Matricule="EMP-103", Email="existing@example.com", CIN="323456789"),
                self._row(Matricule="EMP-104", Email="valid.two@example.com", CIN="423456789", **{"Date Embauche (JJ/MM/AAAA)": "99/99/2024"}),
            ]
        )

        report, created, updated, skipped = _import_workers_dataframe(
            df=df,
            update_existing=False,
            db=self.db,
            user=self.user,
            dry_run=False,
        )
        self.db.commit()

        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        self.assertEqual(skipped, 0)
        self.assertEqual(report.failed, 3)
        self.assertEqual(report.created, 1)
        self.assertTrue(any(issue.code == "invalid_email" for issue in report.issues))
        self.assertTrue(any("Email deja utilise" in issue.message for issue in report.issues))
        self.assertTrue(any(issue.code == "invalid_date" for issue in report.issues))
        self.assertEqual(self.db.query(models.Worker).filter(models.Worker.matricule == "EMP-101").count(), 1)
        self.assertEqual(self.db.query(models.Worker).filter(models.Worker.matricule == "EMP-102").count(), 0)
        self.assertEqual(self.db.query(models.Worker).filter(models.Worker.matricule == "EMP-103").count(), 0)
        self.assertEqual(self.db.query(models.Worker).filter(models.Worker.matricule == "EMP-104").count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
