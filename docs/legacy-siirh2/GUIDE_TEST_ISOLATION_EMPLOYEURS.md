# 🧪 Guide de Test - Isolation des Filtres entre Employeurs

## 🎯 Objectif

Valider que les filtres de structures organisationnelles sont correctement isolés entre employeurs et qu'aucune fuite de données n'est possible.

## ⚠️ Importance

Ce test est **CRITIQUE** car il valide la sécurité et l'étanchéité des données entre employeurs.

## 🧪 Scénario de Test Principal

### Préparation

1. **Démarrer le backend**
   ```bash
   cd siirh-backend
   python start_server.py
   ```

2. **Démarrer le frontend**
   ```bash
   cd siirh-frontend
   npm run dev
   ```

3. **Ouvrir le navigateur**
   - URL: `http://localhost:5173/payroll`
   - Ouvrir F12 (Console + Network)

### Test 1: Changement d'Employeur Simple

**Étapes:**

1. Cliquer sur "Imprimer tous les bulletins"
2. Le modal s'ouvre
3. Vérifier l'employeur sélectionné par défaut
4. Cocher "Filtrage par structure organisationnelle"
5. Observer les établissements disponibles
6. **Noter mentalement** les noms des établissements
7. Changer d'employeur dans la liste déroulante
8. **VÉRIFICATION CRITIQUE:** Les établissements précédents doivent disparaître immédiatement

**Résultat attendu:**
- ✅ Les établissements changent instantanément
- ✅ Aucun établissement de l'employeur précédent n'est visible
- ✅ La liste est vide OU contient uniquement les établissements du nouvel employeur

**Résultat INCORRECT (bug):**
- ❌ Les établissements de l'employeur précédent restent visibles
- ❌ Mélange d'établissements de différents employeurs
- ❌ Erreur dans la console

### Test 2: Changement d'Employeur avec Sélection Active

**Étapes:**

1. Cliquer sur "Imprimer tous les bulletins"
2. Sélectionner "Karibo Services"
3. Cocher "Filtrage par structure"
4. Sélectionner un établissement (ex: "JICA")
5. Sélectionner un département (si disponible)
6. **Noter** le chemin hiérarchique affiché
7. Changer pour "Mandroso Services"
8. **VÉRIFICATION CRITIQUE:** 
   - Le chemin hiérarchique doit disparaître
   - Les sélections doivent être réinitialisées
   - Les listes déroulantes doivent être vides ou contenir les structures de Mandroso

**Résultat attendu:**
- ✅ Chemin hiérarchique vide
- ✅ Toutes les sélections réinitialisées
- ✅ Listes déroulantes mises à jour
- ✅ Aucune trace de l'employeur précédent

**Résultat INCORRECT (bug):**
- ❌ Le chemin hiérarchique affiche encore les structures de Karibo
- ❌ Les sélections restent actives
- ❌ Possibilité de sélectionner des structures de Karibo pour Mandroso

### Test 3: Fermeture et Réouverture du Modal

**Étapes:**

1. Cliquer sur "Imprimer tous les bulletins"
2. Sélectionner "Karibo Services"
3. Cocher "Filtrage par structure"
4. Sélectionner quelques structures
5. **Fermer le modal** (bouton X ou Annuler)
6. **Réouvrir le modal** immédiatement
7. Changer pour "Mandroso Services"
8. Cocher "Filtrage par structure"
9. **VÉRIFICATION CRITIQUE:** Aucune structure de Karibo ne doit apparaître

**Résultat attendu:**
- ✅ Modal s'ouvre avec état propre
- ✅ Aucune sélection précédente
- ✅ Structures de Mandroso uniquement (ou liste vide)

**Résultat INCORRECT (bug):**
- ❌ Structures de Karibo visibles pour Mandroso
- ❌ Sélections précédentes encore actives

### Test 4: Vérification dans le Network Tab

**Étapes:**

1. Ouvrir F12 → Onglet Network
2. Filtrer par "cascading-options"
3. Cliquer sur "Imprimer tous les bulletins"
4. Sélectionner "Karibo Services" (ID: 1)
5. Cocher "Filtrage par structure"
6. **Observer:** Requête vers `/employers/1/hierarchical-organization/cascading-options`
7. Changer pour "Mandroso Services" (ID: 2)
8. **Observer:** Requête vers `/employers/2/hierarchical-organization/cascading-options`
9. **VÉRIFICATION CRITIQUE:** 
   - Nouvelle requête effectuée (pas de cache)
   - URL contient le bon employer_id
   - Réponse contient uniquement les structures de Mandroso

**Résultat attendu:**
- ✅ Nouvelle requête HTTP pour chaque employeur
- ✅ Pas de réutilisation du cache
- ✅ URL correcte avec le bon employer_id
- ✅ Réponse correcte du backend

**Résultat INCORRECT (bug):**
- ❌ Pas de nouvelle requête (cache réutilisé)
- ❌ Requête vers le mauvais employer_id
- ❌ Réponse contenant des structures d'un autre employeur

## 🔍 Tests Avancés

### Test 5: Changements Rapides d'Employeur

**Objectif:** Vérifier que les changements rapides ne causent pas de race conditions

**Étapes:**

1. Ouvrir le modal
2. Cocher "Filtrage par structure"
3. Changer rapidement d'employeur plusieurs fois:
   - Karibo → Mandroso → Karibo → Mandroso
4. **VÉRIFICATION:** Les structures affichées correspondent toujours à l'employeur sélectionné

**Résultat attendu:**
- ✅ Pas de mélange de données
- ✅ Pas d'erreur dans la console
- ✅ Affichage cohérent

### Test 6: Test avec les 3 Modaux

**Objectif:** Vérifier que l'isolation fonctionne pour tous les modaux

**Modaux à tester:**
1. "Imprimer tous les bulletins"
2. "Aperçu de l'État de Paie"
3. "Exporter l'État de paie"

**Pour chaque modal:**
1. Ouvrir le modal
2. Tester le changement d'employeur
3. Vérifier l'isolation des données

**Résultat attendu:**
- ✅ Les 3 modaux ont le même comportement correct
- ✅ Isolation garantie pour tous

## 📊 Checklist de Validation

### Fonctionnalités de Base
- [ ] Modal s'ouvre correctement
- [ ] Liste des employeurs chargée
- [ ] Changement d'employeur fonctionne
- [ ] Filtrage en cascade fonctionne

### Isolation des Données
- [ ] Changement d'employeur réinitialise les structures
- [ ] Aucune structure de l'employeur précédent visible
- [ ] Chemin hiérarchique réinitialisé
- [ ] Sélections réinitialisées

### Cache et Performance
- [ ] Nouvelle requête HTTP pour chaque employeur
- [ ] Pas de réutilisation du cache entre employeurs
- [ ] URL correcte dans les requêtes
- [ ] Réponses correctes du backend

### Sécurité
- [ ] Impossible de sélectionner des structures d'un autre employeur
- [ ] Impossible de voir des données d'un autre employeur
- [ ] Aucune fuite de données dans la console
- [ ] Aucune erreur de sécurité

## 🐛 Problèmes Connus (Avant Correction)

### Symptôme 1: Structures Persistantes
```
1. Sélectionner Karibo → Voir "JICA", "NUMHERIT"
2. Changer pour Mandroso → Voir encore "JICA", "NUMHERIT" ❌
```

**Cause:** Cache React Query non invalidé

### Symptôme 2: Fuite de Données
```
1. Sélectionner Karibo → Sélectionner "JICA"
2. Changer pour Mandroso → "JICA" encore sélectionné ❌
3. Confirmer → Bulletins de Karibo affichés pour Mandroso ❌❌
```

**Cause:** Sélections non réinitialisées + cache persistant

## ✅ Comportement Correct (Après Correction)

### Scénario 1: Changement Simple
```
1. Sélectionner Karibo → Voir "JICA", "NUMHERIT"
2. Changer pour Mandroso → Liste vide ✅
   (Mandroso n'a pas de structures)
```

### Scénario 2: Avec Sélection
```
1. Sélectionner Karibo → Sélectionner "JICA"
2. Changer pour Mandroso → Sélection réinitialisée ✅
3. Liste vide ou structures de Mandroso uniquement ✅
```

## 🔧 En Cas de Problème

### Si les Structures Persistent

1. **Vérifier la console:**
   - Ouvrir F12 → Console
   - Chercher des erreurs React Query
   - Vérifier les warnings

2. **Vérifier le Network:**
   - Onglet Network
   - Filtrer "cascading-options"
   - Vérifier que de nouvelles requêtes sont faites

3. **Vider le cache:**
   - Ctrl+Shift+R (hard refresh)
   - Ou vider le cache du navigateur

4. **Redémarrer le frontend:**
   ```bash
   # Arrêter avec Ctrl+C
   cd siirh-frontend
   npm run dev
   ```

### Si les Données Sont Mélangées

1. **Vérifier le backend:**
   ```bash
   python test_employer_filter_isolation.py
   ```

2. **Vérifier les logs backend:**
   - Regarder les logs du serveur
   - Vérifier les requêtes SQL

3. **Vérifier la base de données:**
   - Vérifier que les structures ont bien un employer_id
   - Vérifier qu'il n'y a pas de données corrompues

## 📝 Rapport de Test

### Template de Rapport

```
Date: _______________
Testeur: _______________

Test 1: Changement d'Employeur Simple
[ ] PASS  [ ] FAIL
Notes: _________________________________

Test 2: Changement avec Sélection Active
[ ] PASS  [ ] FAIL
Notes: _________________________________

Test 3: Fermeture et Réouverture
[ ] PASS  [ ] FAIL
Notes: _________________________________

Test 4: Vérification Network
[ ] PASS  [ ] FAIL
Notes: _________________________________

Test 5: Changements Rapides
[ ] PASS  [ ] FAIL
Notes: _________________________________

Test 6: Les 3 Modaux
[ ] PASS  [ ] FAIL
Notes: _________________________________

Résultat Global:
[ ] TOUS LES TESTS PASSENT
[ ] CERTAINS TESTS ÉCHOUENT

Problèmes identifiés:
_________________________________
_________________________________
```

## 🎉 Validation Finale

**Critères de succès:**
- ✅ Tous les tests passent
- ✅ Aucune fuite de données détectée
- ✅ Aucune erreur dans la console
- ✅ Comportement cohérent pour les 3 modaux

**Si tous les critères sont remplis:**
```
✅ ISOLATION DES FILTRES VALIDÉE
🔒 SÉCURITÉ DES DONNÉES GARANTIE
✅ PRÊT POUR PRODUCTION
```

---

**Date:** 16 janvier 2026  
**Priorité:** CRITIQUE - Sécurité  
**Temps estimé:** 15 minutes
