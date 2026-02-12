"""
Example/dummy data generator for testing UI vs API comparison.

This generates sample UI and API data, plus a page object with mapping.
"""

from typing import List, Dict, Any
import random

from .page_object import PageObject
from .extractor import UIExtractor, APIExtractor, UIExtractionType
from .comparator import Comparator
from .report_generator import generate_comparison_report


def generate_example_ui_data(num_records: int = 5) -> List[Dict[str, Any]]:
    """
    Generate example UI data (as if extracted from UI).
    
    Args:
        num_records: Number of records to generate
    
    Returns:
        List of UI records with UI labels as keys
    """
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
    domains = ["example.com", "test.com", "demo.org"]
    
    records = []
    for i in range(num_records):
        first = random.choice(first_names)
        last = random.choice(last_names)
        email = f"{first.lower()}.{last.lower()}@{random.choice(domains)}"
        age = random.randint(20, 60)
        
        # Simulate UI labels (different from API keys)
        records.append({
            "Full Name": f"{first} {last}",
            "Email Address": email,
            "Age (years)": str(age),
            "Status": random.choice(["Active", "Inactive", "Pending"]),
        })
    
    return records


def generate_example_api_data(num_records: int = 5) -> List[Dict[str, Any]]:
    """
    Generate example API data (as if from API responses).
    
    Args:
        num_records: Number of records to generate
    
    Returns:
        List of API records with API keys as keys
    """
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
    domains = ["example.com", "test.com", "demo.org"]
    
    records = []
    for i in range(num_records):
        first = random.choice(first_names)
        last = random.choice(last_names)
        email = f"{first.lower()}.{last.lower()}@{random.choice(domains)}"
        age = random.randint(20, 60)
        
        # Simulate API keys (different from UI labels)
        records.append({
            "name": f"{first} {last}",
            "email": email,
            "age": age,  # Note: API returns int, UI returns string
            "status": random.choice(["active", "inactive", "pending"]),  # Lowercase in API
        })
    
    return records


def create_example_page_object() -> PageObject:
    """
    Create example page object with UI label to API key mapping.
    
    Returns:
        PageObject instance
    """
    return PageObject(
        page_name="User List",
        ui_to_api_mapping={
            "Full Name": "name",
            "Email Address": "email",
            "Age (years)": "age",
            "Status": "status",
        },
        extraction_type="table",
        description="Example user list page with table extraction"
    )


def generate_example_data(
    num_records: int = 1,  # Default to 1 record
    introduce_mismatches: bool = True
) -> Dict[str, Any]:
    """
    Generate complete example data for testing.
    
    Args:
        num_records: Number of records to generate
        introduce_mismatches: Whether to introduce some mismatches for testing
    
    Returns:
        Dict with:
        - ui_data: List of UI records
        - api_data: List of API records
        - page_object: PageObject instance
        - comparison_report: Generated report dict
    """
    # Generate data
    ui_data_raw = generate_example_ui_data(num_records)
    api_data_raw = generate_example_api_data(num_records)
    
    # Create page object
    page_object = create_example_page_object()
    
    # Extract/normalize data
    ui_extractor = UIExtractor(UIExtractionType.TABLE)
    api_extractor = APIExtractor()
    
    # Use page object mapping for UI extraction
    ui_data = ui_extractor.extract(ui_data_raw, field_mapping=page_object.ui_to_api_mapping)
    
    # API data is already normalized (keys match API keys)
    api_data = api_extractor.extract(api_data_raw)
    
    # Introduce some mismatches if requested (works with single record)
    if introduce_mismatches and len(ui_data) > 0 and len(api_data) > 0:
        # Modify first record to create mismatches
        if "name" in ui_data[0]:
            ui_data[0]["name"] = "Modified Name"
        # Change age to create mismatch
        if "age" in ui_data[0] and "age" in api_data[0]:
            ui_data[0]["age"] = str(int(api_data[0]["age"]) + 5)  # Make age different
        # Change email to create mismatch
        if "email" in ui_data[0] and "email" in api_data[0]:
            ui_data[0]["email"] = api_data[0]["email"].replace("@", ".modified@")
        # Change status case to create mismatch
        if "status" in ui_data[0] and "status" in api_data[0]:
            ui_data[0]["status"] = "Active" if api_data[0]["status"] != "active" else "Inactive"
        # Optionally remove a field from API to create "missing in API" (only if multiple records)
        if len(api_data) > 1 and "status" in api_data[1]:
            del api_data[1]["status"]
        # Add extra field in UI that doesn't exist in API (only if multiple records)
        if len(ui_data) > 2:
            ui_data[2]["extra_ui_field"] = "This field only exists in UI"
    
    # Perform comparison
    comparator = Comparator(page_object=page_object)
    comparisons = comparator.compare_records(ui_data, api_data)
    summary = comparator.get_summary(comparisons)
    
    # Generate report
    comparison_report = generate_comparison_report(
        ui_data=ui_data,
        api_data=api_data,
        page_object=page_object,
        comparator=comparator,
        project_name="example_ui_api_comparison",
        run_name="Example Comparison Run",
        api_endpoint="/api/v1/users",
        api_parameters={"limit": 10, "offset": 0},
        test_name="User List Comparison"
    )
    
    return {
        "ui_data_raw": ui_data_raw,
        "api_data_raw": api_data_raw,
        "ui_data": ui_data,
        "api_data": api_data,
        "page_object": page_object,
        "comparisons": comparisons,
        "summary": summary,
        "comparison_report": comparison_report,
    }


if __name__ == "__main__":
    # Example usage
    print("Generating example UI vs API comparison data...")
    result = generate_example_data(num_records=1, introduce_mismatches=True)
    
    print(f"\nPage Object: {result['page_object'].page_name}")
    print(f"UI to API Mapping: {result['page_object'].ui_to_api_mapping}")
    
    print(f"\nUI Data (normalized): {len(result['ui_data'])} records")
    for i, record in enumerate(result['ui_data'][:3]):
        print(f"  Record {i}: {record}")
    
    print(f"\nAPI Data (normalized): {len(result['api_data'])} records")
    for i, record in enumerate(result['api_data'][:3]):
        print(f"  Record {i}: {record}")
    
    print(f"\nComparison Summary:")
    s = result['summary']
    print(f"  Total records: {s.total_records}")
    print(f"  Matched: {s.matched_records}")
    print(f"  Mismatched: {s.mismatched_records}")
    print(f"  Missing in UI: {s.records_with_missing_ui}")
    print(f"  Missing in API: {s.records_with_missing_api}")
    
    print(f"\nReport generated with {len(result['comparison_report']['tests'])} test cases")
    print(f"Report project: {result['comparison_report']['project']}")
