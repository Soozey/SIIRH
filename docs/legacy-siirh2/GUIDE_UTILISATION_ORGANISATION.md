# Guide d'Utilisation - Système Organisationnel

## 🏢 Vue d'ensemble

Le système organisationnel permet de structurer votre entreprise selon une hiérarchie claire et de gérer l'assignation des salariés aux différentes unités.

## 📋 Sélection de l'employeur

**Problème résolu** : La liste des employeurs affiche maintenant correctement vos employeurs existants avec leur raison sociale et NIF.

## 🔧 Boutons principaux et leur utilité

### 1. 🏗️ **"Créer une unité racine"**

**Utilité** : Ce bouton permet de créer le premier niveau de votre structure organisationnelle.

**Quand l'utiliser** :
- ✅ Quand vous n'avez encore aucune structure organisationnelle
- ✅ Pour ajouter un nouvel établissement à votre entreprise
- ✅ Au début de la configuration de votre organisation

**Ce qu'il fait** :
- Ouvre un formulaire pour créer une nouvelle unité organisationnelle
- Vous permet de choisir le type d'unité (généralement "Établissement" en premier)
- Demande un nom, un code et une description optionnelle
- Crée la base de votre arbre organisationnel

**Exemple d'usage** :
```
Nom: Siège Social
Code: SIEGE
Type: Établissement
Description: Siège social principal de l'entreprise
```

### 2. 🔄 **"Migrer les données"**

**Utilité** : Ce bouton automatise la migration de vos salariés existants vers la nouvelle structure organisationnelle.

**Quand l'utiliser** :
- ✅ Après avoir créé votre structure organisationnelle
- ✅ Quand vous avez des salariés qui ne sont pas encore assignés à des unités
- ✅ Pour faire la transition depuis l'ancien système vers le nouveau

**Ce qu'il fait** :
- Analyse les données textuelles existantes des salariés (établissement, département, service)
- Crée automatiquement les unités organisationnelles correspondantes si elles n'existent pas
- Assigne les salariés aux bonnes unités selon leurs données actuelles
- Affiche un rapport du nombre de salariés migrés

**Exemple de migration** :
```
Avant: Salarié avec "etablissement": "Siège", "departement": "RH"
Après: Salarié assigné à l'unité "RH" sous l'établissement "Siège"
```

## 🌳 Hiérarchie organisationnelle

Le système respecte cette hiérarchie stricte :
```
Employeur (votre entreprise)
└── Établissement (ex: Siège Social, Filiale Nord)
    └── Département (ex: Ressources Humaines, Comptabilité)
        └── Service (ex: Recrutement, Paie)
            └── Unité (ex: Équipe Junior, Équipe Senior)
```

## 🎯 Workflow recommandé

### Première utilisation :

1. **Sélectionner votre employeur** dans la liste déroulante
2. **Cliquer sur "Créer une unité racine"** pour créer votre premier établissement
3. **Créer la structure** en ajoutant des départements, services, etc.
4. **Cliquer sur "Migrer les données"** pour assigner automatiquement vos salariés existants
5. **Ajuster manuellement** si nécessaire en utilisant les boutons d'assignation

### Utilisation courante :

- **Ajouter de nouvelles unités** avec le bouton "+" à côté de chaque unité
- **Assigner des salariés** avec le bouton "👥" à côté de chaque unité
- **Visualiser la structure** avec l'arbre hiérarchique interactif

## 🚨 Salariés orphelins

Les "salariés orphelins" sont des employés qui ne sont pas encore assignés à une unité organisationnelle. Ils apparaissent dans une section spéciale en bas de la page avec un fond orange pour attirer l'attention.

## 💡 Avantages du système

- **Clarté organisationnelle** : Structure claire de votre entreprise
- **Gestion des droits** : Possibilité future de gérer les accès par unité
- **Reporting avancé** : Rapports par département, service, etc.
- **Compatibilité** : Préserve toutes les fonctionnalités existantes de paie