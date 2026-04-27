import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.routers.recruitment import list_publication_channels
from app.services.recruitment_publication_service import get_or_create_publication_channels, publish_job_channels


class RecruitmentPublicationFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="Karibo Services")
        self.db.add(self.employer)
        self.db.flush()

        self.user = models.AppUser(
            username="rh-publication@example.com",
            password_hash="hash",
            role_code="rh",
            employer_id=self.employer.id,
            is_active=True,
        )
        self.db.add(self.user)
        self.db.flush()

        self.job = models.RecruitmentJobPosting(
            employer_id=self.employer.id,
            title="Chargé de recrutement",
            department="Ressources humaines",
            location="Antananarivo",
            contract_type="CDI",
            description="Pilotage du sourcing et des entretiens.",
        )
        self.db.add(self.job)
        self.db.flush()

        self.profile = models.RecruitmentJobProfile(
            job_posting_id=self.job.id,
            mission_summary="Conduire les publications d'offres et la sélection.",
            main_activities_json='["Publier","Sélectionner"]',
            technical_skills_json='["Sourcing","Entretien"]',
            behavioral_skills_json='["Rigueur","Communication"]',
            languages_json='["Français"]',
            tools_json='["SIIRH"]',
            benefits_json='["Mutuelle"]',
            interview_criteria_json='["Traçabilité"]',
        )
        self.db.add(self.profile)

        self.candidate = models.RecruitmentCandidate(
            employer_id=self.employer.id,
            first_name="Miora",
            last_name="Rakoto",
            email="miora.rakoto@example.com",
        )
        self.db.add(self.candidate)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_list_publication_channels_masks_secrets(self):
        channels = get_or_create_publication_channels(self.db, self.employer.id)
        facebook = next(item for item in channels if item.channel_type == "facebook")
        facebook.config_json = '{"page_name": "Karibo RH", "access_token": "super-secret"}'
        self.db.commit()

        payload = list_publication_channels(employer_id=self.employer.id, db=self.db, user=self.user)
        facebook_payload = next(item for item in payload if item.channel_type == "facebook")
        self.assertEqual(facebook_payload.config.get("page_name"), "Karibo RH")
        self.assertNotIn("super-secret", str(facebook_payload.config))
        self.assertIn("access_token", facebook_payload.secret_fields_configured)

    def test_publish_job_channels_creates_logs_and_updates_status(self):
        channels = get_or_create_publication_channels(self.db, self.employer.id)
        site_interne = next(item for item in channels if item.channel_type == "site_interne")
        email = next(item for item in channels if item.channel_type == "email")
        site_interne.is_active = True
        site_interne.default_publish = True
        email.is_active = True
        email.default_publish = True
        email.config_json = '{"sender_email": "rh@karibo.mg", "audience_emails": ["talent@karibo.mg"]}'
        self.job.publish_channels_json = '["site_interne","email"]'
        self.db.commit()

        logs = publish_job_channels(
            self.db,
            job=self.job,
            profile=self.profile,
            user=self.user,
            requested_channels=["site_interne", "email"],
        )
        self.db.commit()

        self.assertEqual(len(logs), 2)
        self.assertTrue(all(item.status == "success" for item in logs))
        self.assertEqual(self.job.publish_status, "published")
        self.assertEqual(self.job.status, "published")
        self.assertEqual(self.profile.announcement_status, "published")
        self.assertIn("site_interne", self.job.publish_channels_json)
        self.assertIn("email", self.job.publish_channels_json)
        stored_logs = (
            self.db.query(models.RecruitmentPublicationLog)
            .filter(models.RecruitmentPublicationLog.job_id == self.job.id)
            .all()
        )
        self.assertEqual(len(stored_logs), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
