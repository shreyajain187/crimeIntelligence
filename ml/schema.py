"""
Canonical crime-record schema for OmniWatch.

Every dataset adapter (see ml/adapters/) must produce a pandas DataFrame with
(at minimum) these columns, so the rest of the pipeline (cleaning, feature
engineering, hotspot detection, prediction, forecasting) is never coupled to
one specific source dataset's column names.

Required columns
-----------------
crime_id     : str   - unique identifier for the record
timestamp    : datetime64[ns] - when the offence occurred (best available
               resolution; day-level for this dataset)
crime_type   : str   - fine-grained category as given by the source
crime_group  : str   - coarser bucket used for modelling (top-N + "Other")
latitude     : float - NaN if unknown (never fabricated)
longitude    : float - NaN if unknown (never fabricated)
location     : str   - human-readable place text (station/area/district)
district     : str   - administrative district
station      : str   - police station / reporting unit

Optional columns (kept when available, used opportunistically)
----------------------------------------------------------------
victim_count, accused_count, arrested_count, chargesheeted_count,
conviction_count, has_coordinates (bool)
"""

REQUIRED_COLUMNS = [
    "crime_id",
    "timestamp",
    "crime_type",
    "crime_group",
    "latitude",
    "longitude",
    "location",
    "district",
    "station",
]

OPTIONAL_COLUMNS = [
    "victim_count",
    "accused_count",
    "arrested_count",
    "chargesheeted_count",
    "conviction_count",
    "has_coordinates",
]

ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


def validate_canonical(df):
    """Raise if a dataframe is missing required canonical columns."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Canonical dataframe missing required columns: {missing}")
    return True
