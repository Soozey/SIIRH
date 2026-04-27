# Guide des Améliorations de l'État de Paie

## 🎯 Objectifs Réalisés

### 1. Nouvelles Colonnes de Totaux
✅ **Ajout de 4 nouvelles colonnes avant "Coût total employeur" :**
- **Total CNaPS** : Somme des cotisations CNaPS salariales + patronales
- **Total SMIE** : Somme des cotisations SMIE salariales + patronales  
- **Charges salariales** : Total de toutes les charges salariales
- **Charges patronales** : Total de toutes les charges patronales

### 2. Gestion Dynamique des Primes
✅ **Extraction automatique des primes personnalisées :**
- Récupération automatique de toutes les primes définies dans la page "Employeur"
- Affichage dynamique dans l'État de paie
- Colonnes générées automatiquement selon les primes actives

### 3. Synchronisation et Cohérence
✅ **Mise à jour automatique :**
- Toute modification du libellé d'une prime se répercute automatiquement
- Les en-têtes de l'État de paie sont synchronisés avec les définitions de l'employeur
- Pas de configuration manuelle nécessaire

## 🔧 Implémentation Technique

### Backend (siirh-backend/app/routers/reporting.py)

#### Nouvelle fonction `get_dynamic_journal_columns()`
```python
def get_dynamic_journal_columns(employer_id: int, db: Session) -> List[str]:
    # Génère dynamiquement les colonnes incluant :
    # - Colonnes de base (identité, salaire)
    # - Primes personnalisées de l'employeur
    # - Nouvelles colonnes de totaux
```

#### Nouvelle API `/reporting/journal-columns/{employer_id}`
- Retourne les colonnes dynamiques pour un employeur spécifique
- Utilisée par le frontend pour l'aperçu et l'export

#### Calculs des nouvelles colonnes
- **Total CNaPS** : Cotisations salariales + patronales CNaPS
- **Total SMIE** : Cotisations salariales + patronales SMIE
- **Charges salariales** : Toutes les retenues salariales
- **Charges patronales** : Toutes les charges patronales

### Frontend (siirh-frontend/src/pages/PayrollRun.tsx)

#### Aperçu dynamique
- Table d'aperçu adaptative (12 premières colonnes)
- Formatage intelligent selon le type de colonne
- Styles différenciés (montants, texte, totaux)

#### Fonctions utilitaires
- `formatColumnName()` : Formatage des noms de colonnes
- `formatCellValue()` : Formatage des valeurs selon le type
- `getCellStyle()` : Styles CSS adaptatifs

## 📊 Ordre des Colonnes dans l'État de Paie (Mis à jour)

### 1. Identité (10 colonnes)
- Matricule, Nom, Prénom, CIN, N° CNaPS, Date embauche, Poste, Catégorie, Mode de paiement, Nombre d'enfants

### 2. Salaire de Base (3 colonnes)  
- Salaire base, VHM, Salaire de base (calculé)

### 3. Heures Supplémentaires (8 colonnes)
- HS Non Imposable 130%, HS Imposable 130%, HS Non Imposable 150%, HS Imposable 150%
- Heures Majorées (Nuit Hab. 30%, Nuit Occ. 50%, Dimanche 40%, Jours Fériés 50%)

### 4. **🆕 Primes Personnalisées (dynamique)**
- **Toutes les primes définies par l'employeur**
- **Positionnées juste après "Heures Majorées Jours Fériés 50%"**
- **Ordre alphabétique des libellés**

### 5. Avantages en Nature (3 colonnes)
- Avantage véhicule, logement, téléphone

### 6. Totaux et Charges (15 colonnes)
- Total Brut
- Cotisations CNaPS Salarié, SMIE Salarié
- **🆕 Charges salariales** (juste après SMIE Salarié)
- Total CNaPS, Total SMIE
- IRSA, Avances, Autres déductions
- Net à payer
- Charges patronales (CNaPS, SMIE, FMFP)
- Charges patronales (total)
- Coût total employeur

## 🗑️ Colonnes Supprimées

Les colonnes suivantes ont été **supprimées** de l'État de paie standard :
- ❌ Prime fixe
- ❌ Prime variable  
- ❌ 13ème mois
- ❌ Allocation familiale

> **Note :** Ces éléments sont maintenant gérés via les **primes personnalisées** définies dans la page Employeur, offrant plus de flexibilité.

## 🚀 Utilisation

### Pour l'Utilisateur
1. **Définir les primes** dans la page "Employeur"
2. **Générer l'aperçu** de l'État de paie → Colonnes automatiquement mises à jour
3. **Exporter en Excel** → Toutes les colonnes incluses (primes personnalisées comprises)

### Synchronisation Automatique
- ✅ Ajout d'une nouvelle prime → Apparaît automatiquement dans l'État de paie
- ✅ Modification du libellé → Mise à jour automatique des en-têtes
- ✅ Désactivation d'une prime → Retrait automatique de l'État de paie

## 🎯 Avantages

1. **Flexibilité** : Adaptation automatique aux besoins de chaque employeur
2. **Cohérence** : Synchronisation parfaite entre définitions et exports
3. **Complétude** : Toutes les informations du bulletin dans l'État de paie
4. **Maintenance** : Aucune configuration manuelle nécessaire

## 📝 Notes Techniques

- L'aperçu affiche les 12 premières colonnes pour la lisibilité
- L'export Excel contient toutes les colonnes (jusqu'à 49+ colonnes)
- Les primes inactives ne sont pas incluses dans l'export
- Les calculs de totaux sont basés sur les données des bulletins individuels