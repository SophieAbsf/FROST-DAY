from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd
import requests
import requests_cache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from frost_days.cache import LocalCache

LOGGER = logging.getLogger(__name__)
DATA_GOUV_QUOT_BASE = (
    "https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/BASE/QUOT"
)
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
USEFUL_COLUMNS = {
    "NUM_POSTE",
    "NOM_USUEL",
    "LAT",
    "LON",
    "AAAAMMJJ",
    "TN",
    "TMIN",
    "T_MIN",
    "TEMP_MIN",
    "TEMPERATURE_MIN",
    "TEMPERATURE_MINIMALE",
    "MIN_TEMP",
}
READ_CHUNK_SIZE = 200_000


class PublicDataDownloadError(RuntimeError):
    pass


class RetryableDownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class DepartmentFile:
    url: str
    start_year: int
    end_year: int

    def overlaps(self, start: date | None, end: date | None) -> bool:
        if start is None or end is None:
            return True
        return self.start_year <= end.year and self.end_year >= start.year


class PublicMeteoFranceClient:
    """Read public departmental daily files, without Meteo-France API key."""

    def __init__(
        self,
        session: requests.Session | None = None,
        cache: LocalCache | None = None,
        base_url: str = DATA_GOUV_QUOT_BASE,
    ) -> None:
        self.session = session or requests_cache.CachedSession(
            cache_name=".cache/http_cache",
            backend="sqlite",
            expire_after=86400,
        )
        self.cache = cache or LocalCache()
        self.base_url = base_url.rstrip("/")
        self._department_frames: dict[str, pd.DataFrame] = {}

    def list_daily_stations(
        self,
        department: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        frame = self._load_department(department, start, end)
        columns = [column for column in ["NUM_POSTE", "NOM_USUEL", "LAT", "LON"] if column in frame]
        if len(columns) < 3:
            raise ValueError(
                "Impossible d'extraire les stations depuis le fichier departemental. "
                f"Colonnes disponibles: {', '.join(frame.columns)}"
            )
        stations = frame[columns].drop_duplicates(subset=["NUM_POSTE"]).copy()
        return stations.rename(
            columns={
                "NUM_POSTE": "station_id",
                "NOM_USUEL": "station_name",
                "LAT": "latitude",
                "LON": "longitude",
            }
        )

    def get_daily_data(self, station_id: str, start: date, end: date) -> pd.DataFrame:
        department = str(station_id).zfill(8)[:2]
        frame = self._load_department(department, start, end)
        data = frame[frame["NUM_POSTE"].astype(str).str.zfill(8) == str(station_id).zfill(8)].copy()
        data["date"] = pd.to_datetime(data["AAAAMMJJ"].astype(str), format="%Y%m%d", errors="coerce")
        data = data[(data["date"].dt.date >= start) & (data["date"].dt.date <= end)]
        return data

    def _load_department(
        self,
        department: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        department = str(department).zfill(2)
        memory_key = f"{department}:{start}:{end}"
        if memory_key in self._department_frames:
            return self._department_frames[memory_key]

        cache_key = f"public-department:{department}:{start}:{end}"
        cached = self.cache.get_pickle_dataframe("public_department_v2", cache_key)
        if cached is not None:
            self._department_frames[memory_key] = cached
            return cached

        frames: list[pd.DataFrame] = []
        errors: list[str] = []
        for file in build_department_file_candidates(department, self.base_url):
            if not file.overlaps(start, end):
                continue
            try:
                frames.append(self._download_file(file.url, start, end))
                LOGGER.info("Fichier public charge: %s", file.url)
            except FileNotFoundError:
                continue
            except Exception as exc:
                errors.append(f"{file.url}: {exc}")

        if not frames:
            raise PublicDataDownloadError(
                "Aucun fichier public Meteo-France trouve pour le departement "
                f"{department}. Details: {'; '.join(errors[:3])}"
            )

        combined = pd.concat(frames, ignore_index=True).drop_duplicates()
        self.cache.set_pickle_dataframe("public_department_v2", cache_key, combined)
        self._department_frames[memory_key] = combined
        return combined

    @retry(
        retry=retry_if_exception_type(RetryableDownloadError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _download_file(
        self,
        url: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        response = self.session.get(url, timeout=120)
        if response.status_code == 404:
            raise FileNotFoundError(url)
        if response.status_code in RETRY_STATUS_CODES:
            raise RetryableDownloadError(f"Reponse temporaire {response.status_code} pour {url}")
        response.raise_for_status()
        return read_daily_csv(response.content, start, end)


def read_daily_csv(content: bytes, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    start_int = int(start.strftime("%Y%m%d")) if start else None
    end_int = int(end.strftime("%Y%m%d")) if end else None
    chunks: list[pd.DataFrame] = []

    reader = pd.read_csv(
        io.BytesIO(content),
        sep=";",
        compression="gzip",
        low_memory=False,
        usecols=lambda column: column in USEFUL_COLUMNS,
        chunksize=READ_CHUNK_SIZE,
    )
    for chunk in reader:
        if "AAAAMMJJ" in chunk.columns and start_int is not None and end_int is not None:
            day = pd.to_numeric(chunk["AAAAMMJJ"], errors="coerce")
            chunk = chunk[(day >= start_int) & (day <= end_int)]
        if not chunk.empty:
            chunks.append(chunk)

    if not chunks:
        return pd.DataFrame(columns=sorted(USEFUL_COLUMNS))
    return pd.concat(chunks, ignore_index=True)


def build_department_file_candidates(
    department: str,
    base_url: str = DATA_GOUV_QUOT_BASE,
) -> list[DepartmentFile]:
    department = str(department).zfill(2)
    base_url = base_url.rstrip("/")
    current_year = date.today().year
    previous_end_candidates = [current_year - 2, current_year - 1, current_year - 3]
    latest_period_candidates = [
        (current_year - 1, current_year),
        (current_year - 2, current_year),
        (current_year - 1, current_year - 1),
    ]
    candidates: list[DepartmentFile] = []

    for end_year in previous_end_candidates:
        candidates.append(
            DepartmentFile(
                url=f"{base_url}/Q_{department}_previous-1950-{end_year}_RR-T-Vent.csv.gz",
                start_year=1950,
                end_year=end_year,
            )
        )

    for start_year, end_year in latest_period_candidates:
        candidates.append(
            DepartmentFile(
                url=f"{base_url}/Q_{department}_latest-{start_year}-{end_year}_RR-T-Vent.csv.gz",
                start_year=start_year,
                end_year=end_year,
            )
        )

    seen: set[str] = set()
    unique = []
    for candidate in candidates:
        if candidate.url not in seen:
            unique.append(candidate)
            seen.add(candidate.url)
    return unique
