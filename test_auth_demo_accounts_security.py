import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.routers.auth import bootstrap_role_logins, get_public_demo_accounts


class AuthDemoAccountsSecurityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="Karibo Services", nif="123456")
        self.db.add(self.employer)
        self.db.flush()

        self.admin_user = models.AppUser(
            username="admin@siirh.com",
            password_hash="hash",
            role_code="admin",
            is_active=True,
        )
        self.rh_user = models.AppUser(
            username="rh@siirh.com",
            password_hash="hash",
            role_code="rh",
            employer_id=self.employer.id,
            is_active=True,
        )
        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="KRB-001",
            nom="Rasoanaivo",
            prenom="Miora",
            salaire_base=900000,
        )
        self.db.add_all([self.admin_user, self.rh_user, self.worker])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_public_demo_accounts_hide_password_fields(self):
        payload = get_public_demo_accounts(db=self.db)
        self.assertGreaterEqual(len(payload), 1)
        for item in payload:
            self.assertFalse(hasattr(item, "password_hint"))

    def test_bootstrap_role_logins_response_hides_password(self):
        payload = bootstrap_role_logins(employer_id=self.employer.id, user=self.rh_user, db=self.db)
        self.assertTrue(payload["ok"])
        self.assertNotIn("password", payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
