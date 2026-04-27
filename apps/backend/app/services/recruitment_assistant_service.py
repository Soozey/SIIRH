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

PROFESSIONAL_CLASSIFICATION_SYSTEM_ITEMS = [
    {"code": "M1", "label": "Manoeuvre ordinaire", "family": "Industrie", "group": 1, "description": "Travaux simples sans qualification specifique."},
    {"code": "M2", "label": "Manoeuvre specialise", "family": "Industrie", "group": 1, "description": "Execution de taches simples avec adaptation pratique."},
    {"code": "OS1", "label": "Ouvrier", "family": "Industrie", "group": 2, "description": "Execution de travaux de production selon consignes."},
    {"code": "OS2", "label": "Ouvrier superieur", "family": "Industrie", "group": 2, "description": "Production qualifiee avec autonomie partielle."},
    {"code": "OS3", "label": "Ouvrier specialise", "family": "Industrie", "group": 3, "description": "Execution specialisee avec expertise metier terrain."},
    {"code": "OP1A", "label": "Ouvrier professionnel", "family": "Industrie", "group": 3, "description": "Metier technique avec pratique confirmee."},
    {"code": "OP1B", "label": "Ouvrier professionnel experimente", "family": "Industrie", "group": 3, "description": "Meme famille OP1 avec experience complementaire."},
    {"code": "OP2A", "label": "Agent de maitrise", "family": "Industrie", "group": 4, "description": "Pilotage d'activites techniques et coordination d'equipe."},
    {"code": "OP2B", "label": "Agent de maitrise experimente", "family": "Industrie", "group": 4, "description": "Maitrise experimentee sur poste technique ou encadrement."},
    {"code": "OP3", "label": "Agent de maitrise confirme / chef", "family": "Industrie", "group": 4, "description": "Responsabilite de pilotage operationnel et coordination."},
    {"code": "1A", "label": "Personnel subalterne", "family": "Services / Administratif", "group": 1, "description": "Travaux de support administratif de base."},
    {"code": "1B", "label": "Personnel subalterne experimente", "family": "Services / Administratif", "group": 1, "description": "Support administratif avec experience pratique."},
    {"code": "2A", "label": "Personnel executant travaux simples", "family": "Services / Administratif", "group": 2, "description": "Execution de travaux simples selon procedures."},
    {"code": "2B", "label": "Personnel executant experimente", "family": "Services / Administratif", "group": 2, "description": "Execution avec experience et autonomie accrue."},
    {"code": "3A", "label": "Personnel avec connaissances professionnelles", "family": "Services / Administratif", "group": 3, "description": "Fonctions necessitant une base professionnelle solide."},
    {"code": "3B", "label": "Personnel avec experience confirmee", "family": "Services / Administratif", "group": 3, "description": "Niveau confirme avec execution maitrisee."},
    {"code": "4A", "label": "Personnel formation approfondie", "family": "Services / Administratif", "group": 4, "description": "Fonctions necessitant formation technique approfondie."},
    {"code": "4B", "label": "Personnel experimente formation avancee", "family": "Services / Administratif", "group": 4, "description": "Niveau avance avec forte autonomie professionnelle."},
    {"code": "5A", "label": "Personnel hautement qualifie", "family": "Cadre", "group": 5, "description": "Expertise elevee, fonctions de pilotage ou conception."},
    {"code": "5B", "label": "Personnel hautement qualifie experimente", "family": "Cadre", "group": 5, "description": "Niveau cadre confirme, forte responsabilite."},
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
    "contract_type": [
        "CDI",
        "CDD",
        "Contrat d'essai",
        "Contrat d'apprentissage",
        "Contrat saisonnier",
        "Contrat occasionnel",
        "Travail interimaire",
        "Portage salarial",
        "Travailleur migrant / expatrie",
        "Stage",
        "Consultant",
        "Prestataire",
        "Temps partiel",
        "Temps plein",
    ],
    "status": ["Cadre", "Non cadre", "Agent", "Ouvrier", "Manager", "Direction", "Stagiaire"],
    "publication_channel": ["E-mail", "Lien public", "PDF", "Facebook", "LinkedIn", "WhatsApp"],
    "language": ["Français", "Malgache", "Anglais"],
    "education_level": ["Niveau secondaire", "Bac", "Bac+2", "Bac+3", "Master"],
    "experience_level": ["Débutant", "1 à 2 ans", "3 à 5 ans", "5 ans et plus"],
    "candidate_source": ["Candidature spontanee", "Cooptation", "LinkedIn", "Facebook", "Site entreprise", "Cabinet"],
    "benefit": ["Cantine", "Transport", "CNaPS", "OSTIE", "FMFP", "IRSA", "Assurance sante", "Prime de panier"],
    "working_schedule": ["Temps plein", "Temps partiel", "Horaire de nuit", "Horaire decale", "Shift / rotation"],
    "working_days": ["Lundi-Vendredi", "Lundi-Samedi", "Lundi-Samedi matin", "Lundi-Samedi apres-midi"],
    "interview_stage": ["Entretien RH", "Entretien technique", "Entretien manager", "Entretien DG", "Reference check"],
}

CONTRACT_TYPE_DESCRIPTIONS = {
    "CDI": "Contrat a duree indeterminee, reference standard pour un besoin permanent.",
    "CDD": "Contrat a duree determinee, borne dans le temps avec motif de recours a verifier.",
    "Contrat d'essai": "Contrat ou periode d'essai a cadrer avec duree, evaluation et date d'echeance.",
    "Contrat d'apprentissage": "Cadre de transmission de competences avec tutorat et objectifs pedagogiques.",
    "Contrat saisonnier": "Contrat lie a une activite repetitive ou cyclique sur une periode identifiee.",
    "Contrat occasionnel": "Mobilisation ponctuelle pour un besoin limite ou evenementiel.",
    "Travail interimaire": "Mission temporaire avec intervenant externe ou agence de travail temporaire.",
    "Portage salarial": "Modalite specifique pour prestation encadree contractuellement.",
    "Travailleur migrant / expatrie": "Contrat avec vigilance sur autorisations, mobilite et langue du document.",
    "Stage": "Convention de stage ou periode d'immersion professionnalisante.",
    "Consultant": "Mission d'expertise independante ou de conseil selon cahier des charges.",
    "Prestataire": "Intervention externe encadree par prestations et livrables.",
    "Temps partiel": "Organisation du temps de travail avec quotite reduite.",
    "Temps plein": "Organisation standard a plein temps.",
}

JOB_FAMILY_TEMPLATES = {
    "it": {
        "description": "Dans le cadre du renforcement de son equipe technique, l'entreprise recherche un profil capable de concevoir, developper, maintenir et securiser des solutions applicatives fiables au service des operations.",
        "mission_summary": "Concevoir, developper et maintenir des solutions techniques performantes en garantissant la qualite, la stabilite et la maintenabilite.",
        "main_activities": ["Developpement de fonctionnalites", "Correction de bugs", "Participation aux reunions techniques", "Tests et documentation"],
        "technical_skills": ["Python", "JavaScript / TypeScript", "API REST", "SQL", "Tests automatises"],
        "behavioral_skills": ["Rigueur", "Esprit d'analyse", "Travail en equipe", "Autonomie"],
        "tools": ["Git", "VS Code", "Docker", "Postman"],
        "certifications": ["Certification cloud ou devops (optionnelle)"],
        "languages": ["Francais", "Anglais technique"],
        "interview_criteria": ["Logique (40%)", "Technique (40%)", "Communication (20%)"],
        "education_level": "Bac+3 a Bac+5 en informatique",
        "experience_required": "1 a 3 ans selon le niveau de responsabilite",
        "recommended_contracts": ["CDI", "CDD", "Contrat d'essai"],
    },
    "finance": {
        "description": "Pour fiabiliser ses operations financieres et comptables, l'entreprise recherche un profil capable de produire des donnees justes, conformes et exploitables pour le pilotage.",
        "mission_summary": "Assurer la fiabilite comptable et financiere, la conformite documentaire et la production des etats de gestion.",
        "main_activities": ["Tenue des ecritures comptables", "Rapprochements et clotures", "Suivi fiscal et social", "Alerte sur les ecarts"],
        "technical_skills": ["Comptabilite generale", "Excel avance", "Fiscalite", "Analyse financiere"],
        "behavioral_skills": ["Precision", "Fiabilite", "Discretion", "Respect des delais"],
        "tools": ["Excel", "ERP comptable", "Outils de reporting"],
        "certifications": ["Certification comptable ou fiscale (optionnelle)"],
        "languages": ["Francais", "Malgache"],
        "interview_criteria": ["Technique comptable (45%)", "Controle interne (35%)", "Communication (20%)"],
        "education_level": "Bac+3 en comptabilite, finance ou gestion",
        "experience_required": "2 a 4 ans en comptabilite ou finance",
        "recommended_contracts": ["CDI", "CDD"],
    },
    "rh": {
        "description": "Dans le cadre du renforcement de sa fonction RH, l'entreprise recherche un profil capable de securiser les processus sociaux, administratifs et humains.",
        "mission_summary": "Piloter ou appuyer les activites RH en assurant la conformite sociale, la qualite documentaire et l'accompagnement des salaries.",
        "main_activities": ["Gestion des dossiers du personnel", "Suivi des absences et contrats", "Appui recrutement et integration", "Fiabilisation des donnees paie"],
        "technical_skills": ["Administration du personnel", "Droit social", "Excel", "Organisation documentaire"],
        "behavioral_skills": ["Confidentialite", "Ecoute", "Rigueur", "Sens du service"],
        "tools": ["SIRH", "Excel", "Word"],
        "certifications": ["Formation RH ou droit social (optionnelle)"],
        "languages": ["Francais", "Malgache"],
        "interview_criteria": ["Conformite RH (40%)", "Organisation (35%)", "Relationnel (25%)"],
        "education_level": "Bac+3 en RH, droit ou gestion",
        "experience_required": "2 a 5 ans selon le niveau du poste",
        "recommended_contracts": ["CDI", "CDD", "Contrat d'essai"],
    },
    "commercial": {
        "description": "Afin d'accelerer son developpement commercial, l'entreprise recherche un profil capable de generer des opportunites, conclure des ventes et entretenir la relation client.",
        "mission_summary": "Developper le portefeuille client, generer du chiffre d'affaires et contribuer a la visibilite commerciale de l'entreprise.",
        "main_activities": ["Prospection et qualification", "Presentation des offres", "Suivi des objectifs et relances", "Remontee des besoins du marche"],
        "technical_skills": ["Prospection", "Negociation", "CRM", "Suivi de pipeline"],
        "behavioral_skills": ["Aisance relationnelle", "Persuasion", "Resilience", "Orientation resultat"],
        "tools": ["CRM", "Excel", "PowerPoint"],
        "certifications": ["Formation vente / marketing (optionnelle)"],
        "languages": ["Francais", "Malgache"],
        "interview_criteria": ["Commercial (45%)", "Argumentation (35%)", "Communication (20%)"],
        "education_level": "Bac+2 a Bac+3 commercial ou marketing",
        "experience_required": "1 a 3 ans en vente ou developpement commercial",
        "recommended_contracts": ["CDI", "CDD", "Contrat occasionnel"],
    },
    "management": {
        "description": "Dans une logique de pilotage et de structuration, l'entreprise recherche un manager capable de coordonner une equipe, suivre les indicateurs et garantir la continuite de service.",
        "mission_summary": "Organiser, piloter et animer une equipe afin d'atteindre les objectifs de performance, de qualite et de conformite.",
        "main_activities": ["Planification de l'activite", "Suivi des indicateurs", "Encadrement de l'equipe", "Coordination avec la direction"],
        "technical_skills": ["Pilotage d'activite", "Reporting", "Gestion d'equipe", "Analyse de performance"],
        "behavioral_skills": ["Leadership", "Decision", "Organisation", "Communication"],
        "tools": ["Excel", "PowerPoint", "Tableaux de bord"],
        "certifications": ["Formation management (optionnelle)"],
        "languages": ["Francais", "Malgache"],
        "interview_criteria": ["Leadership (40%)", "Pilotage (35%)", "Communication (25%)"],
        "education_level": "Bac+3 a Bac+5 selon le perimetre",
        "experience_required": "3 a 5 ans avec responsabilites progressives",
        "recommended_contracts": ["CDI", "CDD"],
    },
    "operations": {
        "description": "Pour soutenir ses activites terrain et operationnelles, l'entreprise recherche un profil capable d'executer ses missions avec rigueur, securite et respect des procedures.",
        "mission_summary": "Executer ou coordonner les operations terrain en assurant la qualite, la securite et la continuite du service.",
        "main_activities": ["Execution quotidienne selon procedures", "Suivi des controles et mouvements", "Remontee des anomalies", "Respect des standards securite et qualite"],
        "technical_skills": ["Procedures operationnelles", "Securite", "Controle qualite", "Organisation terrain"],
        "behavioral_skills": ["Discipline", "Vigilance", "Fiabilite", "Reactivite"],
        "tools": ["Outils terrain", "Checklists", "Excel de suivi"],
        "certifications": ["Habilitation metier ou securite (si applicable)"],
        "languages": ["Malgache", "Francais"],
        "interview_criteria": ["Execution (40%)", "Securite (35%)", "Comportement (25%)"],
        "education_level": "Niveau secondaire a Bac+2 selon le metier",
        "experience_required": "1 a 3 ans ou premiere experience structuree",
        "recommended_contracts": ["CDI", "CDD", "Contrat saisonnier", "Contrat occasionnel"],
    },
    "autre": {
        "description": "L'entreprise recherche un profil capable de prendre en charge le poste dans un cadre professionnel structure, avec des objectifs clairs et une adaptation rapide au contexte.",
        "mission_summary": "Prendre en charge les responsabilites du poste en garantissant qualite de service, fiabilite et bonne integration a l'equipe.",
        "main_activities": ["Execution des missions principales", "Coordination avec les parties prenantes", "Suivi des livrables", "Proposition d'ameliorations pratiques"],
        "technical_skills": ["Organisation", "Outils bureautiques", "Suivi d'activite"],
        "behavioral_skills": ["Rigueur", "Adaptabilite", "Communication", "Esprit d'equipe"],
        "tools": ["Excel", "Word", "Messagerie professionnelle"],
        "certifications": [],
        "languages": ["Francais", "Malgache"],
        "interview_criteria": ["Metier (40%)", "Organisation (30%)", "Communication (30%)"],
        "education_level": "A definir selon le poste",
        "experience_required": "Ajustable selon le niveau de responsabilite",
        "recommended_contracts": ["CDI", "CDD"],
    },
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


def _seed_system_library_item(
    db,
    *,
    category: str,
    label: str,
    description: str | None = None,
    payload: dict | None = None,
) -> None:
    normalized_key = _normalize_key(label)
    existing = (
        db.query(models.RecruitmentLibraryItem)
        .filter(models.RecruitmentLibraryItem.employer_id.is_(None))
        .filter(models.RecruitmentLibraryItem.category == category)
        .filter(models.RecruitmentLibraryItem.normalized_key == normalized_key)
        .first()
    )
    if existing:
        if existing.is_system:
            existing.description = description
            existing.payload_json = json_dump(payload or {})
            existing.is_active = True
        return

    db.add(
        models.RecruitmentLibraryItem(
            employer_id=None,
            category=category,
            label=label,
            normalized_key=normalized_key,
            description=description,
            payload_json=json_dump(payload or {}),
            is_system=True,
            is_active=True,
        )
    )


def ensure_recruitment_library(db) -> None:
    for item in SYSTEM_LIBRARY_ITEMS:
        _seed_system_library_item(
            db,
            category=item["category"],
            label=item["label"],
            description=item.get("description"),
            payload=item.get("payload", {}),
        )

    for category, values in SYSTEM_REFERENCE_VALUES.items():
        for value in values:
            _seed_system_library_item(
                db,
                category=category,
                label=value,
                payload={"value": value},
            )

    for item in PROFESSIONAL_CLASSIFICATION_SYSTEM_ITEMS:
        label = f"{item['code']} - {item['label']}"
        _seed_system_library_item(
            db,
            category="professional_classification",
            label=label,
            description=item["description"],
            payload={
                "code": item["code"],
                "label": item["label"],
                "family": item["family"],
                "group": item["group"],
                "description": item["description"],
            },
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

def _detect_job_family(title: str, department: str, description: str, sector: str = "") -> str:
    haystack = f"{title} {department} {description} {sector}".lower()
    normalized_haystack = _normalize_key(haystack).replace("-", " ")
    mapping = {
        "it": ["developpeur", "developer", "informatique", "it", "si", "support", "tech", "logiciel", "reseau", "systeme"],
        "finance": ["comptable", "finance", "tresor", "audit", "controleur", "fiscal", "paie"],
        "rh": ["rh", "ressources humaines", "recrutement", "talent", "paie", "social"],
        "commercial": ["commercial", "vente", "marketing", "business", "crm", "client"],
        "management": ["responsable", "manager", "chef", "directeur", "superviseur", "coordinateur"],
        "operations": ["chauffeur", "magasinier", "terrain", "operation", "production", "logistique", "agent", "technicien"],
    }
    for family, keywords in mapping.items():
        for keyword in keywords:
            normalized_keyword = _normalize_key(keyword).replace("-", " ")
            if not normalized_keyword:
                continue
            if len(normalized_keyword) <= 2 or " " in normalized_keyword:
                if re.search(rf"(^|\\s){re.escape(normalized_keyword)}(\\s|$)", normalized_haystack):
                    return family
            elif normalized_keyword in normalized_haystack:
                return family
    return "autre"


def _family_from_template_matches(matches: list) -> str | None:
    for entry in matches:
        payload = _json_load(getattr(entry, "payload_json", None), {})
        department = str(payload.get("department") or "")
        mission_summary = str(payload.get("mission_summary") or "")
        family = _detect_job_family(entry.label, department, mission_summary)
        if family != "autre":
            return family
    return None


def _merge_unique(values: list[str], extras: list[str]) -> list[str]:
    merged = list(values)
    for value in extras:
        if value and value not in merged:
            merged.append(value)
    return merged


def _build_contract_type_suggestions(job_family: str, requested_contract_type: str = "") -> list[dict]:
    recommended = JOB_FAMILY_TEMPLATES.get(job_family, JOB_FAMILY_TEMPLATES["autre"]).get("recommended_contracts", ["CDI", "CDD"])
    ordered = []
    seed = [requested_contract_type] if requested_contract_type else []
    for item in seed + recommended + list(SYSTEM_REFERENCE_VALUES["contract_type"]):
        if item and item not in ordered:
            ordered.append(item)
    return [
        {
            "code": item,
            "label": item,
            "description": CONTRACT_TYPE_DESCRIPTIONS.get(item, "Type de contrat personnalisable selon le contexte de l'entreprise."),
            "recommended": item in recommended or item == requested_contract_type,
        }
        for item in ordered
    ]


def suggest_job_profile(
    db,
    *,
    title: str,
    department: str = "",
    description: str = "",
    employer_id=None,
    sector: str = "",
    mode: str = "generate",
    version: str = "long",
    focus_block: str | None = None,
    contract_type: str = "",
):
    matches = _match_job_templates(db, title, department, description, employer_id=employer_id)
    family = _family_from_template_matches(matches) or _detect_job_family(title, department, description, sector)
    family_template = JOB_FAMILY_TEMPLATES.get(family, JOB_FAMILY_TEMPLATES["autre"])
    classification_entries = get_library_entries(
        db,
        employer_id=employer_id,
        category="professional_classification",
    )
    suggested = {
        "probable_title": title or (matches[0].label if matches else ""),
        "probable_department": department or "",
        "detected_job_family": family,
        "generated_context": family_template["description"],
        "mission_summary": family_template["mission_summary"],
        "main_activities": [],
        "technical_skills": [],
        "behavioral_skills": [],
        "education_level": family_template["education_level"],
        "experience_required": family_template["experience_required"],
        "languages": list(family_template["languages"]),
        "tools": list(family_template["tools"]),
        "certifications": list(family_template["certifications"]),
        "interview_criteria": list(family_template["interview_criteria"]),
        "suggestion_sources": [],
        "classification": "",
        "contract_type_suggestions": _build_contract_type_suggestions(family, contract_type),
    }

    if matches:
        top_payload = _json_load(matches[0].payload_json, {})
        suggested["probable_department"] = department or top_payload.get("department", "")
        suggested["mission_summary"] = top_payload.get("mission_summary", suggested["mission_summary"])
        suggested["main_activities"] = _merge_unique(list(top_payload.get("main_activities", [])), family_template["main_activities"])
        suggested["technical_skills"] = _merge_unique(list(top_payload.get("technical_skills", [])), family_template["technical_skills"])
        suggested["behavioral_skills"] = _merge_unique(list(top_payload.get("behavioral_skills", [])), family_template["behavioral_skills"])
        suggested["education_level"] = top_payload.get("education_level", suggested["education_level"])
        suggested["experience_required"] = top_payload.get("experience_required", suggested["experience_required"])
        suggested["languages"] = _merge_unique(list(top_payload.get("languages", [])), family_template["languages"])
        suggested["tools"] = _merge_unique(list(top_payload.get("tools", [])), family_template["tools"])
        suggested["certifications"] = _merge_unique(list(top_payload.get("certifications", [])), family_template["certifications"])
        suggested["interview_criteria"] = _merge_unique(list(top_payload.get("interview_criteria", [])), family_template["interview_criteria"])
        suggested["suggestion_sources"].append(matches[0].label)
        suggested["classification"] = top_payload.get("classification", "") or suggested["classification"]
    else:
        suggested["main_activities"] = list(family_template["main_activities"])
        suggested["technical_skills"] = list(family_template["technical_skills"])
        suggested["behavioral_skills"] = list(family_template["behavioral_skills"])

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

    suggest_text = f"{title or ''} {department or ''} {description or ''}".lower()
    for entry in classification_entries:
        payload = _json_load(entry.payload_json, {})
        code = str(payload.get("code") or "").strip()
        label = str(payload.get("label") or "").strip().lower()
        family = str(payload.get("family") or "").strip().lower()
        if not code:
            continue
        if code.lower() in suggest_text or label in suggest_text or (family and family in suggest_text):
            suggested["classification"] = code
            if entry.label not in suggested["suggestion_sources"]:
                suggested["suggestion_sources"].append(entry.label)
            break

    if not suggested["classification"] and matches:
        top_payload = _json_load(matches[0].payload_json, {})
        fallback_classification = top_payload.get("classification")
        if isinstance(fallback_classification, str):
            suggested["classification"] = fallback_classification

    if version == "short":
        suggested["main_activities"] = suggested["main_activities"][:3]
        suggested["technical_skills"] = suggested["technical_skills"][:4]
        suggested["behavioral_skills"] = suggested["behavioral_skills"][:3]
        suggested["tools"] = suggested["tools"][:3]
        suggested["interview_criteria"] = suggested["interview_criteria"][:3]
        suggested["generated_context"] = suggested["generated_context"].split(".")[0] + "."

    if mode == "improve":
        suggested["mission_summary"] = f"{suggested['mission_summary']} L'accent est mis sur la qualite d'execution, la conformite et la coordination efficace avec les parties prenantes."
        suggested["generated_context"] = f"{suggested['generated_context']} La version amelioree renforce la precision RH et l'exploitabilite de l'annonce."
        suggested["suggestion_sources"].append("amelioration_interne")
    elif mode == "adapt":
        target_label = suggested["probable_title"] or title or "poste"
        suggested["generated_context"] = f"{suggested['generated_context']} Suggestion adaptee au poste {target_label}."
        suggested["suggestion_sources"].append(f"famille:{family}")

    if focus_block:
        focus_map = {
            "description": "generated_context",
            "mission_summary": "mission_summary",
            "main_activities": "main_activities",
            "technical_skills": "technical_skills",
            "behavioral_skills": "behavioral_skills",
            "tools": "tools",
            "languages": "languages",
            "interview_criteria": "interview_criteria",
            "education_level": "education_level",
            "experience_required": "experience_required",
        }
        target = focus_map.get(focus_block)
        if target:
            suggested["suggestion_sources"].append(f"bloc:{focus_block}")

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
    working_hours = profile.get("working_hours") or ""
    working_days = profile.get("working_days", [])
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
    if working_hours:
        requirements.append(f"Horaires: {working_hours}")
    if working_days:
        requirements.append("Jours de travail: " + ", ".join(working_days))

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


def build_contract_guidance(job, profile: dict) -> dict:
    title = (job.title or "").lower()
    description = f"{job.description or ''} {profile.get('mission_summary') or ''}".lower()
    contract_type = (job.contract_type or "CDI").strip() or "CDI"
    alerts = []
    recommendations = []

    if contract_type == "CDD":
        alerts.append(
            {
                "severity": "warning",
                "code": "cdd_duration_check",
                "message": "Le CDD doit rester borne dans le temps. Verifier la date de fin et le motif de recours.",
            }
        )
        recommendations.append("Prevoir une date de fin explicite et documenter le motif du CDD.")

    permanent_keywords = ("responsable", "manager", "superviseur", "pilotage", "permanent", "continu")
    if any(keyword in title or keyword in description for keyword in permanent_keywords):
        recommendations.append("Le besoin semble durable: evaluer un CDI comme solution de reference.")
        if contract_type == "CDD":
            alerts.append(
                {
                    "severity": "info",
                    "code": "suggest_cdi",
                    "message": "Un usage permanent semble probable; le systeme suggere d'evaluer un CDI.",
                }
            )

    if contract_type == "Travailleur migrant / expatrie":
        alerts.append(
            {
                "severity": "warning",
                "code": "migrant_compliance",
                "message": "Verifier les autorisations administratives, la langue du contrat et les clauses de mobilite.",
            }
        )
        recommendations.append("Prevoir une version bilingue FR/MG ou FR/EN selon le contexte de signature.")

    if contract_type == "Contrat d'apprentissage":
        recommendations.append("Ajouter les modalites de tutorat et les objectifs pedagogiques.")
    if contract_type == "Contrat saisonnier":
        recommendations.append("Documenter la saisonalite, la periode couverte et le site d'affectation.")
    if contract_type == "Contrat d'essai":
        recommendations.append("Verifier la duree d'essai et sa date d'echeance conformement au poste.")

    if not profile.get("classification"):
        alerts.append(
            {
                "severity": "info",
                "code": "classification_missing",
                "message": "La classification professionnelle n'est pas encore renseignee.",
            }
        )

    return {
        "suggested_primary_type": contract_type,
        "available_types": list(SYSTEM_REFERENCE_VALUES["contract_type"]),
        "language_options": ["FR", "MG", "FR/MG"],
        "required_fields": ["fonction", "categorie professionnelle", "salaire", "date d'effet"],
        "alerts": alerts,
        "recommendations": recommendations,
        "suggested_defaults": {
            "fonction": job.title,
            "categorie_professionnelle": profile.get("classification") or "",
            "salaire": profile.get("salary_min") or job.salary_range or "",
            "date_effet": profile.get("desired_start_date") or "",
        },
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
