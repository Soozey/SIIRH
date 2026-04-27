# Formats d'export réglementaires

Date: 2026-03-20

## Templates pris en charge
- `dns_cnaps`
- `ostie_smie`
- `irsa_bimestriel`
- `fmfp`
- `etat_paie`
- `bilan_social`
- `contract_control_bundle`

## Architecture implémentée
- `export_templates`
- `reporting_snapshots`
- `export_jobs`
- `statutory_declarations`
- service d'agrégation: `app/services/statutory_reporting_service.py`

## Sources de données
- Employeur: raison sociale, NIF et autres identifiants disponibles.
- Salarié: matricule, identité, dates, CNaPS, CIN, affectation.
- Paie: lecture seule via le moteur existant et ses prévisualisations.
- SST: incidents enregistrés pour le bilan social.
- Contrats: brouillons et versions de conformité pour le bundle inspection.

## Correspondance avec les pièces jointes
- IRSA bimestriel:
  - feuille `EtatNominatif`
  - feuille `Bordereau`
  - structure inspirée des fichiers `IRSA-KARIBO-*.xlsx`
- État de paie:
  - structure colonnaire issue du reporting existant
  - ordre aligné sur le modèle `Etat_Paie_template.xlsx`
- DNS CNaPS / OSTIE:
  - colonnes alignées sur l'annexe déclarations et les exemples d'état
- FMFP:
  - export intermédiaire propre et versionné
- Bilan social:
  - synthèse annuelle orientée effectifs / masse salariale / SST

## Endpoints
- `GET /statutory-exports/templates`
- `POST /statutory-exports/preview`
- `POST /statutory-exports/generate`
- `GET /statutory-exports/jobs`
- `GET /statutory-exports/jobs/{id}/download`
- `GET /statutory-exports/declarations`
- `POST /statutory-exports/declarations/{id}/submit`

## Hypothèses documentées
- Les taux et assiettes sont lus depuis la paie existante ou estimés depuis les lignes de prévisualisation déjà validées.
- Aucun recalcul du moteur paie n'est effectué dans cette couche.
