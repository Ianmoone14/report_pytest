"""CRUD operations for test runs, results, and screenshots."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models import (
    TestRun,
    TestResult,
    TestScreenshot,
    TestBugLink,
    Bug,
    BugScreenshot,
    LabelMismatch,
    BUG_STATUS_OPEN,
    BUG_STATUSES,
)


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
def _collect_bugs_by_url(db: Session, run_id_filter=None, project_filter=None, date_from=None, date_to=None):
    """Collect (url, label, run_id, run_project, run_created_at) with optional filters."""
    # TestBugLink + TestResult + TestRun
    q = (
        db.query(TestBugLink.url, TestBugLink.label, TestResult.run_id, TestRun.project, TestRun.created_at)
        .join(TestResult, TestResult.id == TestBugLink.test_result_id)
        .join(TestRun, TestRun.id == TestResult.run_id)
    )
    rows = q.all()
    # Legacy TestResult.bug_link: need run_id, project, created_at
    legacy = (
        db.query(TestResult.bug_link, TestResult.run_id, TestRun.project, TestRun.created_at)
        .join(TestRun, TestRun.id == TestResult.run_id)
        .filter(TestResult.bug_link.isnot(None))
        .all()
    )
    out = []
    for url, label, rid, proj, created in rows:
        url = (url or "").strip()
        if not url:
            continue
        if run_id_filter is not None and rid != run_id_filter:
            continue
        if project_filter and proj != project_filter:
            continue
        if date_from and created and created < date_from:
            continue
        if date_to and created and created > date_to:
            continue
        out.append((url, label or "Bug", rid, proj, created))
    for url, rid, proj, created in legacy:
        url = (url or "").strip()
        if not url:
            continue
        if run_id_filter is not None and rid != run_id_filter:
            continue
        if project_filter and proj != project_filter:
            continue
        if date_from and created and created < date_from:
            continue
        if date_to and created and created > date_to:
            continue
        out.append((url, "Bug link", rid, proj, created))
    return out


def get_unique_bugs_overall(
    db: Session,
    run_id: Optional[int] = None,
    project: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort: str = "most_linked",
) -> list[dict]:
    """List unique bugs with optional filters; enrich with Bug (notes, screenshots)."""
    rows = _collect_bugs_by_url(db, run_id_filter=run_id, project_filter=project, date_from=date_from, date_to=date_to)
    by_url: dict[str, dict] = {}
    for url, label, run_id_val, _proj, _created in rows:
        if url not in by_url:
            by_url[url] = {"url": url, "label": label, "run_ids": set(), "test_count": 0}
        by_url[url]["run_ids"].add(run_id_val)
        by_url[url]["test_count"] += 1
    out = []
    for v in by_url.values():
        v["run_ids"] = sorted(v["run_ids"])
        out.append(v)
    # Sort
    if sort == "label_az":
        out.sort(key=lambda x: ((x["label"] or "").lower(), x["url"]))
    elif sort == "label_za":
        out.sort(key=lambda x: ((x["label"] or "").lower(), x["url"]), reverse=True)
    elif sort == "url_az":
        out.sort(key=lambda x: (x["url"].lower(), x["label"]))
    elif sort == "url_za":
        out.sort(key=lambda x: (x["url"].lower(), x["label"]), reverse=True)
    else:
        out.sort(key=lambda x: (-x["test_count"], x["url"]))
    # Enrich with Bug (notes, status, screenshots)
    for b in out:
        bug = get_bug_by_url(db, b["url"])
        b["bug_id"] = bug.id if bug else None
        b["notes"] = bug.notes if bug else None
        b["status"] = bug.status if bug else BUG_STATUS_OPEN
        b["screenshots"] = get_bug_screenshots(db, bug.id) if bug else []
    return out


def get_bug_by_url(db: Session, url: str) -> Optional[Bug]:
    return db.query(Bug).filter(Bug.url == (url or "").strip()).first()


def get_bug(db: Session, bug_id: int) -> Optional[Bug]:
    return db.query(Bug).filter(Bug.id == bug_id).first()


def get_or_create_bug(db: Session, url: str, label: Optional[str] = None) -> Bug:
    url = (url or "").strip()
    if not url:
        raise ValueError("URL required")
    bug = get_bug_by_url(db, url)
    if bug:
        if label:
            bug.label = label
            db.commit()
            db.refresh(bug)
        return bug
    bug = Bug(url=url, label=(label or "").strip() or None, status=BUG_STATUS_OPEN)
    db.add(bug)
    db.commit()
    db.refresh(bug)
    return bug


def update_bug_notes(db: Session, bug_id: int, notes: Optional[str]) -> Optional[Bug]:
    bug = get_bug(db, bug_id)
    if not bug:
        return None
    bug.notes = (notes or "").strip() or None
    db.commit()
    db.refresh(bug)
    return bug


def update_bug_status(db: Session, bug_id: int, status: str) -> Optional[Bug]:
    status = (status or "").strip().lower()
    if status not in BUG_STATUSES:
        return None
    bug = get_bug(db, bug_id)
    if not bug:
        return None
    bug.status = status
    db.commit()
    db.refresh(bug)
    return bug


def get_bug_screenshots(db: Session, bug_id: int) -> list:
    return db.query(BugScreenshot).filter(BugScreenshot.bug_id == bug_id).order_by(BugScreenshot.uploaded_at).all()


def add_bug_screenshot(db: Session, bug_id: int, file_path: str, name: Optional[str] = None) -> Optional[BugScreenshot]:
    bug = get_bug(db, bug_id)
    if not bug:
        return None
    ss = BugScreenshot(bug_id=bug_id, file_path=file_path, name=(name or "").strip() or None)
    db.add(ss)
    db.commit()
    db.refresh(ss)
    return ss


def get_bug_screenshot(db: Session, screenshot_id: int):
    return db.query(BugScreenshot).filter(BugScreenshot.id == screenshot_id).first()


def delete_bug_screenshot(db: Session, screenshot_id: int) -> bool:
    ss = get_bug_screenshot(db, screenshot_id)
    if not ss:
        return False
    db.delete(ss)
    db.commit()
    return True


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
