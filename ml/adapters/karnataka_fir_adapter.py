"""
Adapter: Karnataka Police FIR Details dataset -> OmniWatch canonical schema.

Source
------
"FIR DETAILS (KARNATAKA POLICE)" - a real, publicly shared Kaggle dataset of
1.67M First Information Report (FIR) records recorded by Karnataka Police
between 2016 and 2024, covering 41 districts.
https://www.kaggle.com/datasets/vanshangaria/fir-details-karnataka-police

This adapter performs ONLY column mapping / renaming / dtype coercion. It does
not drop or clean rows - that is the job of ml/cleaning.py, which runs after
this adapter and produces a documented cleaning summary.
"""
import pandas as pd
import numpy as np

RAW_FILENAME = "karnataka_fir_2016_2024.csv"

# Top-N crime groups kept as their own class for modelling; anything else is
# bucketed into "OTHER". Chosen from the actual observed value_counts() so
# that classes are not arbitrary and reflect real frequency in the data.
TOP_CRIME_GROUPS = [
    "MOTOR VEHICLE ACCIDENTS NON-FATAL",
    "THEFT",
    "CASES OF HURT",
    "MISSING PERSON",
    "KARNATAKA POLICE ACT 1963",
    "MOTOR VEHICLE ACCIDENTS FATAL",
    "CYBER CRIME",
    "CHEATING",
    "MOLESTATION",
    "PUBLIC SAFETY",
    "RIOTS",
    "BURGLARY - NIGHT",
    "NARCOTIC DRUGS & PSHYCOTROPIC SUBSTANCES",
    "KIDNAPPING AND ABDUCTION",
    "ATTEMPT TO MURDER",
]


def load_raw(raw_path: str) -> pd.DataFrame:
    """Load the raw CSV exactly as downloaded, no modification."""
    return pd.read_csv(raw_path, low_memory=False)


def to_canonical(raw: pd.DataFrame) -> pd.DataFrame:
    """Map raw Karnataka FIR columns onto the OmniWatch canonical schema."""
    df = raw.copy()

    # Normalize whitespace in categorical text columns (source data has
    # inconsistent leading/trailing spaces, e.g. " CYBER CRIME").
    for col in ["District_Name", "UnitName", "CrimeGroup_Name", "CrimeHead_Name",
                "Village_Area_Name", "Beat_Name", "Place of Offence"]:
        df[col] = df[col].astype(str).str.strip()

    # Reconstruct a real date from the separate year/month/day columns.
    # errors='coerce' -> invalid dates (e.g. day 31 in a 30-day month, or
    # placeholder day '00') become NaT, handled explicitly in cleaning.
    date_str = (
        df["FIR_YEAR"].astype(str) + "-" +
        df["FIR_MONTH"].astype(str).str.zfill(2) + "-" +
        df["FIR_Day"].astype(str).str.zfill(2)
    )
    timestamp = pd.to_datetime(date_str, format="%Y-%m-%d", errors="coerce")

    crime_group_raw = df["CrimeGroup_Name"]
    crime_group = np.where(
        crime_group_raw.isin(TOP_CRIME_GROUPS), crime_group_raw, "OTHER"
    )

    location = (
        df["Village_Area_Name"].replace("nan", "")
        + ", " + df["UnitName"]
        + ", " + df["District_Name"]
    ).str.strip(", ")

    canonical = pd.DataFrame({
        "crime_id": np.arange(len(df)).astype(str),
        "timestamp": timestamp,
        "crime_type": df["CrimeHead_Name"],
        "crime_group": crime_group,
        "latitude": pd.to_numeric(df["Latitude"], errors="coerce"),
        "longitude": pd.to_numeric(df["Longitude"], errors="coerce"),
        "location": location,
        "district": df["District_Name"],
        "station": df["UnitName"],
        "victim_count": pd.to_numeric(df["VICTIM COUNT"], errors="coerce"),
        "accused_count": pd.to_numeric(df["Accused Count"], errors="coerce"),
        "arrested_count": pd.to_numeric(df["Arrested Count\tNo."], errors="coerce"),
        "chargesheeted_count": pd.to_numeric(df["Accused_ChargeSheeted Count"], errors="coerce"),
        "conviction_count": pd.to_numeric(df["Conviction Count"], errors="coerce"),
    })
    canonical["has_coordinates"] = (
        canonical["latitude"].notna() & canonical["longitude"].notna()
    )
    return canonical
