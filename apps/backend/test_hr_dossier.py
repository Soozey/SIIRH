import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.services.hr_dossier_service import build_hr_dossier_view, update_hr_dossier_section, upload_hr_document
from app.services.master_data_service import sync_worker_master_data
from app import schemas


class HrDossierServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="Karibo Services")
        self.db.add(self.employer)
        self.db.flush()

        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="K001",
            nom="Rakoto",
            prenom="Jean",
            adresse="Antananarivo",
            salaire_base=800000,
            salaire_horaire=5000,
            vhm=173.33,
            horaire_hebdo=40,
            nature_contrat="CDI",
        )
        self.admin = models.AppUser(
            username="admin@test.local",
            password_hash="x",
            role_code="admin",
            full_name="Admin Test",
            is_active=True,
            employer_id=self.employer.id,
        )
        self.employee_user = models.AppUser(
            username="employee@test.local",
            password_hash="x",
            role_code="employe",
            full_name="Employee Test",
            is_active=True,
            employer_id=self.employer.id,
        )
        self.db.add_all([self.worker, self.admin, self.employee_user])
        self.db.flush()
        self.employee_user.worker_id = self.worker.id
        sync_worker_master_data(self.db, self.worker)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_build_and_update_hr_dossier(self):
        update_hr_dossier_section(
            self.db,
            worker=self.worker,
            section_key="health",
            data={"date_visite": "2026-04-21", "resultat_aptitude": "apte"},
            actor=self.admin,
        )
        self.db.commit()

        view = build_hr_dossier_view(self.db, worker=self.worker, user=self.admin)
        self.assertEqual(view.access_scope, "full")
        self.assertIn("health", view.sections)
        self.assertEqual(view.sections["health"].data.get("resultat_aptitude"), "apte")

    def test_upload_document_and_self_scope_filtering(self):
        upload_hr_document(
            self.db,
            worker=self.worker,
            actor=self.admin,
            files=[(SimpleNamespace(filename="cin.pdf", content_type="application/pdf"), b"fake-pdf-content")],
            meta=schemas.HrDossierDocumentUploadMetaIn(
                title="CIN",
                section_code="identity",
                document_type="cin_passport",
                visible_to_employee=True,
            ),
        )
        self.db.commit()

        admin_view = build_hr_dossier_view(self.db, worker=self.worker, user=self.admin)
        self.assertTrue(any(item.document_type == "cin_passport" for item in admin_view.documents))

        employee_view = build_hr_dossier_view(self.db, worker=self.worker, user=self.employee_user)
        self.assertEqual(employee_view.access_scope, "self")
        self.assertIn("identity", employee_view.sections)
        self.assertNotIn("payroll", employee_view.sections)
        self.assertTrue(any(item.document_type == "cin_passport" for item in employee_view.documents))


if __name__ == "__main__":
    unittest.main(verbosity=2)
