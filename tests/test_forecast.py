import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import pytest
from ml.forecast import train_and_forecast, _build_daily_series


def _synthetic_df(n_days=400):
    dates = pd.date_range("2022-01-01", periods=n_days, freq="D")
    rng = np.random.default_rng(0)
    # repeat each date a variable number of times to emulate incident rows
    rows = []
    for d in dates:
        n = max(0, int(20 + 5 * np.sin(d.dayofyear / 365 * 2 * np.pi) + rng.normal(0, 2)))
        for _ in range(n):
            rows.append({"timestamp": d, "district": "TestDistrict", "crime_group": "THEFT"})
    return pd.DataFrame(rows)


def test_forecast_shapes_and_non_negative():
    df = _synthetic_df()
    result = train_and_forecast(df, horizon_days=14)
    assert len(result.forecast) == 14
    assert (result.forecast["forecast"] >= 0).all()
    assert (result.forecast["lower"] >= 0).all()
    assert (result.forecast["upper"] >= result.forecast["forecast"]).all()
    assert result.mae >= 0
    assert result.rmse >= 0


def test_forecast_raises_on_insufficient_history():
    df = _synthetic_df(n_days=30)  # far too short
    with pytest.raises(ValueError):
        train_and_forecast(df, horizon_days=14)


def test_build_daily_series_fills_gaps_with_zero():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2022-01-01", "2022-01-03"]),  # gap on Jan 2
        "district": ["A", "A"], "crime_group": ["THEFT", "THEFT"],
    })
    series = _build_daily_series(df)
    assert series.loc[pd.Timestamp("2022-01-02")] == 0
