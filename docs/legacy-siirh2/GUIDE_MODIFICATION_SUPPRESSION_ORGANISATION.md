# Guide - Modification et Suppression des Unités Organisationnelles

## ✅ Nouvelles fonctionnalités ajoutées

Vous pouvez maintenant **modifier** et **supprimer** les unités organisationnelles directement depuis l'interface !

## 🎯 Boutons disponibles pour chaque unité

Chaque unité dans l'arbre organisationnel dispose maintenant de **4 boutons d'action** :

### 1. ➕ **Ajouter une sous-unité** (Vert)
- **Fonction** : Créer une unité enfant sous cette unité
- **Utilisation** : Cliquer sur le bouton "+" vert
- **Exemple** : Ajouter un département sous un établissement

### 2. ✏️ **Modifier cette unité** (Bleu)
- **Fonction** : Modifier le nom, code et description de l'unité
- **Utilisation** : Cliquer sur l'icône crayon bleue
- **Ce qui peut être modifié** :
  - Nom de l'unité
  - Code de l'unité
  - Description (optionnelle)
- **Ce qui ne peut PAS être modifié** :
  - Type d'unité (établissement, département, etc.)
  - Position dans la hiérarchie

### 3. 🗑️ **Supprimer cette unité** (Rouge)
- **Fonction** : Supprimer définitivement l'unité
- **Utilisation** : Cliquer sur l'icône poubelle rouge
- **⚠️ Conditions de suppression** :
  - L'unité ne doit contenir **aucun salarié**
  - L'unité ne doit avoir **aucune sous-unité**
  - **Confirmation obligatoire** avant suppression

### 4. 👥 **Assigner des salariés** (Vert émeraude)
- **Fonction** : Gérer l'assignation des salariés à cette unité
- **Utilisation** : Cliquer sur l'icône utilisateurs verte
- **Note** : Fonctionnalité en cours de développement

## 📝 Comment modifier une unité

1. **Localiser l'unité** dans l'arbre organisationnel
2. **Cliquer sur l'icône crayon bleue** ✏️
3. **Modifier les informations** dans le formulaire :
   - Nom : Nouveau nom de l'unité
   - Code : Nouveau code (automatiquement en majuscules)
   - Description : Nouvelle description (optionnelle)
4. **Cliquer sur "Modifier"** pour sauvegarder
5. **Confirmation** : Message de succès affiché

## 🗑️ Comment supprimer une unité

1. **Vérifier les prérequis** :
   - ✅ Aucun salarié assigné à cette unité
   - ✅ Aucune sous-unité sous cette unité
2. **Cliquer sur l'icône poubelle rouge** 🗑️
3. **Confirmer la suppression** dans la boîte de dialogue
4. **Suppression définitive** : L'unité disparaît de l'arbre

## ⚠️ Règles de sécurité

### Modification
- ✅ **Toujours possible** tant que l'unité existe
- ✅ **Pas d'impact** sur les salariés ou sous-unités
- ✅ **Modification immédiate** dans l'interface

### Suppression
- ❌ **Impossible** si l'unité contient des salariés
- ❌ **Impossible** si l'unité a des sous-unités
- ⚠️ **Action irréversible** - aucun moyen d'annuler
- 🔒 **Confirmation obligatoire** pour éviter les erreurs

## 💡 Conseils d'utilisation

### Avant de supprimer une unité :
1. **Réassigner les salariés** vers d'autres unités
2. **Supprimer ou déplacer** toutes les sous-unités
3. **Vérifier l'impact** sur la structure organisationnelle

### Pour réorganiser :
1. **Créer la nouvelle structure** avant de supprimer l'ancienne
2. **Migrer progressivement** les salariés
3. **Supprimer les anciennes unités** une fois vides

### Messages d'erreur courants :
- **"Cannot delete unit with X assigned workers"** → Réassigner les salariés d'abord
- **"Cannot delete unit with X child units"** → Supprimer les sous-unités d'abord

## 🎉 Avantages

- **Flexibilité totale** : Adapter la structure selon l'évolution de l'entreprise
- **Sécurité** : Protections contre les suppressions accidentelles
- **Simplicité** : Interface intuitive avec icônes claires
- **Temps réel** : Modifications visibles immédiatement

Vous avez maintenant un contrôle complet sur votre structure organisationnelle ! 🚀