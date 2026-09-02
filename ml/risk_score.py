"""
Transparent risk score (0-100) per district and per district-station.

Methodology (documented, not a black box):
  risk_score = round(100 * weighted_sum(normalized_components))

Components (each min-max normalized across all districts in the current
dataset, so the score is always relative to the observed real range, never
to an arbitrary fixed scale):
  1. incident_density   (40%) - total incidents / number of stations in the
                                 district, i.e. average station-level load
  2. recent_activity     (30%) - incidents in the most recent 90 days of the
                                 dataset vs the district's own historical
                                 90-day average (captures a real surge/decline)
  3. hotspot_membership   (15%) - share of the district's geocoded incidents
                                 that fall inside a DBSCAN hotspot cluster
  4. trend                (15%) - linear trend slope of monthly incident
                                 counts over the full observed period,
                                 normalized across districts

This score is a descriptive summary of historical patterns, not a
probability or forecast, and is presented to the user with that caveat.

Interpretation:
  0-30   Low
  31-60  Moderate
  61-80  High
  81-100 Very High
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd


def _minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi - lo < 1e-9:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)


def compute_district_risk_scores(df: pd.DataFrame, hotspot_cluster_labels: np.ndarray | None = None,
                                  hotspot_index: pd.Index | None = None) -> pd.DataFrame:
    df = df.copy()
    max_date = df["timestamp"].max()
    recent_cutoff = max_date - pd.Timedelta(days=90)

    grouped = df.groupby("district", observed=True)

    density = grouped.size() / grouped["station"].nunique().replace(0, 1)

    recent = df[df["timestamp"] > recent_cutoff].groupby("district", observed=True).size()
    total_days = (max_date - df["timestamp"].min()).days or 1
    n_periods = max(total_days / 90, 1)
    historical_avg_90d = grouped.size() / n_periods
    recent_activity = (recent.reindex(density.index, fill_value=0) / historical_avg_90d.replace(0, 1))

    if hotspot_cluster_labels is not None and hotspot_index is not None:
        geo = df.loc[hotspot_index].copy()
        geo["cluster"] = hotspot_cluster_labels
        geo["in_hotspot"] = geo["cluster"] != -1
        hotspot_share = geo.groupby("district", observed=True)["in_hotspot"].mean()
    else:
        hotspot_share = pd.Series(0.0, index=density.index)
    hotspot_share = hotspot_share.reindex(density.index, fill_value=0.0)

    monthly = df.groupby([df["district"], df["timestamp"].dt.to_period("M")], observed=True).size()
    trend_slope = {}
    for district, series in monthly.groupby(level=0, observed=True):
        y = series.values.astype(float)
        if len(y) < 3:
            trend_slope[district] = 0.0
            continue
        x = np.arange(len(y))
        slope = np.polyfit(x, y, 1)[0]
        trend_slope[district] = slope
    trend = pd.Series(trend_slope).reindex(density.index, fill_value=0.0)

    components = pd.DataFrame({
        "incident_density": _minmax(density),
        "recent_activity": _minmax(recent_activity.fillna(0)),
        "hotspot_membership": _minmax(hotspot_share),
        "trend": _minmax(trend),
    })

    weights = {"incident_density": 0.40, "recent_activity": 0.30,
               "hotspot_membership": 0.15, "trend": 0.15}
    score = sum(components[c] * w for c, w in weights.items()) * 100

    result = pd.DataFrame({
        "district": density.index,
        "risk_score": score.round(1).values,
        "incident_density_raw": density.values,
        "recent_activity_ratio": recent_activity.fillna(0).values,
        "hotspot_share": hotspot_share.values,
        "monthly_trend_slope": trend.values,
    }).sort_values("risk_score", ascending=False).reset_index(drop=True)

    result["risk_tier"] = pd.cut(
        result["risk_score"], bins=[-0.1, 30, 60, 80, 100],
        labels=["Low", "Moderate", "High", "Very High"],
    )
    return result
