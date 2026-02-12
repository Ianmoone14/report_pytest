"""
Generate comparison report in format compatible with pytest report viewer.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .comparator import Comparator, RecordComparison, ComparisonSummary
from .page_object import PageObject


def generate_comparison_report(
    ui_data: List[Dict[str, Any]],
    api_data: List[Dict[str, Any]],
    page_object: PageObject,
    comparator: Optional[Comparator] = None,
    project_name: str = "ui_api_comparison",
    run_name: Optional[str] = None,
    api_endpoint: Optional[str] = None,
    api_parameters: Optional[Dict[str, Any]] = None,
    test_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a comparison report compatible with pytest report viewer format.
    
    Args:
        ui_data: List of UI records (normalized)
        api_data: List of API records (normalized)
        page_object: PageObject with label mapping
        comparator: Optional Comparator instance (creates one if not provided)
        project_name: Project name for the report
        run_name: Optional run name
    
    Returns:
        Dict in pytest report format with comparison results as test cases
    """
    if comparator is None:
        comparator = Comparator(page_object=page_object)
    
    # Perform comparison
    comparisons = comparator.compare_records(ui_data, api_data)
    summary = comparator.get_summary(comparisons)
    
    # Generate test cases from comparison results
    tests = []
    
    # Overall summary test
    tests.append({
        "nodeid": f"{page_object.page_name}::summary",
        "outcome": "passed" if summary.matched_records == summary.total_records else "failed",
        "duration": 0.0,
        "setup": {"duration": 0.0},
        "call": {
            "duration": 0.0,
            "longrepr": f"Total: {summary.total_records}, Matched: {summary.matched_records}, "
                       f"Mismatched: {summary.mismatched_records}, "
                       f"Missing in UI: {summary.records_with_missing_ui}, "
                       f"Missing in API: {summary.records_with_missing_api}"
        },
        "teardown": {"duration": 0.0},
        "metadata": {
            "comparison_type": "summary",
            "total_records": summary.total_records,
            "matched_records": summary.matched_records,
            "mismatched_records": summary.mismatched_records,
        }
    })
    
    # One test per record comparison
    for comp in comparisons:
        if comp.overall_match:
            outcome = "passed"
            longrepr = None
        else:
            outcome = "failed"
            mismatches = [fc for fc in comp.field_comparisons if fc.result_type.value == "mismatch"]
            missing_ui = [fc for fc in comp.field_comparisons if fc.result_type.value == "missing_in_ui"]
            missing_api = [fc for fc in comp.field_comparisons if fc.result_type.value == "missing_in_api"]
            
            parts = []
            if mismatches:
                mismatch_details = []
                for fc in mismatches:
                    ui_val = str(fc.ui_value) if fc.ui_value is not None else "null"
                    api_val = str(fc.api_value) if fc.api_value is not None else "null"
                    mismatch_details.append(f"{fc.field_name}: UI='{ui_val}' API='{api_val}'")
                parts.append("Mismatches: " + " | ".join(mismatch_details))
            if missing_ui:
                parts.append(f"Missing in UI: {', '.join(fc.field_name for fc in missing_ui)}")
            if missing_api:
                parts.append(f"Missing in API: {', '.join(fc.field_name for fc in missing_api)}")
            longrepr = " || ".join(parts) if len(parts) > 1 else (parts[0] if parts else None)
        
        # Get original UI and API data for this record
        ui_record = ui_data[comp.record_index] if comp.record_index < len(ui_data) else {}
        api_record = api_data[comp.record_index] if comp.record_index < len(api_data) else {}
        
        # Build comprehensive error message with ALL fields
        # Format: "ALL_UI: field1=value1|field2=value2 || ALL_API: field1=value1|field2=value2 || MISMATCHES: ... || MISSING_UI: ... || MISSING_API: ..."
        all_parts = []
        
        # Add all UI fields
        if ui_record:
            ui_fields = "|".join([f"{k}={v}" for k, v in ui_record.items()])
            all_parts.append(f"ALL_UI: {ui_fields}")
        
        # Add all API fields
        if api_record:
            api_fields = "|".join([f"{k}={v}" for k, v in api_record.items()])
            all_parts.append(f"ALL_API: {api_fields}")
        
        # Add mismatches, missing UI, missing API
        if mismatches:
            mismatch_details = []
            for fc in mismatches:
                ui_val = str(fc.ui_value) if fc.ui_value is not None else "null"
                api_val = str(fc.api_value) if fc.api_value is not None else "null"
                mismatch_details.append(f"{fc.field_name}: UI='{ui_val}' API='{api_val}'")
            all_parts.append("MISMATCHES: " + " | ".join(mismatch_details))
        
        if missing_ui:
            all_parts.append(f"MISSING_UI: {', '.join(fc.field_name for fc in missing_ui)}")
        if missing_api:
            all_parts.append(f"MISSING_API: {', '.join(fc.field_name for fc in missing_api)}")
        
        comprehensive_longrepr = " || ".join(all_parts)
        
        tests.append({
            "nodeid": f"{page_object.page_name}::record_{comp.record_index}",
            "outcome": outcome,
            "duration": 0.0,
            "setup": {"duration": 0.0},
            "call": {
                "duration": 0.0,
                "longrepr": comprehensive_longrepr,
            },
            "teardown": {"duration": 0.0},
            "metadata": {
                "comparison_type": "record",
                "record_index": comp.record_index,
                "overall_match": comp.overall_match,
                "ui_data": {k: str(v) if v is not None else None for k, v in ui_record.items()},
                "api_data": {k: str(v) if v is not None else None for k, v in api_record.items()},
                "field_comparisons": [
                    {
                        "field_name": fc.field_name,
                        "ui_value": str(fc.ui_value) if fc.ui_value is not None else None,
                        "api_value": str(fc.api_value) if fc.api_value is not None else None,
                        "result_type": fc.result_type.value,
                    }
                    for fc in comp.field_comparisons
                ]
            }
        })
    
    # Build report in pytest format
    report = {
        "project": project_name,
        "environment": {
            "project": project_name,
            "run_name": run_name or f"UI vs API Comparison - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "page_object": page_object.to_dict(),
            "test_name": test_name,
            "api_endpoint": api_endpoint,
            "api_parameters": api_parameters,
            "comparison_summary": {
                "total_records": summary.total_records,
                "matched_records": summary.matched_records,
                "mismatched_records": summary.mismatched_records,
                "records_with_missing_ui": summary.records_with_missing_ui,
                "records_with_missing_api": summary.records_with_missing_api,
                "total_fields_compared": summary.total_fields_compared,
                "matched_fields": summary.matched_fields,
                "mismatched_fields": summary.mismatched_fields,
                "missing_in_ui_fields": summary.missing_in_ui_fields,
                "missing_in_api_fields": summary.missing_in_api_fields,
            }
        },
        "tests": tests
    }
    
    return report
