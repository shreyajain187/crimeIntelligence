"""
SHAP explainability for the XGBoost crime-type classifier.

Uses shap.TreeExplainer (CPU) by default; attempts GPUTreeExplainer when a
GPU backend is active and the shap build supports it, falling back cleanly
otherwise. SHAP values are read directly from the fitted booster - never
fabricated or approximated by hand.

Because this is a multi-class model, SHAP values have shape
(n_samples, n_features, n_classes). We report:
  - global feature importance: mean(|SHAP value|) per feature, averaged
    across classes, for a model-wide ranking.
  - per-prediction explanation: SHAP values for the single predicted class,
    which is the class the user actually receives.

Language used throughout: "features associated with the model's prediction"
-- SHAP values describe the trained model's behaviour, not a causal claim
about what causes crime.
"""
import numpy as np
import pandas as pd
import shap

from ml.compute_backend import detect_backend


def build_explainer(trained):
    backend = detect_backend()
    if backend.active_backend == "gpu":
        try:
            return shap.explainers.GPUTree(trained.booster), "gpu"
        except Exception:
            pass
    return shap.TreeExplainer(trained.booster), "cpu"


def global_feature_importance(trained, sample_df: pd.DataFrame, max_samples: int = 3000) -> list[dict]:
    from ml.classifier import _prepare_features, FEATURE_COLUMNS_CATEGORICAL

    sample = sample_df.sample(min(max_samples, len(sample_df)), random_state=42)
    cat_maps = {
        "district": trained.district_categories,
        "season": trained.season_categories,
    }
    X, _ = _prepare_features(sample, cat_maps=cat_maps)

    explainer, backend_used = build_explainer(trained)
    sv = explainer.shap_values(X)
    # sv shape: (n_classes, n_samples, n_features) for older SHAP/XGB combos,
    # or (n_samples, n_features, n_classes) for newer ones - normalize.
    sv = np.array(sv)
    if sv.ndim == 3 and sv.shape[0] == len(trained.label_encoder.classes_):
        mean_abs = np.mean(np.abs(sv), axis=(0, 1))
    else:
        mean_abs = np.mean(np.abs(sv), axis=(0, 2)) if sv.ndim == 3 else np.mean(np.abs(sv), axis=0)

    ranking = sorted(
        zip(trained.feature_columns, mean_abs.tolist()),
        key=lambda x: x[1], reverse=True,
    )
    return [{"feature": f, "mean_abs_shap": float(v)} for f, v in ranking]


def explain_single_prediction(trained, record: dict, predicted_class: str) -> dict:
    from ml.classifier import _prepare_features

    row = pd.DataFrame([record])
    cat_maps = {
        "district": trained.district_categories,
        "season": trained.season_categories,
    }
    X, _ = _prepare_features(row, cat_maps=cat_maps)

    explainer, backend_used = build_explainer(trained)
    sv = explainer.shap_values(X)
    sv = np.array(sv)
    class_idx = list(trained.label_encoder.classes_).index(predicted_class)

    if sv.ndim == 3 and sv.shape[0] == len(trained.label_encoder.classes_):
        row_shap = sv[class_idx, 0, :]
    elif sv.ndim == 3:
        row_shap = sv[0, :, class_idx]
    else:
        row_shap = sv[0, :]

    contributions = sorted(
        zip(trained.feature_columns, row_shap.tolist()),
        key=lambda x: abs(x[1]), reverse=True,
    )
    return {
        "predicted_class": predicted_class,
        "backend_used": backend_used,
        "top_features": [
            {"feature": f, "shap_value": float(v),
             "direction": "increases" if v > 0 else "decreases"}
            for f, v in contributions[:6]
        ],
        "note": "Values show features associated with the model's prediction for this input, not a causal explanation.",
    }
