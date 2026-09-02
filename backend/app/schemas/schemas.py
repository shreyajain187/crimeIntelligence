from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CrimeOut(BaseModel):
    crime_id: str
    timestamp: datetime
    crime_type: str
    crime_group: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    has_coordinates: bool
    location: str
    district: str
    station: str
    victim_count: Optional[int] = None
    cluster_id: Optional[int] = None

    class Config:
        from_attributes = True


class PaginatedCrimes(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CrimeOut]


class HotspotOut(BaseModel):
    cluster_id: int
    centroid_lat: float
    centroid_lon: float
    incident_count: int
    density_per_km2: float
    dominant_crime_type: str
    district: str

    class Config:
        from_attributes = True


class RiskScoreOut(BaseModel):
    district: str
    risk_score: float
    risk_tier: str
    incident_density_raw: float
    recent_activity_ratio: float
    hotspot_share: float
    monthly_trend_slope: float

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_incidents: int
    crime_categories: int
    active_hotspots: int
    highest_density_district: str
    date_range: list[str]
    districts_covered: int
    records_with_coordinates: int
    top_crime_groups: list[dict]


class PredictRequest(BaseModel):
    district: str
    season: str = Field(description="one of: winter, summer, monsoon, post_monsoon")
    year: int
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    day_of_week: int = Field(ge=0, le=6)
    is_weekend: int = Field(ge=0, le=1)
    historical_frequency: Optional[float] = None
    station_total_incidents: Optional[float] = None
    victim_count: Optional[float] = None


class PredictResponse(BaseModel):
    predicted_crime_group: str
    probability: float
    top_predictions: list[dict]
    risk_score: Optional[float] = None
    risk_tier: Optional[str] = None
    disclaimer: str = (
        "This prediction describes patterns in historical data and should "
        "not be interpreted as certainty about any specific future event."
    )


class ExplainRequest(PredictRequest):
    pass


class ExplainResponse(BaseModel):
    predicted_class: str
    backend_used: str
    top_features: list[dict]
    note: str


class ForecastQuery(BaseModel):
    district: Optional[str] = None
    crime_group: Optional[str] = None
    horizon_days: int = 30
