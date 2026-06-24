from datetime import date

import pandas as pd
import pytest

from frost_days.frost_calculator import detect_min_temperature_column, prepare_frost_data


def test_detect_min_temperature_column_tn() -> None:
    frame = pd.DataFrame({"AAAAMMJJ": ["20240101"], "TN": [-1.2]})
    assert detect_min_temperature_column(frame) == "TN"


def test_prepare_frost_data_missing_rate() -> None:
    frame = pd.DataFrame({"AAAAMMJJ": ["20240101", "20240103"], "TMIN": [-1.0, 4.0]})
    prepared = prepare_frost_data(frame, date(2024, 1, 1), date(2024, 1, 3))

    assert prepared.data["is_frost"].tolist() == [True, False, False]
    assert prepared.missing_rate == pytest.approx(33.333, rel=1e-3)


def test_prepare_frost_data_raises_clear_error_without_temperature() -> None:
    frame = pd.DataFrame({"AAAAMMJJ": ["20240101"], "TX": [5.0]})
    with pytest.raises(ValueError, match="temperature minimale"):
        prepare_frost_data(frame, date(2024, 1, 1), date(2024, 1, 1))
