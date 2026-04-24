import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.routers.employee_portal import _assert_worker_scope, _build_labour_case_legal_summary
from app.routers.people_ops import _termination_checklist_payload
from app.services.employee_portal_service import append_history, build_portal_dashboard, next_inspector_case_number, next_request_number
from app.services.people_ops_service import build_hr_dashboard


class EmployeePortalAndPeopleOpsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="SIHMada", nif="123")
        self.db.add(self.employer)
        self.db.flush()

        self.rh_user = models.AppUser(username="rh", password_hash="hash", role_code="rh", employer_id=self.employer.id)
        self.employee_user = models.AppUser(username="emp", password_hash="hash", role_code="employe", employer_id=self.employer.id)
        self.outsider_user = models.AppUser(username="other", password_hash="hash", role_code="employe", employer_id=self.employer.id)
        self.db.add_all([self.rh_user, self.employee_user, self.outsider_user])
        self.db.flush()

        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="EMP-001",
            nom="Rakoto",
            prenom="Aina",
            poste="Assistante RH",
            categorie_prof="Employe",
            indice="A1",
            salaire_base=850000,
            adresse="Antananarivo",
            cin="101010101010",
            date_naissance=date(1996, 5, 2),
            date_embauche=date(2026, 1, 2),
        )
        self.outsider_worker = models.Worker(
            employer_id=self.employer.id,
            matricule="EMP-002",
            nom="Rabe",
            prenom="Tiana",
            poste="Comptable",
            categorie_prof="Employe",
            indice="A2",
            salaire_base=950000,
        )
        self.db.add_all([self.worker, self.outsider_worker])
        self.db.flush()

        self.employee_user.worker_id = self.worker.id
        self.outsider_user.worker_id = self.outsider_worker.id

        self.contract = models.CustomContract(
            worker_id=self.worker.id,
            employer_id=self.employer.id,
            title="Contrat CDI",
            content="Contrat Assistante RH A1 850000",
            template_type="employment_contract",
            is_default=True,
        )
        self.db.add(self.contract)
        self.db.flush()

        self.portal_request = models.EmployeePortalRequest(
            employer_id=self.employer.id,
            worker_id=self.worker.id,
            created_by_user_id=self.employee_user.id,
            request_type="inspection_filing",
            destination="inspection",
            title="Reclamation paie",
            description="Demande de mediation",
            case_number=next_request_number(self.db, self.employer.id),
            history_json=append_history("[]", actor=self.employee_user, status="submitted", note="Initialisation"),
        )
        self.db.add(self.portal_request)
        self.db.flush()

        self.inspector_case = models.InspectorCase(
            case_number=next_inspector_case_number(self.db, self.employer.id),
            employer_id=self.employer.id,
            worker_id=self.worker.id,
            contract_id=self.contract.id,
            portal_request_id=self.portal_request.id,
            filed_by_user_id=self.employee_user.id,
            case_type="salary_dispute",
            source_party="employee",
            subject="Litige salaire",
            description="Salaire convenu a verifier",
            status="received",
            current_stage="filing",
            amicable_attempt_status="documented",
        )
        self.db.add(self.inspector_case)
        self.db.flush()

        self.db.add(
            models.InspectorMessage(
                case_id=self.inspector_case.id,
                employer_id=self.employer.id,
                author_user_id=self.employee_user.id,
                sender_role="employe",
                direction="employee_to_inspector",
                message_type="message",
                visibility="case_parties",
                body="Je joins ma reclamation.",
            )
        )

        cycle = models.PerformanceCycle(
            employer_id=self.employer.id,
            name="Campagne 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status="open",
            created_by_user_id=self.rh_user.id,
        )
        self.db.add(cycle)
        self.db.flush()

        review = models.PerformanceReview(
            cycle_id=cycle.id,
            employer_id=self.employer.id,
            worker_id=self.worker.id,
            reviewer_user_id=self.rh_user.id,
            status="manager_review",
            overall_score=3.8,
        )
        self.db.add(review)
        self.db.flush()

        training = models.TalentTraining(
            employer_id=self.employer.id,
            title="Excel RH",
            provider="Centre RH",
            duration_hours=14,
            status="planned",
        )
        self.db.add(training)
        self.db.flush()

        training_need = models.TrainingNeed(
            employer_id=self.employer.id,
            worker_id=self.worker.id,
            review_id=review.id,
            source="evaluation",
            priority="high",
            title="Monter en competence Excel",
            target_skill="Excel",
            recommended_training_id=training.id,
            due_date=date.today() - timedelta(days=2),
        )
        self.db.add(training_need)
        self.db.flush()

        plan = models.TrainingPlan(
            employer_id=self.employer.id,
            name="Plan 2026",
            plan_year=2026,
            created_by_user_id=self.rh_user.id,
        )
        self.db.add(plan)
        self.db.flush()

        self.db.add(
            models.TrainingPlanItem(
                training_plan_id=plan.id,
                need_id=training_need.id,
                worker_id=self.worker.id,
                status="planned",
            )
        )

        self.db.add(
            models.DisciplinaryCase(
                employer_id=self.employer.id,
                worker_id=self.worker.id,
                created_by_user_id=self.rh_user.id,
                subject="Avertissement",
                description="Retards repetes",
                status="open",
            )
        )
        self.db.add(
            models.TerminationWorkflow(
                employer_id=self.employer.id,
                worker_id=self.worker.id,
                contract_id=self.contract.id,
                created_by_user_id=self.rh_user.id,
                termination_type="economic_dismissal",
                motif="Reorganisation",
                status="draft",
                sensitive_case=True,
                inspection_required=True,
            )
        )
        self.db.add(
            models.DuerEntry(
                employer_id=self.employer.id,
                site_name="Antananarivo",
                risk_family="Ergonomie",
                hazard="Posture ecran",
                probability=2,
                severity=3,
                status="open",
            )
        )
        self.db.add(
            models.PreventionAction(
                employer_id=self.employer.id,
                action_title="Former a l'ergonomie",
                due_date=date.today() - timedelta(days=1),
                status="planned",
                inspection_follow_up=True,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_numbering_and_history_are_generated(self):
        self.assertTrue(self.portal_request.case_number.startswith("REQ-"))
        self.assertTrue(self.inspector_case.case_number.startswith("INS-"))
        self.assertIn("submitted", self.portal_request.history_json)

    def test_portal_dashboard_exposes_requests_cases_contracts_reviews_and_training(self):
        payload = build_portal_dashboard(self.db, self.worker)
        self.assertEqual(len(payload["requests"]), 1)
        self.assertEqual(len(payload["inspector_cases"]), 1)
        self.assertEqual(len(payload["contracts"]), 1)
        self.assertEqual(len(payload["performance_reviews"]), 1)
        self.assertEqual(len(payload["training_plan_items"]), 1)
        self.assertGreaterEqual(len(payload["notifications"]), 1)

    def test_hr_dashboard_aggregates_alerts_and_operational_counts(self):
        dashboard = build_hr_dashboard(self.db, self.employer.id)
        self.assertEqual(dashboard["workforce"]["workers_total"], 2)
        self.assertEqual(dashboard["performance"]["reviews_open"], 1)
        self.assertEqual(dashboard["training"]["needs_open"], 1)
        self.assertEqual(dashboard["discipline"]["terminations_open"], 1)
        self.assertTrue(any(alert["code"] == "inspection_cases_open" for alert in dashboard["alerts"]))
        self.assertTrue(any(alert["code"] == "training_needs_overdue" for alert in dashboard["alerts"]))

    def test_employee_scope_blocks_access_to_another_worker(self):
        with self.assertRaises(Exception):
            _assert_worker_scope(self.db, self.employee_user, self.outsider_worker)
        _assert_worker_scope(self.db, self.rh_user, self.outsider_worker)

    def test_labour_case_legal_summary_tracks_convocations_and_pv_deadline(self):
        now = datetime.now().astimezone().replace(tzinfo=None)
        self.inspector_case.received_at = now - timedelta(days=10)
        self.db.add_all(
            [
                models.LabourCaseEvent(
                    case_id=self.inspector_case.id,
                    employer_id=self.employer.id,
                    created_by_user_id=self.rh_user.id,
                    event_type="convocation",
                    title="Convocation 1",
                    status="completed",
                    metadata_json='{"attendance":"requester_absent"}',
                ),
                models.LabourCaseEvent(
                    case_id=self.inspector_case.id,
                    employer_id=self.employer.id,
                    created_by_user_id=self.rh_user.id,
                    event_type="convocation",
                    title="Convocation 2",
                    status="completed",
                    metadata_json='{"attendance":"respondent_absent"}',
                ),
            ]
        )
        self.db.commit()
        events = self.db.query(models.LabourCaseEvent).filter(models.LabourCaseEvent.case_id == self.inspector_case.id).all()
        summary = _build_labour_case_legal_summary(self.inspector_case, events, [])
        self.assertEqual(summary.convocation_count, 2)
        self.assertEqual(summary.no_show_convocation_count, 2)
        self.assertIn("conciliation", summary.eligible_pv_types)
        self.assertNotIn("carence", summary.eligible_pv_types)
        self.assertIsNotNone(summary.pv_due_at)
        self.assertTrue(any(alert.code == "inspection_prerequisite" for alert in summary.alerts))

    def test_termination_checklist_sets_preavis_from_letter_reception(self):
        notification_sent_at = datetime(2026, 4, 10, 8, 0, 0)
        notification_received_at = datetime(2026, 4, 12, 9, 30, 0)
        checklist, legal_metadata, readonly_stc, risk_level = _termination_checklist_payload(
            worker=self.worker,
            termination_type="economic_dismissal",
            motif="Baisse durable d'activite",
            effective_date=date(2026, 5, 30),
            notification_sent_at=notification_sent_at,
            notification_received_at=notification_received_at,
            pre_hearing_notice_sent_at=None,
            pre_hearing_scheduled_at=None,
            economic_consultation_started_at=date(2026, 4, 2),
            economic_inspection_referral_at=date(2026, 4, 24),
            technical_layoff_declared_at=None,
            technical_layoff_end_at=None,
        )
        self.assertEqual(legal_metadata["preavis_start_date"], "2026-04-12")
        self.assertGreaterEqual(readonly_stc["economic_indemnity_estimate"], 0)
        self.assertEqual(risk_level, "normal")
        self.assertTrue(any(item["code"] == "economic_referral" and item["done"] for item in checklist))


if __name__ == "__main__":
    unittest.main(verbosity=2)
