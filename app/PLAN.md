# Plan Frost Days

## Architecture

- `app.py` : interface Streamlit, saisie utilisateur, orchestration et affichage.
- `frost_days/config.py` : constantes et configuration de logs.
- `frost_days/geo_api.py` : recherche d'une commune via `geo.api.gouv.fr`.
- `frost_days/public_data_client.py` : client des fichiers publics departementaux Meteo-France, retries, cache et telechargement cible.
- `frost_days/stations.py` : normalisation des stations, tri par distance et selection de la premiere station exploitable.
- `frost_days/distance.py` : formule Haversine.
- `frost_days/frost_calculator.py` : detection de la colonne de temperature minimale, nettoyage et calcul du gel.
- `frost_days/statistics.py` : agregations annuelles et par jour de l'annee.
- `frost_days/cache.py` : cache local des stations et donnees quotidiennes.
- `tests/` : tests unitaires et tests API mockes.
- `notebooks/data_quality.ipynb` : notebook de controle qualite exploratoire.

## Etapes

1. Creer la structure du projet et les fichiers de configuration.
2. Implementer l'acces a l'API Geo pour localiser la commune.
3. Implementer le client de donnees publiques Meteo-France sans cle API, avec retries et cache.
4. Implementer la selection de station selon la distance et le seuil de 35 % de donnees manquantes.
5. Implementer les statistiques de gel.
6. Creer l'interface Streamlit avec graphiques Plotly et export CSV.
7. Ajouter les tests unitaires et les mocks du client Meteo-France.
8. Documenter l'installation, la configuration et le lancement.
