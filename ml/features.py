"""
Feature engineering for the OmniWatch canonical crime dataframe.

All features are derived strictly from information available at (or before)
the time of the record, to avoid target leakage when the crime_group /
crime_type is later used as a classification target:

  - Temporal features (year/month/day/hour/etc.) are derived from the
    record's own timestamp - safe, since they describe *when* an offence
    happened, not an outcome of the classification.
  - "Historical crime frequency/density" is computed as the count of prior
    incidents at the same station up to (but excluding) each row's own
    timestamp, using an expanding/rolling count - never counting a row's own
    incident or future incidents.

Note: this dataset has day-level (not hour-level) timestamps, so hour-of-day
features are not available and are intentionally omitted rather than
fabricated.
"""
import numpy as np
import pandas as pd


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ts = df["timestamp"]
    df["year"] = ts.dt.year
    df["month"] = ts.dt.month
    df["day"] = ts.dt.day
    df["day_of_week"] = ts.dt.dayofweek  # 0=Mon
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    def season_of(month):
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "summer"
        if month in (6, 7, 8, 9):
            return "monsoon"
        return "post_monsoon"

    df["season"] = df["month"].apply(season_of)
    return df


def add_historical_frequency(df: pd.DataFrame, group_col: str = "station",
                              window_days: int = 90) -> pd.DataFrame:
    """
    For each row, count how many prior incidents occurred at the same
    `group_col` value in the preceding `window_days`, using only records
    strictly before that row's timestamp (no leakage).
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["_date"] = df["timestamp"].dt.floor("D")

    # Daily incident counts per group, reindexed to a full daily calendar
    # so the rolling window is well-defined across days without an incident.
    daily_counts = (
        df.groupby([group_col, "_date"], observed=True)
        .size()
        .rename("count")
        .reset_index()
    )

    rolling_frames = []
    for grp, g in daily_counts.groupby(group_col, observed=True):
        g = g.set_index("_date")[["count"]].sort_index()
        full_idx = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full_idx, fill_value=0)
        # rolling sum over the trailing window, shifted by 1 day so the
        # current day's own count is excluded (no leakage).
        rolling = g["count"].rolling(window=window_days, min_periods=1).sum().shift(1).fillna(0)
        rolling_frames.append(pd.DataFrame({
            group_col: grp, "_date": rolling.index, "historical_frequency": rolling.values,
        }))

    freq_table = pd.concat(rolling_frames, ignore_index=True)
    df = df.merge(freq_table, on=[group_col, "_date"], how="left")
    df["historical_frequency"] = df["historical_frequency"].fillna(0)
    df = df.drop(columns=["_date"])
    return df


def add_spatial_density(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple, transparent spatial density proxy: total historical incident
    count at the exact same station (all-time, computed once, not per-row
    leakage-sensitive since it is used only as a *station* attribute for
    risk scoring / hotspot summaries, not as a live prediction feature).
    """
    df = df.copy()
    station_counts = df.groupby("station", observed=True).size()
    df["station_total_incidents"] = df["station"].map(station_counts)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_temporal_features(df)
    df = add_historical_frequency(df, group_col="station", window_days=90)
    df = add_spatial_density(df)
    return df
