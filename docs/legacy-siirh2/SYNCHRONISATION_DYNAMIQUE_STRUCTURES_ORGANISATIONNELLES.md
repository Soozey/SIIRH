# Synchronisation Dynamique des Structures Organisationnelles

## 📋 Vue d'Ensemble

Le système de structures organisationnelles est **entièrement synchronisé** entre la page Employeur et la page Travailleur. Toute création ou modification dans la page Employeur est **immédiatement disponible** dans la page Travailleur.

## ✅ Fonctionnalités Validées

### 1. Création de Structures
- ✅ Créer une structure dans la page Employeur
- ✅ Structure immédiatement disponible dans la page Travailleur
- ✅ Hiérarchie respectée (Établissement → Département → Service → Unité)

### 2. Modification de Structures
- ✅ Modifier le nom d'une structure dans la page Employeur
- ✅ Modification reflétée instantanément dans la page Travailleur
- ✅ Pas besoin de rafraîchir la page

### 3. Filtrage en Cascade
- ✅ Sélectionner un établissement affiche ses départements
- ✅ Sélectionner un département affiche ses services
- ✅ Sélectionner un service affiche ses unités
- ✅ Changement de niveau supérieur réinitialise les niveaux inférieurs

## 🔄 Architecture de Synchronisation

```
┌─────────────────────────────────────────────────────────────┐
│                    PAGE EMPLOYEUR                           │
│  (Gestion des structures organisationnelles)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ CRUD Operations
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              BASE DE DONNÉES PostgreSQL                     │
│                organizational_nodes                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ id | employer_id | parent_id | level | name | code   │  │
│  │ 1  | 1          | NULL      | etab  | JICA | JICA   │  │
│  │ 2  | 1          | 1         | dept  | AWC  | AWC    │  │
│  │ 3  | 1          | 2         | serv  | IT   | IT001  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Query via API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    PAGE TRAVAILLEUR                         │
│  (Affectation des salariés aux structures)                  │
│                                                             │
│  Composant: CascadingOrganizationalSelect                   │
│  Endpoint: /hierarchical-organization/cascading-options     │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Workflow Utilisateur

### Scénario 1 : Création d'une Nouvelle Structure

#### Étape 1 : Page Employeur
```
1. Aller sur la page "Employeurs"
2. Sélectionner un employeur
3. Cliquer sur "Gérer la hiérarchie organisationnelle"
4. Créer un nouvel établissement "Siège Social"
5. Créer un département "Ressources Humaines" sous "Siège Social"
```

#### Étape 2 : Page Travailleur (Immédiatement après)
```
1. Aller sur la page "Travailleurs"
2. Créer ou modifier un salarié
3. Dans "Structure Organisationnelle":
   - Établissement: "Siège Social" est disponible ✓
   - Sélectionner "Siège Social"
   - Département: "Ressources Humaines" apparaît ✓
```

### Scénario 2 : Modification d'une Structure

#### Étape 1 : Page Employeur
```
1. Modifier le nom "Siège Social" → "Siège Principal"
2. Sauvegarder
```

#### Étape 2 : Page Travailleur
```
1. Ouvrir le formulaire d'un salarié
2. Dans "Structure Organisationnelle":
   - Établissement: "Siège Principal" (nom mis à jour) ✓
```

## 🔧 Composants Techniques

### 1. Backend - API Endpoints

#### Création de Structure
```http
POST /employers/{employer_id}/hierarchical-organization/nodes
Content-Type: application/json

{
  "name": "Nom de la structure",
  "code": "CODE",
  "level": "etablissement",  // ou "departement", "service", "unite"
  "parent_id": null,          // ou ID du parent
  "description": "Description optionnelle"
}
```

#### Récupération des Options en Cascade
```http
GET /employers/{employer_id}/hierarchical-organization/cascading-options
GET /employers/{employer_id}/hierarchical-organization/cascading-options?parent_id=1
```

**Réponse :**
```json
[
  {
    "id": 1,
    "parent_id": null,
    "level": "etablissement",
    "name": "JICA",
    "code": "JICA",
    "description": null,
    "is_active": true,
    "has_children": true
  }
]
```

#### Modification de Structure
```http
PUT /employers/{employer_id}/hierarchical-organization/nodes/{node_id}
Content-Type: application/json

{
  "name": "Nouveau nom",
  "code": "NOUVEAU_CODE",
  "description": "Nouvelle description"
}
```

#### Suppression de Structure
```http
DELETE /employers/{employer_id}/hierarchical-organization/nodes/{node_id}
```

### 2. Frontend - Composant CascadingOrganizationalSelect

#### Utilisation dans Workers.tsx
```typescript
import { CascadingOrganizationalSelect } from "../components/CascadingOrganizationalSelect";

// Dans le formulaire
<CascadingOrganizationalSelect
  employerId={form.employer_id}
  value={{
    etablissement: form.etablissement ? Number(form.etablissement) : undefined,
    departement: form.departement ? Number(form.departement) : undefined,
    service: form.service ? Number(form.service) : undefined,
    unite: form.unite ? Number(form.unite) : undefined
  }}
  onChange={(values) => {
    setForm(f => ({
      ...f,
      etablissement: values.etablissement ? String(values.etablissement) : '',
      departement: values.departement ? String(values.departement) : '',
      service: values.service ? String(values.service) : '',
      unite: values.unite ? String(values.unite) : ''
    }));
  }}
/>
```

#### Fonctionnalités du Composant
- ✅ Chargement automatique des options via React Query
- ✅ Cache intelligent pour éviter les requêtes inutiles
- ✅ Invalidation automatique du cache lors des modifications
- ✅ Filtrage en cascade avec réinitialisation des niveaux inférieurs
- ✅ Affichage conditionnel des niveaux (un niveau n'apparaît que si le parent est sélectionné)
- ✅ Indicateurs visuels (icônes, états désactivés)
- ✅ Résumé de la sélection actuelle

## 📊 Modèle de Données

### Table : organizational_nodes

```sql
CREATE TABLE organizational_nodes (
    id SERIAL PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES organizational_nodes(id) ON DELETE CASCADE,
    level VARCHAR(50) NOT NULL CHECK (level IN ('etablissement', 'departement', 'service', 'unite')),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(employer_id, parent_id, name),
    UNIQUE(employer_id, code) WHERE code IS NOT NULL
);

-- Index pour les performances
CREATE INDEX idx_org_nodes_employer ON organizational_nodes(employer_id);
CREATE INDEX idx_org_nodes_parent ON organizational_nodes(parent_id);
CREATE INDEX idx_org_nodes_level ON organizational_nodes(level);
```

### Contraintes de Hiérarchie

1. **Niveau Établissement** (level = 'etablissement')
   - parent_id MUST BE NULL
   - Racine de la hiérarchie

2. **Niveau Département** (level = 'departement')
   - parent_id MUST BE un établissement
   - Enfant direct d'un établissement

3. **Niveau Service** (level = 'service')
   - parent_id MUST BE un département
   - Enfant direct d'un département

4. **Niveau Unité** (level = 'unite')
   - parent_id MUST BE un service
   - Enfant direct d'un service

## 🧪 Tests de Validation

### Test Automatisé
```bash
python test_dynamic_organizational_sync.py
```

**Résultats attendus :**
```
✓ Création de structure dans la page Employeur
✓ Structure immédiatement disponible via l'API cascading-options
✓ Création de sous-structure (hiérarchie)
✓ Filtrage en cascade fonctionnel
✓ Modification de structure reflétée dans l'API
✓ Nettoyage des structures de test
```

### Test Manuel

#### Test 1 : Création et Affichage
1. Page Employeur : Créer "Test Établissement"
2. Page Travailleur : Vérifier que "Test Établissement" apparaît dans la liste
3. ✅ Résultat : Structure visible immédiatement

#### Test 2 : Hiérarchie en Cascade
1. Page Employeur : Créer "Département A" sous "Test Établissement"
2. Page Travailleur : Sélectionner "Test Établissement"
3. ✅ Résultat : "Département A" apparaît dans la liste des départements

#### Test 3 : Modification
1. Page Employeur : Renommer "Test Établissement" → "Établissement Test"
2. Page Travailleur : Rafraîchir le formulaire
3. ✅ Résultat : Nouveau nom visible

## 🔍 Dépannage

### Problème : Structure créée mais non visible

**Cause possible :** Cache React Query non invalidé

**Solution :**
```typescript
// Dans le composant qui crée la structure
const queryClient = useQueryClient();

// Après création/modification
queryClient.invalidateQueries({ 
  queryKey: ['cascading-options', employerId] 
});
```

### Problème : Erreur 404 lors de la récupération

**Cause possible :** Mauvais endpoint

**Vérification :**
```typescript
// ✅ Correct
api.get(`/employers/${employerId}/hierarchical-organization/cascading-options`)

// ❌ Incorrect
api.get(`/employers/${employerId}/organizational-data/hierarchical`)
```

### Problème : Filtrage en cascade ne fonctionne pas

**Cause possible :** parent_id non passé correctement

**Vérification :**
```typescript
// ✅ Correct
api.get(`/employers/${employerId}/hierarchical-organization/cascading-options`, {
  params: { parent_id: selectedEtablissementId }
})

// ❌ Incorrect
api.get(`/employers/${employerId}/hierarchical-organization/cascading-options/${selectedEtablissementId}`)
```

## 📝 Bonnes Pratiques

### 1. Nommage des Structures
- ✅ Utiliser des noms descriptifs et uniques
- ✅ Ajouter des codes pour faciliter l'identification
- ❌ Éviter les doublons de noms au même niveau

### 2. Hiérarchie
- ✅ Respecter l'ordre : Établissement → Département → Service → Unité
- ✅ Ne pas sauter de niveaux
- ❌ Ne pas créer de cycles (A parent de B, B parent de A)

### 3. Suppression
- ⚠️ La suppression d'un parent supprime tous ses enfants (CASCADE)
- ✅ Vérifier les dépendances avant suppression
- ✅ Désactiver plutôt que supprimer si des salariés sont affectés

### 4. Performance
- ✅ Utiliser le cache React Query
- ✅ Charger uniquement les niveaux nécessaires
- ✅ Paginer si plus de 100 structures au même niveau

## 🎉 Résumé

Le système de synchronisation dynamique des structures organisationnelles est **pleinement fonctionnel** :

1. ✅ **Création** : Structures créées dans la page Employeur sont immédiatement disponibles dans la page Travailleur
2. ✅ **Modification** : Changements reflétés en temps réel
3. ✅ **Hiérarchie** : Filtrage en cascade respecte la structure parent-enfant
4. ✅ **Performance** : Cache intelligent et requêtes optimisées
5. ✅ **Fiabilité** : Contraintes de base de données garantissent l'intégrité

**Le champ "Structure organisationnelle" de la page Travailleur consomme dynamiquement le référentiel défini sur la page Employeur.** ✅

## 📅 Date de Validation
**16 janvier 2026**

## 🔗 Fichiers Concernés

### Backend
- `siirh-backend/app/routers/hierarchical_organization.py` - Routes API
- `siirh-backend/app/services/hierarchical_organizational_service.py` - Logique métier
- `siirh-backend/app/models.py` - Modèle organizational_nodes
- `siirh-backend/app/schemas.py` - Schémas Pydantic

### Frontend
- `siirh-frontend/src/components/CascadingOrganizationalSelect.tsx` - Composant de sélection
- `siirh-frontend/src/pages/Workers.tsx` - Page Travailleur
- `siirh-frontend/src/pages/Employers.tsx` - Page Employeur

### Tests
- `test_dynamic_organizational_sync.py` - Tests automatisés
