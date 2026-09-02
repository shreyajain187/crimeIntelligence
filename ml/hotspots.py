"""
Geographic crime-hotspot detection via DBSCAN.

Uses cuML DBSCAN when RAPIDS/GPU is available, otherwise falls back to
sklearn DBSCAN automatically. Distance is treated properly for lat/lon by
converting to radians and using the haversine metric with an eps expressed
in real-world kilometers (converted to radians for sklearn's haversine
metric), rather than naively clustering on raw degrees.

Only records with real, validated coordinates (has_coordinates=True) are
used - cluster -1 is noise per DBSCAN convention.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from ml.compute_backend import detect_backend

EARTH_RADIUS_KM = 6371.0088


@dataclass
class HotspotResult:
    labels: np.ndarray
    backend_used: str
    eps_km: float
    min_samples: int


def _run_cpu_dbscan(coords_rad: np.ndarray, eps_km: float, min_samples: int) -> np.ndarray:
    eps_rad = eps_km / EARTH_RADIUS_KM
    model = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine", algorithm="ball_tree")
    return model.fit_predict(coords_rad)


def _run_gpu_dbscan(coords_deg: np.ndarray, eps_km: float, min_samples: int) -> np.ndarray:
    import cudf
    from cuml.cluster import DBSCAN as cuDBSCAN
    # cuML DBSCAN (as of common RAPIDS releases) does not expose a haversine
    # metric, so we approximate small-scale geographic distance with a local
    # planar projection (good enough at district/city scale, ~<200km spans)
    # scaled so that Euclidean eps in degrees roughly matches eps_km.
    lat0 = coords_deg[:, 0].mean()
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * np.cos(np.radians(lat0))
    x = coords_deg[:, 1] * km_per_deg_lon
    y = coords_deg[:, 0] * km_per_deg_lat
    gdf = cudf.DataFrame({"x": x, "y": y})
    model = cuDBSCAN(eps=eps_km, min_samples=min_samples)
    labels = model.fit_predict(gdf)
    return labels.to_numpy()


def detect_hotspots(df: pd.DataFrame, eps_km: float = 0.75, min_samples: int = 15) -> HotspotResult:
    """
    df must contain 'latitude', 'longitude', and 'has_coordinates' columns.
    Only rows with has_coordinates=True are clustered; all other rows are not
    represented in the returned label array (caller is responsible for
    aligning by index on the filtered subset).
    """
    geo = df[df["has_coordinates"]]
    if len(geo) == 0:
        return HotspotResult(labels=np.array([]), backend_used="none", eps_km=eps_km, min_samples=min_samples)

    backend = detect_backend()
    coords_deg = geo[["latitude", "longitude"]].to_numpy()

    if backend.active_backend == "gpu":
        try:
            labels = _run_gpu_dbscan(coords_deg, eps_km, min_samples)
            return HotspotResult(labels=labels, backend_used="gpu", eps_km=eps_km, min_samples=min_samples)
        except Exception:
            pass  # fall through to CPU

    coords_rad = np.radians(coords_deg)
    labels = _run_cpu_dbscan(coords_rad, eps_km, min_samples)
    return HotspotResult(labels=labels, backend_used="cpu", eps_km=eps_km, min_samples=min_samples)


def summarize_hotspots(df: pd.DataFrame, result: HotspotResult) -> pd.DataFrame:
    """
    Build a hotspot summary table: cluster_id, centroid lat/lon, incident
    count, density (incidents / km^2 approx via convex hull area proxy kept
    simple as incidents per cluster bounding-box area), dominant crime type.
    """
    geo = df[df["has_coordinates"]].reset_index(drop=True).copy()
    geo["cluster"] = result.labels

    rows = []
    for cluster_id, g in geo.groupby("cluster"):
        if cluster_id == -1:
            continue  # noise, not a hotspot
        lat_span = max(g["latitude"].max() - g["latitude"].min(), 1e-4)
        lon_span = max(g["longitude"].max() - g["longitude"].min(), 1e-4)
        area_km2 = (lat_span * 111.32) * (lon_span * 111.32 * np.cos(np.radians(g["latitude"].mean())))
        area_km2 = max(area_km2, 0.01)
        dominant = g["crime_type"].mode().iloc[0] if not g["crime_type"].mode().empty else "Unknown"
        rows.append({
            "cluster_id": int(cluster_id),
            "centroid_lat": float(g["latitude"].mean()),
            "centroid_lon": float(g["longitude"].mean()),
            "incident_count": int(len(g)),
            "density_per_km2": float(len(g) / area_km2),
            "dominant_crime_type": dominant,
            "district": g["district"].mode().iloc[0] if not g["district"].mode().empty else "Unknown",
        })
    summary = pd.DataFrame(rows).sort_values("incident_count", ascending=False).reset_index(drop=True)
    return summary
