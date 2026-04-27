import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.config.config import Base
from app.routers.compliance import (
    create_formal_message,
    create_inspector_assignment,
    get_inspector_dashboard,
    list_formal_messages,
    list_inspector_employers,
    mark_formal_message_read,
    review_job_offer,
    send_formal_message,
)
from app.routers.employee_portal import create_inspector_case
from app.routers.recruitment import get_job_profile, submit_job_for_validation, upsert_job_profile


class InspectorPortalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(
            raison_sociale="SIH Mada Test",
            nif="123456",
            stat="987654",
            activite="BPO",
            contact_rh="RH Principal",
            email="rh@test.mg",
        )
        self.db.add(self.employer)
        self.db.flush()

        self.rh_user = models.AppUser(username="rh@test.mg", password_hash="hash", role_code="rh", employer_id=self.employer.id, is_active=True)
        self.employer_user = models.AppUser(username="admin@company.mg", password_hash="hash", role_code="employeur", employer_id=self.employer.id, is_active=True)
        self.inspector_user = models.AppUser(username="insp@mg.gov", password_hash="hash", role_code="inspecteur", is_active=True)
        self.employee_user = models.AppUser(username="agent@company.mg", password_hash="hash", role_code="employe", employer_id=self.employer.id, is_active=True)
        self.db.add_all([self.rh_user, self.employer_user, self.inspector_user, self.employee_user])
        self.db.flush()

        create_inspector_assignment(
            schemas.LabourInspectorAssignmentCreate(
                employer_id=self.employer.id,
                inspector_user_id=self.inspector_user.id,
                assignment_scope="portfolio",
                circonscription="Antananarivo I",
            ),
            db=self.db,
            user=self.rh_user,
        )

        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="EMP001",
            nom="Rakoto",
            prenom="Aina",
            poste="Assistante",
            salaire_base=800000,
            date_embauche=date(2026, 1, 5),
        )
        self.db.add(self.worker)
        self.db.flush()
        self.employee_user.worker_id = self.worker.id

        self.job = models.RecruitmentJobPosting(
            employer_id=self.employer.id,
            title="Charge RH",
            department="RH",
            location="Antananarivo",
            contract_type="CDI",
            status="draft",
            description="Besoin de renfort RH",
        )
        self.db.add(self.job)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_job_offer_review_workflow_and_dashboard(self):
        upsert_job_profile(
            self.job.id,
            schemas.RecruitmentJobProfileUpsert(
                manager_title="DRH",
                mission_summary="Gestion recrutement",
                main_activities=["Publier les offres"],
                technical_skills=["Excel"],
                behavioral_skills=["Rigueur"],
                publication_channels=["Email"],
                workflow_status="draft",
            ),
            db=self.db,
            user=self.rh_user,
        )

        submitted = submit_job_for_validation(self.job.id, db=self.db, user=self.rh_user)
        self.assertEqual(submitted.workflow_status, "en_revue_inspecteur")

        correction = review_job_offer(
            self.job.id,
            schemas.RecruitmentInspectorDecisionIn(action="request_correction", comment="Merci de preciser les horaires"),
            db=self.db,
            user=self.inspector_user,
        )
        self.assertEqual(correction.workflow_status, "needs_correction")

        resubmitted = submit_job_for_validation(self.job.id, db=self.db, user=self.rh_user)
        self.assertEqual(resubmitted.workflow_status, "en_revue_inspecteur")

        approved = review_job_offer(
            self.job.id,
            schemas.RecruitmentInspectorDecisionIn(action="approve", comment="Conforme"),
            db=self.db,
            user=self.inspector_user,
        )
        self.assertEqual(approved.workflow_status, "validated_with_observations")
        self.assertEqual(approved.validation_comment, "Conforme")

        dashboard = get_inspector_dashboard(employer_id=self.employer.id, status=None, db=self.db, user=self.inspector_user)
        self.assertEqual(dashboard.metrics["companies_followed"], 1)
        self.assertEqual(len(dashboard.recent_companies), 1)

        employers = list_inspector_employers(search="SIH", db=self.db, user=self.inspector_user)
        self.assertEqual(len(employers), 1)
        self.assertEqual(employers[0].id, self.employer.id)

        refreshed_profile = get_job_profile(self.job.id, db=self.db, user=self.rh_user)
        self.assertEqual(refreshed_profile.workflow_status, "validated_with_observations")

    def test_formal_message_and_case_creation_are_traceable(self):
        case_item = create_inspector_case(
            schemas.InspectorCaseCreate(
                employer_id=self.employer.id,
                worker_id=self.worker.id,
                case_type="salary_dispute",
                source_party="employee",
                subject="Retard salaire",
                description="Salaire non recu",
                category="non_paiement_salaire",
                urgency="high",
                is_sensitive=True,
            ),
            db=self.db,
            user=self.inspector_user,
        )
        self.assertEqual(case_item.category, "non_paiement_salaire")
        self.assertEqual(case_item.urgency, "high")
        self.assertTrue(case_item.is_sensitive)

        draft_message = create_formal_message(
            schemas.LabourFormalMessageCreate(
                subject="Demande de pieces",
                body="Merci de transmettre les bulletins et le contrat.",
                message_scope="individual",
                related_entity_type="inspector_case",
                related_entity_id=str(case_item.id),
                recipients=[schemas.LabourFormalMessageRecipientIn(employer_id=self.employer.id)],
                send_now=False,
            ),
            db=self.db,
            user=self.inspector_user,
        )
        self.assertEqual(draft_message.status, "draft")

        sent_message = send_formal_message(draft_message.id, db=self.db, user=self.inspector_user)
        self.assertEqual(sent_message.status, "sent")

        inbox = list_formal_messages(employer_id=self.employer.id, status=None, db=self.db, user=self.employer_user)
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0].subject, "Demande de pieces")

        read_message = mark_formal_message_read(sent_message.id, db=self.db, user=self.employer_user)
        self.assertEqual(read_message.recipients[0].status, "read")


if __name__ == "__main__":
    unittest.main(verbosity=2)
