# Guide du Référentiel Centralisé de Constantes SIIRH

## 🎯 Vue d'ensemble

Le référentiel centralisé de constantes SIIRH permet de gérer toutes les données de référence du système dans un seul endroit, avec une interface intuitive pour l'insertion automatique dans les documents.

## 📋 Fonctionnalités Principales

### 1. **Référentiel Backend Centralisé**
- **Constantes de Paie** : Taux de cotisations, majorations HS, formules de calcul
- **Constantes Métier** : Types de contrats, modes de paiement, catégories professionnelles
- **Champs de Documents** : Tous les champs disponibles pour l'insertion dans les documents
- **Règles de Validation** : Listes déroulantes, règles de validation, messages d'erreur

### 2. **Interface de Gestion des Documents**
- **Éditeur Intuitif** : Interface simple avec palette de champs
- **Insertion par Clic** : Cliquez sur un champ pour l'insérer automatiquement
- **Aperçu en Temps Réel** : Visualisez le rendu final avec les vraies données
- **Templates Prédéfinis** : Certificats, attestations, contrats de travail

### 3. **API Centralisée**
- **Endpoints RESTful** : Accès programmatique à toutes les constantes
- **Cache Intelligent** : Optimisation des performances avec mise en cache
- **Données Formatées** : Données prêtes à l'emploi pour l'insertion

## 🚀 Utilisation

### Accès à l'Interface

1. **Navigation** : Cliquez sur "Documents" dans le menu principal
2. **Gestion des Constantes** : Bouton "Constantes" pour voir le référentiel
3. **Création de Documents** : Bouton "Nouveau Document" pour créer

### Création d'un Document

1. **Choisir un Template** :
   - Certificat de travail
   - Attestation d'emploi  
   - Contrat de travail
   - Ou créer un document vierge

2. **Utiliser l'Éditeur** :
   - **Palette de Gauche** : Tous les champs disponibles par catégorie
   - **Zone d'Édition** : Tapez votre texte et insérez des champs
   - **Aperçu** : Bouton "Aperçu" pour voir le rendu final

3. **Insertion de Champs** :
   - Cliquez sur un champ dans la palette
   - Le champ s'insère sous forme `{{nom_du_champ}}`
   - En aperçu, il est remplacé par la vraie valeur

### Catégories de Champs Disponibles

#### 🏢 **Employeur**
- `{{raison_sociale}}` - Nom de l'entreprise
- `{{adresse}}` - Adresse complète
- `{{representant}}` - Représentant légal
- `{{nif}}` - Numéro d'Identification Fiscale
- `{{stat}}` - Numéro statistique
- `{{cnaps_num}}` - Numéro CNaPS employeur

#### 👤 **Travailleur**
- `{{nom_complet}}` - Nom et prénom
- `{{matricule}}` - Numéro matricule
- `{{poste}}` - Intitulé du poste
- `{{date_embauche}}` - Date d'entrée (formatée)
- `{{salaire_base}}` - Salaire de base (formaté)
- `{{cin}}` - Carte d'Identité Nationale
- `{{cnaps}}` - Numéro CNaPS du salarié

#### 💰 **Paie**
- `{{periode}}` - Période de paie
- `{{salaire_brut}}` - Salaire brut total
- `{{net_a_payer}}` - Montant net à payer
- `{{cotisations_salariales}}` - Total cotisations

#### 🗓️ **Système**
- `{{date_aujourd_hui}}` - Date actuelle (formatée)
- `{{annee_courante}}` - Année en cours

## 📊 Référentiel de Constantes

### Constantes de Paie

#### Taux de Cotisations
```json
{
  "cnaps": {
    "salarial": 1.0,
    "patronal_general": 13.0,
    "patronal_scolaire": 8.0
  },
  "smie": {
    "salarial": 0.0,
    "patronal": 0.0
  },
  "fmfp": {
    "patronal": 1.0
  }
}
```

#### Majorations Heures Supplémentaires
- **HS 130%** : +30% (non imposable et imposable)
- **HS 150%** : +50% (non imposable et imposable)
- **HM Nuit Habituelle** : +30%
- **HM Nuit Occasionnelle** : +50%
- **HM Dimanche** : +40%
- **HM Jours Fériés** : +50%

#### Constantes de Calcul
- **Diviseur Absences** : 21.67 jours
- **Heures par Mois** : 173.33 heures
- **Jours Travaillés** : 21.67 jours

### Constantes Métier

#### Types de Contrats
- **CDI** : Contrat à Durée Indéterminée (90 jours d'essai max)
- **CDD** : Contrat à Durée Déterminée (30 jours d'essai max)

#### Modes de Paiement
- **Virement** : Virement bancaire (RIB requis)
- **Espèces** : Paiement en espèces
- **Chèque** : Paiement par chèque

#### Catégories Professionnelles
- M1, M2 : Manœuvres
- OS1, OS2 : Ouvriers Spécialisés
- OP1, OP2 : Ouvriers Professionnels
- EM1, EM2 : Employés
- AM : Agent de Maîtrise
- CAD : Cadre

## 🔧 API Endpoints

### Constantes Générales
- `GET /constants/payroll` - Constantes de paie
- `GET /constants/business` - Constantes métier
- `GET /constants/validation` - Règles de validation
- `GET /constants/document-fields` - Champs de documents

### Données Contextuelles
- `GET /constants/worker-data/{worker_id}` - Données d'un travailleur
- `GET /constants/employer-data/{employer_id}` - Données d'un employeur
- `GET /constants/system-data` - Données système (dates)

### Utilitaires
- `GET /constants/field-categories` - Champs par catégorie
- `GET /constants/dropdowns/{field_name}` - Options d'une liste

## 💡 Exemples d'Utilisation

### Certificat de Travail
```
CERTIFICAT DE TRAVAIL

Je soussigné(e) {{representant}}, {{rep_fonction}} de {{raison_sociale}}, 
certifie que {{nom_complet}} a été employé(e) dans notre entreprise 
en qualité de {{poste}} du {{date_embauche}} à ce jour.

Ce certificat lui est délivré pour servir et valoir ce que de droit.

Fait à {{ville}}, le {{date_aujourd_hui}}

{{representant}}
{{rep_fonction}}
```

### Attestation d'Emploi
```
ATTESTATION D'EMPLOI

L'entreprise {{raison_sociale}}, située {{adresse}}, 
NIF : {{nif}}, atteste que :

{{nom_complet}}, matricule {{matricule}}, 
est employé(e) dans notre entreprise en qualité de {{poste}} 
depuis le {{date_embauche}}.

Son salaire mensuel de base est de {{salaire_base}}.

Cette attestation est délivrée à l'intéressé(e) pour servir et valoir ce que de droit.

Fait le {{date_aujourd_hui}}
```

## 🎯 Avantages

### 1. **Centralisation**
- Une seule source de vérité pour toutes les constantes
- Cohérence garantie entre backend et frontend
- Maintenance simplifiée

### 2. **Automatisation**
- Insertion automatique des données dans les documents
- Élimination des erreurs de saisie manuelle
- Génération rapide de documents

### 3. **Flexibilité**
- Ajout facile de nouveaux champs
- Modification centralisée des constantes
- Templates personnalisables

### 4. **Performance**
- Cache intelligent pour optimiser les performances
- Chargement à la demande des données
- Synchronisation automatique

## 🔄 Intégration avec l'Existant

### Calculs de Paie
Le système utilise maintenant les constantes centralisées pour :
- Calcul des cotisations (taux CNaPS, SMIE, FMFP)
- Majorations des heures supplémentaires
- Diviseurs pour les absences et congés
- Variables dans les formules de primes

### Import Excel
Les listes déroulantes sont générées automatiquement depuis les constantes :
- Sexe (M/F)
- Situation familiale
- Nature du contrat (CDI/CDD)
- Mode de paiement
- Catégories professionnelles

### États de Paie
Les colonnes dynamiques utilisent les constantes pour :
- Libellés des primes personnalisées
- Formatage des montants
- Ordre des colonnes
- Métadonnées d'export

## 📈 Évolutions Futures

### Fonctionnalités Prévues
1. **Éditeur Avancé** : Formatage riche, tableaux, images
2. **Templates Sectoriels** : Modèles spécialisés par secteur d'activité
3. **Workflow d'Approbation** : Circuit de validation des documents
4. **Signature Électronique** : Intégration de signatures numériques
5. **Export Multi-Format** : PDF, Word, HTML

### Extensions Possibles
1. **API Externe** : Intégration avec d'autres systèmes
2. **Notifications** : Alertes automatiques pour les documents
3. **Historique** : Versioning des templates et documents
4. **Collaboration** : Édition collaborative en temps réel

## 🛠️ Maintenance

### Ajout de Nouvelles Constantes
1. Modifier les fichiers dans `siirh-backend/app/constants/`
2. Redémarrer le serveur backend
3. Les nouvelles constantes sont automatiquement disponibles

### Modification des Templates
1. Accéder à l'interface de gestion des documents
2. Modifier le template existant ou en créer un nouveau
3. Tester avec l'aperçu avant sauvegarde

### Mise à Jour des Champs
1. Ajouter le champ dans `document_constants.py`
2. Implémenter la logique de récupération dans l'API
3. Le champ apparaît automatiquement dans la palette

---

**Le référentiel centralisé de constantes SIIRH transforme la gestion documentaire en automatisant l'insertion des données et en garantissant la cohérence de l'information dans tout le système.**