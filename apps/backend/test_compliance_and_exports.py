import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base, settings
from app.routers.compliance import _assert_scope as compliance_assert_scope
from app.services.compliance_service import build_contract_checklist, build_employee_flow, create_contract_version
from app.services.statutory_reporting_service import build_export_preview, ensure_export_templates, generate_export_job


def fake_preview_data(worker_id: int, period: str, db):
    _ = (worker_id, period, db)
    return {
        "lines": [
            {"label": "Cotisation CNaPS", "montant_sal": 3500, "montant_pat": 45500},
            {"label": "Cotisation SMIE", "montant_sal": 1200, "montant_pat": 6000},
            {"label": "Cotisation FMFP", "montant_sal": 0, "montant_pat": 3500},
        ],
        "totaux": {"brut": 350000, "irsa": 10000, "net": 305300},
    }


class ComplianceAndExportsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="Karibo Services", nif="1234567890")
        self.db.add(self.employer)
        self.db.flush()

        self.user = models.AppUser(
            username="rh_user",
            password_hash="hash",
            role_code="rh",
            employer_id=self.employer.id,
        )
        self.db.add(self.user)
        self.db.flush()

        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="MAT001",
            nom="Rakoto",
            prenom="Jean",
            cin="123456789012",
            date_naissance=date(1995, 1, 1),
            adresse="Antananarivo",
            date_embauche=date(2026, 1, 2),
            nature_contrat="CDI",
            poste="Assistant RH",
            categorie_prof="Employe",
            indice="A1",
            salaire_base=850000,
        )
        self.db.add(self.worker)
        self.db.flush()

        self.contract = models.CustomContract(
            worker_id=self.worker.id,
            employer_id=self.employer.id,
            title="Contrat CDI",
            content="Assistant RH Employe A1 850000 2026-01-02",
            template_type="employment_contract",
            is_default=True,
        )
        self.db.add(self.contract)

        self.job = models.RecruitmentJobPosting(
            employer_id=self.employer.id,
            title="Assistant RH",
            department="RH",
            location="Antananarivo",
            contract_type="CDI",
            salary_range="850000 - 1000000",
            status="published",
        )
        self.db.add(self.job)
        self.db.flush()

        self.profile = models.RecruitmentJobProfile(
            job_posting_id=self.job.id,
            salary_min=850000,
            salary_max=1000000,
            desired_start_date=date(2026, 1, 2),
            workflow_status="validated",
            announcement_status="published",
        )
        self.db.add(self.profile)

        self.candidate = models.RecruitmentCandidate(
            employer_id=self.employer.id,
            first_name="Jean",
            last_name="Rakoto",
            email="jean.rakoto@example.com",
            phone="+261340000000",
            status="offer",
        )
        self.db.add(self.candidate)
        self.db.flush()

        self.application = models.RecruitmentApplication(
            job_posting_id=self.job.id,
            candidate_id=self.candidate.id,
            stage="offer",
        )
        self.db.add(self.application)
        self.db.flush()

        self.decision = models.RecruitmentDecision(
            application_id=self.application.id,
            decision_status="hired",
            converted_worker_id=self.worker.id,
            contract_draft_id=self.contract.id,
        )
        self.db.add(self.decision)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_contract_checklist_confirms_required_contract_mentions(self):
        checklist = build_contract_checklist(self.contract, self.worker)
        missing = [item["label"] for item in checklist if item["status"] != "ok"]
        self.assertEqual(missing, [])

    def test_employee_flow_links_candidate_job_contract_and_worker(self):
        flow = build_employee_flow(self.db, self.worker)
        self.assertEqual(flow["candidate"]["email"], "jean.rakoto@example.com")
        self.assertEqual(flow["job_posting"]["title"], "Assistant RH")
        self.assertEqual(flow["contract"]["title"], "Contrat CDI")
        self.assertEqual(flow["worker"]["matricule"], "MAT001")

    def test_contract_version_is_created_from_existing_contract_without_touching_payroll(self):
        version = create_contract_version(
            self.db,
            contract=self.contract,
            worker=self.worker,
            actor=self.user,
            source_module="inspection",
            status="generated",
        )
        self.db.commit()
        self.assertEqual(version.version_number, 1)
        self.assertIn("Assistant RH", version.snapshot_json)

    @patch("app.services.statutory_reporting_service.generate_preview_data", side_effect=fake_preview_data)
    def test_build_export_preview_irsa_uses_existing_payroll_data_read_only(self, _preview_mock):
        ensure_export_templates(self.db)
        preview = build_export_preview(
            self.db,
            employer_id=self.employer.id,
            template_code="irsa_bimestriel",
            start_period="2026-01",
            end_period="2026-02",
        )
        self.assertEqual(preview["document_type"], "IRSA bimestriel")
        self.assertEqual(len(preview["rows"]), 1)
        self.assertGreater(preview["rows"][0]["irsa_ret"], 0)

    @patch("app.services.statutory_reporting_service.generate_preview_data", side_effect=fake_preview_data)
    def test_generate_export_job_creates_snapshot_file_and_declaration(self, _preview_mock):
        ensure_export_templates(self.db)
        with tempfile.TemporaryDirectory() as temp_dir:
            previous_upload_dir = settings.UPLOAD_DIR
            settings.UPLOAD_DIR = temp_dir
            try:
                job = generate_export_job(
                    self.db,
                    employer_id=self.employer.id,
                    template_code="fmfp",
                    start_period="2026-01",
                    end_period="2026-01",
                    requested_by=self.user,
                )
                self.assertEqual(job.status, "generated")
                self.assertTrue(job.file_path)
                declarations = self.db.query(models.StatutoryDeclaration).filter(models.StatutoryDeclaration.export_job_id == job.id).all()
                self.assertEqual(len(declarations), 1)
            finally:
                settings.UPLOAD_DIR = previous_upload_dir

    def test_compliance_scope_allows_rh_and_blocks_unscoped_employer(self):
        compliance_assert_scope(self.user, self.employer.id)
        external_user = models.AppUser(username="ext", password_hash="hash", role_code="employeur", employer_id=999)
        with self.assertRaises(Exception):
            compliance_assert_scope(external_user, self.employer.id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
