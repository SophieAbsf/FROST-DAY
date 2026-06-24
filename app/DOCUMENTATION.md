# Documentation complete du projet Frost Days

## 1. Objectif du projet

Frost Days est une application qui permet de calculer les jours de gel pour une commune francaise.

Un jour de gel est un jour ou la temperature minimale quotidienne est inferieure ou egale a 0 degC.

L'utilisateur choisit :

- un departement ;
- une commune ;
- une date de debut ;
- une date de fin.

Dans cette version, la periode est limitee de `2013-01-01` a `2024-12-31`.

L'application affiche ensuite :

- la station meteo utilisee ;
- la distance entre la commune et cette station ;
- le taux de donnees manquantes ;
- le nombre total de jours de gel ;
- la moyenne annuelle de jours de gel ;
- un graphique des jours de gel par annee ;
- un graphique des probabilites de gel pour chaque jour de l'annee ;
- un tableau telechargeable en CSV.

## 2. Fonctionnement general

Le projet suit ce parcours :

1. L'utilisateur ouvre l'application Streamlit.
2. Il choisit un departement dans une liste deroulante.
3. L'application demande a `geo.api.gouv.fr` la liste des communes de ce departement.
4. L'utilisateur choisit une commune.
5. L'application recupere les coordonnees GPS de cette commune.
6. L'application telecharge les donnees publiques Meteo-France du departement choisi.
7. Elle extrait les stations meteo disponibles dans ce departement.
8. Elle calcule la distance entre la commune et chaque station.
9. Elle trie les stations de la plus proche a la plus eloignee.
10. Elle teste les stations une par une.
11. Elle garde la premiere station qui a au maximum 35 % de donnees manquantes.
12. Elle calcule les statistiques de gel.
13. Elle affiche les resultats dans l'interface.

## 3. Sources de donnees

### Communes

Les communes viennent de l'API publique :

```text
https://geo.api.gouv.fr/communes
```

Cette API permet de recuperer les communes d'un departement avec leur nom, leur code INSEE et leurs coordonnees GPS.

### Donnees meteo

Les donnees meteo viennent des fichiers publics Meteo-France publies sur `data.gouv.fr`.

Le projet utilise les fichiers quotidiens departementaux `RR-T-Vent`, par exemple :

```text
Q_21_previous-1950-2024_RR-T-Vent.csv.gz
```

Le code ne telecharge pas tous les departements. Il telecharge seulement les fichiers du departement choisi par l'utilisateur.

Le fichier est ensuite mis en cache pour accelerer les prochains lancements.

## 4. Structure du projet

```text
frost-days/
|-- app.py
|-- README.md
|-- DOCUMENTATION.md
|-- PLAN.md
|-- requirements.txt
|-- .gitignore
|-- frost_days/
|   |-- __init__.py
|   |-- cache.py
|   |-- config.py
|   |-- departments.py
|   |-- distance.py
|   |-- frost_calculator.py
|   |-- geo_api.py
|   |-- public_data_client.py
|   |-- stations.py
|   `-- statistics.py
|-- tests/
|   |-- test_distance.py
|   |-- test_frost_calculator.py
|   |-- test_public_data_client.py
|   `-- test_statistics.py
`-- notebooks/
    `-- data_quality.ipynb
```

## 5. Explication des fichiers principaux

### `app.py`

`app.py` est le fichier principal de l'application.

C'est lui qui lance l'interface Streamlit. Streamlit est un outil Python qui permet de creer une interface web simple sans coder directement du HTML ou du JavaScript.

Dans ce fichier, on trouve :

- la configuration de la page ;
- la liste deroulante des departements ;
- la liste deroulante des communes ;
- les champs de dates ;
- le bouton `Calculer` ;
- l'appel aux fonctions metier ;
- l'affichage des resultats ;
- les graphiques Plotly ;
- le bouton de telechargement CSV.

En resume, `app.py` est le chef d'orchestre. Il ne fait pas tous les calculs lui-meme, mais il appelle les autres fichiers.

### `README.md`

Le README explique rapidement :

- le but du projet ;
- comment installer les dependances ;
- comment lancer l'application ;
- comment lancer les tests.

C'est le fichier a lire en premier quand on decouvre le projet.

### `DOCUMENTATION.md`

C'est le fichier que vous lisez actuellement.

Il explique le fonctionnement du projet de maniere plus detaillee, avec un niveau accessible a quelqu'un qui ne connait pas Python.

### `PLAN.md`

Ce fichier contient le plan technique initial :

- architecture prevue ;
- grandes etapes de realisation ;
- modules attendus.

Il sert a montrer comment le projet a ete organise.

### `requirements.txt`

Ce fichier liste les bibliotheques Python necessaires pour faire fonctionner le projet.

Exemples :

- `streamlit` pour l'interface web ;
- `pandas` pour manipuler les tableaux de donnees ;
- `plotly` pour les graphiques ;
- `requests` pour faire des appels web ;
- `pytest` pour les tests.

Quand on lance :

```bash
pip install -r requirements.txt
```

Python installe toutes les bibliotheques listees dans ce fichier.

### `.gitignore`

Ce fichier indique a Git quels fichiers ne doivent pas etre suivis.

Exemples :

- les caches ;
- les environnements virtuels ;
- les fichiers temporaires Python.

Cela evite de polluer le depot avec des fichiers generes automatiquement.

## 6. Explication du dossier `frost_days/`

Le dossier `frost_days/` contient le code metier de l'application.

Le code metier correspond a la logique importante du projet : recuperer les donnees, choisir une station, calculer les jours de gel, produire les statistiques.

### `frost_days/__init__.py`

Ce fichier indique a Python que `frost_days` est un package.

Un package est un dossier qui regroupe plusieurs fichiers Python pouvant etre importes dans d'autres fichiers.

Il contient aussi une version du projet :

```python
__version__ = "0.1.0"
```

### `frost_days/config.py`

Ce fichier contient des constantes generales :

- le chemin du cache local ;
- l'adresse de l'API Geo ;
- la configuration des logs.

Les logs sont des messages techniques qui permettent de suivre ce que fait l'application.

### `frost_days/departments.py`

Ce fichier contient la liste des departements francais.

Chaque departement est defini par :

- un code, par exemple `21` ;
- un nom, par exemple `Cote-d'Or`.

Il contient aussi deux fonctions :

- `department_options()` : prepare les textes affiches dans la liste deroulante ;
- `parse_department_option()` : recupere uniquement le code du departement choisi.

Exemple :

```text
21 - Cote-d'Or
```

devient :

```text
21
```

### `frost_days/geo_api.py`

Ce fichier communique avec l'API publique `geo.api.gouv.fr`.

Il contient :

- une classe `Commune`, qui represente une commune avec son nom, son code, son departement, sa latitude et sa longitude ;
- une fonction `list_communes()`, qui recupere toutes les communes d'un departement ;
- une fonction `get_commune()`, qui peut rechercher une commune par son nom ;
- une fonction interne qui transforme la reponse de l'API en objet `Commune`.

Ce fichier permet a l'application de ne pas stocker localement un gros fichier de communes.

### `frost_days/public_data_client.py`

Ce fichier est responsable des donnees Meteo-France.

Il ne demande aucune cle API.

Son role est de :

- construire les URL des fichiers publics Meteo-France ;
- telecharger les fichiers du departement choisi ;
- lire uniquement les colonnes utiles ;
- garder uniquement les lignes de la periode demandee ;
- mettre les donnees en cache ;
- retourner la liste des stations ;
- retourner les donnees quotidiennes d'une station.

Les colonnes utiles sont notamment :

- `NUM_POSTE` : identifiant de la station ;
- `NOM_USUEL` : nom de la station ;
- `LAT` : latitude ;
- `LON` : longitude ;
- `AAAAMMJJ` : date au format annee-mois-jour ;
- `TN` : temperature minimale quotidienne.

Pour ameliorer la rapidite, le fichier est lu par morceaux. Cela evite de charger un tres gros fichier complet en memoire d'un seul coup.

### `frost_days/cache.py`

Ce fichier gere le cache local.

Un cache est une copie locale de donnees deja telechargees ou deja traitees.

Sans cache :

- l'application doit retelecharger et relire les donnees a chaque lancement.

Avec cache :

- le premier lancement peut prendre quelques secondes ;
- les lancements suivants sont beaucoup plus rapides.

Le cache est stocke dans :

```text
.cache/frost_days
```

### `frost_days/distance.py`

Ce fichier contient le calcul de distance entre deux points GPS.

Il utilise la formule de Haversine.

Cette formule permet de calculer la distance a vol d'oiseau entre deux points sur la Terre a partir de :

- leur latitude ;
- leur longitude.

Dans le projet, cette distance sert a trouver la station meteo la plus proche de la commune.

### `frost_days/stations.py`

Ce fichier gere la selection de la station meteo.

Il fait plusieurs choses :

1. Il normalise les colonnes des stations.
2. Il calcule la distance entre la commune et chaque station.
3. Il trie les stations de la plus proche a la plus eloignee.
4. Il teste chaque station.
5. Il garde la premiere station avec au maximum 35 % de donnees manquantes.

Pourquoi ne pas prendre automatiquement la station la plus proche ?

Parce que la station la plus proche peut avoir trop de donnees manquantes. Dans ce cas, l'application passe a la station suivante.

### `frost_days/frost_calculator.py`

Ce fichier prepare les donnees meteo avant les calculs.

Il sert notamment a :

- trouver la colonne de date ;
- trouver la colonne de temperature minimale ;
- convertir les dates dans un format utilisable ;
- convertir les temperatures en nombres ;
- ajouter les jours absents ;
- calculer le taux de donnees manquantes ;
- identifier les jours de gel.

Le code cherche plusieurs noms possibles pour la temperature minimale :

- `TN` ;
- `TMIN` ;
- `T_MIN` ;
- `TEMP_MIN` ;
- etc.

Cela rend le projet plus robuste si le nom de colonne change legerement.

### `frost_days/statistics.py`

Ce fichier calcule les statistiques finales.

Il produit :

- le nombre total de jours de gel ;
- la moyenne annuelle ;
- le tableau des jours de gel par annee ;
- le tableau des probabilites de gel par jour de l'annee.

Le 29 fevrier est retire des statistiques par jour de l'annee.

Pourquoi ?

Parce que le 29 fevrier n'existe que les annees bissextiles. Le retirer permet de comparer plus proprement les jours entre les annees.

## 7. Explication du dossier `tests/`

Le dossier `tests/` contient des tests automatises.

Un test automatise est un petit programme qui verifie qu'une partie du code fonctionne correctement.

On lance les tests avec :

```bash
pytest
```

### `tests/test_distance.py`

Ce fichier teste le calcul de distance.

Il verifie par exemple :

- que la distance entre un point et lui-meme est 0 ;
- que la distance entre Paris et Lyon est dans un ordre de grandeur correct.

### `tests/test_frost_calculator.py`

Ce fichier teste la preparation des donnees de gel.

Il verifie :

- que la colonne `TN` est detectee ;
- que les donnees manquantes sont bien calculees ;
- qu'une erreur claire est levee si aucune colonne de temperature minimale n'est trouvee.

### `tests/test_public_data_client.py`

Ce fichier teste le client de donnees publiques Meteo-France.

Il ne fait pas de vrai appel reseau.

Il utilise de fausses reponses pour verifier que :

- les stations sont bien lues ;
- les donnees d'une station sont bien filtrees ;
- les colonnes inutiles sont ignorees ;
- les URL Meteo-France sont construites correctement.

### `tests/test_statistics.py`

Ce fichier teste les statistiques.

Il verifie notamment que le 29 fevrier est bien exclu des statistiques par jour de l'annee.

## 8. Explication du dossier `notebooks/`

### `notebooks/data_quality.ipynb`

Ce fichier est un notebook Jupyter.

Un notebook permet de faire des analyses exploratoires avec du texte et du code dans le meme document.

Ici, il sert de support pour inspecter la qualite des donnees :

- valeurs manquantes ;
- colonnes disponibles ;
- coherence des dates ;
- anomalies possibles.

Il n'est pas necessaire pour lancer l'application.

## 9. Comment lancer le projet

### Etape 1 : creer un environnement virtuel

Un environnement virtuel est un dossier qui contient les bibliotheques Python du projet.

Cela evite de melanger les dependances de plusieurs projets.

Commande :

```bash
python -m venv .venv
```

### Etape 2 : activer l'environnement virtuel

Sur Linux ou macOS :

```bash
source .venv/bin/activate
```

Sur Windows PowerShell :

```powershell
.\.venv\Scripts\Activate.ps1
```

### Etape 3 : installer les dependances

```bash
pip install -r requirements.txt
```

### Etape 4 : lancer l'application

```bash
streamlit run app.py
```

Une page web s'ouvre ensuite avec l'interface Frost Days.

## 10. Comment expliquer le calcul a quelqu'un

Phrase simple :

> L'application cherche la station meteo la plus proche de la commune avec assez de donnees disponibles, puis compte tous les jours ou la temperature minimale est inferieure ou egale a 0 degC.

Explication plus detaillee :

1. On choisit une commune.
2. L'application trouve sa position GPS.
3. Elle recupere les stations meteo du departement.
4. Elle calcule quelle station est la plus proche.
5. Elle verifie que cette station a assez de donnees.
6. Elle lit les temperatures minimales quotidiennes.
7. Elle compte les jours ou la temperature minimale est negative ou nulle.
8. Elle produit des graphiques et des statistiques.

## 11. Pourquoi il y a un taux de donnees manquantes

Les donnees meteo historiques ne sont pas toujours completes.

Une station peut avoir :

- des jours sans mesure ;
- des temperatures manquantes ;
- des periodes interrompues.

Le projet accepte une station seulement si elle a au maximum 35 % de donnees manquantes sur la periode demandee.

Cela evite de produire des statistiques trop peu fiables.

## 12. Difference entre les deux graphiques

### Graphique des jours de gel par annee

Ce graphique repond a la question :

> Combien y a-t-il eu de jours de gel chaque annee ?

L'axe horizontal contient les annees :

```text
2013, 2014, 2015, ..., 2024
```

### Graphique de probabilite par jour de l'annee

Ce graphique repond a la question :

> Pour une date donnee, par exemple le 15 janvier, quelle proportion des annees observees ont eu du gel ce jour-la ?

L'axe horizontal contient les jours de l'annee :

```text
01-01, 01-02, 01-03, ..., 12-31
```

Ce ne sont pas des annees. Ce sont des jours au format mois-jour.

Exemple :

Si le 10 janvier a gele 6 fois entre 2013 et 2024, alors la probabilite est environ :

```text
6 / 12 = 50 %
```

## 13. Pourquoi le premier chargement peut etre lent

Le premier chargement d'un departement peut prendre du temps car l'application doit :

- telecharger un fichier Meteo-France public ;
- lire un fichier compresse ;
- filtrer les donnees de 2013 a 2024 ;
- mettre le resultat en cache.

Ensuite, les prochains lancements sont plus rapides car l'application reutilise le cache local.

## 14. Points importants pour une presentation orale

Vous pouvez expliquer le projet avec ces idees :

- Le projet est modulaire : chaque fichier a une responsabilite claire.
- L'application ne demande pas de cle API Meteo-France.
- Les donnees sont publiques.
- Seul le departement choisi est telecharge.
- La station n'est pas seulement la plus proche : elle doit aussi avoir assez de donnees.
- La formule de Haversine sert a calculer les distances GPS.
- Les tests automatises securisent les parties importantes du code.
- Le cache ameliore fortement la rapidite apres le premier chargement.

## 15. Glossaire simple

### Python

Langage de programmation utilise pour tout le projet.

### Streamlit

Bibliotheque Python qui permet de creer une application web rapidement.

### Pandas

Bibliotheque Python utilisee pour manipuler des tableaux de donnees.

### DataFrame

Tableau de donnees Pandas, comparable a une feuille Excel.

### API

Service web qui permet a un programme de demander des donnees a un autre service.

### CSV

Fichier texte qui contient des donnees en colonnes.

### Cache

Copie locale de donnees deja recuperees ou traitees, utilisee pour aller plus vite.

### Test unitaire

Petit test qui verifie qu'une fonction precise fonctionne comme prevu.

### Station meteo

Point de mesure Meteo-France qui fournit des observations meteorologiques.

### Temperature minimale

Temperature la plus basse mesuree pendant une journee.

### Jour de gel

Jour ou la temperature minimale est inferieure ou egale a 0 degC.
