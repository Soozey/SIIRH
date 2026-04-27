# 🌐 Guide - Templates Globaux Réutilisables

## 🎯 Concept : Un Template pour Tous les Salariés

Au lieu de créer un contrat spécifique pour chaque salarié, vous pouvez maintenant :
1. **Créer un template global** (ex: "Contrat CDI Standard")
2. **L'appliquer à n'importe quel salarié**
3. **Les informations se remplissent automatiquement** selon le salarié sélectionné

## ✅ Avantages

### 🚀 Gain de Temps
- **Créez une fois**, utilisez pour tous
- **Pas de duplication** de travail
- **Application instantanée** à n'importe quel salarié

### 🎯 Cohérence
- **Même structure** pour tous les contrats
- **Standardisation** des documents
- **Maintenance centralisée** (modifier le template = tous les futurs contrats mis à jour)

### 🔄 Flexibilité
- **Remplacement automatique** des données (nom, salaire, etc.)
- **Templates multiples** (CDI, CDD, Stage, etc.)
- **Personnalisation** par employeur

## 🛠️ Comment Utiliser

### 1. Créer un Template Global

1. **Ouvrir un contrat** d'un salarié quelconque
2. **Utiliser la palette de constantes** pour insérer les champs dynamiques :
   - `{{worker.nom}}` → Nom du salarié
   - `{{worker.prenom}}` → Prénom du salarié
   - `{{worker.salaire_base}}` → Salaire
   - `{{employer.raison_sociale}}` → Nom de l'entreprise
   - etc.
3. **Cliquer sur "Créer Template"** (bouton violet)
4. **Donner un nom** au template (ex: "Contrat CDI Standard")
5. **Confirmer** → Le template est sauvegardé pour tous les salariés

### 2. Appliquer un Template à un Salarié

1. **Ouvrir le contrat** du salarié souhaité
2. **Cliquer sur "Templates Globaux"** (bouton indigo)
3. **Sélectionner le template** désiré dans la liste
4. **Cliquer pour appliquer** → Le contrat se remplit automatiquement avec les données du salarié
5. **Modifier si nécessaire** et sauvegarder

### 3. Gérer les Templates

- **Voir tous les templates** : Bouton "Templates Globaux"
- **Modifier un template** : L'appliquer, modifier, puis "Créer Template" avec le même nom
- **Templates système** : Certains templates peuvent être fournis par défaut

## 🎨 Exemple Concret

### Template Créé (Une Fois)
```
CONTRAT DE TRAVAIL CDI

Entre la société {{employer.raison_sociale}}
Et M./Mme {{worker.nom}} {{worker.prenom}}
Matricule: {{worker.matricule}}
Salaire: {{worker.salaire_base}}
Date: {{system.date_aujourd_hui}}
```

### Application à RAFALIMANANA
```
CONTRAT DE TRAVAIL CDI

Entre la société Karibo Services
Et M./Mme RAFALIMANANA HENINTSOA
Matricule: N0003
Salaire: 2,500,000 Ar
Date: 26/12/2025
```

### Application à RAKOTOBE
```
CONTRAT DE TRAVAIL CDI

Entre la société Karibo Services
Et M./Mme RAKOTOBE Souzzy
Matricule: N0007
Salaire: 1,800,000 Ar
Date: 26/12/2025
```

## 🔍 Interface Utilisateur

### Nouveaux Boutons dans le Contrat

1. **📋 Palette Constantes** (bleu) - Insérer des champs dynamiques
2. **💾 Sauvegarder** (vert) - Sauvegarder pour ce salarié uniquement
3. **📄 Créer Template** (violet) - Créer un template global réutilisable
4. **📄 Templates Globaux** (indigo) - Appliquer un template existant

### Workflow Recommandé

1. **Première fois** :
   - Créer le contrat avec la palette de constantes
   - Sauvegarder comme template global
   
2. **Salariés suivants** :
   - Ouvrir le contrat
   - Appliquer le template global
   - Ajuster si nécessaire
   - Sauvegarder (optionnel)

## 🎯 Cas d'Usage

### Templates Multiples par Type
- **"Contrat CDI Standard"** - Pour les CDI classiques
- **"Contrat CDD Saisonnier"** - Pour les CDD courts
- **"Contrat Cadre"** - Pour les postes de direction
- **"Contrat Stage"** - Pour les stagiaires

### Templates par Département
- **"Contrat Commercial"** - Avec clauses spécifiques
- **"Contrat Technique"** - Avec horaires particuliers
- **"Contrat Administratif"** - Avec avantages spécifiques

## 🔧 Maintenance

### Modifier un Template Existant
1. Appliquer le template à un salarié
2. Faire les modifications souhaitées
3. "Créer Template" avec le même nom → Écrase l'ancien

### Supprimer un Template
- Actuellement via l'API (fonctionnalité à ajouter dans l'interface)

## 🎉 Résultat Final

**Avant** : Créer 50 contrats pour 50 salariés = 50 fois le même travail
**Après** : Créer 1 template + appliquer 50 fois = 1 création + 50 clics

**Gain de temps estimé : 95% !** 🚀

Le système de templates globaux transforme la création de contrats d'une tâche répétitive en un processus efficace et standardisé.