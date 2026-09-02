import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from ml.features import add_temporal_features, add_historical_frequency, add_spatial_density


def _base_df():
    return pd.DataFrame({
        "timestamp": pd.to_datetime(["2020-01-06", "2020-06-15", "2020-12-25"]),  # Mon, Mon, Fri
        "station": ["PS1", "PS1", "PS2"],
        "crime_type": ["THEFT", "THEFT", "RIOTS"],
    })


def test_temporal_features_are_correct():
    df = add_temporal_features(_base_df())
    assert df.loc[0, "year"] == 2020
    assert df.loc[0, "day_of_week"] == 0  # Monday
    assert df.loc[0, "is_weekend"] == 0
    assert df.loc[0, "season"] == "winter"
    assert df.loc[1, "season"] == "monsoon"


def test_historical_frequency_has_no_leakage():
    """
    A station's historical_frequency on a given day must never include that
    day's own incidents, nor any future incidents.
    """
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02"]),
        "station": ["PS1", "PS1", "PS1"],
    })
    out = add_historical_frequency(df, group_col="station", window_days=90)
    # both records on day 1 must see zero prior history
    day1 = out[out["timestamp"] == pd.Timestamp("2020-01-01")]
    assert (day1["historical_frequency"] == 0).all()
    # the record on day 2 must see the 2 incidents from day 1, not itself
    day2 = out[out["timestamp"] == pd.Timestamp("2020-01-02")]
    assert (day2["historical_frequency"] == 2).all()


def test_spatial_density_counts_all_time_station_total():
    df = add_spatial_density(_base_df())
    assert df.loc[df["station"] == "PS1", "station_total_incidents"].iloc[0] == 2
    assert df.loc[df["station"] == "PS2", "station_total_incidents"].iloc[0] == 1
