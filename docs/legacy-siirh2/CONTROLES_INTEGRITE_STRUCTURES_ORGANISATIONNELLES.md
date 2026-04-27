# Contrôles d'Intégrité - Structures Organisationnelles

## 📋 Vue d'Ensemble

Le système de gestion des structures organisationnelles intègre des **contrôles d'intégrité stricts** pour garantir la cohérence des données et éviter les suppressions accidentelles.

## ✅ Fonctionnalités Implémentées

### 1. Boutons de Gestion Restaurés
- ✅ **Bouton "Nouvel Établissement"** : Créer un établissement racine
- ✅ **Bouton "+" (Ajouter)** : Créer une sous-structure sous le nœud sélectionné
- ✅ **Bouton "✏️" (Modifier)** : Modifier le nom, code et description
- ✅ **Bouton "🗑️" (Supprimer)** : Supprimer avec contrôles d'intégrité

### 2. Contrôles d'Intégrité pour la Suppression

#### Règle 1 : Interdiction si Sous-Structures
```
❌ INTERDIT : Supprimer une structure qui contient des sous-structures
✅ AUTORISÉ : Suppression forcée avec confirmation explicite
```

**Exemple :**
- Établissement "Siège" contient Département "RH"
- Tentative de suppression de "Siège" → **REFUSÉE**
- Message : "Impossible de supprimer le nœud: il a 1 enfant(s)"

#### Règle 2 : Interdiction si Salariés Affectés
```
❌ INTERDIT : Supprimer une structure avec des salariés affectés
✅ AUTORISÉ : Suppression forcée (les salariés seront désaffectés)
```

**Exemple :**
- Service "Paie" a 5 salariés affectés
- Tentative de suppression → **REFUSÉE**
- Message : "Impossible de supprimer le nœud: 5 salarié(s) y sont affectés"

### 3. Endpoint de Vérification Pré-Suppression

**Endpoint :** `GET /employers/{id}/hierarchical-organization/nodes/{node_id}/deletion-info`

**Réponse :**
```json
{
  "node_id": 15,
  "node_name": "Établissement Test",
  "node_level": "etablissement",
  "children_count": 2,
  "workers_count": 5,
  "can_delete": false,
  "requires_force": true,
  "warnings": [
    "Cette structure contient 2 sous-structure(s)",
    "5 salarié(s) sont affectés à cette structure"
  ]
}
```

## 🎯 Workflow Utilisateur

### Scénario 1 : Création d'une Structure

```
1. Ouvrir la page "Employeurs"
2. Cliquer sur "Gérer la hiérarchie organisationnelle"
3. Cliquer sur "Nouvel Établissement"
4. Remplir le formulaire:
   - Nom: "Siège Social" (obligatoire)
   - Code: "SIEGE" (optionnel)
   - Description: "Établissement principal" (optionnel)
5. Cliquer sur "Créer"
6. ✅ Structure créée et visible immédiatement
```

### Scénario 2 : Ajout d'une Sous-Structure

```
1. Sélectionner un nœud parent (ex: Établissement "Siège Social")
2. Cliquer sur le bouton "+" à côté du nœud
3. Le formulaire s'ouvre avec le niveau automatique (Département)
4. Remplir le nom et cliquer sur "Créer"
5. ✅ Sous-structure créée sous le parent
```

### Scénario 3 : Modification d'une Structure

```
1. Sélectionner un nœud
2. Cliquer sur le bouton "✏️" (Modifier)
3. Modifier le nom, code ou description
4. Cliquer sur "Modifier"
5. ✅ Structure mise à jour
6. ✅ Changement visible dans la page Travailleur
```

### Scénario 4 : Suppression Sécurisée

```
1. Sélectionner un nœud
2. Cliquer sur le bouton "🗑️" (Supprimer)
3. Modal de confirmation s'affiche avec:
   - Nombre de sous-structures
   - Nombre de salariés affectés
   - Avertissements
4. Deux cas possibles:

   CAS A - Structure vide:
   ✅ Bouton "Supprimer" disponible
   → Suppression immédiate

   CAS B - Structure occupée:
   ⚠️  Bouton "Suppression Forcée" disponible
   → Confirmation supplémentaire requise
   → Suppression en cascade des sous-structures
   → Désaffectation des salariés
```

## 🔧 Architecture Technique

### Backend - Contrôles d'Intégrité

#### Service : `HierarchicalOrganizationalService`

**Méthode `delete_node`:**
```python
def delete_node(self, node_id: int, force: bool = False) -> bool:
    # 1. Vérifier les enfants
    children_count = self.db.query(OrganizationalNode).filter(
        OrganizationalNode.parent_id == node_id,
        OrganizationalNode.is_active == True
    ).count()
    
    if children_count > 0 and not force:
        raise ValueError(f"Impossible de supprimer: {children_count} enfant(s)")
    
    # 2. Vérifier les salariés affectés
    workers_count = self._count_assigned_workers(node_id)
    if workers_count > 0 and not force:
        raise ValueError(f"Impossible de supprimer: {workers_count} salarié(s) affectés")
    
    # 3. Suppression logique
    node.is_active = False
    self.db.commit()
```

**Méthode `_count_assigned_workers`:**
```python
def _count_assigned_workers(self, node_id: int) -> int:
    node = self.db.query(OrganizationalNode).filter(
        OrganizationalNode.id == node_id
    ).first()
    
    if node.level == 'etablissement':
        return self.db.query(Worker).filter(
            Worker.etablissement == str(node_id)
        ).count()
    elif node.level == 'departement':
        return self.db.query(Worker).filter(
            Worker.departement == str(node_id)
        ).count()
    # ... etc pour service et unite
```

**Méthode `get_node_deletion_info`:**
```python
def get_node_deletion_info(self, node_id: int) -> Dict[str, Any]:
    children_count = self.db.query(OrganizationalNode).filter(
        OrganizationalNode.parent_id == node_id,
        OrganizationalNode.is_active == True
    ).count()
    
    workers_count = self._count_assigned_workers(node_id)
    can_delete = children_count == 0 and workers_count == 0
    
    return {
        'node_id': node_id,
        'node_name': node.name,
        'children_count': children_count,
        'workers_count': workers_count,
        'can_delete': can_delete,
        'requires_force': not can_delete,
        'warnings': self._get_deletion_warnings(children_count, workers_count)
    }
```

### Frontend - Modal Amélioré

**Composant :** `HierarchyManagerModalEnhanced.tsx`

**Fonctionnalités :**
1. **Affichage de l'arbre hiérarchique**
   - Icônes par niveau (🏢 🏬 👥 📦)
   - Couleurs par niveau
   - Compteur de salariés par nœud
   - Expand/Collapse

2. **Boutons d'action contextuels**
   - Apparaissent uniquement sur le nœud sélectionné
   - "+" : Ajouter une sous-structure (si niveau < unite)
   - "✏️" : Modifier
   - "🗑️" : Supprimer

3. **Formulaire de création/modification**
   - Modal overlay
   - Champs : Nom, Code, Description
   - Niveau automatique selon le parent
   - Validation côté client

4. **Modal de confirmation de suppression**
   - Affichage des informations critiques
   - Compteurs : sous-structures et salariés
   - Avertissements visuels
   - Deux boutons selon le cas :
     - "Supprimer" (structure vide)
     - "Suppression Forcée" (structure occupée)

**Code clé :**
```typescript
// Charger les infos de suppression
const { data: deletionInfo } = useQuery({
  queryKey: ['deletion-info', selectedNodeId],
  queryFn: async () => {
    const response = await api.get(
      `/employers/${employerId}/hierarchical-organization/nodes/${selectedNodeId}/deletion-info`
    );
    return response.data;
  },
  enabled: !!selectedNodeId && showDeleteConfirm
});

// Mutation de suppression
const deleteMutation = useMutation({
  mutationFn: async ({ nodeId, force }: { nodeId: number; force: boolean }) => {
    const response = await api.delete(
      `/employers/${employerId}/hierarchical-organization/nodes/${nodeId}`,
      { params: { force } }
    );
    return response.data;
  },
  onSuccess: () => {
    // Invalider les caches pour rafraîchir
    queryClient.invalidateQueries({ queryKey: ['organizational-tree'] });
    queryClient.invalidateQueries({ queryKey: ['cascading-options'] });
  }
});
```

## 🧪 Tests de Validation

### Test Automatisé
```bash
python test_integrity_controls_deletion.py
```

**Résultats attendus :**
```
✓ TEST 1: Suppression interdite avec sous-structures
   - Endpoint /deletion-info retourne children_count > 0
   - DELETE sans force retourne erreur 400
   - Message explicite

✓ TEST 2: Suppression autorisée pour structure vide
   - children_count = 0
   - workers_count = 0
   - DELETE réussit

✓ TEST 3: Suppression forcée fonctionne
   - force=True permet la suppression
   - Cascade sur les enfants
```

### Test Manuel

#### Test 1 : Création et Suppression Simple
1. Créer un établissement "Test"
2. Tenter de le supprimer → ✅ Réussit (pas d'enfants)

#### Test 2 : Suppression avec Sous-Structures
1. Créer établissement "Test"
2. Créer département "Dept" sous "Test"
3. Tenter de supprimer "Test" → ❌ Refusé
4. Message : "Impossible de supprimer: 1 enfant(s)"

#### Test 3 : Suppression Forcée
1. Même configuration que Test 2
2. Cliquer sur "Suppression Forcée"
3. Confirmer l'avertissement
4. ✅ Établissement et département supprimés

#### Test 4 : Suppression avec Salariés
1. Créer service "Paie"
2. Affecter 2 salariés au service
3. Tenter de supprimer "Paie" → ❌ Refusé
4. Message : "Impossible de supprimer: 2 salarié(s) affectés"

## 📊 Indicateurs Visuels

### Dans l'Arbre Hiérarchique

**Structure vide (supprimable) :**
```
🏢 Établissement Test
   ✓ Supprimable
   👥 0 salariés
```

**Structure occupée :**
```
🏢 Siège Social
   ⚠ Occupée
   👥 15 salariés
   └── 🏬 Département RH
```

### Dans le Modal de Suppression

**Structure vide :**
```
┌─────────────────────────────────────┐
│ ✅ Confirmer la suppression         │
│                                     │
│ Établissement Test                  │
│                                     │
│ Sous-structures: 0                  │
│ Salariés affectés: 0                │
│                                     │
│ ✓ Cette structure peut être         │
│   supprimée en toute sécurité       │
│                                     │
│ [Annuler]  [Supprimer]              │
└─────────────────────────────────────┘
```

**Structure occupée :**
```
┌─────────────────────────────────────┐
│ ⚠️  Confirmer la suppression        │
│                                     │
│ Siège Social                        │
│                                     │
│ Sous-structures: 3                  │
│ Salariés affectés: 15               │
│                                     │
│ ⚠️  Cette structure contient 3      │
│    sous-structure(s)                │
│ ⚠️  15 salarié(s) sont affectés     │
│                                     │
│ [Annuler]  [Suppression Forcée]     │
└─────────────────────────────────────┘
```

## 🔄 Synchronisation Dynamique Maintenue

### Garanties
1. ✅ **Création** : Structure immédiatement disponible dans page Travailleur
2. ✅ **Modification** : Changements reflétés en temps réel
3. ✅ **Suppression** : Structure retirée des options de sélection
4. ✅ **Cache invalidé** : React Query rafraîchit automatiquement

### Workflow Complet
```
PAGE EMPLOYEUR                    PAGE TRAVAILLEUR
     │                                  │
     │ 1. Créer "Siège"                │
     ├──────────────────────────────>  │
     │                                  │ 2. "Siège" apparaît
     │                                  │    dans les options
     │                                  │
     │ 3. Modifier "Siège"              │
     │    → "Siège Principal"           │
     ├──────────────────────────────>  │
     │                                  │ 4. Nom mis à jour
     │                                  │    automatiquement
     │                                  │
     │ 5. Supprimer "Siège Principal"   │
     ├──────────────────────────────>  │
     │                                  │ 6. "Siège Principal"
     │                                  │    retiré des options
```

## 📝 Bonnes Pratiques

### Pour les Administrateurs

1. **Avant de supprimer :**
   - Vérifier le nombre de sous-structures
   - Vérifier le nombre de salariés affectés
   - Utiliser l'endpoint `/deletion-info` pour évaluer l'impact

2. **Suppression forcée :**
   - Utiliser uniquement en connaissance de cause
   - Comprendre que les salariés seront désaffectés
   - Prévoir une réaffectation des salariés

3. **Organisation hiérarchique :**
   - Créer d'abord les établissements
   - Puis les départements
   - Puis les services
   - Enfin les unités

### Pour les Développeurs

1. **Invalidation du cache :**
   ```typescript
   queryClient.invalidateQueries({ queryKey: ['organizational-tree'] });
   queryClient.invalidateQueries({ queryKey: ['cascading-options'] });
   ```

2. **Gestion des erreurs :**
   ```typescript
   try {
     await deleteMutation.mutateAsync({ nodeId, force });
   } catch (error) {
     if (error.response?.status === 400) {
       // Afficher le message d'erreur à l'utilisateur
       alert(error.response.data.detail);
     }
   }
   ```

3. **Confirmation utilisateur :**
   ```typescript
   if (deletionInfo.requires_force) {
     const confirmed = confirm(
       '⚠️ ATTENTION: Cette suppression forcée supprimera toutes les sous-structures. Continuer?'
     );
     if (!confirmed) return;
   }
   ```

## ✅ Résumé

Le système de gestion des structures organisationnelles est maintenant **complet et sécurisé** :

1. ✅ **Boutons restaurés** : Création, modification, suppression
2. ✅ **Contrôles d'intégrité** : Interdiction si sous-structures ou salariés
3. ✅ **Endpoint de vérification** : `/deletion-info` pour évaluer l'impact
4. ✅ **Suppression forcée** : Avec confirmation explicite
5. ✅ **Synchronisation dynamique** : Page Travailleur consomme le référentiel à jour
6. ✅ **Interface intuitive** : Indicateurs visuels et avertissements clairs

**Les règles de gestion sont strictement appliquées :**
- ⚠️  Interdiction de suppression si sous-structures (sauf force)
- ⚠️  Interdiction de suppression si salariés affectés (sauf force)
- ✅ Synchronisation automatique entre pages Employeur et Travailleur

## 📅 Date de Validation
**16 janvier 2026**

## 🐛 Problèmes Résolus

### Problème 1 : Affichage après Création (RÉSOLU ✅)

**Symptôme :** Les structures créées n'apparaissaient pas dans l'arbre du modal.

**Cause :** Incompatibilité de format entre backend et frontend:
- Backend retournait: `{ nodes: [...], total_count: X }`
- Frontend attendait: `{ tree: [...], total_units: X }`

**Solution :** Modification du router backend pour retourner le format correct.

**Fichier modifié :** `siirh-backend/app/routers/hierarchical_organization.py`

**Tests de validation :**
- ✅ `debug_creation_display.py` - Diagnostic du problème
- ✅ `test_creation_workflow.py` - Workflow complet
- ✅ `test_frontend_creation.py` - Compatibilité frontend
- ✅ `test_frontend_simulation.py` - Simulation complète

**Résultat :** Les structures créées apparaissent maintenant immédiatement dans l'arbre sans nécessiter de rafraîchissement manuel.

**Documentation :** Voir `RESOLUTION_AFFICHAGE_CREATION_STRUCTURES.md` pour les détails complets.

## 🔗 Fichiers Modifiés/Créés

### Backend
- `siirh-backend/app/services/hierarchical_organizational_service.py` - Contrôles d'intégrité
- `siirh-backend/app/routers/hierarchical_organization.py` - Endpoint `/deletion-info`

### Frontend
- `siirh-frontend/src/components/HierarchyManagerModalEnhanced.tsx` - Modal amélioré (NOUVEAU)
- `siirh-frontend/src/pages/Employers.tsx` - Utilisation du nouveau modal

### Tests
- `test_integrity_controls_deletion.py` - Tests automatisés
