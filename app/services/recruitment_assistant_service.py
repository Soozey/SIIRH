import json
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from .. import models
from ..config.config import settings


SYSTEM_LIBRARY_ITEMS = [
    {
        "category": "job_template",
        "label": "Assistant RH",
        "description": "Support administratif RH, dossiers salariés et suivi du cycle de vie.",
        "payload": {
            "department": "Ressources humaines",
            "mission_summary": "Assurer l'administration RH quotidienne, la tenue des dossiers salariés et le support aux processus RH.",
            "main_activities": [
                "Préparer les dossiers d'embauche et de sortie",
                "Mettre à jour les dossiers salariés et les attestations",
                "Suivre les absences, congés et pièces justificatives",
                "Appuyer la préparation des éléments variables de paie",
            ],
            "technical_skills": ["Administration du personnel", "Droit social", "Excel", "Archivage RH"],
            "behavioral_skills": ["Rigueur", "Confidentialité", "Sens du service", "Organisation"],
            "education_level": "Bac+3 en RH, droit ou gestion",
            "experience_required": "2 ans d'expérience sur un poste RH opérationnel",
            "languages": ["Français", "Malgache"],
            "tools": ["Excel", "Word", "SIRH"],
            "interview_criteria": [
                "Fiabilité documentaire",
                "Capacité à gérer plusieurs dossiers",
                "Sens de la confidentialité",
            ],
        },
    },
    {
        "category": "job_template",
        "label": "Comptable",
        "description": "Tenue comptable, rapprochements et production des états.",
        "payload": {
            "department": "Finance / Comptabilité",
            "mission_summary": "Garantir la fiabilité des écritures comptables, des rapprochements et des obligations déclaratives.",
            "main_activities": [
                "Saisir et contrôler les écritures comptables",
                "Préparer les rapprochements bancaires",
                "Suivre les déclarations fiscales et sociales",
                "Produire les états de clôture mensuelle",
            ],
            "technical_skills": ["Comptabilité générale", "Fiscalité", "Excel avancé", "Analyse de comptes"],
            "behavioral_skills": ["Précision", "Fiabilité", "Esprit d'analyse", "Respect des délais"],
            "education_level": "Bac+3 en comptabilité, finance ou gestion",
            "experience_required": "3 ans d'expérience en comptabilité",
            "languages": ["Français", "Malgache"],
            "tools": ["Excel", "Logiciel comptable", "ERP"],
            "interview_criteria": ["Maîtrise des écritures", "Contrôle interne", "Lecture des états financiers"],
        },
    },
    {
        "category": "job_template",
        "label": "Développeur",
        "description": "Conception logicielle, qualité de code et livraison applicative.",
        "payload": {
            "department": "Informatique / SI",
            "mission_summary": "Concevoir, développer et maintenir des applications fiables et maintenables.",
            "main_activities": [
                "Développer des fonctionnalités backend et frontend",
                "Corriger les anomalies et écrire des tests",
                "Participer aux revues de code et aux déploiements",
                "Documenter les évolutions techniques",
            ],
            "technical_skills": ["Python ou TypeScript", "API REST", "SQL", "Tests automatisés"],
            "behavioral_skills": ["Résolution de problèmes", "Autonomie", "Travail en équipe", "Apprentissage continu"],
            "education_level": "Bac+3 à Bac+5 en informatique",
            "experience_required": "2 à 4 ans d'expérience en développement logiciel",
            "languages": ["Français", "Anglais technique"],
            "tools": ["Git", "VS Code", "PostgreSQL", "Docker"],
            "interview_criteria": ["Qualité de code", "Architecture", "Débogage", "Communication technique"],
        },
    },
    {
        "category": "job_template",
        "label": "Chauffeur",
        "description": "Transport sécurisé de personnes, documents ou marchandises.",
        "payload": {
            "department": "Logistique",
            "mission_summary": "Assurer les déplacements, livraisons et transports en toute sécurité tout en garantissant l'entretien du véhicule.",
            "main_activities": [
                "Réaliser les trajets planifiés",
                "Contrôler l'état du véhicule et signaler les anomalies",
                "Gérer les documents de transport",
                "Respecter les consignes de sécurité et les délais",
            ],
            "technical_skills": ["Conduite sécurisée", "Entretien courant du véhicule", "Lecture de planning", "Gestion documentaire"],
            "behavioral_skills": ["Ponctualité", "Prudence", "Discrétion", "Courtoisie"],
            "education_level": "Permis adapté et niveau secondaire",
            "experience_required": "2 ans d'expérience en conduite professionnelle",
            "languages": ["Français", "Malgache"],
            "tools": ["GPS", "Téléphone professionnel"],
            "interview_criteria": ["Antécédents de conduite", "Gestion du stress", "Connaissance des itinéraires"],
        },
    },
    {
        "category": "job_template",
        "label": "Magasinier",
        "description": "Gestion des stocks, réception et préparation des mouvements.",
        "payload": {
            "department": "Logistique",
            "mission_summary": "Piloter la réception, le stockage et la sortie des articles en garantissant la fiabilité des stocks.",
            "main_activities": [
                "Réceptionner et contrôler les marchandises",
                "Enregistrer les mouvements de stock",
                "Préparer les sorties et inventaires",
                "Signaler les écarts et produits sensibles",
            ],
            "technical_skills": ["Gestion de stock", "Inventaire", "Contrôle quantitatif", "Traçabilité"],
            "behavioral_skills": ["Méthode", "Vigilance", "Discipline", "Fiabilité"],
            "education_level": "Niveau secondaire ou technique",
            "experience_required": "1 à 2 ans en magasin ou entrepôt",
            "languages": ["Français", "Malgache"],
            "tools": ["Excel", "ERP stock", "Lecteur code-barres"],
            "interview_criteria": ["Rigueur inventaire", "Organisation physique", "Sécurité stock"],
        },
    },
    {
        "category": "job_template",
        "label": "Commercial",
        "description": "Développement commercial, prospection et suivi portefeuille.",
        "payload": {
            "department": "Commercial / Marketing",
            "mission_summary": "Développer le portefeuille client et sécuriser le chiffre d'affaires par une prospection structurée.",
            "main_activities": [
                "Prospecter et qualifier les opportunités",
                "Préparer les offres commerciales",
                "Suivre le portefeuille client et les relances",
                "Remonter les tendances marché et besoins clients",
            ],
            "technical_skills": ["Prospection", "Négociation", "CRM", "Suivi d'offres"],
            "behavioral_skills": ["Aisance relationnelle", "Persuasion", "Résilience", "Orientation résultat"],
            "education_level": "Bac+2 à Bac+3 commercial ou marketing",
            "experience_required": "2 ans d'expérience en vente ou développement commercial",
            "languages": ["Français", "Malgache"],
            "tools": ["CRM", "Excel", "PowerPoint"],
            "interview_criteria": ["Capacité de vente", "Gestion pipeline", "Argumentation"],
        },
    },
    {
        "category": "job_template",
        "label": "Agent administratif",
        "description": "Gestion de dossiers, courriers et support administratif transversal.",
        "payload": {
            "department": "Administration",
            "mission_summary": "Garantir le traitement administratif des dossiers et la fluidité des échanges internes.",
            "main_activities": [
                "Saisir et mettre à jour les données administratives",
                "Classer et archiver les pièces",
                "Préparer les courriers et comptes rendus",
                "Assister les responsables dans le suivi des dossiers",
            ],
            "technical_skills": ["Bureautique", "Classement", "Rédaction administrative", "Saisie de données"],
            "behavioral_skills": ["Organisation", "Discrétion", "Fiabilité", "Polyvalence"],
            "education_level": "Bac à Bac+2 en administration ou gestion",
            "experience_required": "1 à 2 ans sur un poste administratif",
            "languages": ["Français", "Malgache"],
            "tools": ["Word", "Excel", "Messagerie"],
            "interview_criteria": ["Qualité documentaire", "Gestion de volume", "Communication écrite"],
        },
    },
    {
        "category": "job_template",
        "label": "Responsable paie",
        "description": "Pilotage de la paie, contrôles et conformité sociale.",
        "payload": {
            "department": "Ressources humaines",
            "mission_summary": "Superviser la production de paie, sécuriser les contrôles et garantir la conformité sociale.",
            "main_activities": [
                "Piloter le calendrier de paie et les contrôles mensuels",
                "Valider les éléments variables et anomalies",
                "Superviser les déclarations sociales",
                "Accompagner les audits et évolutions réglementaires",
            ],
            "technical_skills": ["Paie", "Déclarations sociales", "Contrôle de masse salariale", "Excel avancé"],
            "behavioral_skills": ["Leadership", "Rigueur", "Confidentialité", "Capacité d'arbitrage"],
            "education_level": "Bac+3 à Bac+5 RH, gestion ou finance",
            "experience_required": "5 ans d'expérience en paie dont management ou supervision",
            "languages": ["Français", "Malgache"],
            "tools": ["SIRH", "Excel", "Outils de reporting"],
            "interview_criteria": ["Contrôle paie", "Maîtrise réglementaire", "Gestion d'équipe"],
        },
    },
    {
        "category": "job_template",
        "label": "Juriste",
        "description": "Conseil juridique, conformité et rédaction d'actes.",
        "payload": {
            "department": "Juridique",
            "mission_summary": "Sécuriser les actes, contrats et décisions de l'entreprise sur les volets droit du travail et conformité.",
            "main_activities": [
                "Rédiger et relire les contrats et documents juridiques",
                "Conseiller les directions sur les risques",
                "Gérer les contentieux et précontentieux",
                "Assurer la veille réglementaire",
            ],
            "technical_skills": ["Droit du travail", "Rédaction contractuelle", "Veille juridique", "Gestion contentieuse"],
            "behavioral_skills": ["Analyse", "Discrétion", "Argumentation", "Esprit critique"],
            "education_level": "Master en droit",
            "experience_required": "3 ans d'expérience en cabinet ou entreprise",
            "languages": ["Français", "Malgache"],
            "tools": ["Outils de recherche juridique", "Word", "Excel"],
            "interview_criteria": ["Analyse de risque", "Clarté rédactionnelle", "Réflexes conformité"],
        },
    },
    {
        "category": "job_template",
        "label": "Technicien support",
        "description": "Support utilisateur, diagnostic et résolution d'incidents.",
        "payload": {
            "department": "Informatique / SI",
            "mission_summary": "Assurer l'assistance utilisateur, la résolution des incidents et la continuité du poste de travail.",
            "main_activities": [
                "Diagnostiquer les incidents et demandes utilisateurs",
                "Assurer l'installation et le paramétrage des postes",
                "Documenter les interventions et escalader si besoin",
                "Suivre les tickets jusqu'à résolution",
            ],
            "technical_skills": ["Support utilisateur", "Réseaux de base", "Windows", "Gestion de tickets"],
            "behavioral_skills": ["Pédagogie", "Patience", "Réactivité", "Sens du service"],
            "education_level": "Bac+2 en informatique ou support",
            "experience_required": "1 à 3 ans en helpdesk ou support IT",
            "languages": ["Français", "Malgache"],
            "tools": ["Outil de ticketing", "Active Directory", "Remote support"],
            "interview_criteria": ["Diagnostic", "Relation utilisateur", "Priorisation"],
        },
    },
]

SYSTEM_REFERENCE_VALUES = {
    "department": [
        "Ressources humaines",
        "Finance / Comptabilité",
        "Informatique / SI",
        "Commercial / Marketing",
        "Logistique",
        "Juridique",
        "Administration",
        "Production",
        "Direction",
    ],
    "location": [
        "Antananarivo",
        "Toamasina",
        "Mahajanga",
        "Fianarantsoa",
        "Toliara",
        "Antsiranana",
        "Nosy Be",
    ],
    "contract_type": ["CDI", "CDD", "Stage", "Consultant", "Prestataire", "Temps partiel", "Temps plein"],
    "status": ["Cadre", "Non cadre", "Agent", "Ouvrier", "Manager", "Direction", "Stagiaire"],
    "publication_channel": ["E-mail", "Lien public", "PDF", "Facebook", "LinkedIn", "WhatsApp"],
    "language": ["Français", "Malgache", "Anglais"],
    "education_level": ["Niveau secondaire", "Bac", "Bac+2", "Bac+3", "Master"],
    "experience_level": ["Débutant", "1 à 2 ans", "3 à 5 ans", "5 ans et plus"],
}


def _normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").strip().lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def _json_load(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def ensure_recruitment_library(db) -> None:
    existing = db.query(models.RecruitmentLibraryItem).filter(models.RecruitmentLibraryItem.is_system == True).count()
    if existing:
        return

    for item in SYSTEM_LIBRARY_ITEMS:
        db.add(
            models.RecruitmentLibraryItem(
                employer_id=None,
                category=item["category"],
                label=item["label"],
                normalized_key=_normalize_key(item["label"]),
                description=item.get("description"),
                payload_json=json_dump(item.get("payload", {})),
                is_system=True,
                is_active=True,
            )
        )

    for category, values in SYSTEM_REFERENCE_VALUES.items():
        for value in values:
            db.add(
                models.RecruitmentLibraryItem(
                    employer_id=None,
                    category=category,
                    label=value,
                    normalized_key=_normalize_key(value),
                    description=None,
                    payload_json=json_dump({"value": value}),
                    is_system=True,
                    is_active=True,
                )
            )

    db.commit()


def get_library_entries(db, employer_id=None, category=None):
    ensure_recruitment_library(db)
    query = db.query(models.RecruitmentLibraryItem).filter(models.RecruitmentLibraryItem.is_active == True)
    if category:
        query = query.filter(models.RecruitmentLibraryItem.category == category)
    if employer_id:
        query = query.filter(
            (models.RecruitmentLibraryItem.employer_id == employer_id)
            | (models.RecruitmentLibraryItem.employer_id.is_(None))
        )
    else:
        query = query.filter(models.RecruitmentLibraryItem.employer_id.is_(None))
    return query.order_by(models.RecruitmentLibraryItem.category.asc(), models.RecruitmentLibraryItem.label.asc()).all()


def _match_job_templates(db, title: str, department: str, description: str, employer_id=None):
    entries = get_library_entries(db, employer_id=employer_id, category="job_template")
    haystack = f"{title} {department} {description}".lower()
    matches = []
    normalized_haystack = _normalize_key(haystack).replace("-", " ")
    for entry in entries:
        entry_key = entry.normalized_key.replace("-", " ")
        if entry.label.lower() in haystack or entry_key in normalized_haystack:
            matches.append(entry)
    if not matches and title:
        title_key = _normalize_key(title)
        matches = [entry for entry in entries if title_key in entry.normalized_key or entry.normalized_key in title_key]
    return matches[:3]


def suggest_job_profile(db, *, title: str, department: str = "", description: str = "", employer_id=None):
    matches = _match_job_templates(db, title, department, description, employer_id=employer_id)
    suggested = {
        "probable_title": title or (matches[0].label if matches else ""),
        "probable_department": department or "",
        "mission_summary": "",
        "main_activities": [],
        "technical_skills": [],
        "behavioral_skills": [],
        "education_level": "",
        "experience_required": "",
        "languages": [],
        "tools": [],
        "certifications": [],
        "interview_criteria": [],
        "suggestion_sources": [],
    }

    if matches:
        top_payload = _json_load(matches[0].payload_json, {})
        suggested["probable_department"] = department or top_payload.get("department", "")
        suggested["mission_summary"] = top_payload.get("mission_summary", "")
        suggested["main_activities"] = list(top_payload.get("main_activities", []))
        suggested["technical_skills"] = list(top_payload.get("technical_skills", []))
        suggested["behavioral_skills"] = list(top_payload.get("behavioral_skills", []))
        suggested["education_level"] = top_payload.get("education_level", "")
        suggested["experience_required"] = top_payload.get("experience_required", "")
        suggested["languages"] = list(top_payload.get("languages", []))
        suggested["tools"] = list(top_payload.get("tools", []))
        suggested["certifications"] = list(top_payload.get("certifications", []))
        suggested["interview_criteria"] = list(top_payload.get("interview_criteria", []))
        suggested["suggestion_sources"].append(matches[0].label)

    department_key = _normalize_key(department)
    department_map = {
        "ressources-humaines": ["Administration du personnel", "Droit social", "Confidentialité", "Sens du service"],
        "finance-comptabilite": ["Comptabilité", "Contrôle interne", "Excel avancé", "Fiabilité"],
        "informatique-si": ["Support applicatif", "SQL", "Documentation", "Résolution de problèmes"],
        "commercial-marketing": ["Prospection", "CRM", "Négociation", "Orientation résultat"],
        "logistique": ["Gestion de stock", "Traçabilité", "Sécurité", "Rigueur"],
        "juridique": ["Droit du travail", "Analyse", "Rédaction", "Veille juridique"],
        "administration": ["Bureautique", "Classement", "Organisation", "Qualité documentaire"],
        "production": ["Sécurité", "Qualité", "Procédures", "Discipline"],
        "direction": ["Pilotage", "Leadership", "Reporting", "Décision"],
    }
    for key, values in department_map.items():
        if key in department_key:
            for value in values[:2]:
                if value not in suggested["technical_skills"]:
                    suggested["technical_skills"].append(value)
            for value in values[2:]:
                if value not in suggested["behavioral_skills"]:
                    suggested["behavioral_skills"].append(value)
            if not suggested["probable_department"]:
                suggested["probable_department"] = department

    keyword_map = {
        "paie": ("Responsable paie", ["Contrôle paie", "Déclarations sociales"], ["Confidentialité"], "Bac+3 à Bac+5 RH, gestion ou finance", "3 à 5 ans"),
        "excel": ("Analyste RH", ["Excel avancé"], ["Rigueur"], "", ""),
        "support": ("Technicien support", ["Support utilisateur"], ["Pédagogie"], "", ""),
        "recrut": ("Chargé de recrutement", ["Sourcing", "Entretien"], ["Communication"], "", ""),
        "jurid": ("Juriste", ["Droit du travail"], ["Analyse"], "", ""),
    }
    description_lower = (description or "").lower()
    for keyword, payload in keyword_map.items():
        if keyword in description_lower:
            probable_title, technical_skills, behavioral_skills, education_level, experience = payload
            if not suggested["probable_title"]:
                suggested["probable_title"] = probable_title
            for value in technical_skills:
                if value not in suggested["technical_skills"]:
                    suggested["technical_skills"].append(value)
            for value in behavioral_skills:
                if value not in suggested["behavioral_skills"]:
                    suggested["behavioral_skills"].append(value)
            if education_level and not suggested["education_level"]:
                suggested["education_level"] = education_level
            if experience and not suggested["experience_required"]:
                suggested["experience_required"] = experience

    return suggested


def _slugify(value: str) -> str:
    return _normalize_key(value) or "offre"


def build_announcement_payload(job, profile: dict) -> dict:
    title = (profile.get("announcement_title") or job.title or "Offre d'emploi").strip()
    mission_summary = profile.get("mission_summary") or job.description or ""
    activities = profile.get("main_activities", [])
    technical_skills = profile.get("technical_skills", [])
    behavioral_skills = profile.get("behavioral_skills", [])
    languages = profile.get("languages", [])
    tools = profile.get("tools", [])
    certifications = profile.get("certifications", [])
    benefits = profile.get("benefits", [])
    salary_min = profile.get("salary_min")
    salary_max = profile.get("salary_max")
    salary_range = ""
    if salary_min is not None or salary_max is not None:
        salary_range = f"{salary_min or 0:,.0f} - {salary_max or salary_min or 0:,.0f} MGA"
    elif job.salary_range:
        salary_range = job.salary_range

    requirements = []
    if profile.get("education_level"):
        requirements.append(f"Niveau d'études: {profile['education_level']}")
    if profile.get("experience_required"):
        requirements.append(f"Expérience: {profile['experience_required']}")
    if technical_skills:
        requirements.append("Compétences techniques: " + ", ".join(technical_skills))
    if behavioral_skills:
        requirements.append("Compétences comportementales: " + ", ".join(behavioral_skills))
    if languages:
        requirements.append("Langues: " + ", ".join(languages))
    if tools:
        requirements.append("Outils / logiciels: " + ", ".join(tools))
    if certifications:
        requirements.append("Certifications: " + ", ".join(certifications))

    publication_deadline = profile.get("application_deadline") or ""
    public_link = f"{settings.APP_PUBLIC_URL.rstrip('/')}/careers/{job.id}-{_slugify(title)}"
    body_lines = [
        mission_summary,
        "",
        "Responsabilités:",
        *[f"- {item}" for item in activities],
        "",
        "Profil recherché:",
        *[f"- {item}" for item in requirements],
    ]
    if benefits:
        body_lines.extend(["", "Avantages:", *[f"- {item}" for item in benefits]])
    body_lines.extend([
        "",
        "Engagement de non-discrimination: toutes les candidatures sont étudiées sans distinction de genre, origine, situation familiale ou handicap.",
    ])
    if salary_range:
        body_lines.extend(["", f"Fourchette salariale: {salary_range}"])
    if publication_deadline:
        body_lines.append(f"Date limite de candidature: {publication_deadline}")

    web_body = "\n".join([line for line in body_lines if line is not None]).strip()
    email_subject = f"Ouverture de poste - {title}"
    email_body = (
        f"Bonjour,\n\nNous recrutons actuellement pour le poste de {title}.\n\n"
        f"{web_body}\n\nCandidature via: {public_link}\n"
    )
    facebook_text = f"{title} | {job.location or 'Madagascar'} | {job.contract_type}.\n{mission_summary}\nPostulez ici: {public_link}"
    linkedin_text = (
        f"Nous recrutons un(e) {title} pour renforcer {job.department or profile.get('probable_department') or 'notre équipe'}.\n"
        f"{mission_summary}\n"
        f"Compétences clés: {', '.join(technical_skills[:5])}\n"
        f"Postulez: {public_link}"
    )
    whatsapp_text = f"Offre {title} - {mission_summary} - Lien: {public_link}"

    return {
        "title": title,
        "slug": _slugify(title),
        "public_url": public_link,
        "web_body": web_body,
        "email_subject": email_subject,
        "email_body": email_body,
        "facebook_text": facebook_text,
        "linkedin_text": linkedin_text,
        "whatsapp_text": whatsapp_text,
        "copy_text": web_body,
    }


def extract_text_from_upload(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".txt", ".md"}:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")

    if suffix == ".docx":
        with ZipFile(BytesIO(file_bytes)) as archive:
            xml_content = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", " ", xml_content)
        return re.sub(r"\s+", " ", text).strip()

    return ""


def parse_candidate_profile(raw_text: str, db=None, employer_id=None) -> dict:
    text = raw_text or ""
    lowered = text.lower()
    profile = {
        "email": "",
        "phone": "",
        "languages": [],
        "technical_skills": [],
        "tools": [],
        "education_level": "",
        "experience_years": 0,
        "summary": text[:320].strip(),
    }

    email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
    if email_match:
        profile["email"] = email_match.group(0)

    phone_match = re.search(r"(\+?\d[\d\s\-]{7,}\d)", text)
    if phone_match:
        profile["phone"] = phone_match.group(1).strip()

    years_match = re.search(r"(\d+)\s*(ans|years)", lowered)
    if years_match:
        profile["experience_years"] = int(years_match.group(1))

    education_keywords = [
        ("master", "Master"),
        ("bac+5", "Bac+5"),
        ("bac+3", "Bac+3"),
        ("licence", "Licence"),
        ("bts", "BTS"),
        ("bac", "Bac"),
    ]
    for keyword, label in education_keywords:
        if keyword in lowered:
            profile["education_level"] = label
            break

    for language in SYSTEM_REFERENCE_VALUES["language"]:
        if language.lower() in lowered and language not in profile["languages"]:
            profile["languages"].append(language)

    if db is not None:
        for entry in get_library_entries(db, employer_id=employer_id):
            if entry.category in {"technical_skill", "tool"} and entry.label.lower() in lowered:
                bucket = "tools" if entry.category == "tool" else "technical_skills"
                if entry.label not in profile[bucket]:
                    profile[bucket].append(entry.label)

    generic_skills = ["Excel", "Word", "SIRH", "SQL", "Python", "Support utilisateur", "Recrutement", "Paie"]
    for skill in generic_skills:
        if skill.lower() in lowered and skill not in profile["technical_skills"]:
            profile["technical_skills"].append(skill)

    return profile


def build_contract_draft_html(candidate, job, employer, profile: dict) -> str:
    salary_min = profile.get("salary_min")
    salary_max = profile.get("salary_max")
    if salary_min is not None or salary_max is not None:
        salary_text = f"{salary_min or 0:,.0f} - {salary_max or salary_min or 0:,.0f} MGA"
    elif job.salary_range:
        salary_text = job.salary_range
    else:
        salary_text = "À préciser"

    mission_summary = profile.get("mission_summary") or job.description or ""
    start_date = profile.get("desired_start_date") or ""
    return f"""
    <div>
      <h1>Promesse / brouillon de contrat - {job.title}</h1>
      <p>Employeur: {employer.raison_sociale}</p>
      <p>Candidat: {candidate.first_name} {candidate.last_name}</p>
      <p>Département: {job.department or ''}</p>
      <p>Type de contrat: {job.contract_type}</p>
      <p>Date souhaitée: {start_date}</p>
      <p>Mission principale: {mission_summary}</p>
      <p>Fourchette salariale indicative: {salary_text}</p>
      <p>Ce document constitue un brouillon contractuel généré depuis la fiche de poste et la décision de recrutement.</p>
    </div>
    """.strip()
