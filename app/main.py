"""FastAPI application: upload, dashboard, run detail, bug links, screenshots."""

import csv
import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, init_db
from app.models import TestRun, TestResult, BUG_STATUSES
from app.parser import parse_pytest_json, build_test_results
from app import crud

# Display labels for bug status (value -> label)
BUG_STATUS_LABELS = {
    "open": "Open",
    "closed": "Closed",
    "in_progress": "In progress",
    "wont_fix": "Won't fix",
}
BUG_STATUS_CHOICES = [(s, BUG_STATUS_LABELS.get(s, s)) for s in BUG_STATUSES]

app = FastAPI(title="Pytest Execution Report Viewer")

# Ensure uploads exist
settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
settings.bug_screenshots_dir.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    project: Optional[str] = None,
    db: Session = Depends(get_db),
):
    runs = crud.get_runs(db, project=project)
    projects = crud.get_projects(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "runs": runs, "projects": projects, "current_project": project},
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
def upload_report(
    request: Request,
    file: UploadFile = File(...),
    project: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(400, "Please upload a JSON file.")
    content = file.file.read()
    try:
        proj, tests_data = parse_pytest_json(content)
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON or report format: {e}")
    run_project = (project or proj or "default").strip() or "default"
    run = crud.create_run(db, project=run_project)
    results = build_test_results(run, tests_data)
    for r in results:
        db.add(r)
    db.commit()
    return RedirectResponse(url=f"/runs/{run.id}", status_code=303)


@app.get("/runs/new", response_class=HTMLResponse)
def new_run_page(request: Request):
    return templates.TemplateResponse("create_run.html", {"request": request})


@app.post("/runs/create")
def create_run_action(
    request: Request,
    name: str = Form(...),
    project: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    project = (project or "default").strip() or "default"
    name = (name or "").strip() or None
    run = crud.create_run(db, project=project, name=name)
    return RedirectResponse(url=f"/runs/{run.id}", status_code=303)


@app.post("/runs/{run_id}/results/upload")
def upload_results_to_run(
    run_id: int,
    files: List[UploadFile] = File(..., alias="files"),
    db: Session = Depends(get_db),
):
    run = crud.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if not files:
        raise HTTPException(400, "No files uploaded")
    total_added = 0
    errors = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".json"):
            errors.append(f"{file.filename or 'unknown'}: not a JSON file")
            continue
        try:
            content = file.file.read()
            _, tests_data = parse_pytest_json(content)
            added = crud.add_results_to_run(db, run_id, tests_data)
            total_added += added
        except Exception as e:
            errors.append(f"{file.filename}: {e}")
    if total_added == 0 and errors:
        raise HTTPException(400, "No tests imported. " + "; ".join(errors[:3]))
    return RedirectResponse(url=f"/runs/{run_id}?added={total_added}", status_code=303)


@app.post("/runs/{run_id}/delete")
def delete_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = crud.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    # Collect screenshot paths before deleting (cascade removes DB rows)
    results = crud.get_results_by_run(db, run_id)
    paths_to_remove = []
    for r in results:
        for ss in crud.get_screenshots_for_result(db, r.id):
            paths_to_remove.append(settings.uploads_dir / ss.file_path)
    crud.delete_run(db, run_id)
    for p in paths_to_remove:
        if p.is_file():
            try:
                p.unlink()
            except OSError:
                pass
    return RedirectResponse(url="/", status_code=303)


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(
    request: Request,
    run_id: int,
    added: Optional[int] = None,
    db: Session = Depends(get_db),
):
    run = crud.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    results = crud.get_results_by_run(db, run_id)
    for r in results:
        r.screenshot_list = crud.get_screenshots_for_result(db, r.id)
        db_links = crud.get_bug_links(db, r.id)
        if r.bug_link and not any(bl.url == r.bug_link for bl in db_links):
            r.bug_links_list = [{"id": None, "label": "Bug link", "url": r.bug_link}] + [
                {"id": bl.id, "label": bl.label, "url": bl.url} for bl in db_links
            ]
        else:
            r.bug_links_list = [{"id": bl.id, "label": bl.label, "url": bl.url} for bl in db_links]
    unique_bugs_run = crud.get_unique_bugs_for_run(db, run_id)
    seen_urls = {b["url"] for b in unique_bugs_run}
    for r in results:
        if r.bug_link and r.bug_link.strip() and r.bug_link not in seen_urls:
            unique_bugs_run.append({"url": r.bug_link, "label": "Bug link", "test_count": 1})
            seen_urls.add(r.bug_link)
    return templates.TemplateResponse(
        "run_detail.html",
        {
            "request": request,
            "run": run,
            "results": results,
            "unique_bugs_run": unique_bugs_run,
            "added": added,
        },
    )


@app.post("/runs/{run_id}/rename")
def rename_run(
    run_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    run = crud.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    crud.update_run_name(db, run_id, name)
    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)


@app.get("/runs/{run_id}/export/csv")
def export_run_csv(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = crud.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    results = crud.get_results_by_run(db, run_id)
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Status", "Test (nodeid)", "Duration (s)", "Error"])
    for r in results:
        w.writerow([r.status, r.nodeid, f"{r.duration:.2f}", (r.error_message or "")[:500]])
    buf.seek(0)
    filename = f"run-{run_id}-{run.name or 'export'}.csv".replace(" ", "_")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/runs/{run_id}/results/{result_id}/bug-links")
async def add_bug_link(
    run_id: int,
    result_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    result = crud.get_result(db, result_id)
    if not result or result.run_id != run_id:
        raise HTTPException(404, "Test result not found")
    form = await request.form()
    label = (form.get("label") or "Link").strip()
    url = (form.get("url") or "").strip()
    if not url:
        raise HTTPException(400, "URL is required")
    crud.add_bug_link(db, result_id, label=label, url=url)
    return RedirectResponse(url=f"/runs/{run_id}#result-{result_id}", status_code=303)


@app.post("/runs/{run_id}/results/{result_id}/bug-links/{link_id}/delete")
async def delete_bug_link(
    run_id: int,
    result_id: int,
    link_id: int,
    db: Session = Depends(get_db),
):
    result = crud.get_result(db, result_id)
    if not result or result.run_id != run_id:
        raise HTTPException(404, "Test result not found")
    link = crud.get_bug_link(db, link_id)
    if not link or link.test_result_id != result_id:
        raise HTTPException(404, "Bug link not found")
    crud.delete_bug_link(db, link_id)
    return RedirectResponse(url=f"/runs/{run_id}#result-{result_id}", status_code=303)


def _allowed_screenshot(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in settings.allowed_image_extensions


@app.post("/runs/{run_id}/results/{result_id}/screenshots")
async def upload_screenshot(
    run_id: int,
    result_id: int,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    run = crud.get_run(db, run_id)
    result = crud.get_result(db, result_id)
    if not run or not result or result.run_id != run_id:
        raise HTTPException(404, "Run or result not found")
    if not file.filename or not _allowed_screenshot(file.filename):
        raise HTTPException(
            400,
            f"Invalid file. Allowed: {', '.join(settings.allowed_image_extensions)}",
        )
    label = (name or "").strip() or None
    ext = Path(file.filename).suffix.lower()
    safe_name = f"{result_id}_{uuid.uuid4().hex}{ext}"
    dest = settings.screenshots_dir / safe_name
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    rel_path = f"screenshots/{safe_name}"
    crud.add_screenshot(db, result_id, rel_path, name=label)
    return RedirectResponse(url=f"/runs/{run_id}#result-{result_id}", status_code=303)


@app.post("/runs/{run_id}/results/{result_id}/screenshots/{screenshot_id}/delete")
def delete_screenshot(
    run_id: int,
    result_id: int,
    screenshot_id: int,
    db: Session = Depends(get_db),
):
    result = crud.get_result(db, result_id)
    if not result or result.run_id != run_id:
        raise HTTPException(404, "Test result not found")
    ss = crud.get_screenshot(db, screenshot_id)
    if not ss or ss.test_result_id != result_id:
        raise HTTPException(404, "Screenshot not found")
    file_path = settings.uploads_dir / ss.file_path
    if file_path.is_file():
        try:
            file_path.unlink()
        except OSError:
            pass
    crud.delete_screenshot(db, screenshot_id)
    return RedirectResponse(url=f"/runs/{run_id}#result-{result_id}", status_code=303)


@app.get("/ideas", response_class=HTMLResponse)
def ideas_page(request: Request):
    return templates.TemplateResponse("ideas.html", {"request": request})


def _parse_date(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    except Exception:
        return None


@app.get("/bugs", response_class=HTMLResponse)
def bugs_dashboard(
    request: Request,
    run_id: Optional[int] = None,
    project: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: Optional[str] = None,
    db: Session = Depends(get_db),
):
    df = _parse_date(date_from)
    dt = _parse_date(date_to)
    sort_val = (sort or "most_linked").strip() or "most_linked"
    if sort_val not in ("most_linked", "label_az", "label_za", "url_az", "url_za"):
        sort_val = "most_linked"
    unique_bugs = crud.get_unique_bugs_overall(
        db, run_id=run_id, project=project, date_from=df, date_to=dt, sort=sort_val
    )
    total_links = sum(b["test_count"] for b in unique_bugs)
    runs = crud.get_runs(db, limit=500)
    projects = crud.get_projects(db)
    return templates.TemplateResponse(
        "bugs.html",
        {
            "request": request,
            "unique_bugs": unique_bugs,
            "total_links": total_links,
            "runs": runs,
            "projects": projects,
            "bug_status_choices": BUG_STATUS_CHOICES,
            "current_run_id": run_id,
            "current_project": project,
            "current_date_from": date_from or "",
            "current_date_to": date_to or "",
            "current_sort": sort_val,
        },
    )


@app.get("/bugs/export/csv")
def bugs_export_csv(
    run_id: Optional[int] = None,
    project: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    df = _parse_date(date_from)
    dt = _parse_date(date_to)
    unique_bugs = crud.get_unique_bugs_overall(
        db, run_id=run_id, project=project, date_from=df, date_to=dt, sort="most_linked"
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Label", "URL", "Status", "Notes", "Runs", "Tests linked"])
    for b in unique_bugs:
        notes = (b.get("notes") or "").replace("\r", " ").replace("\n", " ")
        runs_str = ", ".join(f"Run #{r}" for r in b["run_ids"])
        status_label = BUG_STATUS_LABELS.get((b.get("status") or "open"), b.get("status") or "Open")
        w.writerow([b.get("label") or "", b["url"], status_label, notes, runs_str, b["test_count"]])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bugs.csv"},
    )


def _bugs_redirect_url(run_id=None, project=None, date_from=None, date_to=None, sort=None):
    parts = []
    if run_id is not None and run_id != "":
        parts.append(f"run_id={run_id}")
    if project:
        parts.append(f"project={project}")
    if date_from:
        parts.append(f"date_from={date_from}")
    if date_to:
        parts.append(f"date_to={date_to}")
    if sort:
        parts.append(f"sort={sort}")
    return "/bugs" + ("?" + "&".join(parts) if parts else "")


@app.post("/bugs/notes")
def bugs_save_notes(
    url: str = Form(...),
    notes: Optional[str] = Form(None),
    run_id: Optional[str] = Form(None),
    project: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    bug = crud.get_or_create_bug(db, url=url)
    crud.update_bug_notes(db, bug.id, notes)
    return RedirectResponse(url=_bugs_redirect_url(run_id, project, date_from, date_to, sort), status_code=303)


@app.post("/bugs/status")
def bugs_set_status(
    url: str = Form(...),
    status: str = Form(...),
    run_id: Optional[str] = Form(None),
    project: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    bug = crud.get_or_create_bug(db, url=url)
    crud.update_bug_status(db, bug.id, status)
    return RedirectResponse(url=_bugs_redirect_url(run_id, project, date_from, date_to, sort), status_code=303)


@app.post("/bugs/screenshots")
async def bugs_upload_screenshot(
    url: str = Form(...),
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    run_id: Optional[str] = Form(None),
    project: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "No file")
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_image_extensions:
        raise HTTPException(400, f"Allowed: {', '.join(settings.allowed_image_extensions)}")
    bug = crud.get_or_create_bug(db, url=url)
    safe_name = f"bug_{bug.id}_{uuid.uuid4().hex}{ext}"
    dest = settings.bug_screenshots_dir / safe_name
    content = await file.read()
    dest.write_bytes(content)
    rel_path = f"bug_screenshots/{safe_name}"
    crud.add_bug_screenshot(db, bug.id, rel_path, name=(name or "").strip() or None)
    return RedirectResponse(url=_bugs_redirect_url(run_id, project, date_from, date_to, sort), status_code=303)


@app.post("/bugs/screenshots/{screenshot_id}/delete")
def bugs_delete_screenshot(
    screenshot_id: int,
    run_id: Optional[str] = Form(None),
    project: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    ss = crud.get_bug_screenshot(db, screenshot_id)
    if not ss:
        raise HTTPException(404, "Screenshot not found")
    file_path = settings.uploads_dir / ss.file_path
    if file_path.is_file():
        try:
            file_path.unlink()
        except OSError:
            pass
    crud.delete_bug_screenshot(db, screenshot_id)
    return RedirectResponse(url=_bugs_redirect_url(run_id, project, date_from, date_to, sort), status_code=303)


@app.get("/labels-mismatch", response_class=HTMLResponse)
def labels_mismatch_page(request: Request, db: Session = Depends(get_db)):
    mismatches = crud.get_label_mismatches(db)
    return templates.TemplateResponse(
        "labels_mismatch.html",
        {"request": request, "mismatches": mismatches},
    )


@app.post("/labels-mismatch")
def add_label_mismatch_action(
    term1: str = Form(...),
    term2: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    try:
        crud.add_label_mismatch(db, term1=term1, term2=term2, notes=notes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse(url="/labels-mismatch", status_code=303)


@app.post("/labels-mismatch/{mismatch_id}/delete")
def delete_label_mismatch_action(mismatch_id: int, db: Session = Depends(get_db)):
    if not crud.delete_label_mismatch(db, mismatch_id):
        raise HTTPException(404, "Label mismatch not found")
    return RedirectResponse(url="/labels-mismatch", status_code=303)


@app.get("/labels-mismatch/export/csv")
def export_labels_mismatch_csv(db: Session = Depends(get_db)):
    mismatches = crud.get_label_mismatches(db)
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Term 1", "Term 2", "Notes"])
    for m in mismatches:
        w.writerow([m.term1, m.term2, m.notes or ""])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labels-mismatch.csv"},
    )


@app.get("/uploads/{path:path}")
def serve_upload(path: str):
    """Serve uploaded screenshots (screenshots/filename)."""
    full = (settings.uploads_dir / path).resolve()
    base = settings.uploads_dir.resolve()
    if not str(full).startswith(str(base)):
        raise HTTPException(404)
    if not full.is_file():
        raise HTTPException(404)
    from fastapi.responses import FileResponse
    return FileResponse(full)


# Mount static last so /runs/* routes are matched first
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
