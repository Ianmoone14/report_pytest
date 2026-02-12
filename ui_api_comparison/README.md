# UI vs API Comparison Module

This module provides complete logic for comparing UI and API data, generating reports compatible with the pytest report viewer.

## Structure

- **`extractor.py`**: UI and API data extraction logic
- **`page_object.py`**: Page object with label mapping (UI label = API key)
- **`comparator.py`**: Comparison engine (mismatches, missing fields)
- **`report_generator.py`**: Generate reports in pytest format
- **`example.py`**: Example/dummy data generator for testing

## Usage

### 1. Define Page Object

```python
from ui_api_comparison import PageObject

page_object = PageObject(
    page_name="User List",
    ui_to_api_mapping={
        "Full Name": "name",
        "Email Address": "email",
        "Age (years)": "age",
        "Status": "status",
    },
    extraction_type="table",  # or "row_expansion" or "page_navigation"
)
```

### 2. Extract UI Data

```python
from ui_api_comparison import UIExtractor, UIExtractionType

# Your UI navigation code here (Selenium/Playwright)
# Extract raw data from UI
raw_ui_data = [
    {"Full Name": "John Doe", "Email Address": "john@example.com", "Age (years)": "30"},
    # ... more rows
]

# Extract and normalize
extractor = UIExtractor(UIExtractionType.TABLE)
ui_data = extractor.extract(raw_ui_data, field_mapping=page_object.ui_to_api_mapping)
```

### 3. Extract API Data

```python
from ui_api_comparison import APIExtractor

# Your API calls here (requests/httpx)
# Get API responses
api_responses = [
    {"name": "John Doe", "email": "john@example.com", "age": 30},
    # ... more responses
]

# Extract and normalize
api_extractor = APIExtractor()
api_data = api_extractor.extract(api_responses)
```

### 4. Compare and Generate Report

```python
from ui_api_comparison import Comparator, generate_comparison_report

# Compare
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
    run_name="UI vs API Comparison Run"
)

# Save report as JSON
import json
with open("comparison_report.json", "w") as f:
    json.dump(report, f, indent=2)
```

### 5. Upload to Report Viewer

Upload the generated `comparison_report.json` to the pytest report viewer - it will be recognized and displayed as a test run.

## Example

See `example.py` for a complete working example:

```python
from ui_api_comparison.example import generate_example_data

result = generate_example_data(num_records=5, introduce_mismatches=True)
print(result['summary'])
# Save report
import json
with open("example_report.json", "w") as f:
    json.dump(result['comparison_report'], f, indent=2)
```

## Comparison Results

The comparison engine identifies:

1. **Mismatches**: Same field exists in both UI and API but values differ
2. **Missing in UI**: Field exists in API but not in UI
3. **Missing in API**: Field exists in UI but not in API
4. **Matches**: Fields that match between UI and API

Results are grouped by:
- Overall summary
- Per-record comparisons
- Per-field comparisons

## Integration

The generated report follows the pytest JSON format, so it integrates seamlessly with the existing report viewer. Each comparison becomes a test case:
- `passed` if record matches completely
- `failed` if there are mismatches or missing fields

Metadata includes detailed comparison information for analysis.
