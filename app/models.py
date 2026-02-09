"""SQLAlchemy models for test runs, results, and screenshots."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db import Base


class TestRun(Base):
    """A single run: manual or from upload; can aggregate multiple test-suite JSONs."""

    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)  # user-defined run name
    project = Column(String(255), default="default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("TestResult", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TestRun(id={self.id}, name={self.name!r}, project={self.project}, created_at={self.created_at})>"


class TestResult(Base):
    """One test execution result within a run."""

    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    nodeid = Column(String(512), nullable=False, index=True)
    status = Column(String(32), nullable=False)  # passed, failed, skipped
    duration = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    bug_link = Column(String(1024), nullable=True)  # legacy single link; prefer bug_links

    run = relationship("TestRun", back_populates="results")
    screenshots = relationship(
        "TestScreenshot", back_populates="test_result", cascade="all, delete-orphan"
    )
    bug_links = relationship(
        "TestBugLink", back_populates="test_result", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TestResult(id={self.id}, nodeid={self.nodeid}, status={self.status})>"


class TestBugLink(Base):
    """Named bug/ticket link attached to a test result."""

    __tablename__ = "test_bug_links"

    id = Column(Integer, primary_key=True, index=True)
    test_result_id = Column(
        Integer, ForeignKey("test_results.id", ondelete="CASCADE"), nullable=False
    )
    label = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    test_result = relationship("TestResult", back_populates="bug_links")

    def __repr__(self):
        return f"<TestBugLink(id={self.id}, label={self.label!r})>"


class TestScreenshot(Base):
    """Screenshot attached to a test result."""

    __tablename__ = "test_screenshots"

    id = Column(Integer, primary_key=True, index=True)
    test_result_id = Column(
        Integer, ForeignKey("test_results.id", ondelete="CASCADE"), nullable=False
    )
    file_path = Column(String(512), nullable=False)
    name = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    test_result = relationship("TestResult", back_populates="screenshots")

    def __repr__(self):
        return f"<TestScreenshot(id={self.id}, file_path={self.file_path})>"


# Allowed values for Bug.status (stored lowercase)
BUG_STATUS_OPEN = "open"
BUG_STATUS_CLOSED = "closed"
BUG_STATUS_IN_PROGRESS = "in_progress"
BUG_STATUS_WONT_FIX = "wont_fix"
BUG_STATUSES = (BUG_STATUS_OPEN, BUG_STATUS_CLOSED, BUG_STATUS_IN_PROGRESS, BUG_STATUS_WONT_FIX)


class Bug(Base):
    """Bug-level entity (by URL): notes, status, and screenshots attached to the bug, not the test."""

    __tablename__ = "bugs"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1024), nullable=False, unique=True)
    label = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default=BUG_STATUS_OPEN)  # open, closed, in_progress, wont_fix
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    screenshots = relationship("BugScreenshot", back_populates="bug", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Bug(id={self.id}, url={self.url[:50]!r})>"


class BugScreenshot(Base):
    """Screenshot attached to a bug (bug-level, not test-level)."""

    __tablename__ = "bug_screenshots"

    id = Column(Integer, primary_key=True, index=True)
    bug_id = Column(Integer, ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512), nullable=False)
    name = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    bug = relationship("Bug", back_populates="screenshots")

    def __repr__(self):
        return f"<BugScreenshot(id={self.id}, bug_id={self.bug_id})>"


class LabelMismatch(Base):
    """Terminology mismatch: same concept, different labels (e.g. 'attachments' vs 'attachment')."""

    __tablename__ = "label_mismatches"

    id = Column(Integer, primary_key=True, index=True)
    term1 = Column(String(255), nullable=False)
    term2 = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LabelMismatch(id={self.id}, term1={self.term1!r}, term2={self.term2!r})>"
