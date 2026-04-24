import unittest
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app import models, schemas
from app.config.config import Base
from app.routers.workers import delete_worker, reset_employees


class WorkerResetFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="SIIRH Test")
        self.db.add(self.employer)
        self.db.flush()

        self.admin = models.AppUser(
            username="admin-workers@example.com",
            password_hash="hash",
            role_code="admin",
            employer_id=self.employer.id,
            is_active=True,
        )
        self.drh = models.AppUser(
            username="drh-workers@example.com",
            password_hash="hash",
            role_code="drh",
            employer_id=self.employer.id,
            is_active=True,
        )
        self.rh = models.AppUser(
            username="rh-workers@example.com",
            password_hash="hash",
            role_code="rh",
            employer_id=self.employer.id,
            is_active=True,
        )
        self.manager = models.AppUser(
            username="manager-workers@example.com",
            password_hash="hash",
            role_code="manager",
            employer_id=self.employer.id,
            is_active=True,
        )
        self.db.add_all([self.admin, self.drh, self.rh, self.manager])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _create_worker(self, matricule: str, first_name: str = "Jean") -> models.Worker:
        worker = models.Worker(
            employer_id=self.employer.id,
            matricule=matricule,
            nom="Rakoto",
            prenom=first_name,
            salaire_base=1000000,
            salaire_horaire=5000,
            vhm=200,
            horaire_hebdo=40,
            nature_contrat="CDI",
        )
        self.db.add(worker)
        self.db.flush()
        return worker

    def test_delete_worker_rh_soft_deletes_and_writes_audit(self):
        worker = self._create_worker("EMP-001")
        linked_user = models.AppUser(
            username="employee-linked@example.com",
            password_hash="hash",
            role_code="employe",
            employer_id=self.employer.id,
            worker_id=worker.id,
            is_active=True,
        )
        self.db.add(linked_user)
        self.db.flush()
        session = models.AuthSession(
            user_id=linked_user.id,
            token="session-token",
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        )
        self.db.add(session)
        self.db.commit()

        result = delete_worker(worker.id, db=self.db, user=self.rh)

        self.assertEqual(result["mode"], "soft")
        refreshed_worker = self.db.get(models.Worker, worker.id)
        refreshed_user = self.db.get(models.AppUser, linked_user.id)
        refreshed_session = self.db.get(models.AuthSession, session.id)
        audit_entry = (
            self.db.query(models.AuditLog)
            .filter(models.AuditLog.action == "worker.delete.soft", models.AuditLog.worker_id == worker.id)
            .order_by(models.AuditLog.id.desc())
            .first()
        )
        self.assertIsNotNone(refreshed_worker)
        self.assertFalse(refreshed_worker.is_active)
        self.assertIsNotNone(refreshed_worker.deleted_at)
        self.assertFalse(refreshed_user.is_active)
        self.assertIsNotNone(refreshed_session.revoked_at)
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.actor_user_id, self.rh.id)
        self.assertEqual(audit_entry.actor_role, "rh")
        self.assertEqual(audit_entry.worker_id, worker.id)

    def test_delete_worker_drh_is_allowed(self):
        worker = self._create_worker("EMP-002", "Soa")
        self.db.commit()

        result = delete_worker(worker.id, db=self.db, user=self.drh)

        self.assertEqual(result["mode"], "soft")
        refreshed_worker = self.db.get(models.Worker, worker.id)
        self.assertIsNotNone(refreshed_worker)
        self.assertFalse(refreshed_worker.is_active)

    def test_delete_worker_rejects_other_roles(self):
        worker = self._create_worker("EMP-003", "Hery")
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            delete_worker(worker.id, db=self.db, user=self.manager)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("DRH", str(ctx.exception.detail))
        refreshed_worker = self.db.get(models.Worker, worker.id)
        self.assertIsNotNone(refreshed_worker)
        self.assertTrue(refreshed_worker.is_active)

    def test_reset_employees_soft_disables_all_workers_in_scope(self):
        first = self._create_worker("EMP-101", "Miora")
        second = self._create_worker("EMP-102", "Tiana")
        self.db.commit()

        result = reset_employees(
            schemas.WorkerResetRequest(mode="soft", confirmation_text="RESET EMPLOYEES"),
            db=self.db,
            user=self.admin,
        )

        self.assertEqual(result.mode, "soft")
        self.assertEqual(result.count, 2)
        refreshed = self.db.query(models.Worker).filter(models.Worker.id.in_([first.id, second.id])).all()
        self.assertTrue(all(not item.is_active for item in refreshed))

    def test_reset_employees_hard_purges_worker_and_contract_dependencies(self):
        worker = self._create_worker("EMP-201", "Noro")
        contract = models.CustomContract(
            worker_id=worker.id,
            employer_id=self.employer.id,
            title="Contrat CDI",
            content="<p>Contrat</p>",
        )
        self.db.add(contract)
        self.db.flush()
        contract_version = models.ContractVersion(
            contract_id=contract.id,
            worker_id=worker.id,
            employer_id=self.employer.id,
            version_number=1,
            source_module="contracts",
            status="draft",
            snapshot_json="{}",
            created_by_user_id=self.admin.id,
        )
        self.db.add(contract_version)
        self.db.commit()
        contract_id = contract.id
        contract_version_id = contract_version.id
        worker_id = worker.id

        result = reset_employees(
            schemas.WorkerResetRequest(mode="hard", confirmation_text="RESET EMPLOYEES HARD"),
            db=self.db,
            user=self.admin,
        )

        self.assertEqual(result.mode, "hard")
        self.assertEqual(result.count, 1)
        self.assertIsNone(self.db.get(models.Worker, worker_id))
        self.assertEqual(
            self.db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).count(),
            0,
        )
        self.assertEqual(
            self.db.query(models.ContractVersion).filter(models.ContractVersion.id == contract_version_id).count(),
            0,
        )

    def test_reset_employees_hard_purges_portal_request_dependencies_in_safe_order(self):
        worker = self._create_worker("EMP-301", "Lova")
        portal_request = models.EmployeePortalRequest(
            worker_id=worker.id,
            employer_id=self.employer.id,
            request_type="document_access",
            destination="rh",
            title="Test reset",
            description="Validation ordre de purge",
            status="pending",
        )
        self.db.add(portal_request)
        self.db.flush()
        inspector_case = models.InspectorCase(
            employer_id=self.employer.id,
            worker_id=worker.id,
            case_number="CASE-RESET-001",
            portal_request_id=portal_request.id,
            case_type="portal_review",
            subject="Contrôle test",
            description="Contrôle test",
            status="open",
        )
        self.db.add(inspector_case)
        self.db.commit()
        portal_request_id = portal_request.id
        inspector_case_id = inspector_case.id

        result = reset_employees(
            schemas.WorkerResetRequest(mode="hard", confirmation_text="RESET EMPLOYEES HARD"),
            db=self.db,
            user=self.admin,
        )

        self.assertEqual(result.mode, "hard")
        self.assertEqual(
            self.db.query(models.EmployeePortalRequest).filter(models.EmployeePortalRequest.id == portal_request_id).count(),
            0,
        )
        self.assertEqual(
            self.db.query(models.InspectorCase).filter(models.InspectorCase.id == inspector_case_id).count(),
            0,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
