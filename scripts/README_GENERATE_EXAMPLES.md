# Generate UI vs API Comparison Examples

This script generates example JSON report files for testing the UI vs API comparison viewer.

## Usage

### Basic Usage (Generate Default Examples)

```bash
python scripts/generate_ui_api_example.py
```

This generates 3 test report files:
- `test_1_user_list_comparison.json`
- `test_2_product_catalog_comparison.json`
- `test_3_order_details_comparison.json`

### Generate Single Test with Custom Endpoint

```bash
python scripts/generate_ui_api_example.py --single --endpoint /api/v1/custom --params '{"id": 123}'
```

### Generate Single Test with Custom Name

```bash
python scripts/generate_ui_api_example.py --single --endpoint /api/v1/users --test-name "My Custom Test" --page-name "User Details Page"
```

### Override Endpoint for All Tests

```bash
python scripts/generate_ui_api_example.py --endpoint /api/v1/custom --params '{"limit": 20}'
```

## Command-Line Options

- `--endpoint ENDPOINT`: Custom API endpoint (e.g., `/api/v1/users`)
- `--params JSON_STRING`: Custom API parameters as JSON string (e.g., `'{"limit": 10, "offset": 0}'`)
- `--single`: Generate only one test report instead of multiple
- `--test-name NAME`: Custom test name (used with `--single`)
- `--page-name NAME`: Custom page name (used with `--single`)

## Output

Each generated JSON file represents:
- ✅ **One test case** (e.g., "User List Comparison")
- ✅ **One API endpoint** (e.g., `/api/v1/users`)
- ✅ **One record** (one item/row being compared)

## Examples

```bash
# Generate default examples
python scripts/generate_ui_api_example.py

# Generate single test with custom endpoint
python scripts/generate_ui_api_example.py --single --endpoint /api/v1/products/123

# Generate with custom parameters
python scripts/generate_ui_api_example.py --single --endpoint /api/v1/users --params '{"limit": 50, "offset": 0}'

# Generate with custom test name
python scripts/generate_ui_api_example.py --single --endpoint /api/v1/orders/456 --test-name "Order #456 Comparison" --page-name "Order Details"
```

## Uploading to Report Viewer

After generating the files, you can:
1. Upload them individually via the "Upload" page
2. Upload multiple files to the same run using the "Upload Test" button on a run detail page
3. Each file will appear as a separate test case in your run
