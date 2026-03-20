import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.config.config import Base
from app.services.recruitment_assistant_service import (
    build_announcement_payload,
    build_contract_draft_html,
    ensure_recruitment_library,
    parse_candidate_profile,
    suggest_job_profile,
)


class RecruitmentAssistantServiceTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.SessionLocal = sessionmaker(bind=engine)
        self.db = self.SessionLocal()

        employer = models.Employer(raison_sociale="Demo Employer")
        self.db.add(employer)
        self.db.flush()
        self.employer = employer

        self.job = models.RecruitmentJobPosting(
            employer_id=employer.id,
            title="Assistant RH",
            department="Ressources humaines",
            location="Antananarivo",
            contract_type="CDI",
            salary_range="800000 - 1200000 MGA",
            description="Gestion administrative RH et suivi des dossiers salariés.",
        )
        self.db.add(self.job)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_suggest_job_profile_returns_editable_structured_draft(self):
        ensure_recruitment_library(self.db)
        result = suggest_job_profile(
            self.db,
            title="Assistant RH",
            department="Ressources humaines",
            description="Gestion administrative RH, congés, dossiers salariés et paie.",
            employer_id=self.employer.id,
        )
        self.assertEqual(result["probable_title"], "Assistant RH")
        self.assertEqual(result["probable_department"], "Ressources humaines")
        self.assertTrue(result["mission_summary"])
        self.assertIn("Excel", result["tools"])
        self.assertIn("Français", result["languages"])

    def test_parse_candidate_profile_extracts_email_phone_and_skills(self):
        ensure_recruitment_library(self.db)
        raw_text = (
            "Jean Rakoto\n"
            "jean.rakoto@example.com\n"
            "+261 34 12 345 67\n"
            "Bac+3 en informatique avec 3 ans en support utilisateur.\n"
            "Compétences: Excel, Python, SQL, Français, Anglais.\n"
        )
        result = parse_candidate_profile(raw_text, db=self.db, employer_id=self.employer.id)
        self.assertEqual(result["email"], "jean.rakoto@example.com")
        self.assertIn("+261 34 12 345 67", result["phone"])
        self.assertEqual(result["education_level"], "Bac+3")
        self.assertEqual(result["experience_years"], 3)
        self.assertIn("Python", result["technical_skills"])
        self.assertIn("Français", result["languages"])

    def test_build_announcement_payload_generates_multichannel_pack(self):
        profile = {
            "mission_summary": "Assurer l'administration RH et le suivi documentaire.",
            "main_activities": ["Préparer les dossiers", "Suivre les absences"],
            "technical_skills": ["Administration du personnel", "Excel"],
            "behavioral_skills": ["Rigueur", "Confidentialité"],
            "education_level": "Bac+3 RH",
            "experience_required": "2 ans",
            "languages": ["Français", "Malgache"],
            "tools": ["Excel", "SIRH"],
            "certifications": [],
            "benefits": ["Assurance santé"],
            "salary_min": 800000,
            "salary_max": 1200000,
            "application_deadline": "2026-04-15",
            "announcement_title": "Assistant RH confirmé",
        }
        payload = build_announcement_payload(self.job, profile)
        self.assertEqual(payload["title"], "Assistant RH confirmé")
        self.assertIn("Postulez", payload["facebook_text"])
        self.assertIn("LinkedIn", "LinkedIn " + payload["linkedin_text"])
        self.assertIn("non-discrimination", payload["web_body"])

    def test_build_contract_draft_html_links_candidate_job_and_employer(self):
        candidate = models.RecruitmentCandidate(
            employer_id=self.employer.id,
            first_name="Jean",
            last_name="Rakoto",
            email="jean.rakoto@example.com",
        )
        html = build_contract_draft_html(
            candidate,
            self.job,
            self.employer,
            {"mission_summary": "Support RH", "desired_start_date": "2026-04-01", "salary_min": 800000, "salary_max": 1200000},
        )
        self.assertIn("Jean Rakoto", html)
        self.assertIn("Assistant RH", html)
        self.assertIn("Demo Employer", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
