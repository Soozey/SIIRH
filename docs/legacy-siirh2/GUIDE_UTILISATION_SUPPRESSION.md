# Guide d'Utilisation - Suppression des Structures Organisationnelles

## 🎯 Comment Supprimer une Structure Organisationnelle

### Étape 1 : Accéder à la Gestion Hiérarchique

1. **Naviguez vers Organisation**
   ```
   Menu Principal → Organisation
   ```

2. **Sélectionnez l'onglet approprié**
   ```
   Onglets → "Gestion Hiérarchique avec Suppression"
   ```

### Étape 2 : Sélectionner la Structure à Supprimer

1. **Parcourez l'arbre hiérarchique**
   - Vous verrez toutes vos structures organisationnelles
   - Chaque structure a un indicateur coloré :
     - **✓ Supprimable** (vert) = Structure vide
     - **⚠ Occupée** (orange) = Contient des éléments

2. **Cliquez sur la structure à supprimer**
   - La structure sera surlignée en bleu
   - Un badge "Unité sélectionnée" apparaîtra

### Étape 3 : Déclencher la Suppression

1. **Cliquez sur le bouton "🗑️ Supprimer"**
   - Situé dans la barre d'actions en haut
   - Le bouton n'est actif que si une structure est sélectionnée

2. **Le modal de suppression s'ouvre automatiquement**

## 🔄 Processus de Suppression Intelligent

### Cas 1 : Structure Vide (✓ Supprimable)

**Affichage :**
```
✅ Suppression possible
Cette structure organisationnelle ne contient aucun salarié 
ni sous-structure et peut être supprimée en toute sécurité.

[Annuler] [🗑️ Supprimer]
```

**Action :** Cliquez sur "🗑️ Supprimer" → Suppression immédiate

### Cas 2 : Structure Occupée (⚠ Occupée)

**Affichage :**
```
❌ Suppression impossible
Contient: 2 sous-structures, 3 salariés directement assignés

Détails :
• Sous-structures (2) :
  - Service Paie (service)
  - Service Formation (service)

• Salariés directement assignés (3) :
  - Jean Dupont (EMP001)
  - Marie Martin (EMP002)
  - Paul Durand (EMP003)

⚠️ Suppression forcée
Vous pouvez forcer la suppression. Cela réassignera 
automatiquement les sous-structures au niveau parent 
et désassignera tous les salariés.

[Annuler] [⚠️ Voir les options de suppression forcée]
```

**Options :**
1. **Annuler** → Retour sans suppression
2. **Voir les options de suppression forcée** → Affiche les options avancées

### Cas 3 : Suppression Forcée

**Affichage après avoir cliqué sur "Voir les options" :**
```
⚠️ Attention !
La suppression forcée va :
• Réassigner les 2 sous-structures au niveau parent
• Désassigner les 3 salariés directement assignés
• Les 5 salariés des sous-structures ne seront pas affectés

Cette action est irréversible.

[Annuler] [Retour] [🗑️ Forcer la suppression]
```

## 📊 Exemples Pratiques

### Exemple 1 : Supprimer un Service Vide

1. **Situation :** Service "Test" sans salariés ni sous-services
2. **Indicateur :** ✓ Supprimable (vert)
3. **Action :** 
   - Cliquer sur "Service Test"
   - Cliquer sur "🗑️ Supprimer"
   - Confirmer dans le modal
4. **Résultat :** Service supprimé immédiatement

### Exemple 2 : Supprimer un Département avec Sous-structures

1. **Situation :** Département "RH" avec 2 services mais sans salariés directs
2. **Indicateur :** ⚠ Occupée (orange)
3. **Action :**
   - Cliquer sur "Département RH"
   - Cliquer sur "🗑️ Supprimer"
   - Voir que la suppression est bloquée
   - Choisir "Suppression forcée"
   - Confirmer l'action
4. **Résultat :** Département supprimé, services remontent à l'établissement

### Exemple 3 : Supprimer un Établissement avec Salariés

1. **Situation :** Établissement "Siège" avec salariés et départements
2. **Indicateur :** ⚠ Occupée (orange)
3. **Action :**
   - Cliquer sur "Établissement Siège"
   - Cliquer sur "🗑️ Supprimer"
   - Voir les détails des contraintes
   - Évaluer l'impact de la suppression forcée
   - Décider si procéder ou annuler

## 🛡️ Sécurités Intégrées

### Protections Automatiques

1. **Validation des contraintes** - Vérification automatique avant suppression
2. **Informations détaillées** - Liste complète des éléments affectés
3. **Confirmations multiples** - Plusieurs étapes pour éviter les erreurs
4. **Réassignation intelligente** - Préservation de la hiérarchie

### Messages d'Avertissement

- **Structure avec salariés :** "Contient X salariés directement assignés"
- **Structure avec sous-structures :** "Contient X sous-structures"
- **Impact sur descendants :** "X salariés dans les sous-structures ne seront pas affectés"

## 🔧 Conseils d'Utilisation

### Bonnes Pratiques

1. **Commencez par les feuilles** - Supprimez d'abord les unités les plus petites
2. **Vérifiez les impacts** - Lisez attentivement les détails avant de forcer
3. **Réassignez manuellement** - Si possible, réassignez les salariés avant suppression
4. **Testez sur un environnement de développement** - Pour les suppressions importantes

### Quand Utiliser la Suppression Forcée

✅ **Recommandé :**
- Réorganisation de la structure
- Fusion de départements/services
- Nettoyage de structures obsolètes

⚠️ **Attention :**
- Structures avec beaucoup de salariés
- Éléments critiques de l'organisation
- Suppressions en cascade importantes

## 🆘 Dépannage

### Problèmes Courants

**Q : Le bouton "Supprimer" est grisé**
R : Vous devez d'abord sélectionner une structure dans l'arbre

**Q : "Erreur lors de la suppression"**
R : Vérifiez que la structure existe encore et réessayez

**Q : "Impossible de vérifier les contraintes"**
R : Problème de connexion, vérifiez le backend

### Support

Si vous rencontrez des problèmes :
1. Vérifiez que la structure est bien sélectionnée
2. Actualisez la page (F5)
3. Vérifiez la console F12 pour d'éventuelles erreurs
4. Contactez le support technique si le problème persiste

## 📋 Résumé des Actions

| Action | Bouton | Résultat |
|--------|--------|----------|
| Sélectionner | Clic sur structure | Surlignage bleu |
| Supprimer simple | 🗑️ Supprimer | Modal de confirmation |
| Supprimer forcé | ⚠️ Options forcées | Modal d'avertissement |
| Annuler | Annuler | Retour sans action |

**Rappel :** Toutes les suppressions sont définitives. Assurez-vous de vos choix avant de confirmer !