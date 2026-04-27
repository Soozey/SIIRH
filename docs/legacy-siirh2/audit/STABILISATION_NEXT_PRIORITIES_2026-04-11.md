# Stabilisation - Priorites Traitees au 2026-04-11

## Portee

Ce document couvre les priorites demandees :

1. assainissement de la racine du depot et isolement des scripts legacy ;
2. qualification du lint frontend par lots fonctionnels ;
3. cartographie prouvable des routes/pages/composants reels ;
4. audit plus fin de la base et des anciens flux organisationnels avant toute suppression.

Les actions appliquees ici sont additives et backward-compatible. Aucune suppression de table, colonne ou flux organisationnel utile n'a ete faite.

## 1. Assainissement de la racine du depot

### Actions realisees

- Creation du dossier `tools/legacy_root_scripts/`.
- Creation du dossier `tools/manual_maintenance_scripts/`.
- Deplacement de `189` scripts Python techniques hors de la racine vers le dossier legacy.
- Archivage de `17` scripts Python supplementaires de maintenance manuelle hors de la racine.
- Ajout d'un fichier d'explication dans `tools/legacy_root_scripts/README.md`.
- Ajout d'un fichier d'explication dans `tools/manual_maintenance_scripts/README.md`.

### Ce qui a ete isole

Les scripts de ce type ont ete sortis de la racine :

- `analyze_*`
- `check_*`
- `debug_*`
- `diagnostic_*`
- `fix_*`
- `test_*`
- `verify_*`
- `final_*`
- `task_*`
- `verification_*`

Les scripts plus ambigus mais non-runtime ont egalement ete ranges hors racine en maintenance manuelle.

### Pourquoi c'etait un probleme

- La racine du depot etait surchargee par des scripts d'investigation ponctuels.
- Le demarrage et la maintenance devenaient plus confus : impossible d'identifier rapidement ce qui releve du runtime, du support ou d'un ancien diagnostic.
- Le bruit augmentait le risque d'executer un mauvais script de maintenance.

### Etat actuel de la racine

- `0` script Python restant a la racine du depot.
- les scripts exploratoires sont ranges dans `tools/legacy_root_scripts/`.
- les scripts plus sensibles de maintenance manuelle sont ranges dans `tools/manual_maintenance_scripts/`.

### Decision de stabilisation

- Deplacement automatique : oui, pour les scripts manifestement exploratoires.
- Deplacement automatique : oui, vers un dossier de maintenance manuelle, pour les scripts potentiellement operationnels ou destructifs.
- Suppression : aucune a ce stade.

## 2. Lint frontend par lots fonctionnels

### Resultat de qualification

Le lint global frontend remonte encore une dette notable, mais elle est maintenant caracterisee par familles fonctionnelles et non plus traitee comme un bloc indistinct.

### Lots fonctionnels identifies

#### Lot 1 - Organisation / hierarchie / filtres

Fichiers concernes notamment :

- `src/components/CascadingOrganizationalSelect.tsx`
- `src/components/CascadingOrganizationalSelection.ts`
- `src/components/HierarchicalOrganizationTree.tsx`
- `src/components/HierarchicalOrganizationTreeFinal.tsx`
- `src/components/HierarchyManagerModalEnhanced.tsx`
- `src/components/OrganizationManagerFixed.tsx`
- `src/components/OrganizationalListInput.tsx`
- `src/components/OrganizationalSyncButton.tsx`
- `src/components/SimpleOrganizationalDeleteModal.tsx`
- `src/hooks/useOrganization.ts`

Nature dominante :

- `@typescript-eslint/no-explicit-any`
- `@typescript-eslint/no-unused-vars`
- `react-hooks/exhaustive-deps`
- `react-refresh/only-export-components`

### Corrections sures deja appliquees sur ce lot

- suppression de `console.log` de debug dans `src/components/OrganizationalFilterModal.tsx`
- correction d'un typage de params dans `src/components/OrganizationalFilterModal.tsx`
- extraction du hook `useOrganizationalSelection` hors du composant pour supprimer une erreur `react-refresh/only-export-components`
- suppression de `src/components/HierarchicalOrganizationTreeNew.tsx` avec preuve d'absence de references
- suppression de `src/components/CascadingOrganizationalSelectNew.tsx` avec preuve d'absence de references
- correction des typings de `src/components/HierarchicalOrganizationTreeFinal.tsx`

### Verification ciblée du sous-lot deja traite

Lint cible passe avec succes sur :

- `src/components/CascadingOrganizationalSelect.tsx`
- `src/components/CascadingOrganizationalSelection.ts`
- `src/components/HierarchicalOrganizationTree.tsx`
- `src/components/HierarchicalOrganizationTreeFinal.tsx`

#### Lot 2 - Paie / primes / heures / bulletins

Fichiers concernes notamment :

- `src/components/HsHmManagerModal.tsx`
- `src/components/ImportHsHmDialog.tsx`
- `src/components/PrimesManagerModal.tsx`
- `src/components/ResetPrimesDialog.tsx`
- `src/components/PayslipDocument.tsx`
- `src/pages/Payslip.tsx`
- `src/pages/PayslipsBulk.tsx`
- `src/pages/PrimesManagement.tsx`

Nature dominante :

- `any` residuel
- hooks mal cadences
- un cas structurel a corriger dans `PayslipDocument.tsx` : hook appele conditionnellement

#### Lot 3 - Inspection / IAM / portail

Fichiers concernes notamment :

- `src/components/IamAccessManagerPanel.tsx`
- `src/components/inspection/InspectorPortalWorkspace.tsx`

Nature dominante :

- `any`
- variables inutilisees
- `react-hooks/set-state-in-effect`

#### Lot 4 - Fondations transverses

Fichiers concernes notamment :

- `src/components/ui/ToastProvider.tsx`
- `src/contexts/AuthContext.tsx`
- `src/contexts/ThemeContext.tsx`
- `src/constants/index.ts`
- `src/html2pdf.d.ts`

Nature dominante :

- export non conforme aux regles fast-refresh
- typings faibles
- constante mutable inutile

## 3. Cartographie front/back et preuve de reachability

### Routes frontend detectees dans `src/App.tsx`

- `/`
- `/*`
- `/absences`
- `/contracts`
- `/data-transfer`
- `/declarations`
- `/employee-360`
- `/employee-portal`
- `/employers`
- `/employers/:employerId/primes`
- `/help`
- `/hs`
- `/inspection`
- `/leaves`
- `/login`
- `/messages`
- `/organization`
- `/payroll`
- `/payslip`
- `/payslip-bulk`
- `/payslip-bulk/:employerId/:period`
- `/payslip/:workerId/:period`
- `/people-ops`
- `/primes`
- `/recruitment`
- `/reporting`
- `/sst`
- `/talents`
- `/workers`

### Pages actuellement atteintes par le routeur frontend

Presence constatee dans `App.tsx` ou dans le graphe d'import :

- `Absences`
- `Contracts`
- `Dashboard`
- `DataTransfer`
- `Declarations`
- `Employee360`
- `EmployeePortal`
- `Employers`
- `HelpCenter`
- `HeuresSupplementairesPageHS`
- `InspectionCompliance`
- `LeavePermissionManagement`
- `Login`
- `Messages`
- `Organization`
- `PayrollRun`
- `Payslip`
- `PayslipsBulk`
- `PeopleOps`
- `PrimesHub`
- `PrimesManagement`
- `Recruitment`
- `Reporting`
- `Sst`
- `Talents`
- `Workers`

Conclusion : les pages principales ne sont pas du code mort. La suppression de pages ne doit pas etre engagee sans preuve supplementaire.

### Composants de transition verifies et retires

Suppression documentee dans [FRONTEND_REACHABILITY_MAP_2026-04-11.md](c:\Users\Laptop\Desktop\SIIRH\SIIRH2\docs\audit\FRONTEND_REACHABILITY_MAP_2026-04-11.md) :

- `src/components/CascadingOrganizationalSelectNew.tsx`
- `src/components/HierarchicalOrganizationTreeNew.tsx`

### Observation sur la coherence front/back

Le front couvre les grands domaines exposes par le back : employeurs, travailleurs, paie, primes, organisation, absences, conges, inspection, messagerie, reporting, import/export, etc.

En revanche, la verification "tout le back est represente dans le front" doit rester prudente :

- certaines routes backend sont de support technique ou de service interne ;
- certaines fonctions sont exposees via des modules existants et non par un ecran dedie ;
- l'equivalence se mesure par usage metier reel, pas par correspondance 1 route = 1 page.

## 4. Audit base et anciens flux organisationnels

### Constat structurel

Le projet maintient actuellement deux couches organisationnelles en parallele :

- une couche historique a base de champs texte sur `workers` ;
- une couche structuree a base d'unites organisationnelles et de noeuds hierarchiques.

### Preuves dans le modele

Dans `siirh-backend/app/models.py` :

- `Worker.etablissement`
- `Worker.departement`
- `Worker.service`
- `Worker.unite`
- `Worker.organizational_unit_id`
- proprietes de compatibilite :
  - `effective_etablissement`
  - `effective_departement`
  - `effective_service`
  - `effective_unite`
- coexistence de `OrganizationalNode` et `OrganizationalUnit`

### Preuves d'usage encore actif

Les recherches de references montrent encore des usages dans :

- `siirh-frontend/src/pages/Workers.tsx`
- `siirh-backend/app/services/compliance_service.py`
- `siirh-backend/app/services/system_data_import_service.py`
- `siirh-backend/app/services/organizational_migration_service.py`
- la securite backend via `organizational_unit_id`

### Decision de stabilisation

Suppressions interdites a ce stade :

- colonnes `workers.etablissement`
- colonnes `workers.departement`
- colonnes `workers.service`
- colonnes `workers.unite`
- colonne `workers.organizational_unit_id`
- tables ou modeles lies aux anciennes et nouvelles structures organisationnelles

Raison :

- la compatibilite est encore active ;
- plusieurs ecrans front consomment encore les anciens champs ;
- plusieurs services back s'appuient sur les deux systemes en parallele ;
- une suppression brutale casserait des flux organisation, paie, reporting, controle et securite.

## 5. Nettoyages backend deja realises en soutien

### `siirh-backend/app/main.py`

- suppression d'imports inutiles
- conservation de la route racine `/` pour eviter le `{"detail":"Not Found"}` sur l'URL de base

### `siirh-backend/app/routers/workers.py`

- suppression d'ecritures de fichiers de debug
- suppression de traces de debug superflues

### `siirh-backend/app/routers/payroll_hs_hm.py`

- suppression d'imports dupliques
- remplacement de `print` de debug par un logger

## 6. Verification technique apres nettoyage

Verifications passees :

- compilation backend : `python -m compileall siirh-backend\\app`
- build frontend : `npm run build`
- lint cible reussi sur un sous-lot Organisation

## 7. Prochaines priorites immediates

1. Poursuivre le lot lint Organisation sur `HierarchyManagerModalEnhanced`, `OrganizationManagerFixed`, `OrganizationalSyncButton` et `useOrganization`.
2. Traiter ensuite le lot Paie / Primes avec la meme methode : corrections ciblees, build, puis lot suivant.
3. Cartographier les tables/colonnes legacy organisationnelles par niveau d'usage avant de parler de suppression schema.
4. Introduire une strategie de deprecation documentee avant toute simplification de la base.
5. Etendre la preuve de reachability a certains composants transverses avant toute nouvelle suppression.
