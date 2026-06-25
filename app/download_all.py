
from __future__ import annotations
import sys
from pathlib import Path

import requests

BASE = "https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/BASE/QUOT"
OUT_DIR = Path("data/meteo")

# Departements metropolitains (+ Corse 2A/2B).
DEPARTMENTS = [f"{i:02d}" for i in range(1, 96) if i != 20] + ["2A", "2B"]

# Annee de fin du fichier "previous" (on essaie ces valeurs dans l'ordre).
END_YEAR_CANDIDATES = [2024, 2025, 2023]


def url_for(dep: str, end_year: int) -> str:
    return f"{BASE}/Q_{dep}_previous-1950-{end_year}_RR-T-Vent.csv.gz"


def download_one(dep: str, session: requests.Session) -> bool:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for end_year in END_YEAR_CANDIDATES:
        url = url_for(dep, end_year)
        dest = OUT_DIR / f"Q_{dep}_previous-1950-{end_year}_RR-T-Vent.csv.gz"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  [={dep}] deja present ({dest.name})")
            return True
        try:
            with session.get(url, stream=True, timeout=180) as r:
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            mb = dest.stat().st_size / 1e6
            print(f"  [OK {dep}] {dest.name} ({mb:.1f} Mo)")
            return True
        except Exception as exc:
            print(f"  [! {dep}] echec sur {url} : {exc}")
    print(f"  [X {dep}] aucun fichier trouve")
    return False


def main():
    session = requests.Session()
    ok = bad = 0
    for dep in DEPARTMENTS:
        print(f"Departement {dep} ...")
        if download_one(dep, session):
            ok += 1
        else:
            bad += 1
    print(f"\nTermine : {ok} departements OK, {bad} en echec. Dossier : {OUT_DIR}/")
    if bad:
        print("Relance le script pour reessayer les departements manquants.")


if __name__ == "__main__":
    sys.exit(main())
