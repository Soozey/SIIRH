import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.config import Base
from app import models
from app.services.payroll_period_service import (
    close_payroll_period,
    ensure_payroll_period_open,
    reopen_payroll_period,
)


class PayrollPeriodClosingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        employer = models.Employer(raison_sociale="Test Employer")
        self.db.add(employer)
        self.db.flush()
        worker = models.Worker(
            employer_id=employer.id,
            matricule="T001",
            nom="Rakoto",
            prenom="Jean",
            salaire_base=500000,
            salaire_horaire=2500,
            vhm=200,
        )
        self.db.add(worker)
        self.db.commit()
        self.employer_id = employer.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_close_snapshots_and_locks_period(self):
        period, archived_count = close_payroll_period(self.db, self.employer_id, 4, 2026)

        self.assertTrue(period.is_closed)
        self.assertEqual(archived_count, 1)
        archive = self.db.query(models.PayrollArchive).one()
        self.assertEqual(archive.period, "2026-04")
        self.assertGreaterEqual(archive.brut, 0)

        with self.assertRaises(HTTPException) as ctx:
            ensure_payroll_period_open(self.db, self.employer_id, period="2026-04")
        self.assertEqual(ctx.exception.status_code, 423)

    def test_reopen_allows_period_writes_again(self):
        close_payroll_period(self.db, self.employer_id, 5, 2026)
        reopened = reopen_payroll_period(self.db, self.employer_id, 5, 2026)
        self.assertFalse(reopened.is_closed)

        ensure_payroll_period_open(self.db, self.employer_id, period="2026-05")


if __name__ == "__main__":
    unittest.main()
