# Guide Visuel - Comment Supprimer une Structure Organisationnelle

## 🎯 Étapes Visuelles Détaillées

### Étape 1 : Navigation vers la Gestion Hiérarchique

```
[Menu Principal]
    ↓
[Organisation] ← Cliquez ici
    ↓
[Onglets en haut de page]
    ↓
[Gestion Hiérarchique avec Suppression] ← Cliquez sur cet onglet
```

### Étape 2 : Interface de Gestion

Vous verrez cette interface :

```
┌─────────────────────────────────────────────────────────────┐
│ Gestion des Structures Organisationnelles                  │
│                                                             │
│ [➕ Créer] [✏️ Modifier] [🗑️ Supprimer] ← Boutons d'action │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 🌳 Hiérarchie Organisationnelle                           │
│                                                             │
│ 🏢 Établissement A                    👥 5  ⚠ Occupée     │ ← Cliquez pour sélectionner
│   └── 🏬 Département B               👥 2  ⚠ Occupée     │
│       ├── 👥 Service C               👥 0  ✓ Supprimable │ ← Structure vide
│       └── 👥 Service D               👥 3  ⚠ Occupée     │
│                                                             │
│ 🏢 Établissement E                    👥 0  ✓ Supprimable │ ← Structure vide
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Étape 3 : Sélection d'une Structure

**Avant sélection :**
```
🏢 Établissement E                    👥 0  ✓ Supprimable
```

**Après clic (sélectionnée) :**
```
🏢 Établissement E                    👥 0  ✓ Supprimable  [Unité sélectionnée]
   ↑ Surlignée en bleu
```

### Étape 4 : Déclenchement de la Suppression

**Boutons d'action (en haut) :**
```
[➕ Créer une structure] [✏️ Modifier] [🗑️ Supprimer] ← Cliquez ici
                                        ↑
                                   Actif seulement si 
                                   une structure est 
                                   sélectionnée
```

### Étape 5 : Modal de Suppression

#### Cas A : Structure Vide (Suppression Simple)

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Supprimer la structure organisationnelle            │
│                                                         │
│ Établissement E (Établissement)                        │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✅ Suppression possible                             │ │
│ │ Cette structure organisationnelle ne contient       │ │
│ │ aucun salarié ni sous-structure et peut être       │ │
│ │ supprimée en toute sécurité.                       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│                           [Annuler] [🗑️ Supprimer] ← Cliquez │
└─────────────────────────────────────────────────────────┘
```

#### Cas B : Structure Occupée (Suppression Bloquée)

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Supprimer la structure organisationnelle            │
│                                                         │
│ Département B (Département)                            │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ❌ Suppression impossible                           │ │
│ │ Contient: 2 sous-structures, 3 salariés           │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Sous-structures (2) :                                  │
│ • Service C (service)                                  │
│ • Service D (service)                                  │
│                                                         │
│ Salariés directement assignés (3) :                   │
│ • Jean Dupont (EMP001)                                 │
│ • Marie Martin (EMP002)                                │
│ • Paul Durand (EMP003)                                 │
│                                                         │
│ ⚠️ Suppression forcée                                  │
│ Vous pouvez forcer la suppression...                  │
│                                                         │
│     [Annuler] [⚠️ Voir les options de suppression forcée] │
│                                    ↑                    │
│                              Cliquez ici pour          │
│                              les options avancées      │
└─────────────────────────────────────────────────────────┘
```

#### Cas C : Options de Suppression Forcée

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Attention !                                          │
│                                                         │
│ La suppression forcée va :                             │
│ • Réassigner les 2 sous-structures au niveau parent   │
│ • Désassigner les 3 salariés directement assignés     │
│ • Les 5 salariés des sous-structures ne seront pas    │
│   affectés                                             │
│                                                         │
│ Cette action est irréversible.                        │
│                                                         │
│        [Annuler] [Retour] [🗑️ Forcer la suppression] │
│                                        ↑               │
│                                  Confirmation finale   │
└─────────────────────────────────────────────────────────┘
```

## 🎮 Actions Possibles

### Dans l'Arbre Hiérarchique

| Action | Résultat |
|--------|----------|
| **Clic sur une structure** | Sélection (surlignage bleu) |
| **Clic sur ▶** | Expansion/Réduction des enfants |
| **Survol** | Affichage des tooltips |

### Dans la Barre d'Actions

| Bouton | État | Action |
|--------|------|--------|
| **➕ Créer** | Toujours actif | Ouvre le modal de création |
| **✏️ Modifier** | Actif si sélection | Ouvre le modal d'édition |
| **🗑️ Supprimer** | Actif si sélection | Ouvre le modal de suppression |

### Dans le Modal de Suppression

| Bouton | Action |
|--------|--------|
| **Annuler** | Ferme le modal sans action |
| **🗑️ Supprimer** | Suppression directe (si possible) |
| **⚠️ Voir options** | Affiche les options de suppression forcée |
| **Retour** | Retour à l'écran précédent |
| **🗑️ Forcer** | Suppression forcée avec réassignation |

## 🚦 Codes Couleur

### Indicateurs de Structure

- **🟢 ✓ Supprimable** : Structure vide, suppression sûre
- **🟠 ⚠ Occupée** : Contient des éléments, attention requise

### États des Boutons

- **🔵 Bleu** : Bouton principal (Créer)
- **🟡 Jaune** : Bouton d'avertissement (Options forcées)
- **🔴 Rouge** : Bouton de suppression (Supprimer/Forcer)
- **⚪ Gris** : Bouton neutre (Annuler/Retour)

### Sélection

- **🔵 Surlignage bleu** : Structure sélectionnée
- **🏷️ Badge bleu** : "Unité sélectionnée"

## 💡 Conseils Pratiques

### Pour Débuter
1. **Commencez par les structures vertes** (✓ Supprimable)
2. **Lisez attentivement les modals** avant de confirmer
3. **Testez d'abord sur des structures de test**

### Pour les Suppressions Complexes
1. **Vérifiez l'impact** sur les salariés et sous-structures
2. **Considérez la réassignation manuelle** avant suppression forcée
3. **Documentez vos actions** pour traçabilité

### En Cas de Doute
1. **Cliquez sur "Annuler"** pour sortir sans risque
2. **Consultez les détails** dans le modal avant de décider
3. **Demandez conseil** si l'impact est important

---

**Rappel Important :** Toutes les suppressions sont définitives. Le système vous protège avec des vérifications et confirmations, mais la décision finale vous appartient !