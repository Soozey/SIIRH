import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.config.config import Base
from app.routers.employee_portal import (
    create_labour_case_pv,
    create_inspector_case_assignment,
    download_labour_case_pv,
    get_inspection_document,
    get_inspection_case_workspace,
    list_inspector_cases,
)
from app.routers.messages import acknowledge_notice, create_channel, create_channel_message, create_notice, list_channel_messages
from app.services.employee_portal_service import next_inspector_case_number
from app.services.messages_service import build_messages_dashboard


class InspectionHardeningAndMessagesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="SIHMada Test", nif="123")
        self.db.add(self.employer)
        self.db.flush()

        self.rh_user = models.AppUser(username="rh", password_hash="hash", role_code="rh", employer_id=self.employer.id)
        self.employee_user = models.AppUser(username="emp", password_hash="hash", role_code="employe", employer_id=self.employer.id)
        self.inspector_a = models.AppUser(username="insp_a", password_hash="hash", role_code="inspecteur")
        self.inspector_b = models.AppUser(username="insp_b", password_hash="hash", role_code="inspecteur")
        self.db.add_all([self.rh_user, self.employee_user, self.inspector_a, self.inspector_b])
        self.db.flush()

        self.worker = models.Worker(
            employer_id=self.employer.id,
            matricule="EMP-900",
            nom="Rakoto",
            prenom="Hery",
            poste="Analyste RH",
            salaire_base=950000,
            adresse="Antananarivo",
            cin="101010101010",
            date_naissance=date(1995, 6, 20),
            date_embauche=date(2026, 1, 10),
        )
        self.db.add(self.worker)
        self.db.flush()
        self.employee_user.worker_id = self.worker.id

        self.case_a = models.InspectorCase(
            case_number=next_inspector_case_number(self.db, self.employer.id),
            employer_id=self.employer.id,
            worker_id=self.worker.id,
            filed_by_user_id=self.employee_user.id,
            case_type="general_claim",
            source_party="employee",
            subject="Litige A",
            description="Description A",
            status="received",
            current_stage="filing",
            amicable_attempt_status="documented",
            assigned_inspector_user_id=self.inspector_a.id,
        )
        self.case_b = models.InspectorCase(
            case_number=f"{next_inspector_case_number(self.db, self.employer.id)}-B",
            employer_id=self.employer.id,
            worker_id=self.worker.id,
            filed_by_user_id=self.employee_user.id,
            case_type="general_claim",
            source_party="employee",
            subject="Litige B",
            description="Description B",
            status="received",
            current_stage="filing",
            amicable_attempt_status="documented",
            assigned_inspector_user_id=self.inspector_b.id,
        )
        self.db.add_all([self.case_a, self.case_b])
        self.db.flush()

        self.db.add(
            models.InspectorCaseAssignment(
                case_id=self.case_a.id,
                inspector_user_id=self.inspector_a.id,
                assigned_by_user_id=self.rh_user.id,
                scope="lead",
                status="active",
            )
        )

        self.document = models.InspectionDocument(
            case_id=self.case_a.id,
            employer_id=self.employer.id,
            uploaded_by_user_id=self.rh_user.id,
            document_type="contract_review",
            title="Contrat soumis",
            visibility="case_parties",
            confidentiality="restricted",
            status="active",
            current_version_number=1,
        )
        self.db.add(self.document)
        self.db.flush()
        self.db.add(
            models.InspectionDocumentVersion(
                document_id=self.document.id,
                case_id=self.case_a.id,
                employer_id=self.employer.id,
                uploaded_by_user_id=self.rh_user.id,
                version_number=1,
                file_name="contrat_v1.pdf",
                original_name="contrat.pdf",
                storage_path="inspection_vault/test/contrat_v1.pdf",
                static_url="/static/inspection_vault/test/contrat_v1.pdf",
                content_type="application/pdf",
                file_size=1024,
                checksum="abc123",
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_inspector_only_sees_assigned_cases(self):
        items = list_inspector_cases(employer_id=None, worker_id=None, status=None, db=self.db, user=self.inspector_a)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, self.case_a.id)

    def test_assignment_endpoint_sets_primary_inspector(self):
        response = create_inspector_case_assignment(
            self.case_b.id,
            schemas.InspectorCaseAssignmentCreate(inspector_user_id=self.inspector_a.id, scope="backup", notes="Renfort"),
            db=self.db,
            user=self.rh_user,
        )
        refreshed = self.db.query(models.InspectorCase).filter(models.InspectorCase.id == self.case_b.id).first()
        self.assertEqual(refreshed.assigned_inspector_user_id, self.inspector_a.id)
        self.assertEqual(response.status, "active")
        self.assertEqual(response.scope, "backup")

    def test_document_access_is_logged_when_viewed(self):
        get_inspection_document(self.document.id, db=self.db, user=self.inspector_a)
        logs = (
            self.db.query(models.InspectionDocumentAccessLog)
            .filter(models.InspectionDocumentAccessLog.document_id == self.document.id)
            .all()
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].action, "view")

    def test_internal_messages_and_notices_are_separate_and_trackable(self):
        channel = create_channel(
            schemas.InternalMessageChannelCreate(
                employer_id=self.employer.id,
                title="Coordination RH",
                description="Canal interne RH",
                member_user_ids=[self.employee_user.id],
            ),
            db=self.db,
            user=self.rh_user,
        )
        create_channel_message(
            channel.id,
            schemas.InternalMessageCreate(body="Message interne"),
            db=self.db,
            user=self.employee_user,
        )
        messages = list_channel_messages(channel.id, db=self.db, user=self.rh_user)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].body, "Message interne")

        notice = create_notice(
            schemas.InternalNoticeCreate(
                employer_id=self.employer.id,
                title="Affichage obligatoire",
                body="Le reglement interieur est disponible au RH.",
                ack_required=True,
            ),
            db=self.db,
            user=self.rh_user,
        )
        acknowledged = acknowledge_notice(notice.id, db=self.db, user=self.employee_user)
        dashboard = build_messages_dashboard(self.db, user=self.employee_user, employer_id=self.employer.id)

        self.assertTrue(acknowledged.acknowledged_by_current_user)
        self.assertEqual(dashboard["active_channels"], 1)
        self.assertEqual(dashboard["pending_acknowledgements"], 0)

    def test_carence_pv_requires_three_convocations(self):
        self.db.add_all(
            [
                models.LabourCaseEvent(
                    case_id=self.case_a.id,
                    employer_id=self.employer.id,
                    created_by_user_id=self.inspector_a.id,
                    event_type="convocation",
                    title="Convocation 1",
                    status="completed",
                    metadata_json='{"attendance":"requester_absent"}',
                ),
                models.LabourCaseEvent(
                    case_id=self.case_a.id,
                    employer_id=self.employer.id,
                    created_by_user_id=self.inspector_a.id,
                    event_type="convocation",
                    title="Convocation 2",
                    status="completed",
                    metadata_json='{"attendance":"both_absent"}',
                ),
            ]
        )
        self.db.commit()
        with self.assertRaises(Exception):
            create_labour_case_pv(
                self.case_a.id,
                schemas.LabourPVCreate(pv_type="carence", status="issued"),
                db=self.db,
                user=self.inspector_a,
            )

    def test_workspace_exposes_legal_summary_and_pv_download(self):
        self.db.add_all(
            [
                models.LabourCaseEvent(
                    case_id=self.case_a.id,
                    employer_id=self.employer.id,
                    created_by_user_id=self.inspector_a.id,
                    event_type="convocation",
                    title="Convocation 1",
                    status="completed",
                    metadata_json='{"attendance":"requester_absent"}',
                ),
                models.LabourCaseEvent(
                    case_id=self.case_a.id,
                    employer_id=self.employer.id,
                    created_by_user_id=self.inspector_a.id,
                    event_type="convocation",
                    title="Convocation 2",
                    status="completed",
                    metadata_json='{"attendance":"respondent_absent"}',
                ),
                models.LabourCaseEvent(
                    case_id=self.case_a.id,
                    employer_id=self.employer.id,
                    created_by_user_id=self.inspector_a.id,
                    event_type="convocation",
                    title="Convocation 3",
                    status="completed",
                    metadata_json='{"attendance":"both_absent"}',
                ),
            ]
        )
        self.db.commit()
        pv = create_labour_case_pv(
            self.case_a.id,
            schemas.LabourPVCreate(pv_type="carence", status="issued"),
            db=self.db,
            user=self.inspector_a,
        )
        workspace = get_inspection_case_workspace(self.case_a.id, db=self.db, user=self.inspector_a)
        self.assertTrue(workspace.legal_summary.requires_inspection_before_court)
        self.assertIn("carence", workspace.legal_summary.eligible_pv_types)
        response = download_labour_case_pv(self.case_a.id, pv.id, db=self.db, user=self.inspector_a)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertGreater(len(response.body), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
