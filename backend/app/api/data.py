from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Crime, Hotspot
from backend.app.schemas.schemas import StatsOut, PaginatedCrimes, CrimeOut

router = APIRouter()


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Crime.id)).scalar()
    categories = db.query(func.count(distinct(Crime.crime_type))).scalar()
    hotspots = db.query(func.count(Hotspot.id)).scalar()
    with_coords = db.query(func.count(Crime.id)).filter(Crime.has_coordinates.is_(True)).scalar()
    districts = db.query(func.count(distinct(Crime.district))).scalar()

    min_ts = db.query(func.min(Crime.timestamp)).scalar()
    max_ts = db.query(func.max(Crime.timestamp)).scalar()

    top_groups_q = (
        db.query(Crime.crime_group, func.count(Crime.id).label("n"))
        .group_by(Crime.crime_group)
        .order_by(func.count(Crime.id).desc())
        .limit(8)
        .all()
    )
    top_groups = [{"crime_group": g, "count": n} for g, n in top_groups_q]

    highest_density = (
        db.query(Crime.district, func.count(Crime.id).label("n"))
        .group_by(Crime.district)
        .order_by(func.count(Crime.id).desc())
        .first()
    )

    return StatsOut(
        total_incidents=total,
        crime_categories=categories,
        active_hotspots=hotspots,
        highest_density_district=highest_density[0] if highest_density else "Unknown",
        date_range=[str(min_ts), str(max_ts)],
        districts_covered=districts,
        records_with_coordinates=with_coords,
        top_crime_groups=top_groups,
    )


@router.get("/crimes", response_model=PaginatedCrimes)
def list_crimes(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    district: Optional[str] = None,
    crime_group: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    only_with_coordinates: bool = False,
    search: Optional[str] = None,
):
    q = db.query(Crime)
    if district:
        q = q.filter(Crime.district == district)
    if crime_group:
        q = q.filter(Crime.crime_group == crime_group)
    if start_date:
        q = q.filter(Crime.timestamp >= start_date)
    if end_date:
        q = q.filter(Crime.timestamp <= end_date)
    if only_with_coordinates:
        q = q.filter(Crime.has_coordinates.is_(True))
    if search:
        like = f"%{search}%"
        q = q.filter((Crime.crime_type.ilike(like)) | (Crime.location.ilike(like)) | (Crime.station.ilike(like)))

    total = q.count()
    items = (
        q.order_by(Crime.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedCrimes(
        total=total, page=page, page_size=page_size,
        items=[CrimeOut.model_validate(i) for i in items],
    )


@router.get("/crimes/map", response_model=list[CrimeOut])
def crimes_for_map(
    db: Session = Depends(get_db),
    district: Optional[str] = None,
    crime_group: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(5000, le=20000),
):
    """
    Point-level crimes for the interactive map. Capped hard at 20,000 points
    (never sends the full multi-million row table to the frontend), and only
    returns records with real validated coordinates.
    """
    q = db.query(Crime).filter(Crime.has_coordinates.is_(True))
    if district:
        q = q.filter(Crime.district == district)
    if crime_group:
        q = q.filter(Crime.crime_group == crime_group)
    if start_date:
        q = q.filter(Crime.timestamp >= start_date)
    if end_date:
        q = q.filter(Crime.timestamp <= end_date)
    items = q.order_by(Crime.timestamp.desc()).limit(limit).all()
    return [CrimeOut.model_validate(i) for i in items]


@router.get("/districts")
def list_districts(db: Session = Depends(get_db)):
    rows = db.query(distinct(Crime.district)).order_by(Crime.district).all()
    return [r[0] for r in rows]


@router.get("/crime-groups")
def list_crime_groups(db: Session = Depends(get_db)):
    rows = db.query(distinct(Crime.crime_group)).order_by(Crime.crime_group).all()
    return [r[0] for r in rows]
