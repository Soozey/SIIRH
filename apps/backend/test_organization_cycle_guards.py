import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.services.organizational_service import OrganizationalService


class OrganizationCycleGuardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self.employer = models.Employer(raison_sociale="Cycle Employer")
        self.db.add(self.employer)
        self.db.commit()
        self.db.refresh(self.employer)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_validate_parent_assignment_rejects_self_parent(self):
        etab = OrganizationalService.create_organizational_unit(self.db, self.employer.id, "etablissement", "HQ", "HQ")

        with self.assertRaisesRegex(ValueError, "propre parent"):
            OrganizationalService.validate_parent_assignment(
                self.db,
                employer_id=self.employer.id,
                unit_id=etab.id,
                parent_id=etab.id,
                level=etab.level,
            )

    def test_get_organization_tree_cuts_existing_cycles(self):
        unit_a = models.OrganizationalUnit(
            employer_id=self.employer.id,
            parent_id=None,
            level="etablissement",
            level_order=1,
            code="A",
            name="A",
            is_active=True,
        )
        unit_b = models.OrganizationalUnit(
            employer_id=self.employer.id,
            parent_id=None,
            level="departement",
            level_order=2,
            code="B",
            name="B",
            is_active=True,
        )
        self.db.add_all([unit_a, unit_b])
        self.db.commit()
        self.db.refresh(unit_a)
        self.db.refresh(unit_b)

        unit_a.parent_id = unit_b.id
        unit_b.parent_id = unit_a.id
        self.db.commit()

        cyclic_ids = OrganizationalService.detect_cyclic_units(self.db, self.employer.id)
        tree = OrganizationalService.get_organization_tree(self.db, self.employer.id)

        self.assertEqual(sorted(cyclic_ids), sorted([unit_a.id, unit_b.id]))
        self.assertTrue(tree["root_units"])
        self.assertLessEqual(len(tree["root_units"]), 2)
        for root in tree["root_units"]:
            self.assertIsInstance(root["children"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
