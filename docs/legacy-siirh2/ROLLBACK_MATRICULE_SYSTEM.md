# Plan de Rollback - Système Matricule

## Contexte
Suite à l'analyse de la charge de travail, décision de rollback du système matricule pour maintenir la stabilité du système actuel.

## Principe
Le système matricule a été développé mais **jamais activé en production**. Le rollback consiste simplement à :
1. Désactiver les routes API matricule
2. Retirer les composants frontend non utilisés
3. Conserver les tables DB (au cas où) mais les ignorer
4. Documenter pour référence future

## Étapes de Rollback

### 1. Backend - Désactivation des Routes Matricule

**Fichier : `siirh-backend/app/main.py`**

Commenter les imports et routes matricule :

```python
# ❌ DÉSACTIVÉ - Système matricule en attente
# from .routers import matricule_api
# app.include_router(matricule_api.router)
# from .middleware import matricule_error_handler
```

### 2. Frontend - Retrait des Composants Matricule

**Fichiers à ignorer (ne pas supprimer, juste ne pas utiliser) :**
- `siirh-frontend/src/pages/MatriculeMigration.tsx`
- `siirh-frontend/src/components/MigrationMonitor.tsx`
- `siirh-frontend/src/components/MatriculeWorkerSelect.tsx`
- `siirh-frontend/src/hooks/useMatriculeResolver.ts`

**Action :** Retirer les liens de navigation vers ces pages dans `App.tsx`

### 3. Base de Données - Conservation des Tables

**Décision : NE PAS SUPPRIMER les tables**

Raisons :
- Aucun impact sur les performances (tables vides ou peu remplies)
- Permet une réactivation future rapide si besoin
- Pas de risque de perte de données

Tables concernées (à conserver mais ignorer) :
- `matricule_assignments`
- `matricule_audit`
- Autres tables matricule créées

### 4. Documentation

Créer un fichier `MATRICULE_SYSTEM_SUSPENDED.md` expliquant :
- Pourquoi le système a été suspendu
- Ce qui a été développé
- Comment le réactiver si besoin futur

## Avantages de cette Approche

✅ **Rollback propre et sûr**
- Aucune suppression de code (juste désactivation)
- Aucune modification de la base de données de production
- Réversible à tout moment

✅ **Zéro impact sur le système actuel**
- Les utilisateurs ne verront aucun changement
- Aucune régression possible
- Système stable maintenu

✅ **Préservation du travail**
- Tout le code reste disponible
- Documentation complète conservée
- Réactivation possible en quelques minutes

## Système Actuel Maintenu

Le système continue de fonctionner avec :
- Champs string dans la table `workers` : etablissement, departement, service, unite
- Listes JSON dans la table `employers` : etablissements, departements, services, unites
- Tous les formulaires et rapports existants
- Aucune modification nécessaire

## Réactivation Future (si besoin)

Si vous décidez plus tard de réactiver le système matricule :

1. Décommenter les routes dans `main.py`
2. Réactiver les liens de navigation
3. Lancer la migration de données
4. Tester en environnement de staging
5. Déployer progressivement

**Temps estimé : 1-2 heures**

## Conclusion

Ce rollback est :
- ✅ **Sûr** : Aucun risque pour le système actuel
- ✅ **Rapide** : Quelques modifications de configuration
- ✅ **Réversible** : Tout le travail est préservé
- ✅ **Propre** : Documentation claire de la décision

Le système actuel reste 100% fonctionnel et stable.
