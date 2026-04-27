# 🔍 Audit et Correction - Persistance du Cache entre Employeurs

## 🚨 Alerte Critique

**Problème:** Malgré les corrections précédentes, la fuite de données entre employeurs persiste.

**Symptôme:** Les résultats de "Mandroso Services" restent pollués par le contexte de "Karibo Services".

## 🔬 Audit Complet Effectué

### 1. Audit Backend

**Script:** `audit_employer_id_chain.py`

**Résultats:**
- ✅ Backend correct - Isolation parfaite au niveau API
- ✅ Karibo Services (ID: 1) → 2 structures
- ✅ Mandroso Services (ID: 2) → 0 structures
- ✅ Pas de chevauchement d'IDs
- ✅ Pas de fuite de données au niveau backend

**Conclusion:** Le backend fonctionne parfaitement. Le problème est **100% côté frontend**.

### 2. Analyse de la Chaîne de Transmission

```
Sélection Employeur (Frontend)
    ↓
selectedEmployerId (State React)
    ↓
React Query queryKey: ['cascading-options', selectedEmployerId, ...]
    ↓
API Request: GET /employers/{selectedEmployerId}/hierarchical-organization/cascading-options
    ↓
Backend Response (Correct)
    ↓
React Query Cache (PROBLÈME ICI)
    ↓
Affichage (Données incorrectes)
```

**Point de blocage identifié:** React Query Cache

## 🛠️ Corrections Appliquées

### Correction 1: Logs de Débogage

Ajout de logs détaillés pour tracer le flux de données:

```typescript
// Ouverture du modal
console.log(`[MODAL DEBUG] Modal opened with employer ${selectedEmployerId}`);

// Changement d'employeur
console.log(`[MODAL DEBUG] Employer changed to: ${selectedEmployerId}`);
console.log(`[MODAL DEBUG] Removing all cascading-options queries from cache`);
console.log(`[MODAL DEBUG] Cache cleared for employer ${selectedEmployerId}`);

// Chargement des données
console.log(`[MODAL DEBUG] Fetching établissements for employer ${selectedEmployerId}`);
console.log(`[MODAL DEBUG] Received ${response.data.length} établissements for employer ${selectedEmployerId}:`, response.data);

// Activation des filtres
console.log(`[MODAL DEBUG] useFilters changed to: ${useFilters}, employer: ${selectedEmployerId}`);
```

### Correction 2: Force Reset du Cache

Ajout d'un reset forcé en plus de `removeQueries`:

```typescript
useEffect(() => {
  // Réinitialiser les sélections
  setSelectedEtablissement(null);
  setSelectedDepartement(null);
  setSelectedService(null);
  setSelectedUnite(null);
  
  // Invalider le cache
  queryClient.removeQueries({ 
    queryKey: ['cascading-options'],
    exact: false 
  });
  
  // NOUVEAU: Force la réinitialisation des données
  queryClient.setQueryData(['cascading-options', selectedEmployerId, null], []);
  
}, [selectedEmployerId, queryClient]);
```

### Correction 3: Configuration Renforcée des Queries

```typescript
const { data: etablissements = [] } = useQuery<CascadingOption[]>({
  queryKey: ['cascading-options', selectedEmployerId, null],
  queryFn: async () => {
    console.log(`[MODAL DEBUG] Fetching établissements for employer ${selectedEmployerId}`);
    const response = await api.get(
      `/employers/${selectedEmployerId}/hierarchical-organization/cascading-options`,
      { params: { parent_id: null } }
    );
    console.log(`[MODAL DEBUG] Received ${response.data.length} établissements:`, response.data);
    return response.data;
  },
  enabled: isOpen && !!selectedEmployerId && useFilters,
  staleTime: 0,
  gcTime: 0,
  refetchOnMount: 'always', // NOUVEAU: Toujours refetch au montage
  refetchOnWindowFocus: false
});
```

## 🧪 Procédure de Test

### Test avec Logs

1. **Ouvrir le navigateur**
   - URL: `http://localhost:5173/payroll`
   - F12 → Console
   - Filtrer: `[MODAL DEBUG]`

2. **Scénario de test**
   ```
   1. Cliquer sur "Imprimer tous les bulletins"
      → Vérifier log: "Modal opened with employer 1"
   
   2. Cocher "Filtrage par structure"
      → Vérifier log: "useFilters changed to: true"
      → Vérifier log: "Fetching établissements for employer 1"
      → Vérifier log: "Received 2 établissements"
   
   3. Changer pour "Mandroso Services"
      → Vérifier log: "Employer changed to: 2"
      → Vérifier log: "Removing all cascading-options queries"
      → Vérifier log: "Cache cleared for employer 2"
      → Vérifier log: "Fetching établissements for employer 2"
      → Vérifier log: "Received 0 établissements"
   
   4. Vérifier l'affichage
      → Liste des établissements doit être VIDE
      → Aucun établissement de Karibo visible
   ```

### Analyse des Logs

Les logs permettront d'identifier exactement où le problème se situe:

**Si les logs montrent "Received 0 établissements" mais que l'affichage montre des établissements:**
→ Problème de rendu React, pas de cache

**Si les logs ne montrent pas "Fetching établissements for employer 2":**
→ La query n'est pas activée, vérifier la condition `enabled`

**Si les logs montrent "Received 2 établissements for employer 2":**
→ Problème backend (peu probable vu l'audit)

## 📊 Hypothèses et Solutions

### Hypothèse 1: Cache React Query Persistant

**Symptôme:** `removeQueries` ne fonctionne pas

**Solution appliquée:**
- Ajout de `queryClient.setQueryData()` pour forcer le reset
- Configuration `refetchOnMount: 'always'`

### Hypothèse 2: Timing de l'Invalidation

**Symptôme:** L'invalidation arrive après le fetch

**Solution appliquée:**
- `staleTime: 0` - Données toujours périmées
- `refetchOnMount: 'always'` - Toujours refetch

### Hypothèse 3: État Local Persistant

**Symptôme:** Les données sont correctes mais l'affichage ne change pas

**Solution:** Les logs permettront de le détecter

### Hypothèse 4: Problème de Rendu React

**Symptôme:** React ne re-render pas avec les nouvelles données

**Solution potentielle:** Ajouter une `key` unique au composant

## 🔧 Solutions Supplémentaires (Si Nécessaire)

### Solution A: Key Unique par Ouverture

```typescript
const [modalKey, setModalKey] = useState(0);

useEffect(() => {
  if (isOpen) {
    setModalKey(prev => prev + 1);
  }
}, [isOpen]);

// Dans le JSX
<div key={modalKey} className="...">
  {/* Contenu du modal */}
</div>
```

### Solution B: Désactiver Complètement le Cache

```typescript
// Dans App.tsx ou main.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0,
      gcTime: 0,
      refetchOnMount: 'always',
      refetchOnWindowFocus: false,
      retry: false
    }
  }
});
```

### Solution C: Forcer un Re-render

```typescript
const [renderKey, setRenderKey] = useState(0);

useEffect(() => {
  setRenderKey(prev => prev + 1);
}, [selectedEmployerId]);

// Dans le select des établissements
<select key={renderKey} ...>
```

## 📝 Fichiers Modifiés

### Frontend

**Fichier:** `siirh-frontend/src/components/OrganizationalFilterModalOptimized.tsx`

**Modifications:**
1. Ajout de logs de débogage (10 lignes)
2. Ajout de `queryClient.setQueryData()` pour force reset
3. Ajout de `refetchOnMount: 'always'` dans la query
4. Ajout d'un useEffect pour logger `useFilters`

**Lignes modifiées:** ~30 lignes

### Scripts de Test

**Fichiers créés:**
1. `audit_employer_id_chain.py` - Audit complet de la chaîne
2. `GUIDE_DEBUG_PERSISTANCE_CACHE.md` - Guide de débogage
3. `AUDIT_CORRECTION_PERSISTANCE_CACHE.md` - Ce document

## ✅ Prochaines Étapes

### 1. Test Immédiat

```bash
# Redémarrer le frontend
cd siirh-frontend
npm run dev

# Ouvrir le navigateur
# http://localhost:5173/payroll
# F12 → Console → Filtrer "[MODAL DEBUG]"
```

### 2. Suivre le Guide de Débogage

Consulter `GUIDE_DEBUG_PERSISTANCE_CACHE.md` pour la procédure détaillée.

### 3. Analyser les Logs

Les logs permettront d'identifier la cause exacte:
- Cache non invalidé?
- Query non activée?
- Données incorrectes du backend?
- Problème de rendu React?

### 4. Appliquer la Solution Appropriée

Selon les logs, appliquer une des solutions supplémentaires si nécessaire.

## 🎯 Résultat Attendu

Avec les logs de débogage, nous pourrons identifier **exactement** où le problème se situe et appliquer la solution appropriée.

**Scénarios possibles:**

1. **Les logs montrent des données correctes mais l'affichage est incorrect**
   → Problème de rendu React → Solution C (forcer re-render)

2. **Les logs ne montrent pas de fetch pour le nouvel employeur**
   → Query non activée → Vérifier la condition `enabled`

3. **Les logs montrent des données incorrectes du backend**
   → Problème backend (peu probable) → Vérifier le service

4. **Le cache n'est pas invalidé**
   → Problème de timing → Solution A (key unique)

---

**Date:** 16 janvier 2026  
**Priorité:** CRITIQUE  
**Statut:** EN COURS DE DÉBOGAGE  
**Prochaine étape:** Tester avec les logs et analyser les résultats
