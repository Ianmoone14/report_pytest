"""
Generate example UI vs API comparison reports for testing.

Creates multiple test report files - one JSON file per test.
Each file can be uploaded separately to the report viewer.

Usage:
    python scripts/generate_ui_api_example.py
    python scripts/generate_ui_api_example.py --endpoint /api/v1/custom --params '{"id": 123}'
"""

import json
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import ui_api_comparison
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui_api_comparison.example import generate_example_data
from ui_api_comparison import (
    PageObject,
    UIExtractor,
    APIExtractor,
    UIExtractionType,
    Comparator,
    generate_comparison_report
)


def generate_test_report(
    test_name: str,
    page_name: str,
    ui_to_api_mapping: dict,
    api_endpoint: str,
    api_parameters: dict,
    num_records: int = 1,  # Default to 1 record per test
    introduce_mismatches: bool = True
):
    """Generate a single test report."""
    from ui_api_comparison.example import (
        generate_example_ui_data,
        generate_example_api_data
    )
    
    # Generate data
    ui_data_raw = generate_example_ui_data(num_records)
    api_data_raw = generate_example_api_data(num_records)
    
    # Create page object
    page_object = PageObject(
        page_name=page_name,
        ui_to_api_mapping=ui_to_api_mapping,
        extraction_type="table"
    )
    
    # Extract/normalize data
    ui_extractor = UIExtractor(UIExtractionType.TABLE)
    api_extractor = APIExtractor()
    
    ui_data = ui_extractor.extract(ui_data_raw, field_mapping=page_object.ui_to_api_mapping)
    api_data = api_extractor.extract(api_data_raw)
    
    # Introduce mismatches if requested (for single record)
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
        # Optionally remove a field from API to create "missing in API"
        if len(api_data) > 0 and "status" in api_data[0]:
            # Don't delete, just make it different - we want to show mismatches, not missing
            pass
    
    # Generate report
    comparator = Comparator(page_object=page_object)
    report = generate_comparison_report(
        ui_data=ui_data,
        api_data=api_data,
        page_object=page_object,
        comparator=comparator,
        project_name="example_ui_api_comparison",
        run_name=None,  # Will be set per test
        api_endpoint=api_endpoint,
        api_parameters=api_parameters,
        test_name=test_name
    )
    
    return report


def main():
    """Generate multiple test report files - one per test."""
    parser = argparse.ArgumentParser(
        description="Generate UI vs API comparison test reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate default examples
  python scripts/generate_ui_api_example.py
  
  # Generate with custom endpoint
  python scripts/generate_ui_api_example.py --endpoint /api/v1/custom --params '{"id": 123}'
  
  # Generate single test with custom endpoint
  python scripts/generate_ui_api_example.py --single --endpoint /api/v1/users --params '{"limit": 10}'
        """
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        help="Custom API endpoint (e.g., /api/v1/users)"
    )
    parser.add_argument(
        "--params",
        type=str,
        help="Custom API parameters as JSON string (e.g., '{\"limit\": 10, \"offset\": 0}')"
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Generate only one test report instead of multiple"
    )
    parser.add_argument(
        "--test-name",
        type=str,
        help="Custom test name (used with --single)"
    )
    parser.add_argument(
        "--page-name",
        type=str,
        help="Custom page name (used with --single)"
    )
    
    args = parser.parse_args()
    
    print("Generating example UI vs API comparison reports (one file per test, one record per test)...")
    
    output_dir = Path(__file__).parent.parent / "example_reports"
    output_dir.mkdir(exist_ok=True)
    
    # Parse custom parameters if provided
    custom_params = {}
    if args.params:
        try:
            custom_params = json.loads(args.params)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in --params: {args.params}")
            sys.exit(1)
    
    # If single test requested
    if args.single:
        endpoint = args.endpoint or "/api/v1/users"
        params = custom_params or {"limit": 10, "offset": 0}
        test_name = args.test_name or "Custom Test Comparison"
        page_name = args.page_name or "Custom Page"
        
        tests = [{
            "test_name": test_name,
            "page_name": page_name,
            "ui_to_api_mapping": {
                "Full Name": "name",
                "Email Address": "email",
                "Age (years)": "age",
                "Status": "status",
            },
            "api_endpoint": endpoint,
            "api_parameters": params,
            "num_records": 1,
        }]
    else:
        # Define multiple tests
        tests = [
            {
                "test_name": "User List Comparison",
                "page_name": "User List",
                "ui_to_api_mapping": {
                    "Full Name": "name",
                    "Email Address": "email",
                    "Age (years)": "age",
                    "Status": "status",
                },
                "api_endpoint": args.endpoint or "/api/v1/users",
                "api_parameters": custom_params if custom_params else {"limit": 10, "offset": 0},
                "num_records": 1,
            },
            {
                "test_name": "Product Catalog Comparison",
                "page_name": "Product Catalog",
                "ui_to_api_mapping": {
                    "Product Name": "name",
                    "Price": "price",
                    "Category": "category",
                    "In Stock": "in_stock",
                },
                "api_endpoint": "/api/v1/products",
                "api_parameters": {"category": "electronics"},
                "num_records": 1,
            },
            {
                "test_name": "Order Details Comparison",
                "page_name": "Order Details",
                "ui_to_api_mapping": {
                    "Order ID": "order_id",
                    "Customer Name": "customer_name",
                    "Total Amount": "total",
                    "Order Status": "status",
                },
                "api_endpoint": "/api/v1/orders/{order_id}",
                "api_parameters": {"order_id": "12345"},
                "num_records": 1,
            },
        ]
    
    generated_files = []
    for i, test_config in enumerate(tests):
        print(f"\nGenerating test {i+1}/{len(tests)}: {test_config['test_name']}...")
        
        report = generate_test_report(
            test_name=test_config["test_name"],
            page_name=test_config["page_name"],
            ui_to_api_mapping=test_config["ui_to_api_mapping"],
            api_endpoint=test_config["api_endpoint"],
            api_parameters=test_config["api_parameters"],
            num_records=test_config["num_records"],
            introduce_mismatches=True
        )
        
        # Create safe filename from test name
        safe_name = test_config["test_name"].lower().replace(" ", "_").replace("/", "_")
        filename = f"test_{i+1}_{safe_name}.json"
        output_file = output_dir / filename
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        generated_files.append(output_file)
        
        summary = report["environment"]["comparison_summary"]
        endpoint = test_config.get("api_endpoint", "N/A")
        print(f"  Saved: {filename}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Records: {summary['total_records']}, Matched: {summary['matched_records']}, "
              f"Mismatched: {summary['mismatched_records']}")
    
    print(f"\n{'='*60}")
    print(f"Generated {len(generated_files)} test report file(s):")
    for f in generated_files:
        print(f"  - {f.name}")
    print(f"\nAll files saved to: {output_dir}")
    print(f"\nEach file represents:")
    print(f"  - One test case")
    print(f"  - One API endpoint")
    print(f"  - One record comparison")
    print(f"\nYou can upload these files individually or together to the report viewer!")


if __name__ == "__main__":
    main()
