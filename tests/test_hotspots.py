import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from ml.hotspots import detect_hotspots, summarize_hotspots


def test_dbscan_finds_a_dense_cluster_and_marks_noise():
    # 20 points tightly packed (a real hotspot), plus 3 far-flung isolated points (noise)
    rng = np.random.default_rng(42)
    cluster_lat = 13.0 + rng.normal(0, 0.0005, 20)
    cluster_lon = 77.5 + rng.normal(0, 0.0005, 20)
    noise_lat = [11.0, 15.0, 18.0]
    noise_lon = [75.0, 78.0, 74.0]

    lat = np.concatenate([cluster_lat, noise_lat])
    lon = np.concatenate([cluster_lon, noise_lon])
    df = pd.DataFrame({
        "latitude": lat, "longitude": lon,
        "has_coordinates": True,
        "crime_type": ["THEFT"] * len(lat),
        "district": ["Bengaluru City"] * len(lat),
    })

    result = detect_hotspots(df, eps_km=0.5, min_samples=10)
    assert result.backend_used == "cpu"
    # the 20 tight points should form exactly one cluster
    cluster_labels = result.labels[:20]
    assert len(set(cluster_labels)) == 1
    assert cluster_labels[0] != -1
    # the 3 isolated points should be noise
    assert all(result.labels[20:] == -1)


def test_hotspot_summary_excludes_noise_cluster():
    df = pd.DataFrame({
        "latitude": [13.0, 13.0001, 13.0002] + [20.0],
        "longitude": [77.5, 77.5001, 77.5002] + [70.0],
        "has_coordinates": True,
        "crime_type": ["THEFT", "THEFT", "BURGLARY - NIGHT", "RIOTS"],
        "district": ["Bengaluru City"] * 4,
    })
    result = detect_hotspots(df, eps_km=0.5, min_samples=2)
    summary = summarize_hotspots(df, result)
    assert -1 not in summary["cluster_id"].values
    assert summary["incident_count"].sum() <= len(df)
