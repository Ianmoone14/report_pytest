"""Database configuration and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and add any missing columns (e.g. test_screenshots.name)."""
    from app.models import TestRun, TestResult, TestScreenshot, TestBugLink, LabelMismatch  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Add missing columns for existing DBs
    if "sqlite" in settings.database_url:
        try:
            with engine.connect() as conn:
                # test_screenshots.name
                r = conn.execute(text("PRAGMA table_info(test_screenshots)"))
                cols = [row[1] for row in r] if r else []
                if "name" not in cols:
                    conn.execute(text("ALTER TABLE test_screenshots ADD COLUMN name VARCHAR(255)"))
                    conn.commit()
                # test_runs.name
                r2 = conn.execute(text("PRAGMA table_info(test_runs)"))
                cols2 = [row[1] for row in r2] if r2 else []
                if "name" not in cols2:
                    conn.execute(text("ALTER TABLE test_runs ADD COLUMN name VARCHAR(255)"))
                    conn.commit()
        except Exception:
            pass
