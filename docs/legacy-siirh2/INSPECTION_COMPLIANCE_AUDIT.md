# Inspection / Conformité sociale

Date: 2026-03-20

## Existant confirmé
- Auth applicative avec `AppUser`, `AuthSession`, `AuditLog`.
- Dossier contractuel existant via `custom_contracts`.
- Conversion recrutement -> salarié -> brouillon de contrat déjà présente.
- Reporting déjà capable de lire les données paie en lecture seule.

## Manques constatés avant cette itération
- Aucun module dédié à l'inspection du travail.
- Aucun versioning de contrat pour contrôle de conformité.
- Aucun registre employeur reconstruit depuis les dossiers salariés.
- Aucun journal structuré d'observations inspecteur / conformité.
- Aucun centre d'exports réglementaires versionnés avec historique.

## Ajouts réalisés
- Tables additives:
  - `contract_versions`
  - `compliance_reviews`
  - `inspector_observations`
  - `compliance_visits`
  - `employer_register_entries`
- Endpoints:
  - `/compliance/dashboard`
  - `/compliance/contracts/queue`
  - `/compliance/contracts/{id}/versions`
  - `/compliance/contracts/{id}/reviews`
  - `/compliance/reviews/{id}/status`
  - `/compliance/reviews/{id}/observations`
  - `/compliance/register`
  - `/compliance/register/sync`
  - `/compliance/data-integrity`
  - `/compliance/employee-flow/{worker_id}`
  - `/compliance/visits`

## Rôle inspecteur
- Lecture des dossiers autorisés via le module conformité.
- Dépôt d'observations.
- Changement de statut de revue: `conforme`, `a_corriger`, `observations_emises`, `submitted_control`.
- Export indirect via le centre de rapports RH et sociaux.
- Aucune écriture sur les modules paie, congés ou absences.

## Limites restantes
- Pas encore de mécanisme fin d'affectation de dossier inspecteur par utilisateur.
- Pas encore de coffre documentaire spécialisé pour pièces d'inspection multi-version.
- Pas encore de workflow dédié au licenciement économique au-delà de la préparation documentaire et du suivi de conformité.
