import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.config.config import Base
from app.services.organizational_filters import apply_worker_hierarchy_filters


class OrganizationalFilterTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        employer = models.Employer(raison_sociale="Demo Employer")
        self.db.add(employer)
        self.db.flush()
        self.employer_id = employer.id

        etab = models.OrganizationalUnit(
            employer_id=self.employer_id,
            parent_id=None,
            level="etablissement",
            level_order=1,
            code="HQ",
            name="HQ",
        )
        self.db.add(etab)
        self.db.flush()
        self.etab_id = etab.id

        dept = models.OrganizationalUnit(
            employer_id=self.employer_id,
            parent_id=self.etab_id,
            level="departement",
            level_order=2,
            code="FIN",
            name="Finance",
        )
        self.db.add(dept)
        self.db.flush()
        self.dept_id = dept.id

        worker_node = models.Worker(
            employer_id=self.employer_id,
            matricule="MAT001",
            nom="Rakoto",
            prenom="Jean",
            organizational_unit_id=self.dept_id,
            etablissement="HQ",
            departement="Finance",
        )
        worker_legacy = models.Worker(
            employer_id=self.employer_id,
            matricule="MAT002",
            nom="Rabe",
            prenom="Anna",
            etablissement="HQ",
        )
        self.db.add_all([worker_node, worker_legacy])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_filters_accept_hierarchical_node_id(self):
        query = self.db.query(models.Worker).filter(models.Worker.employer_id == self.employer_id)
        result = apply_worker_hierarchy_filters(
            query,
            self.db,
            employer_id=self.employer_id,
            filters={"etablissement": str(self.etab_id)},
        ).all()
        self.assertEqual({worker.matricule for worker in result}, {"MAT001", "MAT002"})

    def test_filters_accept_hierarchical_node_name(self):
        query = self.db.query(models.Worker).filter(models.Worker.employer_id == self.employer_id)
        result = apply_worker_hierarchy_filters(
            query,
            self.db,
            employer_id=self.employer_id,
            filters={"etablissement": "HQ"},
        ).all()
        self.assertEqual({worker.matricule for worker in result}, {"MAT001", "MAT002"})

    def test_filters_keep_legacy_text_values_without_fk(self):
        query = self.db.query(models.Worker).filter(models.Worker.employer_id == self.employer_id)
        result = apply_worker_hierarchy_filters(
            query,
            self.db,
            employer_id=self.employer_id,
            filters={"etablissement": "HQ"},
        ).all()
        self.assertIn("MAT002", [worker.matricule for worker in result])

    def test_filters_accept_descendant_level_with_mixed_storage(self):
        query = self.db.query(models.Worker).filter(models.Worker.employer_id == self.employer_id)
        result = apply_worker_hierarchy_filters(
            query,
            self.db,
            employer_id=self.employer_id,
            filters={"departement": str(self.dept_id)},
        ).all()
        self.assertEqual([worker.matricule for worker in result], ["MAT001"])

    def test_report_request_accepts_string_filters(self):
        request = schemas.ReportRequest(
            employer_id=1,
            start_period="2025-01",
            end_period="2025-02",
            columns=["nom"],
            etablissement=" 42 ",
            matricule_search=" MAT ",
            include_matricule=True,
        )
        self.assertEqual(request.etablissement, "42")
        self.assertEqual(request.matricule_search, "MAT")
        self.assertTrue(request.include_matricule)


if __name__ == "__main__":
    unittest.main(verbosity=2)
