# Rapport de migration SIIRH

Branche cible : `monorepo-siirh-migration`

## Dépôts audités

- `Soozey/SIIRH` : nouveau dépôt officiel, vide au démarrage de cette migration.
- `Soozey/SIIRH2` : ancien workspace monorepo avec sous-modules et documentation.
- `Soozey/siirh-backend` : backend actif.
- `Soozey/siirh-frontend_Paie` : frontend actif.
- `Soozey/siirh-web` : ancien front audité, non intégré comme application active.

## Branches sources retenues

- Backend : `activate-leave-requests-inspector-agent-messaging`
- Frontend : `activate-leave-requests-inspector-agent-messaging`
- Workspace SIIRH2 : `activate-leave-requests-inspector-agent-messaging`

## Choix techniques

- Backend migré dans `apps/backend`.
- Frontend migré dans `apps/frontend`.
- Historique Git backend/frontend préservé via `git subtree`.
- Les anciens sous-modules de `SIIRH2` ne sont pas conservés comme sous-modules.
- Documentation utile de `SIIRH2` reprise sous `docs/legacy-siirh2`.
- `siirh-web` conservé en référence uniquement sous `docs/legacy-siirh-web` si nécessaire, car il est distinct du front actif.

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
