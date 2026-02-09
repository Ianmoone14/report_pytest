#!/usr/bin/env python3
"""Generate a sample pytest JSON report for testing the Report Viewer.

Supports two formats:
  1. pytest-json-report style (--format pytest)
  2. Simple custom format (--format simple)

Usage:
  python scripts/make_sample_report.py -o sample_report.json
  python scripts/make_sample_report.py -o sample_report.json --format simple --project my-api
"""

import argparse
import json
import sys
from pathlib import Path


def make_pytest_format(project: str = "default") -> dict:
    """pytest-json-report plugin style."""
    return {
        "created": 0,
        "duration": 2.5,
        "environment": {"project": project},
        "summary": {"passed": 2, "failed": 1, "skipped": 1, "total": 4},
        "tests": [
            {
                "nodeid": "tests/test_login.py::test_login_success",
                "outcome": "passed",
                "duration": 0.12,
                "setup": {"outcome": "passed"},
                "call": {"outcome": "passed"},
                "teardown": {"outcome": "passed"},
            },
            {
                "nodeid": "tests/test_login.py::test_login_invalid_password",
                "outcome": "passed",
                "duration": 0.08,
                "setup": {"outcome": "passed"},
                "call": {"outcome": "passed"},
                "teardown": {"outcome": "passed"},
            },
            {
                "nodeid": "tests/test_api.py::test_create_user",
                "outcome": "failed",
                "duration": 0.45,
                "setup": {"outcome": "passed"},
                "call": {
                    "outcome": "failed",
                    "longrepr": "AssertionError: Expected status 201, got 500\n\n  tests/test_api.py:42",
                },
                "teardown": {"outcome": "passed"},
            },
            {
                "nodeid": "tests/test_legacy.py::test_old_flow",
                "outcome": "skipped",
                "duration": 0.01,
                "setup": {"outcome": "passed"},
                "call": {"outcome": "skipped", "longrepr": "Skipped: deprecated"},
                "teardown": {"outcome": "passed"},
            },
        ],
    }


def make_simple_format(project: str = "default") -> dict:
    """Simple custom format."""
    return {
        "project": project,
        "results": [
            {"nodeid": "tests/test_login.py::test_login_success", "status": "passed", "duration": 0.12},
            {"nodeid": "tests/test_login.py::test_login_invalid_password", "status": "passed", "duration": 0.08},
            {
                "nodeid": "tests/test_api.py::test_create_user",
                "status": "failed",
                "duration": 0.45,
                "error_message": "AssertionError: Expected status 201, got 500",
            },
            {
                "nodeid": "tests/test_legacy.py::test_old_flow",
                "status": "skipped",
                "duration": 0.01,
                "error_message": "Skipped: deprecated",
            },
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate sample pytest JSON report")
    parser.add_argument("-o", "--output", default="sample_report.json", help="Output JSON file path")
    parser.add_argument(
        "--format",
        choices=("pytest", "simple"),
        default="pytest",
        help="Report format",
    )
    parser.add_argument("--project", default="default", help="Project name")
    args = parser.parse_args()

    if args.format == "pytest":
        data = make_pytest_format(project=args.project)
    else:
        data = make_simple_format(project=args.project)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {out} ({args.format} format, project={args.project})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
