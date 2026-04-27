# Guide de Suppression des Structures Organisationnelles

## Vue d'ensemble

Le système de suppression conditionnelle permet de maintenir une base de données propre en supprimant les structures organisationnelles inutiles, tout en protégeant les données importantes.

## Fonctionnalités

### 🔍 Vérification Automatique des Contraintes

Le système vérifie automatiquement avant toute suppression :

1. **Salariés directement assignés** : Nombre de salariés affectés à cette structure
2. **Salariés dans les sous-structures** : Nombre de salariés dans les structures enfants
3. **Sous-structures** : Nombre de structures organisationnelles enfants

### 🚦 Types de Suppression

#### ✅ Suppression Simple (Autorisée)
- Structure vide (0 salarié, 0 sous-structure)
- Suppression immédiate sans confirmation supplémentaire

#### ⚠️ Suppression Bloquée (Protection)
- Structure contenant des salariés
- Structure contenant des sous-structures
- Message d'erreur explicite avec détails

#### 🔧 Suppression Forcée (Option Avancée)
- Réassigne automatiquement les sous-structures au niveau parent
- Désassigne tous les salariés directs
- Nécessite confirmation explicite de l'utilisateur

## Interface Utilisateur

### Indicateurs Visuels dans l'Arbre

- **✓ Supprimable** (vert) : Structure vide, peut être supprimée
- **⚠ Occupée** (orange) : Contient des salariés ou sous-structures

### Modal de Suppression Intelligente

1. **Vérification automatique** des contraintes
2. **Affichage détaillé** des éléments bloquants :
   - Liste des sous-structures
   - Liste des salariés assignés
   - Comptage des salariés dans les sous-structures
3. **Options de suppression** adaptées au contexte

## API Endpoints

### Vérification des Contraintes
```
GET /organizational-structure/{unit_id}/can-delete
```

**Réponse :**
```json
{
  "can_delete": false,
  "reason": "Contient: 2 sous-structures, 3 salariés directement assignés",
  "unit_name": "Département RH",
  "unit_level": "departement",
  "children_count": 2,
  "direct_workers_count": 3,
  "descendant_workers_count": 5,
  "total_workers_count": 8,
  "children": [
    {"id": 10, "name": "Service Paie", "level": "service"},
    {"id": 11, "name": "Service Formation", "level": "service"}
  ],
  "workers": [
    {"id": 1, "nom": "Dupont", "prenom": "Jean", "matricule": "EMP001"},
    {"id": 2, "nom": "Martin", "prenom": "Marie", "matricule": "EMP002"}
  ]
}
```

### Suppression Standard
```
DELETE /organizational-structure/{unit_id}
```

### Suppression Forcée
```
DELETE /organizational-structure/{unit_id}?force=true
```

## Logique de Validation

### Algorithme de Vérification

1. **Comptage des enfants directs**
   ```sql
   SELECT COUNT(*) FROM organizational_units 
   WHERE parent_id = {unit_id}
   ```

2. **Comptage des salariés directs**
   ```sql
   SELECT COUNT(*) FROM workers 
   WHERE organizational_unit_id = {unit_id}
   ```

3. **Comptage récursif des salariés descendants**
   - Récupération de tous les IDs descendants
   - Comptage des salariés dans ces unités

### Règles de Suppression

| Condition | Action | Résultat |
|-----------|--------|----------|
| 0 enfant, 0 salarié | Suppression directe | ✅ Succès |
| > 0 enfants | Blocage ou force | ⚠️ Réassignation |
| > 0 salariés directs | Blocage ou force | ⚠️ Désassignation |
| > 0 salariés descendants | Blocage ou force | ℹ️ Information |

## Sécurité et Intégrité

### Protections Intégrées

1. **Validation en cascade** : Vérification de tous les niveaux
2. **Transaction atomique** : Rollback en cas d'erreur
3. **Logs détaillés** : Traçabilité des suppressions
4. **Confirmation utilisateur** : Double validation pour suppressions forcées

### Réassignation Automatique

Lors d'une suppression forcée :

```python
# Réassignation des enfants au parent
UPDATE organizational_units 
SET parent_id = {unit.parent_id} 
WHERE parent_id = {unit_id}

# Désassignation des salariés
UPDATE workers 
SET organizational_unit_id = NULL 
WHERE organizational_unit_id = {unit_id}
```

## Cas d'Usage

### Scénario 1 : Nettoyage de Structure Vide
```
Établissement A
└── Département B (vide)
    └── Service C (vide)
```
**Action :** Suppression simple de Service C, puis Département B

### Scénario 2 : Réorganisation avec Salariés
```
Établissement A
└── Département B (2 salariés)
    ├── Service C (3 salariés)
    └── Service D (1 salarié)
```
**Action :** Suppression forcée de Département B
**Résultat :** Services C et D remontent à Établissement A, 2 salariés désassignés

### Scénario 3 : Suppression Hiérarchique
```
Établissement A
└── Département B
    └── Service C
        └── Unité D (vide)
```
**Action :** Suppression en cascade : Unité D → Service C → Département B

## Bonnes Pratiques

### Pour les Administrateurs

1. **Vérifiez toujours** les contraintes avant suppression
2. **Réassignez manuellement** les salariés si possible avant suppression forcée
3. **Documentez** les raisons de suppression forcée
4. **Testez** sur un environnement de développement

### Pour les Développeurs

1. **Utilisez les endpoints de vérification** avant toute suppression
2. **Gérez les erreurs** avec des messages explicites
3. **Implémentez des confirmations** pour les suppressions forcées
4. **Loggez** toutes les opérations de suppression

## Messages d'Erreur Types

### Suppression Bloquée
```
"Cannot delete unit Département RH: has 3 assigned workers. Use force=True to reassign."
```

### Suppression avec Sous-structures
```
"Cannot delete unit Service IT: has 2 children units. Use force=True to reassign."
```

### Suppression Mixte
```
"Cannot delete unit Établissement Principal: has 2 directly assigned workers and 15 workers in sub-units. Use force=True to reassign."
```

## Monitoring et Maintenance

### Métriques à Surveiller

1. **Taux de suppression forcée** : Indicateur de qualité des données
2. **Structures vides créées** : Optimisation des processus de création
3. **Réassignations automatiques** : Impact sur l'organisation

### Maintenance Préventive

1. **Audit périodique** des structures vides
2. **Nettoyage automatisé** des structures anciennes non utilisées
3. **Rapports** de structures candidates à la suppression

## Conclusion

Ce système de suppression conditionnelle offre :

- ✅ **Sécurité** : Protection contre les suppressions accidentelles
- ✅ **Flexibilité** : Options de suppression adaptées au contexte
- ✅ **Transparence** : Information complète sur les contraintes
- ✅ **Efficacité** : Nettoyage automatisé des données inutiles

Il permet de maintenir une base de données organisationnelle propre tout en préservant l'intégrité des données critiques.