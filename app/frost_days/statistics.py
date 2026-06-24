from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FrostStatistics:
    total_frost_days: int
    average_frost_days_per_year: float
    yearly: pd.DataFrame
    daily: pd.DataFrame


def compute_statistics(frame: pd.DataFrame) -> FrostStatistics:
    if frame.empty:
        return FrostStatistics(0, 0.0, pd.DataFrame(), pd.DataFrame())

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data[~((data["date"].dt.month == 2) & (data["date"].dt.day == 29))]
    data["is_frost"] = data["temperature_min"] <= 0
    data["year"] = data["date"].dt.year
    data["month_day"] = data["date"].dt.strftime("%m-%d")

    total = int(data["is_frost"].sum())
    yearly = (
        data.groupby("year", as_index=False)["is_frost"]
        .sum()
        .rename(columns={"is_frost": "frost_days"})
    )
    average = float(yearly["frost_days"].mean()) if not yearly.empty else 0.0
    daily = (
        data.groupby("month_day", as_index=False)
        .agg(frost_days=("is_frost", "sum"), observations=("temperature_min", "count"))
        .sort_values("month_day")
    )
    daily["frost_probability_pct"] = daily.apply(
        lambda row: (row["frost_days"] / row["observations"] * 100)
        if row["observations"]
        else 0.0,
        axis=1,
    )
    return FrostStatistics(total, average, yearly, daily)
