# Standardisation Import/Export Templates (2026-03-30)

## Portee executee

### Modules consolides
- Travailleurs: template vide/prefilled, preview import, import creation/mise a jour, rapport d'erreurs CSV.
- Recrutement: template candidats/postes, import massif candidates/jobs, rapport detaille.
- Talents: templates skills/trainings/employee-skills, import massif, rapport detaille.
- SST: template incidents, import incidents, rapport detaille.
- Primes: harmonisation sur `TabularImportReport`, support CSV/XLSX, preview import, compatibilite retour legacy conservee.
- Absences: nouveau template/import standard (`/absences/import/template`, `/absences/import`) avec controles periode/matricule.
- Contrats personnalises: nouveau template/import standard (`/custom-contracts/import/template`, `/custom-contracts/import`) avec controles employeur/salarie.

### UX frontend activee
- Workers: modal import avec template + preview + rapport CSV.
- Recruitment/Talents/SST: blocs import/export templates avec retour de rapport.
- Absences: panneau import/export template + mode update + rapport.
- Contracts: panneau import/export template + mode update + rapport.
- Payroll/Primes: dialog import primes aligne sur rapport standard, fichier erreurs telechargeable.
- Inspection/People Ops/Employee Portal/Employee 360: selections par IDs effectifs (sans `setState` synchrone en `useEffect`) pour stabiliser les flux et reduire la dette lint critique RH.

## Standard technique applique
- Schema commun: `ImportIssue`, `TabularImportReport`.
- Service tabulaire commun: `app/services/tabular_io.py`.
- Validation commune:
  - colonnes manquantes/inconnues,
  - erreurs ligne par ligne,
  - mode create/update/mixed,
  - option dry-run,
  - journalisation audit sur imports effectifs.

## Verifications executees
- Backend: `python -m compileall app` OK.
- Backend smoke import endpoints: `pytest -q test_import_endpoints_smoke.py` OK (7 passed).
- Guardrails paie/temps/absences:
  - `pytest -q test_payroll_guardrails.py` OK,
  - `pytest -q test_hs_engine_guardrails.py` OK,
  - `pytest -q test_absence_guardrails.py` OK.
- Frontend: `npm run build` OK.
- Frontend lint cible modules critiques modifies: OK.
- Frontend lint global apres clean pass 2: 133 errors / 13 warnings (amelioration continue).

## Qualite / fragilites restantes
- Lint global frontend reduit mais non vert: 133 errors / 13 warnings.
- Migration Pydantic v2: reliquat `class Config` converti vers `ConfigDict` dans `app/schemas_hs_hm_addition.py`; la suite passe sans filtre pytest dedie.
- Standard import/export encore a etendre sur certains referentiels administratifs secondaires.
