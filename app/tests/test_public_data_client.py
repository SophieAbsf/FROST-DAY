from datetime import date
from io import BytesIO

import pandas as pd

from frost_days.public_data_client import (
    PublicMeteoFranceClient,
    build_department_file_candidates,
    read_daily_csv,
)


class FakeResponse:
    def __init__(self, content: bytes = b"", status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self, csv_bytes: bytes) -> None:
        self.csv_bytes = csv_bytes
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append((url, timeout))
        if "previous-1950" in url and "RR-T-Vent" in url:
            return FakeResponse(self.csv_bytes)
        return FakeResponse(status_code=404)


class NoCache:
    def get_pickle_dataframe(self, namespace: str, key: str):
        return None

    def set_pickle_dataframe(self, namespace: str, key: str, frame: pd.DataFrame) -> None:
        return None


def test_public_client_reads_stations_and_station_data() -> None:
    raw = pd.DataFrame(
        {
            "NUM_POSTE": [21001001, 21001001, 21002001],
            "NOM_USUEL": ["A", "A", "B"],
            "LAT": [47.3, 47.3, 47.4],
            "LON": [5.0, 5.0, 5.1],
            "AAAAMMJJ": [20240101, 20240102, 20240101],
            "TN": [-1.0, 2.0, -3.0],
        }
    )
    buffer = BytesIO()
    raw.to_csv(buffer, sep=";", index=False, compression="gzip")

    client = PublicMeteoFranceClient(session=FakeSession(buffer.getvalue()), cache=NoCache())

    stations = client.list_daily_stations("21", date(2024, 1, 1), date(2024, 1, 2))
    data = client.get_daily_data("21001001", date(2024, 1, 1), date(2024, 1, 1))

    assert len(stations) == 2
    assert stations.iloc[0]["station_id"] == 21001001
    assert data.iloc[0]["TN"] == -1.0


def test_read_daily_csv_filters_dates_and_columns() -> None:
    raw = pd.DataFrame(
        {
            "NUM_POSTE": [21001001, 21001001],
            "NOM_USUEL": ["A", "A"],
            "LAT": [47.3, 47.3],
            "LON": [5.0, 5.0],
            "AAAAMMJJ": [20120101, 20240101],
            "TN": [-5.0, -1.0],
            "UNUSED": ["ignored", "ignored"],
        }
    )
    buffer = BytesIO()
    raw.to_csv(buffer, sep=";", index=False, compression="gzip")

    frame = read_daily_csv(buffer.getvalue(), date(2013, 1, 1), date(2024, 12, 31))

    assert len(frame) == 1
    assert "UNUSED" not in frame.columns
    assert frame.iloc[0]["AAAAMMJJ"] == 20240101


def test_build_department_file_candidates_contains_public_urls() -> None:
    urls = [candidate.url for candidate in build_department_file_candidates("21")]
    assert any("Q_21_previous-1950" in url and "RR-T-Vent" in url for url in urls)
    assert any("Q_21_latest" in url and "RR-T-Vent" in url for url in urls)
