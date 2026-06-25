
from __future__ import annotations
import pandas as pd

# Noms de colonnes possibles dans les fichiers source Meteo-France.
SOURCE_CANDIDATES = {
    "station_id":   ["NUM_POSTE", "num_poste"],
    "station_name": ["NOM_USUEL", "nom_usuel", "NOM"],
    "latitude":     ["LAT", "lat", "LATITUDE"],
    "longitude":    ["LON", "lon", "LONGITUDE"],
    "alti":         ["ALTI", "alti", "ALTITUDE"],
    "date":         ["AAAAMMJJ", "aaaammjj", "DATE"],
    "tmin":         ["TN", "tn", "TMIN", "T_MIN", "TEMP_MIN"],
}

# Colonnes finales, dans l'ordre, pour chaque type de sortie.
WEATHER_COLUMNS = ["station_id", "station_name", "latitude", "longitude",
                   "alti", "date", "tmin", "frost_day", "year", "month", "day"]
STATION_COLUMNS = ["station_id", "station_name", "date", "tmin",
                   "frost_day", "year", "month", "day"]


def build_station_catalogue(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Construit le catalogue de stations attendu par stations_df (v3).

    Sortie : colonnes [station_id, station_name], station_id en chaine de
    8 caracteres avec zeros de tete (ex "01028001"), sans doublon, trie.
    """
    sid = _pick(df_raw, SOURCE_CANDIDATES["station_id"])
    name = _pick(df_raw, SOURCE_CANDIDATES["station_name"])
    cat = pd.DataFrame({
        "station_id": pd.to_numeric(df_raw[sid], errors="coerce")
                        .astype("Int64").astype(str).str.zfill(8),
        "station_name": df_raw[name].astype(str),
    })
    return (cat.drop_duplicates()
               .sort_values("station_id")
               .reset_index(drop=True))


def _pick(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retourne le premier nom de colonne present dans df, sinon None."""
    for name in candidates:
        if name in df.columns:
            return name
    return None


def build_export(df_raw: pd.DataFrame, with_coords: bool = True) -> pd.DataFrame:
    """Transforme un DataFrame brut Meteo-France au format de validation.

    df_raw : donnees d'UNE station (lignes quotidiennes) deja chargees.
    with_coords : True -> format weather_data (avec lat/lon/alti),
                  False -> format stations_df (sans coordonnees).
    """
    out = pd.DataFrame()

    sid = _pick(df_raw, SOURCE_CANDIDATES["station_id"])
    out["station_id"] = pd.to_numeric(df_raw[sid], errors="coerce").astype("Int64")

    name = _pick(df_raw, SOURCE_CANDIDATES["station_name"])
    out["station_name"] = df_raw[name].astype(str)

    if with_coords:
        for col in ("latitude", "longitude", "alti"):
            src = _pick(df_raw, SOURCE_CANDIDATES[col])
            out[col] = pd.to_numeric(df_raw[src], errors="coerce") if src else pd.NA

    # date : AAAAMMJJ -> AAAA-MM-JJ
    dcol = _pick(df_raw, SOURCE_CANDIDATES["date"])
    dates = pd.to_datetime(df_raw[dcol].astype(str).str.replace("-", "", regex=False),
                           format="%Y%m%d", errors="coerce")
    out["date"] = dates.dt.strftime("%Y-%m-%d")

    # tmin + frost_day
    tcol = _pick(df_raw, SOURCE_CANDIDATES["tmin"])
    if tcol is None:
        raise ValueError("Aucune colonne de temperature minimale trouvee "
                         f"(cherche parmi {SOURCE_CANDIDATES['tmin']}).")
    out["tmin"] = pd.to_numeric(df_raw[tcol], errors="coerce")
    out["frost_day"] = (out["tmin"] <= 0).fillna(False)

    out["year"] = dates.dt.year
    out["month"] = dates.dt.month
    out["day"] = dates.dt.day

    cols = WEATHER_COLUMNS if with_coords else STATION_COLUMNS
    return out[cols].reset_index(drop=True)


def compare_to_reference(my_df: pd.DataFrame, reference_csv: str,
                         period: tuple[str, str] | None = None) -> bool:
    """Compare ta sortie a un fichier de reference. Affiche un rapport.

    period : optionnel ("AAAA-MM-JJ", "AAAA-MM-JJ") pour restreindre ta sortie
             a la meme plage que la reference avant comparaison.
    Retourne True si tout concorde.
    """
    ref = pd.read_csv(reference_csv)
    mine = my_df.copy()

    if period:
        start, end = period
        mine = mine[(mine["date"] >= start) & (mine["date"] <= end)]

    print(f"\n=== Comparaison avec {reference_csv} ===")
    ok = True

    # 1) Colonnes
    if list(mine.columns) != list(ref.columns):
        ok = False
        print("  [X] Colonnes differentes")
        print("      attendu :", list(ref.columns))
        print("      obtenu  :", list(mine.columns))
        common = [c for c in ref.columns if c in mine.columns]
        mine, ref = mine[common], ref[common]
    else:
        print("  [OK] Colonnes identiques")

    # 2) Nombre de lignes
    if len(mine) != len(ref):
        ok = False
        print(f"  [X] Nb de lignes : attendu {len(ref)}, obtenu {len(mine)}")
    else:
        print(f"  [OK] Nb de lignes identique ({len(ref)})")

    # 3) Comparaison ligne a ligne sur la plage commune (par date)
    n = min(len(mine), len(ref))
    m, r = mine.head(n).reset_index(drop=True), ref.head(n).reset_index(drop=True)
    for col in r.columns:
        a, b = m[col], r[col]
        if a.dtype.kind == "f" or b.dtype.kind == "f":
            diff = ~((a.round(3) == b.round(3)) | (a.isna() & b.isna()))
        else:
            diff = ~((a == b) | (a.isna() & b.isna()))
        nbad = int(diff.sum())
        if nbad:
            ok = False
            print(f"  [X] Colonne '{col}' : {nbad} valeur(s) differente(s). Ex :")
            ex = pd.DataFrame({"obtenu": a[diff], "attendu": b[diff]}).head(3)
            print(ex.to_string())
        else:
            print(f"  [OK] Colonne '{col}' identique")

    print("  >>> RESULTAT :", "CONFORME" if ok else "NON CONFORME")
    return ok


if __name__ == "__main__":
    
    import glob
    rename = {"station_id": "NUM_POSTE", "station_name": "NOM_USUEL",
              "latitude": "LAT", "longitude": "LON", "alti": "ALTI",
              "date": "AAAAMMJJ", "tmin": "TN"}

    # Fichiers weather (_half ou _short) et ancien stations_df (donnees quotidiennes)
    weather = [p for p in glob.glob("*weather_data_half.csv") + glob.glob("*_short.csv")
               if not p.startswith(("city_df", "stations_df"))]
    for path in sorted(weather):
        ref = pd.read_csv(path)
        if list(ref.columns) == ["station_id", "station_name"]:
            continue  # c'est un catalogue, traite plus bas
        with_coords = "latitude" in ref.columns
        raw = ref.rename(columns=rename)
        raw["AAAAMMJJ"] = raw["AAAAMMJJ"].astype(str).str.replace("-", "", regex=False)
        mine = build_export(raw, with_coords=with_coords)
        compare_to_reference(mine, path)

    for path in glob.glob("stations_df_short.csv"):
        ref = pd.read_csv(path, dtype={"station_id": str})
        raw = ref.rename(columns={"station_id": "NUM_POSTE",
                                  "station_name": "NOM_USUEL"})
        raw["NUM_POSTE"] = raw["NUM_POSTE"].astype(int)
        mine = build_station_catalogue(raw)
        print("\n=== Catalogue stations_df_short ===")
        print("  >>> RESULTAT :",
              "CONFORME" if mine.astype(str).equals(ref.astype(str)) else "NON CONFORME")
