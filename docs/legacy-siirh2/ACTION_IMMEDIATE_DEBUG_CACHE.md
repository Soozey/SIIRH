# 🚀 Action Immédiate - Débogage du Cache

## 🎯 Objectif

Identifier la cause exacte de la persistance des données entre employeurs avec les logs de débogage.

## ⚡ Actions Rapides

### 1. Redémarrer le Frontend (30 secondes)

```bash
cd siirh-frontend
# Arrêter avec Ctrl+C si déjà lancé
npm run dev
```

### 2. Ouvrir le Navigateur avec Console (1 minute)

1. Ouvrir `http://localhost:5173/payroll`
2. Appuyer sur **F12**
3. Aller dans l'onglet **Console**
4. Dans le filtre, taper: `[MODAL DEBUG]`

### 3. Tester le Scénario (2 minutes)

**Étape 1:** Cliquer sur "Imprimer tous les bulletins"
- ✅ Vérifier log: `[MODAL DEBUG] Modal opened with employer 1`

**Étape 2:** Cocher "Filtrage par structure organisationnelle"
- ✅ Vérifier log: `[MODAL DEBUG] useFilters changed to: true`
- ✅ Vérifier log: `[MODAL DEBUG] Fetching établissements for employer 1`
- ✅ Vérifier log: `[MODAL DEBUG] Received 2 établissements for employer 1`

**Étape 3:** Changer pour "Mandroso Services"
- ✅ Vérifier log: `[MODAL DEBUG] Employer changed to: 2`
- ✅ Vérifier log: `[MODAL DEBUG] Removing all cascading-options queries from cache`
- ✅ Vérifier log: `[MODAL DEBUG] Cache cleared for employer 2`
- ✅ Vérifier log: `[MODAL DEBUG] Fetching établissements for employer 2`
- ✅ Vérifier log: `[MODAL DEBUG] Received 0 établissements for employer 2`

**Étape 4:** Vérifier l'affichage
- ❓ La liste des établissements est-elle vide?
- ❓ Voyez-vous encore "JICA" ou "NUMHERIT"?

## 📊 Analyse Rapide

### Cas 1: Logs OK mais Affichage Incorrect

**Logs montrent:**
```
[MODAL DEBUG] Received 0 établissements for employer 2: []
```

**Mais:** Vous voyez encore "JICA" et "NUMHERIT"

**Diagnostic:** Problème de rendu React, pas de cache

**Solution:** Voir `GUIDE_DEBUG_PERSISTANCE_CACHE.md` → Solution C

### Cas 2: Pas de Fetch pour Employeur 2

**Logs montrent:**
```
[MODAL DEBUG] Employer changed to: 2
[MODAL DEBUG] Cache cleared for employer 2
```

**Mais:** Pas de log "Fetching établissements for employer 2"

**Diagnostic:** La query n'est pas activée

**Solution:** Vérifier que "Filtrage par structure" est bien coché

### Cas 3: Fetch Correct avec Données Incorrectes

**Logs montrent:**
```
[MODAL DEBUG] Received 2 établissements for employer 2: [...]
```

**Diagnostic:** Problème backend (peu probable)

**Solution:** Exécuter `python audit_employer_id_chain.py`

## 🔧 Actions Selon le Résultat

### Si Cas 1 (Rendu React)

Ajouter cette modification dans `OrganizationalFilterModalOptimized.tsx`:

```typescript
// Ajouter un state pour forcer le re-render
const [renderKey, setRenderKey] = useState(0);

// Dans le useEffect du changement d'employeur
useEffect(() => {
  // ... code existant ...
  setRenderKey(prev => prev + 1); // AJOUTER CETTE LIGNE
}, [selectedEmployerId, queryClient]);

// Dans le select des établissements
<select 
  key={`etablissement-${renderKey}`} // AJOUTER key
  value={selectedEtablissement || ''}
  onChange={...}
>
```

### Si Cas 2 (Query Non Activée)

Vérifier que:
1. "Filtrage par structure" est coché
2. Un employeur est sélectionné
3. Le modal est ouvert

### Si Cas 3 (Backend)

Exécuter:
```bash
python audit_employer_id_chain.py
```

## 📝 Rapport Rapide

Copier-coller ce template avec vos résultats:

```
Date: _______________

Logs Console:
[ ] Modal opened: OUI / NON
[ ] Employer changed: OUI / NON
[ ] Cache cleared: OUI / NON
[ ] Fetching pour employeur 2: OUI / NON
[ ] Received 0 établissements: OUI / NON

Affichage:
[ ] Liste vide: OUI / NON
[ ] Établissements de Karibo visibles: OUI / NON

Cas identifié: 1 / 2 / 3

Notes:
_________________________________
```

## 📚 Documentation Complète

- `GUIDE_DEBUG_PERSISTANCE_CACHE.md` - Guide détaillé
- `AUDIT_CORRECTION_PERSISTANCE_CACHE.md` - Analyse complète
- `audit_employer_id_chain.py` - Test backend

## ⏱️ Temps Estimé

- Test: 3 minutes
- Analyse: 2 minutes
- **Total: 5 minutes**

---

**Date:** 16 janvier 2026  
**Priorité:** CRITIQUE  
**Action:** TESTER MAINTENANT
