"""
Loads ML artifacts (trained classifier, SHAP importance, forecast, hotspots,
risk scores, cleaning summary, compute backend info) once at process startup
and caches them in memory. Artifacts are produced by scripts/run_pipeline.py
and never retrained inside the API process itself.
"""
import json
import pickle
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
ARTIFACTS_DIR = ROOT / "artifacts" / "models"


class Artifacts:
    def __init__(self):
        self.trained_classifier = None
        self.classifier_metrics = None
        self.shap_importance = None
        self.forecast_overall = None
        self.cleaning_summary = None
        self.compute_backend = None
        self.district_defaults = None
        self._load()

    def _load(self):
        model_path = ARTIFACTS_DIR / "crime_classifier.pkl"
        if model_path.exists():
            with open(model_path, "rb") as f:
                self.trained_classifier = pickle.load(f)

        metrics_path = ARTIFACTS_DIR / "classifier_metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                self.classifier_metrics = json.load(f)

        shap_path = ARTIFACTS_DIR / "shap_global_importance.json"
        if shap_path.exists():
            with open(shap_path) as f:
                self.shap_importance = json.load(f)

        forecast_path = PROCESSED_DIR / "forecast_overall.json"
        if forecast_path.exists():
            with open(forecast_path) as f:
                self.forecast_overall = json.load(f)

        summary_path = PROCESSED_DIR / "cleaning_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                self.cleaning_summary = json.load(f)

        from ml.compute_backend import detect_backend
        self.compute_backend = detect_backend().to_dict()

        defaults_path = PROCESSED_DIR / "district_feature_defaults.json"
        if defaults_path.exists():
            with open(defaults_path) as f:
                self.district_defaults = json.load(f)


@lru_cache(maxsize=1)
def get_artifacts() -> Artifacts:
    return Artifacts()
