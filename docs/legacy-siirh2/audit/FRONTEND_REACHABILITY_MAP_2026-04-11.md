# Cartographie de Reachability Frontend - 2026-04-11

## Objet

Identifier les pages et composants effectivement atteints afin de supprimer le code mort avec preuve et non par intuition.

## 1. Pages atteintes par le routeur principal

Routes detectees dans `siirh-frontend/src/App.tsx` :

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

Conclusion :

- les pages metier principales sont bien branchees ;
- il n'y a pas de preuve actuelle justifiant la suppression d'une page complete exposee par `App.tsx`.

## 2. Composants supprimes avec preuve

### `src/components/HierarchicalOrganizationTreeNew.tsx`

Constat :

- aucune reference active detectee dans `src` ;
- la version reellement consommee est `HierarchicalOrganizationTreeFinal.tsx`, via :
  - `src/components/HierarchicalOrganizationTree.tsx`
  - `src/components/SimpleOrganizationalUnitManager.tsx`
  - `src/pages/Employers.tsx`

Decision :

- suppression appliquee.

### `src/components/CascadingOrganizationalSelectNew.tsx`

Constat :

- aucune reference active detectee dans `src` ;
- ce fichier n'etait qu'un re-export de compatibilite ;
- la source utile reste `src/components/CascadingOrganizationalSelect.tsx`.

Decision :

- suppression appliquee.

## 3. Composants encore a verifier avant suppression

La cartographie automatique reduit le doute, mais ne suffit pas seule pour supprimer tous les composants faiblement references. Pour les prochains nettoyages, il faudra croiser :

- reachability par route ;
- imports JSX reels ;
- presence dans les menus, modales ou chargements conditionnels ;
- eventuels appels indirects.

## 4. Decision de stabilisation

Pattern retenu :

1. prouver l'absence de references actives ;
2. supprimer seulement les variantes de transition non branchees ;
3. documenter la suppression ;
4. reconstruire et verifier.

Ce pattern est maintenant applique au nettoyage du frontend.

