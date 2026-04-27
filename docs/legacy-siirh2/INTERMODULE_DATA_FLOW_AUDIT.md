# Audit des flux inter-modules

Date: 2026-03-20

## Chaînes vérifiées

### Recrutement -> contrat -> salarié
- `RecruitmentDecision.converted_worker_id` relie la décision d'embauche au salarié créé.
- `RecruitmentDecision.contract_draft_id` relie la décision au brouillon de contrat.
- Le nouveau endpoint `/compliance/employee-flow/{worker_id}` expose la chaîne:
  - candidat
  - fiche de poste
  - décision
  - contrat
  - versions de conformité
  - déclarations

### Contrat -> conformité
- `contract_versions` fige un snapshot contrôlable du contrat.
- `compliance_reviews` supporte checklist, statut et pièces demandées.
- `inspector_observations` trace les remarques externes.

### Salarié -> reporting / déclarations
- Les exports réglementaires lisent:
  - référentiel employeur
  - référentiel salarié
  - contrat / version si disponible
  - paie existante en lecture seule

## Contrôles ajoutés
- Blocage de génération de version contractuelle si les champs minimaux sont incomplets:
  - fonction
  - catégorie professionnelle
  - indice de classification
  - salaire
  - date d'effet
  - nature de contrat
- Détection d'écarts:
  - identité salarié incomplète
  - email candidat != email salarié
  - salaire recrutement != salaire salarié
  - type de contrat fiche de poste != dossier salarié
  - matricule dupliqué

## Limites restantes
- Les champs avancés de candidature ne couvrent pas encore tout le périmètre CIN / NIF / adresse / date de naissance côté UI recrutement.
- Les anomalies sont actuellement calculées dynamiquement; elles ne sont pas encore historisées dans une table d'alertes dédiée.
