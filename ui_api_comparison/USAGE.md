# Quick Usage Guide

## Copy-Paste Ready Code

### 1. Basic Setup

```python
from ui_api_comparison import (
    PageObject,
    UIExtractor,
    APIExtractor,
    UIExtractionType,
    Comparator,
    generate_comparison_report
)
```

### 2. Define Your Page Object

```python
# Define how UI labels map to API keys
page_object = PageObject(
    page_name="User Management Page",
    ui_to_api_mapping={
        "Full Name": "name",           # UI label "Full Name" = API key "name"
        "Email Address": "email",       # UI label "Email Address" = API key "email"
        "Age (years)": "age",          # UI label "Age (years)" = API key "age"
        "Account Status": "status",     # UI label "Account Status" = API key "status"
    },
    extraction_type="table",  # or "row_expansion" or "page_navigation"
)
```

### 3. Extract UI Data

```python
# Your UI automation code (Selenium/Playwright) goes here
# After navigating and extracting raw data:

raw_ui_data = [
    {"Full Name": "John Doe", "Email Address": "john@example.com", "Age (years)": "30", "Account Status": "Active"},
    {"Full Name": "Jane Smith", "Email Address": "jane@example.com", "Age (years)": "25", "Account Status": "Inactive"},
    # ... more rows
]

# Extract and normalize using page object mapping
ui_extractor = UIExtractor(UIExtractionType.TABLE)
ui_data = ui_extractor.extract(raw_ui_data, field_mapping=page_object.ui_to_api_mapping)
```

### 4. Extract API Data

```python
# Your API calls (requests/httpx) go here
# After getting API responses:

api_responses = [
    {"name": "John Doe", "email": "john@example.com", "age": 30, "status": "active"},
    {"name": "Jane Smith", "email": "jane@example.com", "age": 25, "status": "inactive"},
    # ... more responses
]

# Extract and normalize
api_extractor = APIExtractor()
api_data = api_extractor.extract(api_responses)
```

### 5. Compare and Generate Report

```python
# Compare UI vs API
comparator = Comparator(page_object=page_object)
comparisons = comparator.compare_records(ui_data, api_data)
summary = comparator.get_summary(comparisons)

# Generate report (compatible with pytest viewer)
report = generate_comparison_report(
    ui_data=ui_data,
    api_data=api_data,
    page_object=page_object,
    comparator=comparator,
    project_name="my_project",
    run_name="User Management Comparison - 2026-02-09"
)

# Save report
import json
with open("comparison_report.json", "w") as f:
    json.dump(report, f, indent=2)
```

### 6. Upload to Report Viewer

Upload `comparison_report.json` to your report viewer - it will automatically detect it as a UI vs API comparison report and display it as a test run.

## Complete Example

See `example.py` for a complete working example with dummy data:

```python
from ui_api_comparison.example import generate_example_data
import json

# Generate example data
result = generate_example_data(num_records=5, introduce_mismatches=True)

# Save report
with open("example_report.json", "w") as f:
    json.dump(result['comparison_report'], f, indent=2)

# View summary
print(f"Matched: {result['summary'].matched_records}/{result['summary'].total_records}")
```

## Extraction Types

### TABLE
Extract directly from table rows:
```python
extractor = UIExtractor(UIExtractionType.TABLE)
ui_data = extractor.extract(table_rows, field_mapping=page_object.ui_to_api_mapping)
```

### ROW_EXPANSION
Open row, extract from expanded view:
```python
extractor = UIExtractor(UIExtractionType.ROW_EXPANSION)
# For each row, expand it and extract label-value pairs
expanded_data = {"Full Name": "John", "Email": "john@example.com"}
ui_data = extractor.extract([expanded_data], field_mapping=page_object.ui_to_api_mapping)
```

### PAGE_NAVIGATION
Open row, navigate to detail page, extract, go back:
```python
extractor = UIExtractor(UIExtractionType.PAGE_NAVIGATION)
# For each row, click to navigate, extract page data, go back
page_data = {"Title": "User Details", "Name": "John", "Email": "john@example.com"}
ui_data = extractor.extract([page_data], field_mapping=page_object.ui_to_api_mapping)
```

## Comparison Results

The comparison identifies:
- **Mismatches**: Same field, different values (e.g., UI="Active" vs API="active")
- **Missing in UI**: Field exists in API but not in UI
- **Missing in API**: Field exists in UI but not in API
- **Matches**: Fields that match perfectly

Results are available in:
- `comparisons`: List of `RecordComparison` objects (one per record)
- `summary`: `ComparisonSummary` with statistics
- `report`: JSON report compatible with pytest viewer
