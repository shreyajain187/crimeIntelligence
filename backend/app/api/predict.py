from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import get_artifacts
from backend.app.db.database import get_db
from backend.app.db.models import RiskScore
from backend.app.schemas.schemas import (
    PredictRequest, PredictResponse, ExplainRequest, ExplainResponse,
)

router = APIRouter()

VALID_SEASONS = {"winter", "summer", "monsoon", "post_monsoon"}


def _fill_defaults(req: PredictRequest) -> dict:
    artifacts = get_artifacts()
    defaults = (artifacts.district_defaults or {}).get(req.district, {
        "historical_frequency": 0.0, "station_total_incidents": 0.0, "victim_count": 0.0,
    })
    return {
        "district": req.district,
        "season": req.season,
        "year": req.year,
        "month": req.month,
        "day": req.day,
        "day_of_week": req.day_of_week,
        "is_weekend": req.is_weekend,
        "historical_frequency": req.historical_frequency if req.historical_frequency is not None else defaults["historical_frequency"],
        "station_total_incidents": req.station_total_incidents if req.station_total_incidents is not None else defaults["station_total_incidents"],
        "victim_count": req.victim_count if req.victim_count is not None else defaults["victim_count"],
    }


def _validate_request(req: PredictRequest):
    artifacts = get_artifacts()
    if req.season not in VALID_SEASONS:
        raise HTTPException(422, f"season must be one of {sorted(VALID_SEASONS)}")
    if artifacts.trained_classifier is None:
        raise HTTPException(503, "Model not available - run scripts/run_pipeline.py first.")
    valid_districts = set(artifacts.trained_classifier.district_categories)
    if req.district not in valid_districts:
        raise HTTPException(422, f"Unknown district '{req.district}'. Must be a district present in training data.")


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    from ml.classifier import predict_one

    _validate_request(req)
    artifacts = get_artifacts()
    record = _fill_defaults(req)
    result = predict_one(artifacts.trained_classifier, record)

    risk_row = db.query(RiskScore).filter(RiskScore.district == req.district).first()
    return PredictResponse(
        predicted_crime_group=result["predicted_crime_group"],
        probability=result["probability"],
        top_predictions=result["top_predictions"],
        risk_score=risk_row.risk_score if risk_row else None,
        risk_tier=risk_row.risk_tier if risk_row else None,
    )


@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    from ml.classifier import predict_one
    from ml.explain import explain_single_prediction

    _validate_request(req)
    artifacts = get_artifacts()
    record = _fill_defaults(req)
    prediction = predict_one(artifacts.trained_classifier, record)
    explanation = explain_single_prediction(
        artifacts.trained_classifier, record, prediction["predicted_crime_group"]
    )
    return ExplainResponse(**explanation)
