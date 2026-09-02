"""
API endpoint tests.

These tests exercise API *mechanics* (routing, pagination, filtering,
validation, error handling) against a small isolated temporary SQLite
database seeded with a handful of clearly-synthetic fixture rows. This is
standard testing practice and does not conflict with the "real data only"
rule, which governs what the *running application* serves to users -
scripts/load_database.py is what populates the real database from the real
dataset; these tests never touch that database or claim their fixture rows
are real incidents.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.db import models


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    session.add_all([
        models.Crime(crime_id="t1", timestamp=datetime(2023, 1, 1), crime_type="THEFT",
                     crime_group="THEFT", latitude=13.0, longitude=77.5,
                     has_coordinates=True, location="Test Area, PS1, District A",
                     district="District A", station="PS1", victim_count=1, cluster_id=0),
        models.Crime(crime_id="t2", timestamp=datetime(2023, 2, 1), crime_type="RIOTS",
                     crime_group="RIOTS", latitude=None, longitude=None,
                     has_coordinates=False, location="Test Area, PS2, District B",
                     district="District B", station="PS2", victim_count=0, cluster_id=None),
        models.Hotspot(cluster_id=0, centroid_lat=13.0, centroid_lon=77.5,
                        incident_count=1, density_per_km2=1.0,
                        dominant_crime_type="THEFT", district="District A"),
        models.RiskScore(district="District A", risk_score=50.0, risk_tier="Moderate",
                          incident_density_raw=1.0, recent_activity_ratio=1.0,
                          hotspot_share=1.0, monthly_trend_slope=0.0),
    ])
    session.commit()
    session.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stats_reflects_seeded_data(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_incidents"] == 2
    assert data["records_with_coordinates"] == 1
    assert data["districts_covered"] == 2


def test_crimes_pagination(client):
    r = client.get("/api/crimes", params={"page": 1, "page_size": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1


def test_crimes_filter_by_district(client):
    r = client.get("/api/crimes", params={"district": "District A"})
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["district"] == "District A"


def test_crimes_map_excludes_records_without_coordinates(client):
    r = client.get("/api/crimes/map")
    data = r.json()
    assert len(data) == 1
    assert data[0]["has_coordinates"] is True


def test_hotspots_endpoint(client):
    r = client.get("/api/hotspots")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_risk_scores_endpoint(client):
    r = client.get("/api/risk-scores")
    assert r.status_code == 200
    assert r.json()[0]["district"] == "District A"


def test_predict_rejects_unknown_district(client):
    r = client.post("/api/predict", json={
        "district": "Nonexistent District", "season": "summer",
        "year": 2024, "month": 1, "day": 1, "day_of_week": 0, "is_weekend": 0,
    })
    # 422 if model unavailable in test env is also acceptable, but an
    # unknown district must never silently succeed.
    assert r.status_code in (422, 503)


def test_model_metrics_endpoint_shape_or_unavailable(client):
    """
    In this repo the real pipeline has been run, so /model/metrics should
    return real metrics; in a fresh clone before running the pipeline, it
    correctly returns 503 rather than fabricating numbers. Both are valid
    depending on repo state, so we assert the *shape* whichever occurs.
    """
    r = client.get("/api/model/metrics")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        data = r.json()
        assert "accuracy" in data
        assert 0.0 <= data["accuracy"] <= 1.0
