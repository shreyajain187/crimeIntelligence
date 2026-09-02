from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.core.config import get_artifacts

router = APIRouter()


@router.get("/model/metrics")
def model_metrics():
    artifacts = get_artifacts()
    if not artifacts.classifier_metrics:
        raise HTTPException(503, "Model metrics not available - run scripts/run_pipeline.py first.")
    return artifacts.classifier_metrics


@router.get("/model/features")
def model_features():
    artifacts = get_artifacts()
    if not artifacts.shap_importance:
        raise HTTPException(503, "SHAP feature importance not available - run scripts/run_pipeline.py first.")
    return artifacts.shap_importance


@router.get("/forecast")
def forecast(
    district: Optional[str] = None,
    crime_group: Optional[str] = None,
    horizon_days: int = Query(30, le=90),
):
    """
    Returns the precomputed overall forecast for the default (unfiltered)
    view. For a district/category-specific forecast, computing on the fly
    is intentionally NOT done here (would retrain a model per request) -
    the overall forecast is the one produced by the offline pipeline.
    A future extension could precompute a small set of per-district
    forecasts in the pipeline itself.
    """
    artifacts = get_artifacts()
    if district or crime_group:
        raise HTTPException(
            501,
            "Filtered forecasts are not precomputed in this build. "
            "Only the overall (all-Karnataka) forecast is available via this endpoint.",
        )
    if not artifacts.forecast_overall:
        raise HTTPException(503, "Forecast not available - run scripts/run_pipeline.py first.")
    return artifacts.forecast_overall
