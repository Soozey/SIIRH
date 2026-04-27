# 🔧 Correction - Sélection d'Employeur dans le Modal

## 🐛 Problème Identifié

Dans la page Bulletin, le modal "Imprimer tous les bulletins" fixait l'employeur et ne permettait pas de le changer, même si d'autres employeurs contenaient des salariés.

**Symptôme:** Le dropdown de sélection d'employeur était visible mais non fonctionnel - il revenait toujours à l'employeur par défaut.

## 🔍 Cause Racine

Le `useEffect` qui initialisait l'employeur sélectionné s'exécutait **à chaque changement** de `defaultEmployerId` ou `selectedEmployerId`, ce qui réinitialisait la sélection même quand l'utilisateur changeait manuellement d'employeur.

**Code problématique:**
```typescript
useEffect(() => {
  if (isOpen && employers.length > 0) {
    if (defaultEmployerId && defaultEmployerId > 0) {
      setSelectedEmployerId(defaultEmployerId);  // ❌ Force toujours le default
    } else if (!selectedEmployerId || selectedEmployerId === 0) {
      setSelectedEmployerId(employers[0].id);
    }
  }
}, [isOpen, employers, defaultEmployerId, selectedEmployerId]);  // ❌ Trop de dépendances
```

**Résultat:** Chaque fois que `selectedEmployerId` changeait (quand l'utilisateur sélectionnait un autre employeur), le `useEffect` se déclenchait et le réinitialisait à `defaultEmployerId`.

## ✅ Correction Appliquée

### 1. Initialisation Unique à l'Ouverture

**Fichier:** `siirh-frontend/src/components/OrganizationalFilterModalOptimized.tsx`

**Ligne 145-156:**
```typescript
// Initialiser l'employeur sélectionné UNIQUEMENT à l'ouverture
useEffect(() => {
  if (isOpen && employers.length > 0) {
    // N'initialiser que si selectedEmployerId n'est pas déjà défini ou est invalide
    if (!selectedEmployerId || selectedEmployerId === 0) {
      if (defaultEmployerId && defaultEmployerId > 0) {
        setSelectedEmployerId(defaultEmployerId);
      } else {
        setSelectedEmployerId(employers[0].id);
      }
    }
  }
}, [isOpen, employers]); // ✅ Retirer defaultEmployerId et selectedEmployerId des dépendances
```

**Changements:**
- ✅ Condition ajoutée: `if (!selectedEmployerId || selectedEmployerId === 0)`
- ✅ Dépendances réduites: Retirer `defaultEmployerId` et `selectedEmployerId`
- ✅ Résultat: L'employeur n'est initialisé qu'une seule fois à l'ouverture

### 2. Réinitialisation à la Fermeture

**Ligne 159-178:**
```typescript
// Réinitialiser les filtres à l'ouverture/fermeture
useEffect(() => {
  if (isOpen) {
    console.log(`[MODAL DEBUG] Modal opened with employer ${selectedEmployerId}`);
    setSelectedEtablissement(null);
    setSelectedDepartement(null);
    setSelectedService(null);
    setSelectedUnite(null);
    setUseFilters(false);
  } else {
    console.log(`[MODAL DEBUG] Modal closed, clearing cache`);
    queryClient.removeQueries({ 
      queryKey: ['cascading-options'],
      exact: false 
    });
    // ✅ Réinitialiser l'employeur sélectionné pour la prochaine ouverture
    if (defaultEmployerId && defaultEmployerId > 0) {
      setSelectedEmployerId(defaultEmployerId);
    } else if (employers.length > 0) {
      setSelectedEmployerId(employers[0].id);
    }
  }
}, [isOpen, queryClient, defaultEmployerId, employers]);
```

**Changements:**
- ✅ Réinitialisation de l'employeur **à la fermeture** du modal
- ✅ Garantit que la prochaine ouverture utilisera le bon employeur par défaut

## 🎯 Comportement Attendu

### Avant la Correction ❌
1. Ouvrir le modal → Employeur = Karibo Services
2. Changer pour Mandroso Services dans le dropdown
3. **Problème:** Le dropdown revient immédiatement à Karibo Services
4. Impossible de sélectionner un autre employeur

### Après la Correction ✅
1. Ouvrir le modal → Employeur = Karibo Services (par défaut)
2. Changer pour Mandroso Services dans le dropdown
3. **Succès:** Le dropdown reste sur Mandroso Services
4. Possibilité de changer d'employeur librement
5. À la fermeture et réouverture, retour à l'employeur par défaut

## 🧪 Test de Validation

### Procédure de Test

1. **Ouvrir la page Bulletin**
   ```
   http://localhost:5173/payroll
   ```

2. **Sélectionner un salarié de Karibo Services**
   - Par exemple: RAFALIMANANA HENINTSOA

3. **Cliquer sur "Imprimer tous les bulletins"**
   - Le modal s'ouvre avec Karibo Services sélectionné

4. **Changer d'employeur dans le dropdown**
   - Sélectionner "Mandroso Services"
   - ✅ Vérifier que la sélection reste sur Mandroso Services
   - ✅ Vérifier que les structures organisationnelles changent

5. **Cocher "Filtrage par structure organisationnelle"**
   - ✅ Vérifier que les établissements de Mandroso s'affichent
   - ✅ Vérifier qu'il n'y a pas d'établissements de Karibo

6. **Fermer et rouvrir le modal**
   - ✅ Vérifier que l'employeur par défaut est restauré (Karibo)

### Résultats Attendus

```
✅ Le dropdown d'employeur est fonctionnel
✅ Possibilité de changer d'employeur librement
✅ Les structures organisationnelles changent selon l'employeur
✅ Pas de réinitialisation intempestive
✅ Retour à l'employeur par défaut à la réouverture
```

## 📊 Impact de la Correction

### Avant
- ❌ Dropdown d'employeur non fonctionnel
- ❌ Impossible d'imprimer les bulletins d'un autre employeur
- ❌ Limitation artificielle de la fonctionnalité

### Après
- ✅ Dropdown d'employeur pleinement fonctionnel
- ✅ Possibilité d'imprimer les bulletins de n'importe quel employeur
- ✅ Flexibilité maximale pour l'utilisateur
- ✅ Comportement intuitif et prévisible

## 💡 Cas d'Usage

### Scénario 1: Impression Multi-Employeurs
```
Contexte: L'utilisateur gère plusieurs employeurs
Action: Imprimer les bulletins de tous les employeurs
Avant: Devait changer de salarié pour chaque employeur
Après: Peut changer d'employeur directement dans le modal
```

### Scénario 2: Salarié Transféré
```
Contexte: Un salarié a été transféré d'un employeur à un autre
Action: Imprimer les bulletins de l'ancien employeur
Avant: Impossible si le salarié sélectionné est du nouvel employeur
Après: Peut changer d'employeur dans le modal
```

### Scénario 3: Vérification Croisée
```
Contexte: Comparer les bulletins de deux employeurs
Action: Imprimer et comparer
Avant: Devait fermer et rouvrir le modal pour chaque employeur
Après: Peut changer d'employeur sans fermer le modal
```

## 📁 Fichiers Modifiés

1. `siirh-frontend/src/components/OrganizationalFilterModalOptimized.tsx`
   - Ligne 145-156: Initialisation unique à l'ouverture
   - Ligne 159-178: Réinitialisation à la fermeture

## 🔗 Corrections Liées

Cette correction complète les corrections précédentes:
1. `CORRECTION_EMPLOYER_ID_ZERO.md` - Gestion de l'employer ID invalide
2. `CORRECTION_FILTRAGE_CHANGEMENT_EMPLOYEUR.md` - Filtrage après changement d'employeur
3. `CORRECTION_ISOLATION_FILTRES_EMPLOYEURS.md` - Isolation des filtres entre employeurs

## ✅ Résultat Final

Le modal d'impression des bulletins permet maintenant de:
- ✅ Sélectionner n'importe quel employeur
- ✅ Changer d'employeur librement pendant l'utilisation
- ✅ Filtrer par structures organisationnelles de l'employeur sélectionné
- ✅ Garantir l'isolation des données entre employeurs

---

**Date:** 16 janvier 2026  
**Priorité:** HAUTE  
**Statut:** CORRIGÉ ✅  
**Action:** Tester dans le navigateur pour validation
