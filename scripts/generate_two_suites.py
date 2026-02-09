#!/usr/bin/env python3
"""Generate two test-suite JSON files in execution_report format.

Matches the structure you use: created, duration, exitcode, root, environment,
summary, collectors, tests (with metadata, setup/call/teardown, stdout/stderr, log).

Usage:
  python scripts/generate_two_suites.py
  python scripts/generate_two_suites.py -d reports/

Output (default: project root):
  - suite_login_requests.json   (e.g. login + CHO request tests)
  - suite_api_validation.json   (e.g. API and validation tests)
"""

import argparse
import json
import sys
import time
from pathlib import Path


def make_log_entry(level: str, msg: str, pathname: str, lineno: int, func_name: str):
    t = time.time()
    return {
        "name": "utils.my_logging",
        "msg": msg,
        "args": None,
        "levelname": level,
        "levelno": 20 if level == "INFO" else 30,
        "pathname": pathname,
        "filename": Path(pathname).name,
        "module": Path(pathname).stem,
        "exc_info": None,
        "exc_text": None,
        "stack_info": None,
        "lineno": lineno,
        "funcName": func_name,
        "created": t,
        "msecs": 0,
        "relativeCreated": 0,
        "thread": 12345,
        "threadName": "MainThread",
        "processName": "MainProcess",
        "process": 1,
        "taskName": None,
        "asctime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)),
    }


def make_test(
    nodeid: str,
    lineno: int,
    outcome: str,
    test_case_id: int,
    test_case_name: str,
    test_suite_id: int,
    setup_duration: float,
    call_duration: float,
    teardown_duration: float,
    call_stdout: str = "",
    call_stderr: str = "",
    call_longrepr: str | None = None,
    teardown_stderr: str = "",
    log_entries: list | None = None,
) -> dict:
    setup_outcome = "passed"
    call_outcome = outcome
    teardown_outcome = "passed"
    if outcome == "skipped":
        call_longrepr = call_longrepr or "Skipped: condition not met"
    if log_entries is None:
        log_entries = []
    test = {
        "nodeid": nodeid,
        "lineno": lineno,
        "outcome": outcome,
        "keywords": [nodeid.split("::")[-1] if "::" in nodeid else nodeid, "tests"],
        "metadata": {
            "test_case_id": test_case_id,
            "test_case_name": test_case_name,
            "test_suite_id": test_suite_id,
        },
        "setup": {
            "duration": setup_duration,
            "outcome": setup_outcome,
            "stdout": "Test data loaded from executionRequestPayload.json\nMatch found\nDEBUG matching_test_case",
        },
        "call": {
            "duration": call_duration,
            "outcome": call_outcome,
            "stdout": call_stdout,
            "stderr": call_stderr,
            "log": log_entries,
        },
        "teardown": {
            "duration": teardown_duration,
            "outcome": teardown_outcome,
            "stderr": teardown_stderr,
        },
    }
    if call_longrepr is not None:
        test["call"]["longrepr"] = call_longrepr
    return test


def suite_login_requests() -> dict:
    """First suite: login and CHO request / mandatory fields style tests."""
    root = "C:\\Users\\C00660\\Desktop\\CHO\\learning\\applications\\cho\\new_ui\\tests\\create_request"
    created = time.time() - 40
    tests = [
        make_test(
            nodeid="test_cho_requests.py::Test_Generated::test_create_1_01_cho_request_cho_user_mandatory_fields",
            lineno=236,
            outcome="passed",
            test_case_id=28,
            test_case_name="Create 1.01 | CHO Request | CHO User | Mandatory Fields",
            test_suite_id=4,
            setup_duration=7.04,
            call_duration=29.57,
            teardown_duration=0.55,
            call_stdout="Test data for this test:\nCreated request with ID: 97\n[SKIP] Request Number is empty.\n[SKIP] Correspondence Date is empty.",
            call_stderr="2026-02-09 02:12:28,883 - INFO - Starting login.\n2026-02-09 02:12:34,530 - INFO - Currently logged-in user is: CHO2 A.",
            teardown_stderr="2026-02-09 02:12:58,421 - INFO - TEST PASSED: test_cho_requests.py::Test_Generated::test_create_1_01_cho_request_cho_user_mandatory_fields\n",
            log_entries=[
                make_log_entry("INFO", "Starting login.", f"{root}\\..\\pages\\refactor\\login_page.py", 47, "login"),
                make_log_entry("INFO", "Currently logged-in user is: CHO2 A.", f"{root}\\..\\pages\\refactor\\login_page.py", 62, "login"),
            ],
        ),
        make_test(
            nodeid="test_cho_requests.py::Test_Generated::test_create_1_02_cho_request_optional_fields",
            lineno=248,
            outcome="passed",
            test_case_id=29,
            test_case_name="Create 1.02 | CHO Request | Optional Fields",
            test_suite_id=4,
            setup_duration=6.2,
            call_duration=18.3,
            teardown_duration=0.4,
            call_stdout="Created request with ID: 98",
            call_stderr="INFO - Login skipped (session active).",
        ),
        make_test(
            nodeid="test_login.py::test_login_invalid_password",
            lineno=52,
            outcome="failed",
            test_case_id=10,
            test_case_name="Login | Invalid password",
            test_suite_id=1,
            setup_duration=2.1,
            call_duration=1.5,
            teardown_duration=0.2,
            call_longrepr="AssertionError: Expected redirect to dashboard, got 401\n\n  test_login.py:52",
            call_stderr="INFO - Login attempt failed.",
        ),
    ]
    total_duration = sum(
        t["setup"]["duration"] + t["call"]["duration"] + t["teardown"]["duration"] for t in tests
    )
    passed = sum(1 for t in tests if t["outcome"] == "passed")
    return {
        "created": created,
        "duration": total_duration,
        "exitcode": 1 if passed < len(tests) else 0,
        "root": root,
        "environment": {},
        "summary": {"passed": passed, "failed": len(tests) - passed, "skipped": 0, "total": len(tests), "collected": len(tests)},
        "collectors": [
            {
                "nodeid": "",
                "outcome": "passed",
                "result": [
                    {"nodeid": t["nodeid"], "type": "Function", "Lineno": t["lineno"]}
                    for t in tests
                ],
            }
        ],
        "tests": tests,
    }


def suite_api_validation() -> dict:
    """Second suite: API and validation style tests."""
    root = "C:\\Users\\C00660\\Desktop\\CHO\\learning\\applications\\cho\\api_tests"
    created = time.time() - 120
    tests = [
        make_test(
            nodeid="test_api_requests.py::Test_API::test_create_request_returns_201",
            lineno=88,
            outcome="passed",
            test_case_id=41,
            test_case_name="API | Create request returns 201",
            test_suite_id=5,
            setup_duration=1.2,
            call_duration=0.45,
            teardown_duration=0.05,
            call_stdout="Response status: 201\nRequest ID: 101",
        ),
        make_test(
            nodeid="test_api_requests.py::Test_API::test_create_request_validation_error",
            lineno=95,
            outcome="failed",
            test_case_id=42,
            test_case_name="API | Create request validation error",
            test_suite_id=5,
            setup_duration=1.0,
            call_duration=0.12,
            teardown_duration=0.03,
            call_longrepr="AssertionError: Expected 400, got 500\n\n  test_api_requests.py:95",
            call_stderr="ERROR - Server error 500",
        ),
        make_test(
            nodeid="test_validation.py::test_attachments_label_consistency",
            lineno=22,
            outcome="skipped",
            test_case_id=50,
            test_case_name="Validation | Attachments label consistency",
            test_suite_id=6,
            setup_duration=0.5,
            call_duration=0.01,
            teardown_duration=0.02,
            call_longrepr="Skipped: labels mismatch (attachments vs attachment) - see Labels mismatch dashboard",
        ),
    ]
    total_duration = sum(
        t["setup"]["duration"] + t["call"]["duration"] + t["teardown"]["duration"] for t in tests
    )
    passed = sum(1 for t in tests if t["outcome"] == "passed")
    failed = sum(1 for t in tests if t["outcome"] == "failed")
    skipped = sum(1 for t in tests if t["outcome"] == "skipped")
    return {
        "created": created,
        "duration": total_duration,
        "exitcode": 1 if failed else 0,
        "root": root,
        "environment": {},
        "summary": {"passed": passed, "failed": failed, "skipped": skipped, "total": len(tests), "collected": len(tests)},
        "collectors": [
            {
                "nodeid": "",
                "outcome": "passed",
                "result": [
                    {"nodeid": t["nodeid"], "type": "Function", "Lineno": t["lineno"]}
                    for t in tests
                ],
            }
        ],
        "tests": tests,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate two test-suite JSON files (execution_report format)")
    parser.add_argument(
        "-d", "--dir",
        default=".",
        help="Output directory for the two JSON files (default: current dir)",
    )
    args = parser.parse_args()
    out_dir = Path(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = [
        ("suite_login_requests.json", suite_login_requests()),
        ("suite_api_validation.json", suite_api_validation()),
    ]
    for filename, data in files:
        path = out_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Wrote {path} ({len(data['tests'])} tests)", file=sys.stderr)

    print(f"\nGenerated 2 suite files in {out_dir.resolve()}. Upload them to a run via 'Add test results'.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
