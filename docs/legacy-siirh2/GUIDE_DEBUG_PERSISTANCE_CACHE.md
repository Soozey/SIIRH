# 🔍 Guide de Débogage - Persistance du Cache

## 🎯 Objectif

Identifier la cause exacte de la persistance des données entre employeurs en utilisant les logs de débogage ajoutés au modal.

## 🛠️ Modifications Appliquées

### Logs de Débogage Ajoutés

Le modal `OrganizationalFilterModalOptimized.tsx` a été instrumenté avec des logs détaillés:

1. **Ouverture/Fermeture du modal**
2. **Changement d'employeur**
3. **Activation/Désactivation des filtres**
4. **Chargement des données**
5. **Invalidation du cache**

### Configuration Renforcée

- `staleTime: 0` - Données toujours périmées
- `gcTime: 0` - Pas de cache après démontage
- `refetchOnMount: 'always'` - Toujours refetch
- `queryClient.setQueryData()` - Force la réinitialisation

## 🧪 Procédure de Test avec Logs

### 1. Préparer l'Environnement

```bash
# Terminal 1: Backend
cd siirh-backend
python start_server.py

# Terminal 2: Frontend
cd siirh-frontend
npm run dev
```

### 2. Ouvrir le Navigateur avec Console

1. Ouvrir `http://localhost:5173/payroll`
2. Ouvrir F12 → Console
3. Filtrer les logs: Taper `[MODAL DEBUG]` dans le filtre

### 3. Scénario de Test Complet

**Étape 1: Ouvrir le modal**
```
Action: Cliquer sur "Imprimer tous les bulletins"

Logs attendus:
[MODAL DEBUG] Modal opened with employer 1
```

**Étape 2: Activer les filtres**
```
Action: Cocher "Filtrage par structure organisationnelle"

Logs attendus:
[MODAL DEBUG] useFilters changed to: true, employer: 1
[MODAL DEBUG] Fetching établissements for employer 1
[MODAL DEBUG] Received 2 établissements for employer 1: [...]
```

**Étape 3: Changer d'employeur**
```
Action: Sélectionner "Mandroso Services" (ID: 2)

Logs attendus:
[MODAL DEBUG] Employer changed to: 2
[MODAL DEBUG] Removing all cascading-options queries from cache
[MODAL DEBUG] Cache cleared for employer 2
[MODAL DEBUG] useFilters changed to: true, employer: 2
[MODAL DEBUG] Fetching établissements for employer 2
[MODAL DEBUG] Received 0 établissements for employer 2: []
```

**Étape 4: Vérifier l'affichage**
```
Vérification visuelle:
- Liste des établissements doit être VIDE
- Aucun établissement de Karibo visible
- Message "Tous les établissements" ou liste vide
```

## 🔍 Analyse des Logs

### Scénario 1: Logs Corrects mais Affichage Incorrect

**Logs:**
```
[MODAL DEBUG] Employer changed to: 2
[MODAL DEBUG] Removing all cascading-options queries from cache
[MODAL DEBUG] Cache cleared for employer 2
[MODAL DEBUG] Fetching établissements for employer 2
[MODAL DEBUG] Received 0 établissements for employer 2: []
```

**Mais:** Les établissements de Karibo sont toujours visibles

**Diagnostic:** Problème de rendu React - Les données sont correctes mais l'affichage ne se met pas à jour

**Solution:**
- Vérifier que `etablissements` est bien utilisé dans le rendu
- Vérifier qu'il n'y a pas de variable locale qui garde les anciennes données
- Forcer un re-render avec une key unique

### Scénario 2: Pas de Fetch pour Employeur 2

**Logs:**
```
[MODAL DEBUG] Employer changed to: 2
[MODAL DEBUG] Removing all cascading-options queries from cache
[MODAL DEBUG] Cache cleared for employer 2
[MODAL DEBUG] useFilters changed to: true, employer: 2
```

**Mais:** Pas de log "Fetching établissements for employer 2"

**Diagnostic:** La query n'est pas activée

**Causes possibles:**
- `enabled` est false
- `selectedEmployerId` n'est pas mis à jour
- `useFilters` est false

**Solution:**
- Vérifier la condition `enabled: isOpen && !!selectedEmployerId && useFilters`
- Ajouter plus de logs pour voir les valeurs

### Scénario 3: Fetch Correct mais Données Incorrectes

**Logs:**
```
[MODAL DEBUG] Fetching établissements for employer 2
[MODAL DEBUG] Received 2 établissements for employer 2: [{id: 40, name: "JICA"}, ...]
```

**Diagnostic:** Le backend retourne les mauvaises données

**Solution:**
- Vérifier l'URL de la requête dans Network tab
- Vérifier que l'employer_id est correct dans l'URL
- Problème backend - vérifier le service

### Scénario 4: Cache Non Invalidé

**Logs:**
```
[MODAL DEBUG] Employer changed to: 2
```

**Mais:** Pas de log "Removing all cascading-options queries from cache"

**Diagnostic:** Le useEffect ne s'exécute pas

**Causes possibles:**
- `selectedEmployerId` ne change pas réellement
- Le useEffect a un problème de dépendances

**Solution:**
- Vérifier que `selectedEmployerId` change bien
- Ajouter un log avant le useEffect

## 📊 Checklist de Débogage

### Vérifications Console

- [ ] Les logs `[MODAL DEBUG]` apparaissent
- [ ] Log "Modal opened" à l'ouverture
- [ ] Log "Employer changed" lors du changement
- [ ] Log "Removing all cascading-options queries" lors du changement
- [ ] Log "Fetching établissements" pour le nouvel employeur
- [ ] Log "Received X établissements" avec le bon nombre

### Vérifications Network

- [ ] Requête GET vers `/employers/2/hierarchical-organization/cascading-options`
- [ ] URL contient le bon employer_id
- [ ] Réponse contient `[]` (liste vide) pour Mandroso
- [ ] Pas de requête vers `/employers/1/...` après le changement

### Vérifications Visuelles

- [ ] Liste des établissements vide pour Mandroso
- [ ] Aucun établissement de Karibo visible
- [ ] Sélections réinitialisées
- [ ] Chemin hiérarchique vide

## 🐛 Problèmes Connus et Solutions

### Problème 1: React Query Cache Persistant

**Symptôme:** Les données persistent malgré `removeQueries`

**Solution appliquée:**
```typescript
// Force la réinitialisation des données
queryClient.setQueryData(['cascading-options', selectedEmployerId, null], []);
```

### Problème 2: Timing de l'Invalidation

**Symptôme:** L'invalidation arrive après le fetch

**Solution:** Utiliser `refetchOnMount: 'always'`

### Problème 3: État Local Persistant

**Symptôme:** Les données sont correctes mais l'affichage ne change pas

**Solution:** Vérifier qu'il n'y a pas de variable locale qui garde les données

## 🔧 Actions Correctives Supplémentaires

### Si le Problème Persiste

**Option 1: Désactiver Complètement le Cache**
```typescript
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

**Option 2: Utiliser une Key Unique par Ouverture**
```typescript
const [modalKey, setModalKey] = useState(0);

useEffect(() => {
  if (isOpen) {
    setModalKey(prev => prev + 1);
  }
}, [isOpen]);

// Dans la query
queryKey: ['cascading-options', modalKey, selectedEmployerId, null]
```

**Option 3: Forcer un Re-render**
```typescript
const [renderKey, setRenderKey] = useState(0);

useEffect(() => {
  setRenderKey(prev => prev + 1);
}, [selectedEmployerId]);

// Dans le JSX
<div key={renderKey}>
  {/* Contenu du modal */}
</div>
```

## 📝 Rapport de Débogage

### Template

```
Date: _______________
Navigateur: _______________

Logs Console:
[ ] Logs [MODAL DEBUG] visibles
[ ] Modal opened: OUI / NON
[ ] Employer changed: OUI / NON
[ ] Cache cleared: OUI / NON
[ ] Fetching pour nouvel employeur: OUI / NON
[ ] Received correct data: OUI / NON

Network Tab:
URL de la requête: _______________________________
Employer ID dans URL: _______________
Réponse du backend: _______________________________

Affichage:
[ ] Liste vide pour Mandroso
[ ] Établissements de Karibo visibles: OUI / NON

Diagnostic:
_____________________________________________
_____________________________________________

Solution appliquée:
_____________________________________________
_____________________________________________
```

## 🎯 Résultat Attendu

Après avoir suivi ce guide, vous devriez pouvoir identifier exactement où le problème se situe:

1. **Backend** - Si les logs montrent des données incorrectes du backend
2. **React Query** - Si le cache n'est pas invalidé
3. **React Render** - Si les données sont correctes mais l'affichage ne change pas
4. **Timing** - Si l'ordre des opérations est incorrect

---

**Date:** 16 janvier 2026  
**Priorité:** CRITIQUE  
**Objectif:** Identifier la cause racine de la persistance du cache
