"""
generate_validation.py
=======================

Genere les 8 fichiers "_complete.csv" demandes par le professeur, a placer
dans un dossier "validation/" a la racine du projet.

Fichiers produits
------------------
  validation/stations_df_complete.csv          (~3000 stations : id, nom)
  validation/city_df_complete.csv              (~35000 communes -> station la + proche)
  validation/Paris_75_complete.csv             ) donnees quotidiennes 2013-2024
  validation/Marseille_13_complete.csv         ) de la station la plus proche
  validation/Digne-les-Bains_04_complete.csv   ) de la commune, avec frost_day
  validation/Espinchal_63_complete.csv         )
  validation/Montfalcon_38_complete.csv        )
  validation/Asnieres-sur-Saone_01_complete.csv)

Ce script est un traitement par LOT (batch), separe de l'application Streamlit.
Il a besoin, en local :
  1. des fichiers quotidiens Meteo-France RR-T-Vent decompresses (un par dept),
  2. du fichier de reference des communes (data.gouv "communes-et-villes...").
Il NE telecharge rien : adapte les chemins dans la section CONFIG ci-dessous.

Logique (verifiee sur les fichiers de validation fournis par le prof) :
  - station la plus proche = plus proche a vol d'oiseau (Haversine / KDTree),
    calculee sur TOUTES les stations, pas seulement celles du departement ;
  - meme station pour city_df et pour le fichier meteo de la commune ;
  - frost_day = (tmin <= 0), valeur manquante -> False ;
  - periode : 2013-01-01 a 2024-12-31 (12 ans) ;
  - station_id : entier dans les fichiers meteo, chaine 8 car. ("01028001")
    dans stations_df_complete et dans city_df (colonne closest_station_num_poste).
"""

from __future__ import annotations
import glob
import os
import numpy as np
import pandas as pd

from frost_validation import (build_export, build_station_catalogue,
                              SOURCE_CANDIDATES, _pick)

# ============================ CONFIG (a adapter) ============================
# Dossier contenant les CSV(.gz) quotidiens Meteo-France, un fichier par dept.
# C'est le dossier rempli par download_all.py.
METEO_DIR = "data/meteo"
# Fichier de reference des communes (communes-france-2026.csv).
COMMUNES_CSV = "data/communes/communes-france-2026.csv"
# Periode complete.
START, END = "2013-01-01", "2024-12-31"
# Dossier de sortie.
OUT_DIR = "validation"

# Filtre du catalogue stations_df : on garde les stations ayant au plus ce
# taux de jours manquants (TN absent) sur la periode. ATTENTION : ce seuil
# N'EST PAS la regle des 35 % (celle-ci sert au choix de station d'une
# commune). Sur le dept 01, le prof garde des stations jusqu'a ~56 % manquant
# et rejette a partir de ~77 %. Valeur a CONFIRMER avec l'enseignant.
CATALOGUE_MAX_MISSING = 0.65

# Communes a exporter en detail. Cle = (nom officiel exact, dep) ; valeur =
# prefixe du fichier (le prof utilise les noms accentues dans ses fichiers).
TARGET_COMMUNES = {
    ("Paris", "75"):                "Paris_75",
    ("Marseille", "13"):            "Marseille_13",
    ("Digne-les-Bains", "04"):      "Digne-les-Bains_04",
    ("Espinchal", "63"):            "Espinchal_63",
    ("Montfalcon", "38"):           "Montfalcon_38",
    ("Asnières-sur-Saône", "01"):   "Asnières-sur-Saône_01",
}

# Communes sans coordonnees GPS dans le fichier de reference (cf. sujet PDF).
MISSING_CITIES_LAT_LON = {
    "Marseille": [43.295, 5.372], "Paris": [48.866, 2.333],
    "Culey": [48.755, 5.266], "Les Hauts-Talican": [49.3436, 2.0193],
    "Lyon": [45.75, 4.85], "Bihorel": [49.4542, 1.1162],
    "Saint-Lucien": [48.6480, 1.6229], "L'Oie": [46.7982, -1.1302],
    "Sainte-Florence": [46.7965, -1.1520],
}


# ============================ Outils geographiques ============================
# Recherche du plus proche voisin SANS scipy (non present dans requirements.txt).
# On projette (lat, lon) sur la sphere unite : le plus grand produit scalaire
# correspond au plus petit angle, donc a la station la plus proche a vol
# d'oiseau -- exactement comme la formule de Haversine de frost_days/distance.py.
def _unit_vectors(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(la) * np.cos(lo),
                            np.cos(la) * np.sin(lo),
                            np.sin(la)])


def nearest_station(communes: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque commune, trouve la station la plus proche (toutes stations).
    communes : colonnes lat, lon. stations : colonnes id, name, lat, lon.
    Calcul par blocs pour limiter la memoire (35000 x 3000 distances).
    """
    S = _unit_vectors(stations["lat"].values, stations["lon"].values)
    ids = stations["id"].values
    names = stations["name"].values
    n = len(communes)
    best = np.empty(n, dtype=int)
    clat = communes["lat"].values
    clon = communes["lon"].values
    step = 2000
    for i in range(0, n, step):
        C = _unit_vectors(clat[i:i + step], clon[i:i + step])
        best[i:i + step] = (C @ S.T).argmax(axis=1)   # plus grand cos = plus proche
    out = communes.reset_index(drop=True).copy()
    out["closest_station_name"] = names[best]
    out["closest_station_num_poste"] = ids[best]              # chaine 8 car.
    out["station_dept"] = pd.Series(ids[best]).str[:2].values
    return out


# ============================ Lecture Meteo-France ============================
# Cache local du DataFrame meteo concatene : la lecture des .gz ne se fait
# qu'une fois. Supprime ce fichier si tu changes la periode ou les donnees.
METEO_CACHE = "data/_meteo_cache.pkl"


def load_meteo_files() -> pd.DataFrame:
    """Charge tous les fichiers quotidiens, garde la periode et les colonnes
    utiles. Renvoie un DataFrame brut (colonnes Meteo-France d'origine).
    Gere les fichiers compresses .csv.gz (separateur ';'). Met en cache."""
    if os.path.exists(METEO_CACHE):
        print(f"      (cache trouve : {METEO_CACHE})")
        return pd.read_pickle(METEO_CACHE)

    files = sorted(glob.glob(os.path.join(METEO_DIR, "*RR-T-Vent*.csv*")))
    if not files:
        raise FileNotFoundError(
            f"Aucun fichier Meteo-France dans {METEO_DIR!r}. "
            "Telecharge-les avec download_all.py ou ajuste METEO_DIR.")
    frames = []
    usecols = ["NUM_POSTE", "NOM_USUEL", "LAT", "LON", "ALTI", "AAAAMMJJ", "TN"]
    start = int(START.replace("-", "")); end = int(END.replace("-", ""))
    for f in files:
        comp = "gzip" if f.endswith(".gz") else "infer"
        for chunk in pd.read_csv(f, sep=";", compression=comp,
                                 usecols=lambda c: c in usecols,
                                 chunksize=500_000, low_memory=False):
            chunk = chunk[(chunk["AAAAMMJJ"] >= start) & (chunk["AAAAMMJJ"] <= end)]
            if len(chunk):
                frames.append(chunk)
    combined = pd.concat(frames, ignore_index=True)
    try:
        combined.to_pickle(METEO_CACHE)
    except Exception as exc:
        print(f"      (cache non ecrit : {exc})")
    return combined


def build_catalogue_filtered(meteo: pd.DataFrame) -> pd.DataFrame:
    """Catalogue des stations ayant assez de donnees (cf. CATALOGUE_MAX_MISSING)."""
    sid = _pick(meteo, SOURCE_CANDIDATES["station_id"])
    tn = _pick(meteo, SOURCE_CANDIDATES["tmin"])
    ndays = (pd.Timestamp(END) - pd.Timestamp(START)).days + 1
    valid = meteo.groupby(sid)[tn].apply(lambda s: s.notna().sum())
    keep_ids = valid[(1 - valid / ndays) <= CATALOGUE_MAX_MISSING].index
    return build_station_catalogue(meteo[meteo[sid].isin(keep_ids)])


def station_table(meteo: pd.DataFrame) -> pd.DataFrame:
    """Table des stations (id chaine 8 car., name, lat, lon) sans doublon."""
    cols = {k: _pick(meteo, SOURCE_CANDIDATES[k])
            for k in ("station_id", "station_name", "latitude", "longitude")}
    st = meteo[[cols["station_id"], cols["station_name"],
                cols["latitude"], cols["longitude"]]].copy()
    st.columns = ["id", "name", "lat", "lon"]
    st["id"] = pd.to_numeric(st["id"], errors="coerce").astype("Int64").astype(str).str.zfill(8)
    st = st.dropna(subset=["lat", "lon"]).drop_duplicates("id").reset_index(drop=True)
    return st


# ============================ Lecture des communes ============================
# Correspondance colonnes du fichier communes-france-2026.csv -> noms attendus.
# (latitude_centre/longitude_centre = coordonnees du centre, celles qu'utilise
# le prof ; elles correspondent exactement a son city_df.)
COMMUNES_COLUMN_MAP = {
    "code_insee": "insee_code",
    "nom_standard": "name",
    "dep_code": "dep_code",
    "dep_nom": "dep_name",
    "latitude_centre": "lat",
    "longitude_centre": "lon",
}


def load_communes() -> pd.DataFrame:
    """Charge communes-france-2026.csv -> insee_code, name, dep_code, dep_name,
    lat, lon. Garde uniquement les vraies communes (typecom == 'COM') et
    complete les rares coordonnees manquantes."""
    try:
        df = pd.read_csv(COMMUNES_CSV, dtype=str, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(COMMUNES_CSV, dtype=str, encoding="latin-1")
    if "typecom" in df.columns:                       # exclut arrondissements (ARM)
        df = df[df["typecom"] == "COM"]
    df = df.rename(columns=COMMUNES_COLUMN_MAP)
    df = df[list(COMMUNES_COLUMN_MAP.values())].copy()
    for c in ("lat", "lon"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Le prof a utilise ces coordonnees exactes pour ces villes (elles etaient
    # absentes de SON fichier). On les force pour reproduire son entree, meme
    # si communes-france-2026 fournit une valeur legerement differente.
    for name, (la, lo) in MISSING_CITIES_LAT_LON.items():
        m = df["name"] == name
        df.loc[m, ["lat", "lon"]] = [la, lo]
    return df.dropna(subset=["lat", "lon"]).reset_index(drop=True)


# ============================ Generation ============================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("1/4 Lecture des fichiers Meteo-France...")
    meteo = load_meteo_files()

    print("2/4 stations_df_complete.csv ...")
    catalogue = build_catalogue_filtered(meteo)                # filtre couverture
    catalogue.to_csv(os.path.join(OUT_DIR, "stations_df_complete.csv"), index=False)
    print(f"      {len(catalogue)} stations (seuil manquant <= {CATALOGUE_MAX_MISSING:.0%})")

    print("3/4 city_df_complete.csv ...")
    stations = station_table(meteo)
    stations = stations[stations["id"].isin(set(catalogue["station_id"]))]  # memes stations que le catalogue
    communes = load_communes()
    city = nearest_station(communes, stations)
    city = city[["insee_code", "name", "dep_code", "dep_name", "lat", "lon",
                 "closest_station_name", "closest_station_num_poste", "station_dept"]]
    city.to_csv(os.path.join(OUT_DIR, "city_df_complete.csv"), index=False)
    print(f"      {len(city)} communes")

    print("4/4 fichiers meteo par commune ...")
    sid_col = _pick(meteo, SOURCE_CANDIDATES["station_id"])
    meteo["_sid8"] = pd.to_numeric(meteo[sid_col], errors="coerce").astype("Int64").astype(str).str.zfill(8)
    for (name, dep), fname in TARGET_COMMUNES.items():
        row = city[(city["name"] == name) & (city["dep_code"] == dep)]
        if row.empty:
            print(f"      [!] commune introuvable : {name} ({dep})")
            continue
        sid = row["closest_station_num_poste"].iloc[0]
        sub = meteo[meteo["_sid8"] == sid]
        export = build_export(sub, with_coords=True).sort_values("date").reset_index(drop=True)
        export.to_csv(os.path.join(OUT_DIR, f"{fname}_complete.csv"), index=False)
        print(f"      {fname}_complete.csv : {len(export)} lignes (station {sid})")

    print("\nTermine. Verifie avec :  python verifier_validation.py")


if __name__ == "__main__":
    main()
