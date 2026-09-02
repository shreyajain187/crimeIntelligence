#!/usr/bin/env python3
"""
Load processed data + ML artifacts into the SQLite database.

    python scripts/load_database.py

Reads:
  data/processed/crimes_features.parquet
  data/processed/hotspots.csv
  data/processed/hotspot_labels.npy
  data/processed/risk_scores.csv
  data/processed/cleaning_summary.json

Writes: data/processed/omniwatch.db (SQLite)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from backend.app.db.database import engine, Base, SessionLocal
from backend.app.db import models

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"


def main():
    print("Creating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print("Loading processed crimes...")
    df = pd.read_parquet(PROCESSED_DIR / "crimes_features.parquet")

    # attach cluster_id where we have hotspot labels for the geocoded subset
    labels_path = PROCESSED_DIR / "hotspot_labels.npy"
    df["cluster_id"] = None
    if labels_path.exists():
        labels = np.load(labels_path)
        geo_mask = df["has_coordinates"]
        assert geo_mask.sum() == len(labels), "hotspot labels length mismatch with geocoded rows"
        df.loc[geo_mask, "cluster_id"] = labels

    session = SessionLocal()
    try:
        print(f"Inserting {len(df)} crime rows (this may take a minute)...")
        records = df[[
            "crime_id", "timestamp", "crime_type", "crime_group",
            "latitude", "longitude", "has_coordinates", "location",
            "district", "station", "victim_count", "cluster_id",
        ]].copy()
        records["district"] = records["district"].astype(str)
        records["station"] = records["station"].astype(str)
        records["crime_group"] = records["crime_group"].astype(str)
        records["victim_count"] = records["victim_count"].fillna(0).astype(int)
        records["cluster_id"] = records["cluster_id"].apply(lambda x: int(x) if pd.notna(x) else None)

        # Bulk insert via to_sql for speed (far faster than ORM row-by-row
        # for 1M+ rows); ORM model is still used for reads via the API.
        records.to_sql("crimes", con=engine, if_exists="append", index=False, chunksize=20000)
        print("Crimes inserted.")

        hotspots_path = PROCESSED_DIR / "hotspots.csv"
        if hotspots_path.exists():
            hotspots = pd.read_csv(hotspots_path)
            hotspots.to_sql("hotspots", con=engine, if_exists="append", index=False)
            print(f"Inserted {len(hotspots)} hotspots.")

        risk_path = PROCESSED_DIR / "risk_scores.csv"
        if risk_path.exists():
            risk = pd.read_csv(risk_path)
            risk.to_sql("risk_scores", con=engine, if_exists="append", index=False)
            print(f"Inserted {len(risk)} district risk scores.")

        summary_path = PROCESSED_DIR / "cleaning_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)
            session.add(models.DatasetMetadata(key="cleaning_summary", value=json.dumps(summary)))
            session.commit()
            print("Inserted dataset metadata.")
    finally:
        session.close()

    print("Database load complete.")


if __name__ == "__main__":
    main()
