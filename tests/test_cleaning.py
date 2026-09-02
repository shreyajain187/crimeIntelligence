import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from ml.cleaning import validate_and_clean, KARNATAKA_LAT_RANGE, KARNATAKA_LON_RANGE


def _make_canonical_df(rows):
    return pd.DataFrame(rows)


def test_duplicate_rows_are_removed():
    base = {
        "crime_id": "1", "timestamp": pd.Timestamp("2020-01-01"),
        "crime_type": "THEFT", "crime_group": "THEFT",
        "latitude": 13.0, "longitude": 77.5, "location": "x",
        "district": "Bengaluru City", "station": "PS1",
        "victim_count": 1, "accused_count": 1, "arrested_count": 0,
        "chargesheeted_count": 0, "conviction_count": 0,
    }
    dup = dict(base, crime_id="2")  # identical on all dup_cols, different id
    df = _make_canonical_df([base, dup])
    df["has_coordinates"] = True
    cleaned, summary = validate_and_clean(df)
    assert summary.duplicate_rows_removed == 1
    assert len(cleaned) == 1


def test_invalid_dates_are_dropped():
    rows = [
        {"crime_id": "1", "timestamp": pd.Timestamp("2020-01-01"), "crime_type": "THEFT",
         "crime_group": "THEFT", "latitude": np.nan, "longitude": np.nan, "location": "x",
         "district": "A", "station": "PS1", "victim_count": 0, "accused_count": 0,
         "arrested_count": 0, "chargesheeted_count": 0, "conviction_count": 0, "has_coordinates": False},
        {"crime_id": "2", "timestamp": pd.NaT, "crime_type": "THEFT",
         "crime_group": "THEFT", "latitude": np.nan, "longitude": np.nan, "location": "x",
         "district": "A", "station": "PS2", "victim_count": 0, "accused_count": 0,
         "arrested_count": 0, "chargesheeted_count": 0, "conviction_count": 0, "has_coordinates": False},
    ]
    df = _make_canonical_df(rows)
    cleaned, summary = validate_and_clean(df)
    assert summary.invalid_date_rows == 1
    assert len(cleaned) == 1


def test_out_of_bounds_coordinates_are_flagged_not_dropped():
    rows = [
        {"crime_id": "1", "timestamp": pd.Timestamp("2020-01-01"), "crime_type": "THEFT",
         "crime_group": "THEFT", "latitude": 131.4, "longitude": 777.7, "location": "x",
         "district": "A", "station": "PS1", "victim_count": 0, "accused_count": 0,
         "arrested_count": 0, "chargesheeted_count": 0, "conviction_count": 0, "has_coordinates": True},
    ]
    df = _make_canonical_df(rows)
    cleaned, summary = validate_and_clean(df)
    # row is NOT dropped (real FIR record still useful), only coords cleared
    assert len(cleaned) == 1
    assert cleaned.loc[0, "has_coordinates"] == False
    assert pd.isna(cleaned.loc[0, "latitude"])
    assert summary.invalid_coordinate_rows_flagged == 1


def test_valid_karnataka_coordinates_are_kept():
    lat, lon = 12.97, 77.59  # Bengaluru
    assert KARNATAKA_LAT_RANGE[0] <= lat <= KARNATAKA_LAT_RANGE[1]
    assert KARNATAKA_LON_RANGE[0] <= lon <= KARNATAKA_LON_RANGE[1]
    rows = [
        {"crime_id": "1", "timestamp": pd.Timestamp("2020-01-01"), "crime_type": "THEFT",
         "crime_group": "THEFT", "latitude": lat, "longitude": lon, "location": "x",
         "district": "Bengaluru City", "station": "PS1", "victim_count": 0, "accused_count": 0,
         "arrested_count": 0, "chargesheeted_count": 0, "conviction_count": 0, "has_coordinates": True},
    ]
    df = _make_canonical_df(rows)
    cleaned, summary = validate_and_clean(df)
    assert cleaned.loc[0, "has_coordinates"] == True
    assert summary.invalid_coordinate_rows_flagged == 0
