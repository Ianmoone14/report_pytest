"""
Parse UI vs API comparison data from test results.

Extracts structured comparison data from test result error messages and nodeids.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


def is_comparison_run(results: List[Any]) -> bool:
    """
    Check if a run is a UI vs API comparison run.
    
    Args:
        results: List of TestResult objects
    
    Returns:
        True if this appears to be a comparison run
    """
    if not results:
        return False
    
    # Check if any test has a nodeid pattern like "PageName::summary" or "PageName::record_N"
    for r in results:
        if r.nodeid and "::" in r.nodeid and ("summary" in r.nodeid or "record_" in r.nodeid):
            return True
    
    return False


def parse_comparison_data(results: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Parse comparison data from test results.
    
    Groups by test (each test can have its own summary and records).
    
    Args:
        results: List of TestResult objects
    
    Returns:
        Dict with comparison data structure, or None if not a comparison run
    """
    if not is_comparison_run(results):
        return None
    
    # Group tests by test name (everything before ::summary or ::record_)
    tests_dict = {}
    
    for r in results:
        if not r.nodeid or "::" not in r.nodeid:
            continue
        
        test_name = r.nodeid.split("::")[0]
        if test_name not in tests_dict:
            tests_dict[test_name] = {
                "test_name": test_name,
                "summary_test": None,
                "record_tests": [],
                "api_endpoint": None,
                "api_parameters": None,
            }
        
        if "::summary" in r.nodeid:
            tests_dict[test_name]["summary_test"] = r
        elif "::record_" in r.nodeid:
            tests_dict[test_name]["record_tests"].append(r)
    
    if not tests_dict:
        return None
    
    # Parse each test
    tests = []
    for test_name, test_data in tests_dict.items():
        summary_test = test_data["summary_test"]
        if not summary_test:
            continue
        
        # Try to get API endpoint and parameters from error_message
        api_endpoint = None
        api_parameters = None
        
        if summary_test.error_message:
            # Format: "API_ENDPOINT: /api/v1/users || API_PARAMS: {...} || Total: ..."
            endpoint_match = re.search(r"API_ENDPOINT:\s*([^|]+)", summary_test.error_message)
            if endpoint_match:
                api_endpoint = endpoint_match.group(1).strip()
            
            params_match = re.search(r"API_PARAMS:\s*(\{.*?\})(?:\s*\|\||$)", summary_test.error_message)
            if params_match:
                import json
                try:
                    api_parameters = json.loads(params_match.group(1))
                except:
                    pass
        
        # Parse summary
        summary_info = _parse_summary(summary_test.error_message)
        
        # Parse records with full UI/API data
        records = []
        for r in sorted(test_data["record_tests"], key=lambda x: _extract_record_index(x.nodeid)):
            record_data = _parse_record_comparison_full(r)
            if record_data:
                records.append(record_data)
        
        tests.append({
            "test_name": test_name,
            "summary": summary_info,
            "records": records,
            "api_endpoint": api_endpoint,
            "api_parameters": api_parameters,
        })
    
    return {
        "tests": tests,
    }


def _parse_summary(error_message: Optional[str]) -> Dict[str, Any]:
    """Parse summary information from error message."""
    if not error_message:
        return {}
    
    # Format: "Total: 5, Matched: 0, Mismatched: 5, Missing in UI: 0, Missing in API: 2"
    summary = {}
    patterns = {
        "total_records": r"Total:\s*(\d+)",
        "matched_records": r"Matched:\s*(\d+)",
        "mismatched_records": r"Mismatched:\s*(\d+)",
        "missing_in_ui": r"Missing in UI:\s*(\d+)",
        "missing_in_api": r"Missing in API:\s*(\d+)",
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, error_message)
        if match:
            summary[key] = int(match.group(1))
    
    return summary


def _extract_record_index(nodeid: str) -> int:
    """Extract record index from nodeid like 'PageName::record_0'."""
    match = re.search(r"record_(\d+)", nodeid)
    return int(match.group(1)) if match else 999


def _parse_record_comparison_full(test_result: Any) -> Optional[Dict[str, Any]]:
    """
    Parse full record comparison including all UI and API data.
    
    Format: "ALL_UI: field1=value1|field2=value2 || ALL_API: field1=value1|field2=value2 || MISMATCHES: ... || MISSING_UI: ... || MISSING_API: ..."
    """
    if not test_result.error_message:
        return None
    
    record_index = _extract_record_index(test_result.nodeid)
    
    # Parse ALL_UI section
    # Format: "ALL_UI: field1=value1|field2=value2 || ALL_API: ..."
    ui_data = {}
    # Match everything from ALL_UI: until || or end of string
    all_ui_match = re.search(r"ALL_UI:\s*(.*?)(?:\s*\|\||$)", test_result.error_message)
    if all_ui_match:
        ui_section = all_ui_match.group(1).strip()
        # Split by | to get individual field=value pairs
        for pair in ui_section.split("|"):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                ui_data[key.strip()] = value.strip()
    
    # Parse ALL_API section
    # Format: "ALL_API: field1=value1|field2=value2 || MISMATCHES: ..."
    api_data = {}
    # Match everything from ALL_API: until || or end of string
    all_api_match = re.search(r"ALL_API:\s*(.*?)(?:\s*\|\||$)", test_result.error_message)
    if all_api_match:
        api_section = all_api_match.group(1).strip()
        for pair in api_section.split("|"):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                api_data[key.strip()] = value.strip()
    
    # Parse MISMATCHES section
    # Format: "MISMATCHES: field1: UI='val1' API='val2' | field2: UI='val3' API='val4' || MISSING_UI: ..."
    mismatches = []
    mismatches_match = re.search(r"MISMATCHES:\s*(.*?)(?:\s*\|\||$)", test_result.error_message)
    if mismatches_match:
        mismatch_section = mismatches_match.group(1).strip()
        # Match pattern: "field: UI='value' API='value'"
        mismatch_pattern = r"([^:]+):\s*UI='([^']*)'\s*API='([^']*)'"
        for match in re.finditer(mismatch_pattern, mismatch_section):
            mismatches.append({
                "field": match.group(1).strip(),
                "ui_value": match.group(2),
                "api_value": match.group(3),
            })
    
    # Parse MISSING_UI section
    missing_ui = []
    missing_ui_match = re.search(r"MISSING_UI:\s*(.*?)(?:\s*\|\||$)", test_result.error_message)
    if missing_ui_match:
        missing_ui_str = missing_ui_match.group(1).strip()
        if missing_ui_str:
            missing_ui = [f.strip() for f in missing_ui_str.split(",") if f.strip()]
    
    # Parse MISSING_API section
    missing_api = []
    missing_api_match = re.search(r"MISSING_API:\s*(.*?)(?:\s*\|\||$)", test_result.error_message)
    if missing_api_match:
        missing_api_str = missing_api_match.group(1).strip()
        if missing_api_str:
            missing_api = [f.strip() for f in missing_api_str.split(",") if f.strip()]
    
    # Get all unique fields from both UI and API
    all_fields = sorted(set(list(ui_data.keys()) + list(api_data.keys())))
    
    return {
        "record_index": record_index,
        "nodeid": test_result.nodeid,
        "status": test_result.status,
        "ui_data": ui_data,
        "api_data": api_data,
        "all_fields": all_fields,
        "mismatches": mismatches,
        "missing_in_ui": missing_ui,
        "missing_in_api": missing_api,
        "overall_match": test_result.status == "passed",
    }


def _parse_record_comparison(test_result: Any) -> Optional[Dict[str, Any]]:
    """
    Parse record comparison from test result error message.
    
    Format examples:
    - "Mismatches: age: UI='30' API='25' | email: UI='test@example.com' API='test@demo.com'"
    - "Mismatches: age: UI='30' API='25' || Missing in API: status"
    - "Mismatches: age: UI='30' API='25' || Missing in UI: extra_field || Missing in API: status"
    """
    if not test_result.error_message:
        return None
    
    record_index = _extract_record_index(test_result.nodeid)
    
    # Parse mismatches with values
    # Format: "Mismatches: field1: UI='val1' API='val2' | field2: UI='val3' API='val4' || Missing in UI: ..."
    mismatches = []
    if "Mismatches:" in test_result.error_message:
        # Extract everything after "Mismatches:" until "||" or end
        mismatch_match = re.search(r"Mismatches:\s*([^|]+?)(?:\s*\|\||$)", test_result.error_message)
        if mismatch_match:
            mismatch_section = mismatch_match.group(1).strip()
            # Parse individual mismatches: "field: UI='value' API='value'"
            # Handle both " | " and "|" separators
            mismatch_pattern = r"([^:]+):\s*UI='([^']*)'\s*API='([^']*)'"
            for match in re.finditer(mismatch_pattern, mismatch_section):
                mismatches.append({
                    "field": match.group(1).strip(),
                    "ui_value": match.group(2),
                    "api_value": match.group(3),
                })
    
    # Parse missing in UI
    # Format: "Missing in UI: field1, field2 || Missing in API: ..."
    missing_ui = []
    missing_ui_match = re.search(r"Missing in UI:\s*([^|]+?)(?:\s*\|\||$)", test_result.error_message)
    if missing_ui_match:
        missing_ui = [f.strip() for f in missing_ui_match.group(1).split(",")]
    
    # Parse missing in API
    missing_api = []
    missing_api_match = re.search(r"Missing in API:\s*([^|]+?)(?:\s*\|\||$)", test_result.error_message)
    if missing_api_match:
        missing_api = [f.strip() for f in missing_api_match.group(1).split(",")]
    
    return {
        "record_index": record_index,
        "nodeid": test_result.nodeid,
        "status": test_result.status,
        "mismatches": mismatches,
        "missing_in_ui": missing_ui,
        "missing_in_api": missing_api,
        "overall_match": test_result.status == "passed",
    }


def extract_field_values_from_error(error_message: Optional[str], field_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Try to extract UI and API values for a field from error message.
    
    Format: "field_name: UI='value' API='value'"
    """
    if not error_message:
        return None, None
    
    pattern = rf"{re.escape(field_name)}:\s*UI='([^']+)'\s*API='([^']+)'"
    match = re.search(pattern, error_message)
    if match:
        return match.group(1), match.group(2)
    
    return None, None
