# Remarques lecture seule: paie / conges / absences

Date: 2026-03-21

## Regle respectee
Cette iteration n'a modifie:
- ni le moteur metier paie,
- ni les regles de calcul conges,
- ni les regles metier absences.

Les modules ont ete utilises en lecture seule via:
- `generate_preview_data`
- reporting existant
- modeles SQLAlchemy existants
- services d'agregation et dashboards hors paie

## Preuves de non-regression
- `test_payroll_guardrails.py` execute avec succes.
- `test_compliance_and_exports.py` execute avec succes.
- `test_employee_portal_and_people_ops.py` execute avec succes.
- Les nouveaux modules `employee_portal` et `people_ops` ne referencent paie, conges et absences qu'en lecture.

## Remarques techniques
- OpenAPI remonte encore un warning historique de duplication d'`operationId` sur le module HS.
- Le bundle frontend reste lourd apres build Vite; sujet de decoupage futur.
- Plusieurs modules historiques utilisent encore `datetime.utcnow()`; sujet de durcissement transversal, hors logique metier.

## TODO documentaires seulement
- Cartographier plus finement les dependances reporting -> paie pour formaliser un contrat de lecture stable.
- Ajouter des tests d'integration API autour des endpoints existants conges / absences sans modifier leur logique.
- Evaluer une couche de vues SQL de lecture seule pour les dashboards RH multi-modules.
