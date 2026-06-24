# Frost Days

Application Python Streamlit qui calcule les jours de gel pour une commune francaise, un departement et une plage de dates entre 2013 et 2024.

Les donnees sont recuperees a la demande via des sources publiques :

- `geo.api.gouv.fr` pour les coordonnees de la commune ;
- fichiers quotidiens departementaux publics Meteo-France `RR-T-Vent` pour les stations et donnees meteo.

Le projet ne demande aucune cle API Meteo-France. Il ne telecharge pas tous les departements : seul le departement saisi est recupere puis mis en cache localement.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Sous Windows PowerShell, l'activation de l'environnement virtuel se fait avec :

```powershell
.\.venv\Scripts\Activate.ps1
```

## Fonctionnement

1. L'utilisateur choisit un departement, une commune, une date de debut et une date de fin.
2. L'application recupere les coordonnees de la commune avec `geo.api.gouv.fr`.
3. Elle telecharge les fichiers quotidiens publics Meteo-France du departement demande.
4. Elle calcule la distance Haversine entre la commune et chaque station.
5. Elle trie les stations par distance.
6. Pour chaque station proche, elle filtre les donnees quotidiennes sur la periode demandee.
7. Les codes temporaires `429`, `500`, `502`, `503` et `504` sont retentes.
8. Les resultats sont mis en cache local dans `.cache/frost_days`.
9. La premiere station avec au maximum 35 % de valeurs manquantes est utilisee.

La plage de dates est limitee dans l'interface a `2013-01-01` - `2024-12-31`.

Un jour de gel est defini par une temperature minimale quotidienne inferieure ou egale a 0 degC.

## Interface

L'interface Streamlit affiche :

- une liste deroulante des departements ;
- une liste deroulante des communes du departement choisi ;
- la station utilisee ;
- la distance station-commune ;
- le taux de donnees manquantes ;
- le nombre total de jours de gel ;
- la moyenne annuelle ;
- un graphique des jours de gel par annee ;
- un graphique des probabilites de gel par jour de l'annee ;
- un tableau telechargeable en CSV.

## Tests

```bash
pytest
```

Les tests du client de donnees publiques sont mockes et ne realisent aucun appel reseau.

## Documentation detaillee

Une documentation complete, orientee debutant, est disponible dans `DOCUMENTATION.md`.
