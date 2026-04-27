# Recruitment Completeness Audit

Date: 2026-03-19

## Scope
- Reference reviewed: `SIIRH_01_Module_Recrutement_v1.docx`
- Constraint preserved: payroll engine and payroll backends left untouched
- Audit target: real code paths in `siirh-backend/app/routers/recruitment.py`, `siirh-backend/app/services/recruitment_assistant_service.py` and `siirh-frontend/src/pages/Recruitment.tsx`

## Stable Existing Core
- Job postings CRUD exists and remains intact.
- Candidates CRUD exists and remains intact.
- Applications CRUD exists and remains intact.
- Audit logging continues through `audit_logs`.
- Recruitment changes are additive and isolated from payroll tables and payroll logic.

## Completed In This Recovery Iteration
- Fiche de poste structurée avec assistance éditable.
- Suggestions par intitulé, département et description libre.
- Bibliothèque interne d’aide au recrutement avec référentiels réutilisables.
- Workflow `draft -> pending_validation -> validated -> published`.
- Génération d’annonce depuis la fiche de poste.
- Pack de partage multi-canal généré depuis une source unique.
- Dépôt CV + pièces jointes via formulaire structuré.
- Conservation du CV original sur stockage dédié.
- Extraction structurée minimale des coordonnées, niveau d’études, années d’expérience, langues et compétences.
- Entretiens multi-tours avec score, recommandation et notes.
- Décision shortlist / offre / rejet.
- Conversion candidat -> salarié.
- Création automatique d’un brouillon de contrat lors de la conversion.
- Journalisation métier dédiée via `recruitment_activities`.
- RBAC aligné sur les rôles RH existants.
- Traçabilité via audit log et timeline de recrutement.

## Coverage Matrix
- Fiche de poste: `Complete`
- Workflow de validation fiche: `Complete`
- Génération d’annonce: `Complete`
- Publication d’offre: `Complete`
- Formulaire de candidature structuré: `Complete`
- Dépôt CV + pièces jointes: `Complete`
- Conservation du CV original: `Complete`
- Parsing / extraction structurée: `Complete (V1 text extraction)`
- Shortlist triable: `Complete`
- Entretiens multi-tours: `Complete`
- Scorecards pondérées: `Partial`
- Décision: `Complete`
- Génération de promesse / brouillon de contrat: `Complete`
- Transformation candidat -> employé: `Complete`
- Journalisation métier: `Complete`
- RBAC: `Complete`
- Notifications: `Partial`
- Traçabilité des actions: `Complete`

## Remaining Explicit Gaps
- OCR image/PDF avancé demandé par le CDC: non implémenté, seule l’extraction `.txt/.md/.docx` est active en V1.
- Scorecards pondérées multi-critères: structure présente via `scorecard_json`, pondération RH avancée encore à industrialiser.
- Connecteurs natifs Facebook / LinkedIn / WhatsApp: préparation des contenus livrée, publication automatique non branchée.
- Prévisualisation sécurisée intégrée du CV dans le navigateur: téléchargement sécurisé disponible, viewer intégré restant à ajouter.
- Notifications temps réel ou e-mail: journal d’activité présent, notifications automatiques institutionnelles encore à brancher.

## Integration Proof
- `RecruitmentJobPosting` -> `RecruitmentJobProfile`
- `RecruitmentCandidate` -> `RecruitmentCandidateAsset`
- `RecruitmentApplication` -> `RecruitmentInterview`
- `RecruitmentApplication` -> `RecruitmentDecision`
- `RecruitmentDecision` -> `Worker` + `CustomContract`
- `RecruitmentActivity` relie job, candidat, candidature et entretien

## Payroll Protection Proof
- No payroll formula changed.
- No payroll endpoint contract changed.
- No payroll computation service changed.
- Guardrails still pass in `siirh-backend/test_payroll_guardrails.py`.

## Demonstrable User Flow
1. RH crée ou charge une fiche de poste.
2. RH demande des suggestions puis modifie librement tous les champs.
3. RH enregistre, soumet à validation, génère l’annonce, puis publie.
4. RH dépose un CV et des pièces jointes pour un poste.
5. Le système conserve le fichier original et extrait un profil structuré.
6. RH planifie des entretiens, enregistre une décision, puis convertit le candidat en salarié.
7. Un brouillon de contrat est créé sans impacter le moteur de paie.
