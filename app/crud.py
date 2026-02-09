"""CRUD operations for test runs, results, and screenshots."""

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models import TestRun, TestResult, TestScreenshot, TestBugLink, LabelMismatch


# ---- TestRun ----
def get_run(db: Session, run_id: int) -> Optional[TestRun]:
    return db.query(TestRun).filter(TestRun.id == run_id).first()


def get_runs(
    db: Session,
    project: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[TestRun]:
    q = db.query(TestRun).order_by(desc(TestRun.created_at))
    if project:
        q = q.filter(TestRun.project == project)
    return q.offset(skip).limit(limit).all()


def create_run(
    db: Session,
    project: str = "default",
    name: Optional[str] = None,
) -> TestRun:
    run = TestRun(project=(project or "default").strip() or "default", name=(name or "").strip() or None)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update_run_name(db: Session, run_id: int, name: Optional[str]) -> Optional[TestRun]:
    run = get_run(db, run_id)
    if not run:
        return None
    run.name = (name or "").strip() or None
    db.commit()
    db.refresh(run)
    return run


def add_results_to_run(db: Session, run_id: int, tests_data: list[dict]) -> int:
    """Append test results to an existing run. Returns count added."""
    run = get_run(db, run_id)
    if not run:
        return 0
    added = 0
    for t in tests_data:
        result = TestResult(
            run_id=run_id,
            nodeid=t.get("nodeid", "unknown"),
            status=t.get("status", "passed"),
            duration=float(t.get("duration", 0) or 0),
            error_message=t.get("error_message"),
        )
        db.add(result)
        added += 1
    db.commit()
    return added


def delete_run(db: Session, run_id: int) -> bool:
    run = get_run(db, run_id)
    if not run:
        return False
    db.delete(run)
    db.commit()
    return True


# ---- TestResult ----
def get_result(db: Session, result_id: int) -> Optional[TestResult]:
    return db.query(TestResult).filter(TestResult.id == result_id).first()


def get_results_by_run(db: Session, run_id: int) -> list[TestResult]:
    return db.query(TestResult).filter(TestResult.run_id == run_id).order_by(TestResult.id).all()


def update_result_bug_link(db: Session, result_id: int, bug_link: Optional[str]) -> Optional[TestResult]:
    result = get_result(db, result_id)
    if not result:
        return None
    result.bug_link = bug_link or None
    db.commit()
    db.refresh(result)
    return result


# ---- TestBugLink ----
def get_bug_links(db: Session, test_result_id: int) -> list[TestBugLink]:
    return (
        db.query(TestBugLink)
        .filter(TestBugLink.test_result_id == test_result_id)
        .order_by(TestBugLink.id)
        .all()
    )


def add_bug_link(
    db: Session,
    test_result_id: int,
    label: str,
    url: str,
) -> Optional[TestBugLink]:
    result = get_result(db, test_result_id)
    if not result:
        return None
    link = TestBugLink(test_result_id=test_result_id, label=(label or "Link").strip(), url=url.strip())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def delete_bug_link(db: Session, link_id: int) -> bool:
    link = db.query(TestBugLink).filter(TestBugLink.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


def get_bug_link(db: Session, link_id: int) -> Optional[TestBugLink]:
    return db.query(TestBugLink).filter(TestBugLink.id == link_id).first()


# ---- TestScreenshot ----
def add_screenshot(
    db: Session,
    test_result_id: int,
    file_path: str,
    name: Optional[str] = None,
) -> Optional[TestScreenshot]:
    result = get_result(db, test_result_id)
    if not result:
        return None
    screenshot = TestScreenshot(
        test_result_id=test_result_id,
        file_path=file_path,
        name=(name or "").strip() or None,
    )
    db.add(screenshot)
    db.commit()
    db.refresh(screenshot)
    return screenshot


def get_screenshots_for_result(db: Session, test_result_id: int) -> list[TestScreenshot]:
    return (
        db.query(TestScreenshot)
        .filter(TestScreenshot.test_result_id == test_result_id)
        .order_by(TestScreenshot.uploaded_at)
        .all()
    )


def get_screenshot(db: Session, screenshot_id: int) -> Optional[TestScreenshot]:
    return db.query(TestScreenshot).filter(TestScreenshot.id == screenshot_id).first()


def delete_screenshot(db: Session, screenshot_id: int) -> bool:
    ss = get_screenshot(db, screenshot_id)
    if not ss:
        return False
    db.delete(ss)
    db.commit()
    return True


def get_projects(db: Session) -> list[str]:
    """Distinct project names for filter dropdown."""
    rows = db.query(TestRun.project).distinct().order_by(TestRun.project).all()
    return [r[0] for r in rows]


# ---- Unique bugs (by URL) ----
def get_unique_bugs_overall(db: Session) -> list[dict]:
    """List unique bugs across all runs: by URL, with label, run_ids, test count (includes legacy bug_link)."""
    by_url: dict[str, dict] = {}
    # From TestBugLink
    rows = (
        db.query(TestBugLink.url, TestBugLink.label, TestResult.run_id)
        .join(TestResult, TestResult.id == TestBugLink.test_result_id)
        .all()
    )
    for url, label, run_id in rows:
        url = (url or "").strip()
        if not url:
            continue
        if url not in by_url:
            by_url[url] = {"url": url, "label": label or "Bug", "run_ids": set(), "test_count": 0}
        by_url[url]["run_ids"].add(run_id)
        by_url[url]["test_count"] += 1
    # Legacy TestResult.bug_link
    legacy = db.query(TestResult.bug_link, TestResult.run_id).filter(TestResult.bug_link.isnot(None)).all()
    for url, run_id in legacy:
        url = (url or "").strip()
        if not url:
            continue
        if url not in by_url:
            by_url[url] = {"url": url, "label": "Bug link", "run_ids": set(), "test_count": 0}
        by_url[url]["run_ids"].add(run_id)
        by_url[url]["test_count"] += 1
    out = []
    for v in by_url.values():
        v["run_ids"] = sorted(v["run_ids"])
        out.append(v)
    out.sort(key=lambda x: (-x["test_count"], x["url"]))
    return out


def get_unique_bugs_for_run(db: Session, run_id: int) -> list[dict]:
    """List unique bugs (by URL) for a single run."""
    rows = (
        db.query(TestBugLink.url, TestBugLink.label, TestBugLink.test_result_id)
        .join(TestResult, TestResult.id == TestBugLink.test_result_id)
        .filter(TestResult.run_id == run_id)
        .all()
    )
    by_url: dict[str, dict] = {}
    for url, label, _ in rows:
        url = (url or "").strip()
        if not url:
            continue
        if url not in by_url:
            by_url[url] = {"url": url, "label": label or "Bug", "test_count": 0}
        by_url[url]["test_count"] += 1
    return list(by_url.values())


# ---- LabelMismatch ----
def get_label_mismatches(db: Session) -> list[LabelMismatch]:
    return db.query(LabelMismatch).order_by(LabelMismatch.created_at.desc()).all()


def add_label_mismatch(
    db: Session,
    term1: str,
    term2: str,
    notes: Optional[str] = None,
) -> LabelMismatch:
    t1, t2 = (term1 or "").strip(), (term2 or "").strip()
    if not t1 or not t2:
        raise ValueError("Both terms required")
    if t1 == t2:
        raise ValueError("Terms must differ")
    if t1 > t2:
        t1, t2 = t2, t1
    m = LabelMismatch(term1=t1, term2=t2, notes=(notes or "").strip() or None)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def delete_label_mismatch(db: Session, mismatch_id: int) -> bool:
    m = db.query(LabelMismatch).filter(LabelMismatch.id == mismatch_id).first()
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True
