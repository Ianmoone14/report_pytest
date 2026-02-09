"""Parse pytest JSON execution reports into internal structures."""

import json
from typing import Any

from app.models import TestRun, TestResult


def parse_pytest_json(data: str | bytes) -> tuple[str, list[dict[str, Any]]]:
    """
    Parse pytest JSON report. Returns (project_name, list of test result dicts).
    Supports pytest-json-report format and simple custom format.
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    obj = json.loads(data)

    project = "default"
    tests_data: list[dict[str, Any]] = []

    # pytest-json-report / execution_report format (tests array with nodeid, outcome, setup/call/teardown)
    if "tests" in obj:
        for t in obj["tests"]:
            nodeid = t.get("nodeid", t.get("name", "unknown"))
            outcome = (t.get("outcome") or t.get("status") or "unknown").lower()
            if outcome not in ("passed", "failed", "skipped"):
                outcome = "failed" if outcome in ("error",) else "passed"
            # Duration: use top-level, or sum setup + call + teardown (e.g. execution_report.json)
            duration = t.get("duration")
            if duration is None:
                setup = t.get("setup") or {}
                call = t.get("call") or {}
                teardown = t.get("teardown") or {}
                duration = (
                    float(setup.get("duration") or 0)
                    + float(call.get("duration") or 0)
                    + float(teardown.get("duration") or 0)
                )
            else:
                duration = float(duration or 0)
            call = t.get("call") or {}
            longrepr = call.get("longrepr") if isinstance(call, dict) else None
            if longrepr and isinstance(longrepr, str):
                error_message = longrepr
            else:
                error_message = str(longrepr) if longrepr else None
            if not error_message and outcome == "failed" and isinstance(call, dict):
                error_message = call.get("stderr") or call.get("stdout")
                if error_message and not isinstance(error_message, str):
                    error_message = str(error_message)
            tests_data.append({
                "nodeid": nodeid,
                "status": outcome,
                "duration": duration,
                "error_message": error_message,
            })
        if "environment" in obj and isinstance(obj["environment"], dict):
            proj = obj["environment"].get("project") or obj.get("project")
            if proj:
                project = str(proj)
        return project, tests_data

    # Simple format: { "project": "...", "results": [ { "nodeid", "status", "duration", "error_message" } ] }
    if "results" in obj:
        project = str(obj.get("project", "default"))
        for t in obj["results"]:
            tests_data.append({
                "nodeid": t.get("nodeid", "unknown"),
                "status": (t.get("status") or "passed").lower(),
                "duration": float(t.get("duration", 0) or 0),
                "error_message": t.get("error_message"),
            })
        return project, tests_data

    # Fallback: root is list of tests
    if isinstance(obj, list):
        for t in obj:
            if isinstance(t, dict):
                tests_data.append({
                    "nodeid": t.get("nodeid", t.get("name", "unknown")),
                    "status": (t.get("status") or t.get("outcome") or "passed").lower(),
                    "duration": float(t.get("duration", 0) or 0),
                    "error_message": t.get("error_message"),
                })
        return project, tests_data

    return project, tests_data


def build_test_results(run: TestRun, tests_data: list[dict[str, Any]]) -> list[TestResult]:
    """Build TestResult instances for a run from parsed test data."""
    results = []
    for t in tests_data:
        results.append(
            TestResult(
                run_id=run.id,
                nodeid=t["nodeid"],
                status=t["status"],
                duration=t.get("duration", 0),
                error_message=t.get("error_message"),
            )
        )
    return results
