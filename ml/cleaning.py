"""
Validation + cleaning for the OmniWatch canonical crime dataframe.

Produces a CleaningSummary documenting exactly what was removed and why, so
nothing is silently dropped. Coordinates are validated against a real
geographic bounding box for Karnataka (with a small buffer) rather than
fabricated or imputed - rows with invalid/missing coordinates keep
has_coordinates=False and are simply excluded from point-level spatial
analysis (hotspots, crime map), never given made-up locations.
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

# Karnataka's real bounding box, with a small buffer for coastal/border
# districts. Points outside this box are data-entry errors (the raw file
# contains a handful of rows with e.g. latitude=131, longitude=777).
KARNATAKA_LAT_RANGE = (10.5, 19.5)
KARNATAKA_LON_RANGE = (73.5, 79.0)

MIN_VALID_YEAR = 2016
MAX_VALID_YEAR = 2024


@dataclass
class CleaningSummary:
    original_rows: int = 0
    duplicate_rows_removed: int = 0
    invalid_date_rows: int = 0
    out_of_range_year_rows: int = 0
    invalid_coordinate_rows_flagged: int = 0
    rows_removed_total: int = 0
    remaining_rows: int = 0
    missing_values_by_column: dict = field(default_factory=dict)
    date_range: tuple = None
    crime_categories: int = 0
    districts: int = 0
    stations: int = 0
    rows_with_coordinates: int = 0

    def to_dict(self):
        d = self.__dict__.copy()
        if d.get("date_range"):
            d["date_range"] = [str(x) for x in d["date_range"]]
        return d


def validate_and_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningSummary]:
    summary = CleaningSummary()
    summary.original_rows = len(df)
    df = df.copy()

    # 1. Duplicate records (identical across all substantive fields).
    dup_cols = ["timestamp", "crime_type", "district", "station",
                "latitude", "longitude", "victim_count", "accused_count"]
    before = len(df)
    df = df.drop_duplicates(subset=dup_cols, keep="first")
    summary.duplicate_rows_removed = before - len(df)

    # 2. Invalid / unparseable dates (adapter already set these to NaT).
    invalid_dates = df["timestamp"].isna()
    summary.invalid_date_rows = int(invalid_dates.sum())
    df = df[~invalid_dates]

    # 3. Dates outside the dataset's documented coverage window (2016-2024).
    #    A handful of rows have corrupted year values (e.g. typos).
    out_of_range = ~df["timestamp"].dt.year.between(MIN_VALID_YEAR, MAX_VALID_YEAR)
    summary.out_of_range_year_rows = int(out_of_range.sum())
    df = df[~out_of_range]

    # 4. Invalid coordinates: outside Karnataka's real bounding box.
    #    We do NOT drop these rows - we only mark them as not having usable
    #    coordinates, since the FIR record itself (district/station/date/type)
    #    is still real and useful for non-spatial analysis.
    lat_ok = df["latitude"].between(*KARNATAKA_LAT_RANGE)
    lon_ok = df["longitude"].between(*KARNATAKA_LON_RANGE)
    coord_present = df["latitude"].notna() & df["longitude"].notna()
    invalid_coords = coord_present & ~(lat_ok & lon_ok)
    summary.invalid_coordinate_rows_flagged = int(invalid_coords.sum())
    df.loc[invalid_coords, ["latitude", "longitude"]] = np.nan
    df["has_coordinates"] = df["latitude"].notna() & df["longitude"].notna()

    # 5. Invalid crime categories (blank / literal "nan" strings).
    bad_category = df["crime_type"].isna() | (df["crime_type"].str.lower() == "nan") | (df["crime_type"].str.strip() == "")
    before = len(df)
    df = df[~bad_category]
    invalid_category_rows = before - len(df)

    # 6. Data type conversions / feature-ready fields.
    df["district"] = df["district"].astype("category")
    df["station"] = df["station"].astype("category")
    df["crime_group"] = df["crime_group"].astype("category")

    summary.rows_removed_total = (
        summary.duplicate_rows_removed
        + summary.invalid_date_rows
        + summary.out_of_range_year_rows
        + invalid_category_rows
    )
    summary.remaining_rows = len(df)
    summary.missing_values_by_column = df.isna().sum().to_dict()
    summary.date_range = (df["timestamp"].min(), df["timestamp"].max())
    summary.crime_categories = df["crime_type"].nunique()
    summary.districts = df["district"].nunique()
    summary.stations = df["station"].nunique()
    summary.rows_with_coordinates = int(df["has_coordinates"].sum())

    return df.reset_index(drop=True), summary
