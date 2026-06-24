import pandas as pd

from frost_days.statistics import compute_statistics


def test_compute_statistics_excludes_february_29() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-28", "2024-02-29", "2024-03-01"]),
            "temperature_min": [-1.0, -2.0, 2.0],
        }
    )

    stats = compute_statistics(frame)

    assert stats.total_frost_days == 1
    assert "02-29" not in set(stats.daily["month_day"])
    assert stats.average_frost_days_per_year == 1.0
