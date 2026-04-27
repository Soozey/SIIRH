# Recruitment Job Description Assistant Spec

Date: 2026-03-19

## Objective
Assist the user when creating a job description without locking any field. Every suggestion is editable, removable or enrichable before validation and publication.

## Assisted Structured Fields
- Intitulé du poste
- Département / service
- Responsable hiérarchique
- Localisation
- Type de contrat
- Mission principale
- Activités principales
- Compétences techniques
- Compétences comportementales
- Niveau d’études
- Expérience requise
- Langues
- Outils / logiciels / certifications
- Fourchette salariale
- Horaires / temps de travail
- Avantages
- Date souhaitée
- Date limite de candidature
- Canaux de publication
- Classification / indice
- Critères d’entretien

## Suggestion Modes
### By job title
- Uses built-in templates for: Assistant RH, Comptable, Développeur, Chauffeur, Magasinier, Commercial, Agent administratif, Responsable paie, Juriste, Technicien support.
- Returns draft mission, activities, skills, studies, experience, languages, tools and interview criteria.

### By free-text description
- Extracts keywords from the need.
- Infers probable job title, department, required skills, education and experience.
- Adds suggested interview criteria.

### By department
- Applies service-specific skill families and usual wording.
- Examples covered: RH, finance/comptabilité, informatique/SI, commercial/marketing, logistique, juridique, administration, production, direction.

## Editable Internal Library
- `job_template`
- `department`
- `location`
- `contract_type`
- `status`
- `publication_channel`
- `language`
- `education_level`
- `experience_level`

Custom employer-specific items are editable. System seeds remain read-only to preserve a clean baseline.

## Transformation Job Description -> Announcement
- Generates public title
- Generates web body
- Generates e-mail subject/body
- Generates Facebook text
- Generates LinkedIn text
- Generates WhatsApp text
- Generates copy-ready text
- Generates PDF export from the same source of truth

## Business Rules
- Suggestions never overwrite an existing user value unless the field is empty.
- Assistant output is stored in `assistant_source_json`.
- Validation and publication are separated.
- Publication is blocked until validation is completed.
- Conversion candidate -> worker is blocked behind an explicit recruitment decision.

## Current Technical Implementation
- Backend assistant service: `siirh-backend/app/services/recruitment_assistant_service.py`
- Backend workflow routes: `siirh-backend/app/routers/recruitment.py`
- Frontend assisted screen: `siirh-frontend/src/pages/Recruitment.tsx`
- Data model: `recruitment_job_profiles`, `recruitment_library_items`

## V1 Limits
- OCR image parsing not yet active.
- Weighted scorecards are represented but not fully parameterized.
- Social publication connectors are content-ready, not API-published.
