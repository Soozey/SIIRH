import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.services.organizational_service import OrganizationalService


class OrganizationMasterSyncTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self.employer = models.Employer(raison_sociale="Demo Employer")
        self.db.add(self.employer)
        self.db.commit()
        self.db.refresh(self.employer)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_resolve_selected_unit_prefers_deepest_level(self):
        etab = OrganizationalService.create_organizational_unit(self.db, self.employer.id, "etablissement", "HQ", "HQ")
        dept = OrganizationalService.create_organizational_unit(self.db, self.employer.id, "departement", "Finance", "FIN", etab.id)
        service = OrganizationalService.create_organizational_unit(self.db, self.employer.id, "service", "Paie", "PAY", dept.id)
        unit = OrganizationalService.resolve_selected_unit(
            self.db,
            employer_id=self.employer.id,
            etablissement=str(etab.id),
            departement=str(dept.id),
            service=str(service.id),
        )
        self.assertIsNotNone(unit)
        self.assertEqual(unit.id, service.id)

    def test_apply_unit_snapshot_to_worker_fills_text_fields_from_fk(self):
        etab = OrganizationalService.create_organizational_unit(self.db, self.employer.id, "etablissement", "HQ", "HQ")
        dept = OrganizationalService.create_organizational_unit(self.db, self.employer.id, "departement", "Finance", "FIN", etab.id)
        service = OrganizationalService.create_organizational_unit(self.db, self.employer.id, "service", "Paie", "PAY", dept.id)
        worker = models.Worker(
            employer_id=self.employer.id,
            matricule="W001",
            nom="Rakoto",
            prenom="Jean",
            salaire_base=1000,
            salaire_horaire=10,
            vhm=100,
            horaire_hebdo=40,
        )
        OrganizationalService.apply_unit_snapshot_to_worker(worker, service)
        self.assertEqual(worker.organizational_unit_id, service.id)
        self.assertEqual(worker.etablissement, "HQ")
        self.assertEqual(worker.departement, "Finance")
        self.assertEqual(worker.service, "Paie")


if __name__ == "__main__":
    unittest.main(verbosity=2)
