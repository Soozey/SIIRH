import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.config.config import Base
from app.routers.leaves import (
    create_leave_planning_cycle,
    decide_leave_request,
    get_leave_validator_dashboard,
    get_planning_proposals,
    get_worker_dashboard,
    requalify_request,
    submit_leave_request,
)


class LeaveManagementWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="SIIRH Leave", nif="123", stat="456", activite="Services")
        self.db.add(self.employer)
        self.db.flush()

        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="W001",
            nom="Rakoto",
            prenom="Aina",
            poste="Assistante RH",
            salaire_base=600000,
            date_embauche=date(2024, 1, 5),
            solde_conge_initial=10.0,
        )
        self.manager_worker = models.Worker(
            employer_id=self.employer.id,
            matricule="M001",
            nom="Manager",
            prenom="One",
            poste="Manager",
            salaire_base=900000,
            date_embauche=date(2023, 1, 1),
        )
        self.db.add_all([self.worker, self.manager_worker])
        self.db.flush()

        self.employee_user = models.AppUser(username="employee@test.mg", password_hash="x", role_code="employe", employer_id=self.employer.id, worker_id=self.worker.id, is_active=True)
        self.manager_user = models.AppUser(username="manager@test.mg", password_hash="x", role_code="manager", employer_id=self.employer.id, worker_id=self.manager_worker.id, is_active=True)
        self.rh_user = models.AppUser(username="rh@test.mg", password_hash="x", role_code="rh", employer_id=self.employer.id, is_active=True)
        self.db.add_all([self.employee_user, self.manager_user, self.rh_user])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_leave_request_full_workflow_updates_legacy_leave_and_dashboard(self):
        request = submit_leave_request(
            schemas.LeaveRequestCreate(
                worker_id=self.worker.id,
                leave_type_code="CONGE_ANNUEL",
                start_date=date(2026, 4, 14),
                end_date=date(2026, 4, 18),
                subject="Conge annuel avril",
                reason="Repos",
                comment="Planning valide",
                attachments=[],
                submit_now=True,
            ),
            db=self.db,
            user=self.employee_user,
        )
        self.assertEqual(request.status, "pending_validation_1")

        queue = get_leave_validator_dashboard(employer_id=self.employer.id, db=self.db, user=self.manager_user)
        self.assertEqual(queue.metrics["pending"], 1)

        request = decide_leave_request(
            request.id,
            schemas.LeaveRequestDecisionIn(action="approve", comment="OK manager"),
            db=self.db,
            user=self.manager_user,
        )
        self.assertEqual(request.status, "pending_validation_2")

        request = decide_leave_request(
            request.id,
            schemas.LeaveRequestDecisionIn(action="approve", comment="OK RH"),
            db=self.db,
            user=self.rh_user,
        )
        self.assertEqual(request.status, "approved")
        self.assertIsNotNone(request.integrated_at)

        legacy_leave = self.db.query(models.Leave).filter(models.Leave.worker_id == self.worker.id).first()
        self.assertIsNotNone(legacy_leave)
        self.assertEqual(round(legacy_leave.days_taken, 2), 5.0)

        dashboard = get_worker_dashboard(self.worker.id, "2026-04", db=self.db, user=self.employee_user)
        self.assertGreaterEqual(dashboard.balances["consumed"], 5.0)
        self.assertTrue(any(item["type"] == "workflow" for item in dashboard.notifications))

    def test_requalification_and_payroll_absence_sync(self):
        request = submit_leave_request(
            schemas.LeaveRequestCreate(
                worker_id=self.worker.id,
                leave_type_code="PERMISSION_LEGALE",
                start_date=date(2026, 4, 21),
                end_date=date(2026, 4, 21),
                subject="Permission familiale",
                reason="Demarche",
                comment=None,
                attachments=[],
                submit_now=True,
            ),
            db=self.db,
            user=self.employee_user,
        )
        request = requalify_request(
            request.id,
            schemas.LeaveRequestRequalifyIn(new_leave_type_code="ABSENCE_NON_AUTORISEE", comment="Requalifiee apres verification"),
            db=self.db,
            user=self.rh_user,
        )
        self.assertEqual(request.final_leave_type_code, "ABSENCE_NON_AUTORISEE")

        decide_leave_request(
            request.id,
            schemas.LeaveRequestDecisionIn(action="approve", comment="OK manager"),
            db=self.db,
            user=self.manager_user,
        )
        request = decide_leave_request(
            request.id,
            schemas.LeaveRequestDecisionIn(action="approve", comment="OK RH"),
            db=self.db,
            user=self.rh_user,
        )
        self.assertEqual(request.status, "approved")

        absence = self.db.query(models.Absence).filter(models.Absence.worker_id == self.worker.id, models.Absence.mois == "2026-04").first()
        self.assertIsNotNone(absence)
        self.assertGreater(absence.ABSNR_J, 0)

    def test_planning_cycle_generates_ranked_proposals(self):
        cycle = create_leave_planning_cycle(
            schemas.LeavePlanningCycleIn(
                employer_id=self.employer.id,
                title="Plan 2026",
                planning_year=2026,
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 15),
                status="draft",
                max_absent_per_unit=1,
                blackout_periods=[],
                family_priority_enabled=True,
                notes=None,
            ),
            db=self.db,
            user=self.rh_user,
        )
        self.db.commit()

        proposals = get_planning_proposals(cycle.id, regenerate=True, db=self.db, user=self.rh_user)
        self.assertGreaterEqual(len(proposals), 1)
        self.assertTrue(any(item.score >= 0 for item in proposals))


if __name__ == "__main__":
    unittest.main(verbosity=2)
