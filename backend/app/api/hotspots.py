from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Hotspot, RiskScore
from backend.app.schemas.schemas import HotspotOut, RiskScoreOut

router = APIRouter()


@router.get("/hotspots", response_model=list[HotspotOut])
def get_hotspots(db: Session = Depends(get_db), limit: int = 200):
    rows = db.query(Hotspot).order_by(Hotspot.incident_count.desc()).limit(limit).all()
    return [HotspotOut.model_validate(r) for r in rows]


@router.get("/risk-scores", response_model=list[RiskScoreOut])
def get_risk_scores(db: Session = Depends(get_db)):
    rows = db.query(RiskScore).order_by(RiskScore.risk_score.desc()).all()
    return [RiskScoreOut.model_validate(r) for r in rows]
