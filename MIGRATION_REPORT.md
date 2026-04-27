# Rapport de migration SIIRH

Branche cible : `monorepo-siirh-migration`

## Dépôts audités

- `Soozey/SIIRH` : nouveau dépôt officiel, vide au démarrage de cette migration.
- `Soozey/SIIRH2` : ancien workspace monorepo avec sous-modules et documentation.
- `Soozey/siirh-backend` : backend actif.
- `Soozey/siirh-frontend_Paie` : frontend actif.
- `Soozey/siirh-web` : ancien front audité, non intégré comme application active.

## Branches sources retenues

- Backend : `activate-leave-requests-inspector-agent-messaging`, commit `c906b51`.
- Frontend : `activate-leave-requests-inspector-agent-messaging`, commit `da75e04`.
- Workspace SIIRH2 : `activate-leave-requests-inspector-agent-messaging`, commit `4c4936c`.
- siirh-web : `main`, commit `4d46de2`.

## Choix techniques

- Backend migré dans `apps/backend`.
- Frontend migré dans `apps/frontend`.
- Historique Git backend/frontend préservé via `git subtree`.
- Les anciens sous-modules de `SIIRH2` ne sont pas conservés comme sous-modules.
- Documentation utile de `SIIRH2` reprise sous `docs/legacy-siirh2`.
- `siirh-web` conservé en référence documentaire sous `docs/legacy-siirh-web` (`README.md` et manifeste), car il est distinct du front actif et ne doit pas remplacer `apps/frontend`.

## Fichiers migrés

- `apps/backend` : contenu suivi par Git de `Soozey/siirh-backend`, hors fichiers locaux non suivis.
- `apps/frontend` : contenu suivi par Git de `Soozey/siirh-frontend_Paie`, hors fichiers locaux non suivis.
- `docs/legacy-siirh2` : documentation Markdown et anciens dossiers `docs` de `SIIRH2`.
- `docs/legacy-siirh-web` : README et manifeste de fichiers pour audit ultérieur.

## Éléments non migrés comme application active

- `siirh-web` : ancien frontend séparé. Il contient des composants React utiles comme référence, mais le frontend actif est `siirh-frontend_Paie`.
- Sous-modules SIIRH2 : convertis en vrais dossiers via `apps/backend` et `apps/frontend`; aucun `.gitmodules` cible n'est conservé.

## Fichiers exclus

- `.env`, `.env.*` sauf `.env.example`
- `node_modules`, `dist`, `build`
- `.venv`, `__pycache__`, `.pytest_cache`
- bases locales `*.db`, `*.sqlite`
- logs `*.log`
- `uploads`

## Risques restants

- La fusion vers `main` doit être faite après revue GitHub.
- Les anciens dépôts doivent rester intacts jusqu'à validation complète.
- Les variables réelles doivent être configurées hors Git.
