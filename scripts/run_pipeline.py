#!/usr/bin/env python3
"""
OmniWatch one-command pipeline.

    python scripts/run_pipeline.py [--force]

Stages: validate -> clean -> feature engineer -> hotspot detection ->
        classifier training -> SHAP -> forecasting -> risk scoring ->
        save all artifacts.

Idempotent: each stage is skipped if its output artifact already exists,
unless --force is passed. This avoids re-training the (expensive) XGBoost
classifier every time the pipeline is re-run for a later stage.
"""
import argparse
import json
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np

from ml.adapters.karnataka_fir_adapter import load_raw, to_canonical
from ml.cleaning import validate_and_clean
from ml.features import engineer_features
from ml.hotspots import detect_hotspots, summarize_hotspots
from ml.classifier import train_classifier
from ml.explain import global_feature_importance
from ml.forecast import train_and_forecast
from ml.risk_score import compute_district_risk_scores
from ml.compute_backend import detect_backend

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "karnataka_fir_2016_2024.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
ARTIFACTS_DIR = ROOT / "artifacts" / "models"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def stage_clean_and_feature_engineer(force: bool) -> pd.DataFrame:
    out_path = PROCESSED_DIR / "crimes_features.parquet"
    summary_path = PROCESSED_DIR / "cleaning_summary.json"
    if out_path.exists() and not force:
        log(f"[skip] {out_path.name} already exists")
        return pd.read_parquet(out_path)

    log("Loading raw dataset...")
    raw = load_raw(str(RAW_PATH))
    log(f"Raw shape: {raw.shape}")

    log("Adapting to canonical schema...")
    canonical = to_canonical(raw)
    del raw

    log("Validating and cleaning...")
    clean, summary = validate_and_clean(canonical)
    del canonical
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary.to_dict(), f, indent=2, default=str)
    log(f"Cleaning summary: {summary.original_rows} -> {summary.remaining_rows} rows")

    log("Engineering features...")
    features = engineer_features(clean)
    features.to_parquet(out_path)
    log(f"Saved processed features: {features.shape} -> {out_path}")
    return features


def stage_hotspots(df: pd.DataFrame, force: bool):
    out_path = PROCESSED_DIR / "hotspots.csv"
    labels_path = PROCESSED_DIR / "hotspot_labels.npy"
    if out_path.exists() and not force:
        log(f"[skip] {out_path.name} already exists")
        return pd.read_csv(out_path), np.load(labels_path)

    log("Running DBSCAN hotspot detection...")
    result = detect_hotspots(df, eps_km=0.75, min_samples=15)
    log(f"Hotspot backend: {result.backend_used}, clusters found: {len(set(result.labels)) - (1 if -1 in result.labels else 0)}")
    summary = summarize_hotspots(df, result)
    summary.to_csv(out_path, index=False)
    np.save(labels_path, result.labels)
    log(f"Saved {len(summary)} hotspots -> {out_path}")
    return summary, result.labels


def stage_classifier(df: pd.DataFrame, force: bool):
    model_path = ARTIFACTS_DIR / "crime_classifier.pkl"
    metrics_path = ARTIFACTS_DIR / "classifier_metrics.json"
    if model_path.exists() and not force:
        log(f"[skip] {model_path.name} already exists")
        with open(model_path, "rb") as f:
            trained = pickle.load(f)
        return trained

    log("Training XGBoost classifier (temporal split)... this can take several minutes on CPU-only single-core hardware")
    trained = train_classifier(df)
    log(f"Classifier trained. accuracy={trained.metrics['accuracy']:.4f} "
        f"f1_macro={trained.metrics['f1_macro']:.4f} f1_weighted={trained.metrics['f1_weighted']:.4f}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(trained, f)
    with open(metrics_path, "w") as f:
        json.dump(trained.metrics, f, indent=2, default=str)
    log(f"Saved model -> {model_path}")
    return trained


def stage_shap(df: pd.DataFrame, trained, force: bool):
    out_path = ARTIFACTS_DIR / "shap_global_importance.json"
    if out_path.exists() and not force:
        log(f"[skip] {out_path.name} already exists")
        with open(out_path) as f:
            return json.load(f)

    log("Computing global SHAP feature importance (sampled)...")
    importance = global_feature_importance(trained, df[df["year"] >= 2023], max_samples=2000)
    with open(out_path, "w") as f:
        json.dump(importance, f, indent=2)
    log(f"Saved SHAP importance -> {out_path}")
    return importance


def stage_forecast(df: pd.DataFrame, force: bool):
    out_path = PROCESSED_DIR / "forecast_overall.json"
    if out_path.exists() and not force:
        log(f"[skip] {out_path.name} already exists")
        with open(out_path) as f:
            return json.load(f)

    log("Training forecasting model (overall daily volume)...")
    result = train_and_forecast(df, horizon_days=30)
    payload = {
        "history": result.history.assign(date=result.history["date"].astype(str)).to_dict("records"),
        "forecast": result.forecast.assign(date=result.forecast["date"].astype(str)).to_dict("records"),
        "mae": result.mae,
        "rmse": result.rmse,
        "horizon_days": result.horizon_days,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    log(f"Forecast MAE={result.mae:.2f} RMSE={result.rmse:.2f} -> {out_path}")
    return payload


def stage_risk_scores(df: pd.DataFrame, hotspot_labels, force: bool):
    out_path = PROCESSED_DIR / "risk_scores.csv"
    if out_path.exists() and not force:
        log(f"[skip] {out_path.name} already exists")
        return pd.read_csv(out_path)

    log("Computing district risk scores...")
    geo_index = df[df["has_coordinates"]].index
    scores = compute_district_risk_scores(df, hotspot_cluster_labels=hotspot_labels, hotspot_index=geo_index)
    scores.to_csv(out_path, index=False)
    log(f"Saved risk scores for {len(scores)} districts -> {out_path}")
    return scores


def stage_district_defaults(df: pd.DataFrame, force: bool):
    out_path = PROCESSED_DIR / "district_feature_defaults.json"
    if out_path.exists() and not force:
        log(f"[skip] {out_path.name} already exists")
        with open(out_path) as f:
            return json.load(f)

    log("Computing district-level feature defaults for real-time prediction...")
    agg = df.groupby("district", observed=True).agg(
        historical_frequency=("historical_frequency", "mean"),
        station_total_incidents=("station_total_incidents", "mean"),
        victim_count=("victim_count", "mean"),
    ).reset_index()
    defaults = {
        row["district"]: {
            "historical_frequency": float(row["historical_frequency"]),
            "station_total_incidents": float(row["station_total_incidents"]),
            "victim_count": float(row["victim_count"]),
        }
        for _, row in agg.iterrows()
    }
    with open(out_path, "w") as f:
        json.dump(defaults, f, indent=2)
    log(f"Saved district feature defaults -> {out_path}")
    return defaults


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-run all stages even if artifacts exist")
    args = parser.parse_args()

    t0 = time.time()
    backend = detect_backend()
    log(f"Compute backend: {backend.to_dict()}")

    df = stage_clean_and_feature_engineer(args.force)
    hotspot_summary, hotspot_labels = stage_hotspots(df, args.force)
    trained = stage_classifier(df, args.force)
    stage_shap(df, trained, args.force)
    stage_forecast(df, args.force)
    stage_risk_scores(df, hotspot_labels, args.force)
    stage_district_defaults(df, args.force)

    log(f"Pipeline complete in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
