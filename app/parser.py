"""Parse pytest JSON execution reports into internal structures."""

import json
from typing import Any

from app.models import TestRun, TestResult


def parse_pytest_json(data: str | bytes) -> tuple[str, list[dict[str, Any]]]:
    """
    Parse pytest JSON report. Returns (project_name, list of test result dicts).
    Supports pytest-json-report format, simple custom format, and UI vs API comparison reports.
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    obj = json.loads(data)

    project = "default"
    tests_data: list[dict[str, Any]] = []
    
    # Check if this is a UI vs API comparison report
    # It will have "environment" with "page_object" or "comparison_summary"
    if isinstance(obj, dict) and "environment" in obj:
        env = obj.get("environment", {})
        if isinstance(env, dict) and ("page_object" in env or "comparison_summary" in env):
            # This is a UI vs API comparison report
            return _parse_ui_api_comparison_report(obj)

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


def _parse_ui_api_comparison_report(obj: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """
    Parse UI vs API comparison report.
    
    These reports have:
    - "project": project name
    - "environment": dict with "page_object", "comparison_summary", "run_name", "api_endpoint", "api_parameters"
    - "tests": list of test cases (one per comparison record)
    
    Returns:
        (project_name, list of test result dicts)
    """
    project = obj.get("project", "ui_api_comparison")
    env = obj.get("environment", {})
    api_endpoint = None
    api_parameters = None
    test_name = None
    
    if isinstance(env, dict):
        run_name = env.get("run_name")
        if run_name:
            project = f"{project} - {run_name}"
        api_endpoint = env.get("api_endpoint")
        api_parameters = env.get("api_parameters")
        test_name = env.get("test_name")
    
    tests_data = []
    tests = obj.get("tests", [])
    
    # Store API endpoint info in summary test's error_message for comparison parser to extract
    api_info_str = ""
    if api_endpoint:
        api_info_str = f"API_ENDPOINT: {api_endpoint}"
        if api_parameters:
            import json
            api_info_str += f" || API_PARAMS: {json.dumps(api_parameters)}"
    
    for t in tests:
        nodeid = t.get("nodeid", "unknown")
        outcome = (t.get("outcome") or "unknown").lower()
        if outcome not in ("passed", "failed", "skipped"):
            outcome = "failed" if outcome in ("error",) else "passed"
        
        duration = t.get("duration", 0.0)
        if duration is None:
            duration = 0.0
        else:
            duration = float(duration)
        
        # Get error message from call.longrepr
        error_message = None
        call = t.get("call") or {}
        if isinstance(call, dict):
            longrepr = call.get("longrepr")
            if longrepr and isinstance(longrepr, str):
                error_message = longrepr
                # Add API endpoint info to summary test for comparison parser
                if "::summary" in nodeid and api_info_str:
                    error_message = api_info_str + " || " + error_message
        
        # If no error message but failed, try metadata
        if not error_message and outcome == "failed":
            metadata = t.get("metadata", {})
            if isinstance(metadata, dict):
                field_comparisons = metadata.get("field_comparisons", [])
                if field_comparisons:
                    parts = []
                    for fc in field_comparisons:
                        if fc.get("result_type") == "mismatch":
                            parts.append(
                                f"{fc.get('field_name')}: UI='{fc.get('ui_value')}' "
                                f"API='{fc.get('api_value')}'"
                            )
                        elif fc.get("result_type") == "missing_in_ui":
                            parts.append(f"{fc.get('field_name')}: missing in UI")
                        elif fc.get("result_type") == "missing_in_api":
                            parts.append(f"{fc.get('field_name')}: missing in API")
                    if parts:
                        error_message = " | ".join(parts)
        
        tests_data.append({
            "nodeid": nodeid,
            "status": outcome,
            "duration": duration,
            "error_message": error_message,
        })
    
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
