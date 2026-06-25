"""
verifier_validation.py
=======================

Compare les fichiers "_complete.csv" que TU as generes (dossier validation/)
aux echantillons fournis par le professeur (short/half).

Principe : les echantillons du prof sont des EXTRAITS de la version complete.
On verifie donc que :
  - fichiers meteo par commune : sur la plage de dates de l'echantillon,
    ta version complete est identique a l'echantillon ;
  - stations_df : toutes les stations de l'echantillon sont dans ta version ;
  - city_df : sur les communes de l'echantillon, le mapping est identique.

Usage :
    python verifier_validation.py --complete validation --samples chemin/vers/echantillons
"""

from __future__ import annotations
import argparse
import glob
import os
import re
import pandas as pd


def find_complete(complete_dir: str, key: str) -> str | None:
    """Trouve le fichier _complete correspondant a une cle (ex 'Paris_75')."""
    hits = glob.glob(os.path.join(complete_dir, f"{key}*_complete.csv"))
    return hits[0] if hits else None


def norm_name(path: str) -> str:
    """Normalise un nom de fichier d'echantillon vers une cle 'Commune_dep'."""
    base = os.path.basename(path)
    base = base.replace("#U00e8", "e").replace("#U00f4", "o")  # accents zip
    return re.sub(r"_(short|half|weather_data_half|complete)\.csv$", "", base)


def check_weather(sample_path: str, complete_path: str) -> bool:
    s = pd.read_csv(sample_path)
    c = pd.read_csv(complete_path)
    lo, hi = s["date"].min(), s["date"].max()
    c = c[(c["date"] >= lo) & (c["date"] <= hi)].reset_index(drop=True)
    if list(s.columns) != list(c.columns):
        print(f"   [X] colonnes differentes"); return False
    if len(s) != len(c):
        print(f"   [X] nb lignes sur la plage {lo}->{hi} : prof {len(s)}, toi {len(c)}")
        return False
    diff_cols = [col for col in s.columns
                 if not ((s[col] == c[col]) | (s[col].isna() & c[col].isna())).all()]
    if diff_cols:
        print(f"   [X] colonnes qui different : {diff_cols}"); return False
    print(f"   [OK] identique sur {lo} -> {hi} ({len(s)} lignes)")
    return True


def check_stations(sample_path: str, complete_path: str) -> bool:
    s = pd.read_csv(sample_path, dtype=str)
    c = pd.read_csv(complete_path, dtype=str)
    merged = s.merge(c, on="station_id", how="left", suffixes=("_prof", "_toi"))
    missing = merged["station_name_toi"].isna().sum()
    badname = ((merged["station_name_prof"] != merged["station_name_toi"])
               & merged["station_name_toi"].notna()).sum()
    if missing or badname:
        print(f"   [X] {missing} station(s) absente(s), {badname} nom(s) divergent(s)")
        return False
    print(f"   [OK] les {len(s)} stations de l'echantillon sont presentes et nommees pareil")
    return True


def check_city(sample_path: str, complete_path: str) -> bool:
    s = pd.read_csv(sample_path, dtype=str)
    c = pd.read_csv(complete_path, dtype=str)
    key = ["insee_code"]
    m = s.merge(c, on=key, how="left", suffixes=("_prof", "_toi"))
    bad = m[m["closest_station_num_poste_prof"] != m["closest_station_num_poste_toi"]]
    if len(bad):
        print(f"   [X] {len(bad)}/{len(s)} communes avec une station differente. Ex :")
        print(bad[["name_prof", "closest_station_num_poste_prof",
                   "closest_station_num_poste_toi"]].head(5).to_string(index=False))
        return False
    print(f"   [OK] mapping identique sur les {len(s)} communes de l'echantillon")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--complete", default="validation",
                    help="dossier contenant tes fichiers *_complete.csv")
    ap.add_argument("--samples", default=".",
                    help="dossier contenant les echantillons du prof")
    args = ap.parse_args()

    samples = glob.glob(os.path.join(args.samples, "*.csv"))
    all_ok = True
    for sp in sorted(samples):
        base = os.path.basename(sp)
        print(f"\n>>> {base}")
        if base.startswith("stations_df"):
            cp = find_complete(args.complete, "stations_df")
            ok = check_stations(sp, cp) if cp else print("   [X] stations_df_complete.csv manquant") or False
        elif base.startswith("city_df"):
            cp = find_complete(args.complete, "city_df")
            ok = check_city(sp, cp) if cp else print("   [X] city_df_complete.csv manquant") or False
        else:
            key = norm_name(sp)
            cp = find_complete(args.complete, key)
            ok = check_weather(sp, cp) if cp else (print(f"   [X] {key}*_complete.csv manquant") or False)
        all_ok &= bool(ok)

    print("\n==============================")
    print("RESULTAT GLOBAL :", "TOUT CONCORDE" if all_ok else "DES ECARTS A CORRIGER")


if __name__ == "__main__":
    main()
