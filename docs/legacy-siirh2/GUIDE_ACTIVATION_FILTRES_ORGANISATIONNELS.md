# 🚀 Guide d'Activation des Filtres Organisationnels

## ✅ État Actuel

Le diagnostic confirme que **tous les fichiers sont correctement configurés** :
- ✅ Composant `OrganizationalFilter.tsx` créé
- ✅ Import dans `PayrollRun.tsx` présent
- ✅ État `orgFilters` défini
- ✅ Composant utilisé dans le JSX
- ✅ Fonctions modifiées pour utiliser les filtres

## 🔧 Étapes pour Activer les Filtres

### 1. 🔄 Redémarrer le Serveur de Développement

Le serveur frontend doit être redémarré pour prendre en compte les nouveaux fichiers :

```bash
# Dans le terminal du serveur frontend
# Appuyez sur Ctrl+C pour arrêter le serveur

# Puis relancez :
cd siirh-frontend
npm run dev
# ou
yarn dev
```

**Attendez** que la compilation soit terminée (message "ready" ou "compiled successfully").

### 2. 🌐 Vider le Cache du Navigateur

1. **Ouvrez** http://localhost:5173/payroll-run
2. **Appuyez** sur F12 pour ouvrir les outils de développement
3. **Clic droit** sur le bouton de rechargement du navigateur
4. **Sélectionnez** "Vider le cache et recharger" ou "Empty Cache and Hard Reload"

### 3. 🎯 Localiser les Filtres Organisationnels

Les filtres apparaissent dans le **panneau de paramètres** (colonne de gauche) :

1. **Allez** sur http://localhost:5173/payroll-run
2. **Sélectionnez** un salarié dans le dropdown
3. **Regardez** dans le panneau de gauche, **après** la sélection de période
4. **Cherchez** la section "🏢 Filtres Organisationnels"

### 4. 📍 Emplacement Exact

```
┌─────────────────────────────────────┐
│ 📋 Paramètres                       │
├─────────────────────────────────────┤
│ Salarié: [Dropdown]                 │
│ Période: [2026-01]                  │
│ ─────────────────────────────────── │  ← Ligne de séparation
│ 🏢 Filtres Organisationnels         │  ← ICI !
│    Établissement: [Tous ▼]          │
│    Département:   [Tous ▼]          │
│    Service:       [Tous ▼]          │
│    Unité:         [Tous ▼]          │
│ ─────────────────────────────────── │
│ [📅 Calendrier de Travail]          │
│ [👁️ Prévisualiser ce bulletin]      │
│ [🖨️ Imprimer TOUS les bulletins]    │
└─────────────────────────────────────┘
```

## 🔍 Vérifications de Dépannage

### Si les Filtres ne Sont Toujours Pas Visibles

1. **Vérifiez la Console** (F12 → Console) :
   - Cherchez les erreurs en rouge
   - Notez les erreurs d'import ou de compilation

2. **Vérifiez l'Onglet Network** (F12 → Network) :
   - Rechargez la page
   - Vérifiez que `OrganizationalFilter.tsx` est chargé
   - Cherchez les erreurs 404 ou 500

3. **Vérifiez que le Salarié est Sélectionné** :
   - Les filtres n'apparaissent **que si** un salarié est sélectionné
   - Ils utilisent l'`employer_id` du salarié pour charger les données

### Messages d'Erreur Courants

- **"Cannot resolve module"** → Redémarrer le serveur
- **"Unexpected token"** → Erreur de syntaxe, vérifier le code
- **"Failed to fetch"** → Problème de connexion backend

## 🧪 Test des Fonctionnalités

Une fois les filtres visibles :

### 1. Test des Dropdowns
- **Cliquez** sur chaque dropdown
- **Vérifiez** que les données se chargent
- **Sélectionnez** différentes valeurs

### 2. Test des Boutons Adaptatifs
- **Sans filtres** : "Imprimer TOUS les bulletins"
- **Avec filtres** : "Imprimer bulletins (filtrés)"
- **Observez** les changements de libellés

### 3. Test de l'Aperçu Filtré
- **Sélectionnez** un établissement ou département
- **Cliquez** sur "Aperçu État (filtré)"
- **Vérifiez** que seuls les salariés filtrés apparaissent

### 4. Test de l'Export Filtré
- **Appliquez** des filtres
- **Cliquez** sur "Exporter État (filtré)"
- **Vérifiez** le nom du fichier téléchargé

## 📊 Worker de Test Disponible

Un worker de test avec données organisationnelles est disponible :
- **Nom** : "Test ORGANISATIONNEL"
- **ID** : 2046
- **Matricule** : ORG_TEST_1767524134
- **Données** :
  - Établissement : "Établissement Test API"
  - Département : "Département Test API"
  - Service : "Service Test API"
  - Unité : "Unité Test API"

## 🆘 Si le Problème Persiste

1. **Vérifiez** que le backend est démarré (http://localhost:8000)
2. **Testez** l'endpoint : http://localhost:8000/employers/2/organizational-data
3. **Redémarrez** complètement les deux serveurs (backend + frontend)
4. **Vérifiez** les logs du serveur frontend pour les erreurs

## ✅ Confirmation de Réussite

Vous saurez que les filtres fonctionnent quand :
- ✅ La section "🏢 Filtres Organisationnels" est visible
- ✅ Les dropdowns se remplissent avec des données
- ✅ Les boutons changent de libellé selon les filtres
- ✅ L'aperçu et l'export respectent les filtres appliqués

**Les filtres organisationnels sont prêts à fonctionner !** 🎯