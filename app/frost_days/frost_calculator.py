from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

import pandas as pd

MIN_TEMP_CANDIDATES = {
    "TN",
    "TMIN",
    "T_MIN",
    "TEMP_MIN",
    "TEMPERATURE_MIN",
    "TEMPERATURE_MINIMALE",
    "MIN_TEMP",
    "MINT",
}
DATE_CANDIDATES = {"DATE", "JOUR", "AAAAMMJJ", "DATE_OBSERVATION"}


@dataclass(frozen=True)
class PreparedFrostData:
    data: pd.DataFrame
    min_temperature_column: str
    missing_rate: float


def prepare_frost_data(raw: pd.DataFrame, start: date, end: date) -> PreparedFrostData:
    if raw.empty:
        frame = _empty_period(start, end)
        return PreparedFrostData(frame, "temperature_min", 100.0)

    date_column = detect_date_column(raw)
    temp_column = detect_min_temperature_column(raw)

    frame = raw.copy()
    frame["date"] = parse_date_series(frame[date_column])
    frame["temperature_min"] = pd.to_numeric(frame[temp_column], errors="coerce")
    frame = frame.dropna(subset=["date"])
    frame = frame[(frame["date"].dt.date >= start) & (frame["date"].dt.date <= end)]
    frame = frame[["date", "temperature_min"]].drop_duplicates(subset=["date"], keep="first")

    all_days = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    frame = all_days.merge(frame, on="date", how="left")
    frame["is_frost"] = frame["temperature_min"] <= 0

    missing_rate = float(frame["temperature_min"].isna().mean() * 100) if len(frame) else 100.0
    return PreparedFrostData(frame, temp_column, missing_rate)


def detect_min_temperature_column(frame: pd.DataFrame) -> str:
    normalized = {_normalize_column(column): column for column in frame.columns}
    for candidate in MIN_TEMP_CANDIDATES:
        normalized_candidate = _normalize_column(candidate)
        if normalized_candidate in normalized:
            return normalized[normalized_candidate]

    for column in frame.columns:
        norm = _normalize_column(column)
        if re.search(r"(^|_)T(MIN|N)($|_)", norm) or ("MIN" in norm and "TEMP" in norm):
            return column

    raise ValueError(
        "Colonne de temperature minimale introuvable. Colonnes disponibles: "
        + ", ".join(map(str, frame.columns))
    )


def detect_date_column(frame: pd.DataFrame) -> str:
    normalized = {_normalize_column(column): column for column in frame.columns}
    for candidate in DATE_CANDIDATES:
        normalized_candidate = _normalize_column(candidate)
        if normalized_candidate in normalized:
            return normalized[normalized_candidate]
    raise ValueError(
        "Colonne de date introuvable. Colonnes disponibles: " + ", ".join(map(str, frame.columns))
    )


def parse_date_series(series: pd.Series) -> pd.Series:
    as_text = series.astype(str).str.strip()
    compact = as_text.str.fullmatch(r"\d{8}")
    parsed = pd.to_datetime(as_text, errors="coerce")
    if compact.any():
        parsed.loc[compact] = pd.to_datetime(as_text.loc[compact], format="%Y%m%d", errors="coerce")
    return parsed


def _normalize_column(column: object) -> str:
    text = unicodedata.normalize("NFKD", str(column))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text.upper()


def _empty_period(start: date, end: date) -> pd.DataFrame:
    frame = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    frame["temperature_min"] = pd.NA
    frame["is_frost"] = False
    return frame
