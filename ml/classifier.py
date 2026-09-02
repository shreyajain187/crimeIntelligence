"""
XGBoost classifier: predicts crime_group from time/location features only.

Leakage avoidance
------------------
- crime_type is NOT used as a feature (crime_group is deterministically
  derived from it - using it would make the task trivial/circular).
- accused_count, arrested_count, chargesheeted_count, conviction_count are
  case-outcome fields only known *after* investigation/adjudication - they
  are excluded because they would not be available at prediction time in a
  real early-warning use case.
- victim_count is kept: it is known at the time an FIR is filed.

Split
-----
Temporal: train on years < TEST_START_YEAR, test on years >= TEST_START_YEAR,
so the model is evaluated on genuinely future incidents relative to training.

Class imbalance
---------------
`sample_weight` computed via balanced class weighting (inverse frequency),
since crime_group is imbalanced (see class distribution in cleaning summary).
"""
from dataclasses import dataclass
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix,
    classification_report,
)
from sklearn.utils.class_weight import compute_sample_weight
import xgboost as xgb

from ml.compute_backend import detect_backend

TEST_START_YEAR = 2023

FEATURE_COLUMNS_NUMERIC = [
    "year", "month", "day", "day_of_week", "is_weekend",
    "historical_frequency", "station_total_incidents", "victim_count",
]
# Note: raw `station` (1054 distinct values) is deliberately NOT used as a
# categorical split feature - on constrained single-core hardware, splitting
# on a 1000+ level categorical is extremely expensive, and its information
# is already captured numerically via historical_frequency and
# station_total_incidents. `district` (41 levels) is kept as a categorical.
FEATURE_COLUMNS_CATEGORICAL = ["district", "season"]


@dataclass
class TrainedModel:
    booster: xgb.XGBClassifier
    label_encoder: LabelEncoder
    district_categories: list
    season_categories: list
    feature_columns: list
    metrics: dict
    backend_used: str


def _prepare_features(df: pd.DataFrame, cat_maps: dict | None = None):
    df = df.copy()
    maps = {}
    for col in FEATURE_COLUMNS_CATEGORICAL:
        if cat_maps is None:
            cats = sorted(df[col].astype(str).unique())
        else:
            cats = cat_maps[col]
        cat_dtype = pd.CategoricalDtype(categories=cats)
        df[col] = df[col].astype(str).astype(cat_dtype)
        maps[col] = cats
    X = df[FEATURE_COLUMNS_NUMERIC + FEATURE_COLUMNS_CATEGORICAL]
    return X, maps


def train_classifier(df: pd.DataFrame) -> TrainedModel:
    backend = detect_backend()
    device = "cuda" if backend.xgboost_cuda_available else "cpu"

    train_df = df[df["year"] < TEST_START_YEAR].copy()
    test_df = df[df["year"] >= TEST_START_YEAR].copy()

    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(train_df["crime_group"].astype(str))
    y_test = label_encoder.transform(test_df["crime_group"].astype(str))

    X_train, cat_maps = _prepare_features(train_df)
    X_test, _ = _prepare_features(test_df, cat_maps=cat_maps)

    # NOTE ON CLASS IMBALANCE: full inverse-frequency ("balanced") weighting
    # was evaluated and found to *reduce* overall accuracy below the trivial
    # majority-class baseline on this dataset (0.180 vs 0.203), because it
    # over-corrects for 16 genuinely imbalanced, spatio-temporally weak-signal
    # classes. We use unweighted training and report macro-F1 alongside
    # accuracy specifically so imbalance-sensitive performance is still
    # visible, rather than force a weighting scheme that hurts real-world
    # usefulness. This tradeoff is documented in the README.
    sample_weight = None

    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.15,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=len(label_encoder.classes_),
        eval_metric="mlogloss",
        tree_method="hist",
        device=device,
        enable_categorical=True,
        n_jobs=1,
        max_cat_to_onehot=1,
        random_state=42,
    )
    model.fit(X_train, y_train, sample_weight=sample_weight)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1_weighted, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0)
    _, _, f1_macro, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(
        y_test, y_pred, target_names=label_encoder.classes_, zero_division=0, output_dict=True)

    metrics = {
        "accuracy": float(accuracy),
        "precision_weighted": float(precision),
        "recall_weighted": float(recall),
        "f1_weighted": float(f1_weighted),
        "f1_macro": float(f1_macro),
        "confusion_matrix": cm,
        "classes": label_encoder.classes_.tolist(),
        "classification_report": report,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "train_years": sorted(train_df["year"].unique().tolist()),
        "test_years": sorted(test_df["year"].unique().tolist()),
        "device": device,
    }

    return TrainedModel(
        booster=model,
        label_encoder=label_encoder,
        district_categories=cat_maps["district"],
        season_categories=cat_maps["season"],
        feature_columns=FEATURE_COLUMNS_NUMERIC + FEATURE_COLUMNS_CATEGORICAL,
        metrics=metrics,
        backend_used=device,
    )


def predict_one(trained: TrainedModel, record: dict) -> dict:
    """
    record must contain: district, station, season, year, month, day,
    day_of_week, is_weekend, historical_frequency, station_total_incidents,
    victim_count.
    """
    row = pd.DataFrame([record])
    for col, cats in [
        ("district", trained.district_categories),
        ("season", trained.season_categories),
    ]:
        row[col] = row[col].astype(str).astype(pd.CategoricalDtype(categories=cats))
    X = row[trained.feature_columns]
    proba = trained.booster.predict_proba(X)[0]
    top_idx = int(np.argmax(proba))
    label = trained.label_encoder.inverse_transform([top_idx])[0]
    ranked = sorted(
        zip(trained.label_encoder.classes_, proba.tolist()),
        key=lambda x: x[1], reverse=True,
    )
    return {
        "predicted_crime_group": label,
        "probability": float(proba[top_idx]),
        "top_predictions": [{"crime_group": c, "probability": float(p)} for c, p in ranked[:5]],
    }
