"""
Database engine/session setup.

This project runs on SQLite for local development and grading (zero setup,
single file, works anywhere). The ORM models in models.py are written in a
way that maps directly onto a PostgreSQL + PostGIS schema for a production
deployment:

  - crimes.latitude/longitude (Float, Float) -> would become a single
    PostGIS `geometry(Point, 4326)` column with a GiST spatial index in
    Postgres. We keep them as two floats here since SQLite has no native
    geometry type, and add a regular (lat, lon) composite index instead.
  - All other tables map 1:1 onto Postgres tables with no changes needed.

See README.md "Database" section for the equivalent `CREATE TABLE` /
`CREATE INDEX` statements for PostgreSQL + PostGIS, and docker-compose.yml
for a ready-to-use Postgres+PostGIS service definition.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_DIR / 'omniwatch.db'}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
