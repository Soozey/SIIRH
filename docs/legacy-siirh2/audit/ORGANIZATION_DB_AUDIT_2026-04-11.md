# Audit Base et Flux Organisationnels - 2026-04-11

## Objet

Verifier si des tables ou champs lies a l'organisation peuvent etre supprimes sans casser les flux utiles du projet.

Conclusion courte : non, pas encore. Le systeme execute encore une compatibilite active entre ancien modele organisationnel et nouveau modele structure.

## 1. Coexistence de deux modeles

### Ancien modele

Champs texte portes par `Worker` :

- `etablissement`
- `departement`
- `service`
- `unite`

### Nouveau modele

Champ de rattachement structure :

- `organizational_unit_id`

Entites structurelles :

- `OrganizationalUnit`
- `OrganizationalNode`

### Couche de compatibilite

Le modele `Worker` expose encore :

- `effective_etablissement`
- `effective_departement`
- `effective_service`
- `effective_unite`

Ces proprietes prouvent qu'on ne se trouve pas dans une migration terminee. Le code tente encore de servir les deux representations.

## 2. Preuves d'usage cote backend

### Import / export / migration

Fichiers fortement relies aux anciens champs :

- `siirh-backend/app/services/system_data_import_service.py`
- `siirh-backend/app/services/organizational_migration_service.py`

Signaux utiles :

- mapping explicite des niveaux `etablissement`, `departement`, `service`, `unite`
- lecture et ecriture de `organizational_unit_id`
- logique de migration entre structure a plat et structure hierarchique

### Services metier

Fichiers relies a la compatibilite :

- `siirh-backend/app/services/compliance_service.py`
- `siirh-backend/app/security.py`

Le code de securite et de reporting continue a exploiter `organizational_unit_id`, tandis que d'autres services utilisent encore les niveaux texte ou leurs variantes effectives.

## 3. Preuves d'usage cote frontend

Le frontend utilise encore directement les champs historiques dans plusieurs flux, notamment `siirh-frontend/src/pages/Workers.tsx`.

Tant que ces ecrans lisent, editent ou transportent ces champs, leur suppression en base ou dans les schemas casserait :

- les formulaires travailleurs ;
- les imports ;
- certaines vues de filtrage ;
- certaines integrations organisationnelles de paie et reporting.

## 4. Risques si suppression prematuree

Suppression des champs texte sur `workers` :

- casse potentielle des formulaires et payloads existants ;
- perte de compatibilite avec les anciens imports ;
- rupture des migrations ou resynchronisations intermediaires.

Suppression de `organizational_unit_id` :

- rupture des liens de securite et d'affectation manageriale ;
- rupture des filtres structurels ;
- rupture de certains calculs ou rattachements croises.

Suppression de tables organisationnelles legacy ou intermediaires :

- risque de casser les services de migration encore appeles ;
- risque de casser les ecrans qui reposent encore sur des transformations de compatibilite.

## 5. Decision technique

### Ce qui est autorise maintenant

- documenter les champs legacy et leur niveau d'usage ;
- isoler les scripts de migration manuels ;
- ajouter une couche de deprecation documentaire ;
- renforcer la synchronisation entre la page Organisation et les usages Primes / Paie.

### Ce qui ne doit pas etre fait maintenant

- supprimer des colonnes organisationnelles de `workers`
- supprimer `organizational_unit_id`
- supprimer des tables ou modeles organisationnels sans matrice complete de references
- supprimer des services de migration tant que les anciens flux existent

## 6. Strategie recommandee avant suppression reelle

1. Cartographier chaque champ legacy avec ses points d'entree et de sortie.
2. Identifier les ecrans frontend qui lisent encore les niveaux texte.
3. Identifier les endpoints backend qui les acceptent encore en entree.
4. Mettre les usages en mode "lecture seule de compatibilite" quand c'est possible.
5. Supprimer seulement apres une version ou les payloads front, imports et services n'en dependent plus.

## 7. Candidats a deprecation, pas a suppression

Sous reserve de verification complementaire :

- composants frontend suffixes `New` non references
- scripts de migration ponctuels en racine
- helpers de transition autour des anciennes structures si plus aucun appel metier ne les consomme

Le bon pattern ici est :

- deprecier
- mesurer
- couper

et non :

- supprimer
- esperer
- corriger apres coup
