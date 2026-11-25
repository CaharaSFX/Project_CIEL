# StageCIEL : la carte des entreprises

Une carte des entreprises d'informatique, réseau, électronique et cybersécurité en Charente, pour aider les élèves de bac pro CIEL à trouver un stage.

**Site en ligne : https://caharasfx.github.io/Project_CIEL/**

Projet réalisé en terminale bac pro CIEL au lycée Coulomb d'Angoulême.

## Fonctionnement

1. `recuperer_entreprises.py` interroge l'[API Recherche d'entreprises](https://recherche-entreprises.api.gouv.fr) et filtre par département, code NAF et effectif.
2. Le résultat est écrit dans `entreprises.geojson`.
3. `index.html` affiche ces points sur une carte [Leaflet](https://leafletjs.com), avec des filtres par secteur.

Les données sont actualisées chaque lundi par GitHub Actions (`.github/workflows/maj-entreprises.yml`).

## Lancer le projet

Il faut Python 3, sans bibliothèque à installer.

```bash
python recuperer_entreprises.py   # met à jour les données
python -m http.server             # lance un serveur local
```

Puis ouvrir http://localhost:8000.

## Réglages

En haut de `recuperer_entreprises.py` :

| Variable | Rôle |
|---|---|
| `DEPARTEMENTS` | Départements couverts |
| `CODES_NAF` | Activités retenues |
| `NOMS_A_AJOUTER` | Entreprises ajoutées à la main (sans les filtres) |
| `EFFECTIF_MINIMUM` | Tranche d'effectif minimale (`"02"` = 3 à 5 salariés) |

## Sources des données

Base Sirene (Insee) via api.gouv.fr. Fond de carte © contributeurs OpenStreetMap.
