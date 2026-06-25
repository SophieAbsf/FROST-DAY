"""
diagnose_catalogue.py
=====================

Trouve le bon seuil CATALOGUE_MAX_MISSING pour que ton catalogue contienne
les memes stations que celui du prof.

Idee : pour chaque station de l'echantillon du prof (stations_df_short.csv),
on regarde son taux de jours manquants DANS TES donnees. Le seuil doit etre
au moins egal au pire de ces taux. On affiche aussi combien de stations ton
catalogue contiendrait a differents seuils.

Usage :
    python diagnose_catalogue.py --samples data\\validation_3
"""

from __future__ import annotations
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_validation as gv
from frost_validation import SOURCE_CANDIDATES, _pick


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default="data/validation_3")
    args = ap.parse_args()

    prof_path = os.path.join(args.samples, "stations_df_short.csv")
    prof = pd.read_csv(prof_path, dtype={"station_id": str})
    prof_ids = set(prof["station_id"])
    print(f"Echantillon prof : {len(prof_ids)} stations")

    print("Lecture des donnees meteo (cache si dispo)...")
    meteo = gv.load_meteo_files()
    sid = _pick(meteo, SOURCE_CANDIDATES["station_id"])
    tn = _pick(meteo, SOURCE_CANDIDATES["tmin"])
    ndays = (pd.Timestamp(gv.END) - pd.Timestamp(gv.START)).days + 1

    valid = meteo.groupby(sid)[tn].apply(lambda s: s.notna().sum())
    miss = (1 - valid / ndays)
    miss.index = miss.index.astype("Int64").astype(str).str.zfill(8)  # id 8 car.

    # Taux de manquant des stations de l'echantillon prof, dans tes donnees
    prof_rates = miss[miss.index.isin(prof_ids)]
    absentes = prof_ids - set(miss.index)
    print(f"\nStations du prof presentes dans tes fichiers : {len(prof_rates)}/{len(prof_ids)}")
    if absentes:
        print(f"  (!) {len(absentes)} station(s) du prof ABSENTE(S) de tes fichiers : "
              f"{sorted(absentes)[:8]}{'...' if len(absentes) > 8 else ''}")
        print("      -> si ces stations existent, un departement manque encore.")
    if len(prof_rates):
        print(f"  Taux de manquant de ces stations : min {prof_rates.min():.1%} | "
              f"median {prof_rates.median():.1%} | max {prof_rates.max():.1%}")
        seuil = float(prof_rates.max())
        print(f"\n  >>> Seuil minimal pour TOUTES les inclure : {seuil:.1%}")

    print("\nNombre de stations de TON catalogue selon le seuil :")
    for thr in [0.65, 0.70, 0.80, 0.90, 0.95, 0.99, 1.0]:
        n = int((miss <= thr).sum())
        inclus = int(prof_rates[prof_rates <= thr].count()) if len(prof_rates) else 0
        print(f"  seuil {thr:>4.0%} -> {n:5d} stations au total | "
              f"{inclus}/{len(prof_rates)} stations du prof incluses")

    print("\nConseil : choisis le plus petit seuil qui inclut toutes les stations "
          "du prof, puis mets cette valeur dans CATALOGUE_MAX_MISSING.")
    print("Si le total reste loin de ~3000, demande au prof la regle exacte du catalogue.")


if __name__ == "__main__":
    main()
