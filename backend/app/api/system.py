from fastapi import APIRouter
from backend.app.core.config import get_artifacts

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/metadata")
def metadata():
    artifacts = get_artifacts()
    return {
        "dataset_name": "Karnataka Police FIR Details (2016-2024)",
        "dataset_source": "https://www.kaggle.com/datasets/vanshangaria/fir-details-karnataka-police",
        "dataset_description": (
            "Real First Information Report (FIR) records recorded by "
            "Karnataka Police across 41 districts, 2016-2024."
        ),
        "cleaning_summary": artifacts.cleaning_summary,
        "compute_backend": artifacts.compute_backend,
        "classifier_available": artifacts.trained_classifier is not None,
        "forecast_available": artifacts.forecast_overall is not None,
    }
