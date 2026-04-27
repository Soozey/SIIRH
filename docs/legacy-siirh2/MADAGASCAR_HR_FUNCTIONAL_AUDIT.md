# Audit Fonctionnel et Technique SIIRH Madagascar

Date: 2026-03-21

## 1. Existant confirme avant cette iteration
- Administration du personnel:
  - `workers`, `custom_contracts`, `document_templates`, `generated_documents`
  - historique de position partiel via `worker_position_history`
  - conversion recrutement -> salarie -> brouillon de contrat deja disponible
- Recrutement:
  - fiche de poste, validation, annonce, candidature, CV, entretiens, decision, conversion
- Talents:
  - referentiel competences, competences salarie, catalogue de formation, sessions
- SST:
  - incidents / AT-MP de base
- Conformite / inspection:
  - revues de conformite contrat, versions de contrat, registre employeur, observations inspecteur, visites
- Reporting / declarations:
  - reporting RH, exports DNS / OSTIE / IRSA / FMFP / etat de paie / bilan social
- Auth / audit:
  - `AppUser`, `AuthSession`, `AuditLog`

## 2. Manques constates avant les ajouts de cette iteration
- Pas de vrai portail employe self-service.
- Pas de canal formel employe <-> inspecteur avec dossier, messages et pieces historisees.
- Pas de campagnes d'evaluation ni de reviews structurees.
- Pas de GPEC structuree avec profils emplois et planification des effectifs.
- Pas de chaine besoins de formation -> plan de formation -> suivi.
- Pas de module disciplinaire et de workflow de rupture sensibles.
- Pas de DUER / PAP structurels.
- Pilotage RH avance seulement partiel: plusieurs indicateurs existaient, mais sans cockpit RH transverse.

## 3. Priorisation des ecarts

### Critique
- Portail employe et demandes RH formelles.
- Saisine inspection du travail et fil d'echanges formels.
- Coherence dossier salarie / contrat / inspection / reporting.
- Historisation et controles d'acces.

### Importante
- Evaluations et performance.
- GPEC et profils emplois.
- Besoins de formation et plan de formation.
- Discipline et rupture sensibles.
- DUER / PAP.

### Confort
- Affectation fine des dossiers inspecteur par utilisateur.
- Coffre documentaire specialise inspection.
- Decoupage front supplementaire pour reduire le bundle Vite.

## 4. Ajouts realises dans cette iteration
- Nouveau module backend `employee_portal`:
  - demandes RH employe
  - dossiers inspection
  - messages formels
  - upload de pieces dans les echanges
  - dashboard portail
  - exposition du flux recrutement -> contrat -> salarie
- Nouveau module backend `people_ops`:
  - profils emplois GPEC
  - campagnes d'evaluation
  - reviews de performance
  - planification effectifs
  - besoins de formation
  - plans de formation
  - items de plan
  - evaluations de formation
  - dossiers disciplinaires
  - workflows de rupture
  - DUER
  - PAP / actions de prevention
  - dashboard RH transverse
- Nouveaux ecrans frontend:
  - `EmployeePortal.tsx`
  - `PeopleOps.tsx`
- Navigation et routage mis a jour pour exposer les nouveaux modules.

## 5. Migrations BD creees
- `siirh-backend/alembic/versions/e3b7a9c4d511_add_employee_portal_people_ops_tables.py`

## 6. Endpoints, services et composants ajoutes

### Backend
- `app/routers/employee_portal.py`
- `app/routers/people_ops.py`
- `app/services/employee_portal_service.py`
- `app/services/people_ops_service.py`

### Frontend
- `src/pages/EmployeePortal.tsx`
- `src/pages/PeopleOps.tsx`
- mises a jour:
  - `src/App.tsx`
  - `src/components/Navigation.tsx`

## 7. Impacts architecture
- Extension additive du monolithe FastAPI existant.
- Aucun changement de logique paie, conges, absences.
- Nouvelles tables relationnelles reliees aux entites existantes:
  - `workers`
  - `custom_contracts`
  - `app_users`
  - `talent_trainings`
  - `talent_training_sessions`
- Les nouveaux modules lisent la paie en lecture seule via les services deja en place.

## 8. Points juridiques malgaches pris en compte
- Contrat de travail:
  - mentions minimales deja verifiees par la couche conformite
  - controle de conformite contractuelle par inspection maintenu
- Saisine inspection:
  - tentative amiable traçable
  - dossier numerote
  - statuts, echanges, historique, pieces
- Formation:
  - besoins et plans relies aux evaluations et au FMFP via suivi budgetaire
- Discipline:
  - interdiction des sanctions pecuniaires appliquee au backend
- Sante securite:
  - DUER et PAP ajoutes
  - lien avec inspections et actions de prevention

## 9. Remarques lecture seule sur paie / conges / absences
- Aucun calcul paie modifie.
- Aucune logique metier conges modifiee.
- Aucune logique metier absences modifiee.
- Les garde-fous de non-regression existants ont ete relances.
- Les remarques detaillees restent centralisees dans `PAYROLL_LEAVE_ABSENCE_READONLY_REMARKS.md`.

## 10. Limites restantes
- Affectation fine inspecteur <-> dossier non encore modelisee.
- Le portail employe manipule des pieces dans les messages inspection, mais pas encore un coffre documentaire complet multi-version.
- Le module Messages interne du cahier des charges n'est pas encore completement implemente comme espace distinct.
- Les workflows de licenciement sensible restent documentaires et de conformite, pas de decision juridique automatisee.

## 11. Guide de test manuel
1. Ouvrir `Portail Employe`.
2. Selectionner un employeur et un salarie.
3. Creer une demande RH puis un dossier inspection.
4. Envoyer un message formel avec ou sans piece jointe.
5. Verifier le fil officiel et la chaine recrutement -> contrat -> salarie.
6. Ouvrir `People Ops`.
7. Creer un profil emploi, une campagne d'evaluation et une evaluation.
8. Creer un besoin de formation puis un plan de formation.
9. Creer un dossier disciplinaire, un workflow de rupture, une entree DUER et une action PAP.
10. Verifier le dashboard RH et les alertes remontees.
