from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd

from frost_days.distance import haversine_km
from frost_days.frost_calculator import PreparedFrostData, prepare_frost_data


class DailyDataClient(Protocol):
    def get_daily_data(self, station_id: str, start: date, end: date) -> pd.DataFrame:
        ...


@dataclass(frozen=True)
class SelectedStation:
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    distance_km: float
    missing_rate: float
    prepared: PreparedFrostData


def normalize_stations(stations: pd.DataFrame) -> pd.DataFrame:
    if stations.empty:
        return stations
    mapping = {}
    for column in stations.columns:
        norm = str(column).strip().upper().replace("-", "_")
        if norm in {"ID", "IDSTATION", "ID_STATION", "NUM_POSTE", "POSTE"}:
            mapping[column] = "station_id"
        elif norm in {"NOM", "NOM_USUEL", "NOM_STATION", "LIBELLE", "NAME"}:
            mapping[column] = "station_name"
        elif norm in {"LAT", "LATITUDE"}:
            mapping[column] = "latitude"
        elif norm in {"LON", "LONGITUDE", "LNG"}:
            mapping[column] = "longitude"

    normalized = stations.rename(columns=mapping).copy()
    required = {"station_id", "latitude", "longitude"}
    missing = required - set(normalized.columns)
    if missing:
        raise ValueError("Colonnes station manquantes: " + ", ".join(sorted(missing)))

    if "station_name" not in normalized.columns:
        normalized["station_name"] = normalized["station_id"].astype(str)

    normalized["station_id"] = normalized["station_id"].astype(str).str.strip()
    normalized["latitude"] = pd.to_numeric(normalized["latitude"], errors="coerce")
    normalized["longitude"] = pd.to_numeric(normalized["longitude"], errors="coerce")
    return normalized.dropna(subset=["station_id", "latitude", "longitude"])


def sort_stations_by_distance(
    stations: pd.DataFrame,
    commune_latitude: float,
    commune_longitude: float,
) -> pd.DataFrame:
    normalized = normalize_stations(stations)
    normalized["distance_km"] = normalized.apply(
        lambda row: haversine_km(
            commune_latitude,
            commune_longitude,
            float(row["latitude"]),
            float(row["longitude"]),
        ),
        axis=1,
    )
    return normalized.sort_values("distance_km").reset_index(drop=True)


def select_first_valid_station(
    stations: pd.DataFrame,
    client: DailyDataClient,
    commune_latitude: float,
    commune_longitude: float,
    start: date,
    end: date,
    max_missing_rate: float = 35.0,
) -> SelectedStation:
    sorted_stations = sort_stations_by_distance(stations, commune_latitude, commune_longitude)
    errors: list[str] = []
    for _, station in sorted_stations.iterrows():
        station_id = str(station["station_id"])
        try:
            raw = client.get_daily_data(station_id, start, end)
            prepared = prepare_frost_data(raw, start, end)
        except Exception as exc:
            errors.append(f"{station_id}: {exc}")
            continue

        if prepared.missing_rate <= max_missing_rate:
            return SelectedStation(
                station_id=station_id,
                station_name=str(station["station_name"]),
                latitude=float(station["latitude"]),
                longitude=float(station["longitude"]),
                distance_km=float(station["distance_km"]),
                missing_rate=prepared.missing_rate,
                prepared=prepared,
            )

    details = "; ".join(errors[:5])
    raise ValueError(
        "Aucune station ne respecte le seuil de donnees manquantes de "
        f"{max_missing_rate:.0f} %. {details}"
    )
