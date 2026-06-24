from __future__ import annotations

from dataclasses import dataclass

import requests

from frost_days.config import GEO_API_URL


@dataclass(frozen=True)
class Commune:
    name: str
    code: str
    department: str
    latitude: float
    longitude: float


def get_commune(
    name: str,
    department: str,
    session: requests.Session | None = None,
) -> Commune:
    client = session or requests.Session()
    response = client.get(
        GEO_API_URL,
        params={
            "nom": name,
            "codeDepartement": department,
            "fields": "nom,code,centre,departement",
            "format": "json",
            "geometry": "centre",
        },
        timeout=15,
    )
    response.raise_for_status()
    communes = response.json()
    if not communes:
        raise ValueError(f"Commune introuvable: {name} dans le departement {department}.")

    exact = [c for c in communes if c.get("nom", "").casefold() == name.casefold()]
    selected = exact[0] if exact else communes[0]
    coordinates = selected.get("centre", {}).get("coordinates")
    if not coordinates or len(coordinates) != 2:
        raise ValueError(f"Coordonnees absentes pour la commune {selected.get('nom', name)}.")

    return Commune(
        name=selected["nom"],
        code=selected["code"],
        department=selected.get("departement", {}).get("code", department),
        longitude=float(coordinates[0]),
        latitude=float(coordinates[1]),
    )


def list_communes(
    department: str,
    session: requests.Session | None = None,
) -> list[Commune]:
    client = session or requests.Session()
    response = client.get(
        GEO_API_URL,
        params={
            "codeDepartement": department,
            "fields": "nom,code,centre,departement",
            "format": "json",
            "geometry": "centre",
        },
        timeout=20,
    )
    response.raise_for_status()
    communes = [_commune_from_payload(item, department) for item in response.json()]
    return sorted(communes, key=lambda commune: commune.name.casefold())


def _commune_from_payload(payload: dict, fallback_department: str) -> Commune:
    coordinates = payload.get("centre", {}).get("coordinates")
    if not coordinates or len(coordinates) != 2:
        raise ValueError(f"Coordonnees absentes pour la commune {payload.get('nom', '')}.")

    return Commune(
        name=payload["nom"],
        code=payload["code"],
        department=payload.get("departement", {}).get("code", fallback_department),
        longitude=float(coordinates[0]),
        latitude=float(coordinates[1]),
    )
