from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index
from backend.app.db.database import Base


class Crime(Base):
    __tablename__ = "crimes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crime_id = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, index=True)
    crime_type = Column(String, index=True)
    crime_group = Column(String, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    has_coordinates = Column(Boolean, default=False, index=True)
    location = Column(String)
    district = Column(String, index=True)
    station = Column(String, index=True)
    victim_count = Column(Integer, nullable=True)
    cluster_id = Column(Integer, nullable=True, index=True)

    __table_args__ = (
        Index("ix_crimes_lat_lon", "latitude", "longitude"),
        Index("ix_crimes_district_timestamp", "district", "timestamp"),
    )


class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, unique=True, index=True)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)
    incident_count = Column(Integer)
    density_per_km2 = Column(Float)
    dominant_crime_type = Column(String)
    district = Column(String, index=True)


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district = Column(String, unique=True, index=True)
    risk_score = Column(Float)
    risk_tier = Column(String)
    incident_density_raw = Column(Float)
    recent_activity_ratio = Column(Float)
    hotspot_share = Column(Float)
    monthly_trend_slope = Column(Float)


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)  # JSON-encoded string
