"""
Comparison engine for UI vs API data.

Finds:
- Mismatches (same key, different values)
- Missing labels in UI (key exists in API but not in UI)
- Missing keys in API (key exists in UI but not in API)
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum


class ComparisonResultType(Enum):
    """Types of comparison results."""
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING_IN_UI = "missing_in_ui"
    MISSING_IN_API = "missing_in_api"


@dataclass
class FieldComparison:
    """Result of comparing a single field."""
    field_name: str
    ui_value: Any
    api_value: Any
    result_type: ComparisonResultType
    ui_label: Optional[str] = None  # Original UI label if different from field_name
    api_key: Optional[str] = None  # Original API key if different from field_name


@dataclass
class RecordComparison:
    """Result of comparing a single record (row)."""
    record_index: int
    ui_data: Dict[str, Any]
    api_data: Dict[str, Any]
    field_comparisons: List[FieldComparison]
    overall_match: bool


@dataclass
class ComparisonSummary:
    """Summary of comparison results."""
    total_records: int
    matched_records: int
    mismatched_records: int
    records_with_missing_ui: int
    records_with_missing_api: int
    total_fields_compared: int
    matched_fields: int
    mismatched_fields: int
    missing_in_ui_fields: int
    missing_in_api_fields: int


class Comparator:
    """
    Compare UI and API data.
    """
    
    def __init__(
        self,
        page_object: Optional["PageObject"] = None,
        ignore_case: bool = True,
        normalize_whitespace: bool = True
    ):
        """
        Initialize comparator.
        
        Args:
            page_object: Optional PageObject for label mapping
            ignore_case: Whether to ignore case when comparing strings
            normalize_whitespace: Whether to normalize whitespace when comparing strings
        """
        self.page_object = page_object
        self.ignore_case = ignore_case
        self.normalize_whitespace = normalize_whitespace
    
    def normalize_value(self, value: Any) -> Any:
        """
        Normalize a value for comparison.
        
        Args:
            value: Value to normalize
        
        Returns:
            Normalized value
        """
        if isinstance(value, str):
            if self.normalize_whitespace:
                value = " ".join(value.split())
            if self.ignore_case:
                value = value.lower()
        elif isinstance(value, (int, float)):
            # Convert to float for numeric comparison
            value = float(value)
        elif value is None:
            value = None
        return value
    
    def values_match(self, ui_value: Any, api_value: Any) -> bool:
        """
        Check if two values match after normalization.
        
        Args:
            ui_value: Value from UI
            api_value: Value from API
        
        Returns:
            True if values match
        """
        ui_norm = self.normalize_value(ui_value)
        api_norm = self.normalize_value(api_value)
        
        # Handle None
        if ui_norm is None and api_norm is None:
            return True
        if ui_norm is None or api_norm is None:
            return False
        
        return ui_norm == api_norm
    
    def compare_records(
        self,
        ui_records: List[Dict[str, Any]],
        api_records: List[Dict[str, Any]]
    ) -> List[RecordComparison]:
        """
        Compare UI and API records.
        
        Args:
            ui_records: List of normalized UI records
            api_records: List of normalized API records
        
        Returns:
            List of RecordComparison objects
        """
        results = []
        max_len = max(len(ui_records), len(api_records))
        
        for i in range(max_len):
            ui_data = ui_records[i] if i < len(ui_records) else {}
            api_data = api_records[i] if i < len(api_records) else {}
            
            # Get all unique field names
            all_fields = set(ui_data.keys()) | set(api_data.keys())
            
            field_comparisons = []
            for field_name in sorted(all_fields):
                ui_value = ui_data.get(field_name)
                api_value = api_data.get(field_name)
                
                # Determine result type
                if field_name not in ui_data:
                    result_type = ComparisonResultType.MISSING_IN_UI
                elif field_name not in api_data:
                    result_type = ComparisonResultType.MISSING_IN_API
                elif not self.values_match(ui_value, api_value):
                    result_type = ComparisonResultType.MISMATCH
                else:
                    result_type = ComparisonResultType.MATCH
                
                # Get original labels/keys if page object is available
                ui_label = None
                api_key = None
                if self.page_object:
                    ui_label = self.page_object.get_ui_label_for_api_key(field_name)
                    api_key = field_name  # Already normalized
                
                field_comparisons.append(FieldComparison(
                    field_name=field_name,
                    ui_value=ui_value,
                    api_value=api_value,
                    result_type=result_type,
                    ui_label=ui_label,
                    api_key=api_key
                ))
            
            # Overall match: all fields match and no missing fields
            overall_match = all(
                fc.result_type == ComparisonResultType.MATCH
                for fc in field_comparisons
            )
            
            results.append(RecordComparison(
                record_index=i,
                ui_data=ui_data,
                api_data=api_data,
                field_comparisons=field_comparisons,
                overall_match=overall_match
            ))
        
        return results
    
    def get_summary(self, comparisons: List[RecordComparison]) -> ComparisonSummary:
        """
        Generate summary statistics from comparison results.
        
        Args:
            comparisons: List of RecordComparison objects
        
        Returns:
            ComparisonSummary object
        """
        total_records = len(comparisons)
        matched_records = sum(1 for r in comparisons if r.overall_match)
        mismatched_records = total_records - matched_records
        
        records_with_missing_ui = sum(
            1 for r in comparisons
            if any(fc.result_type == ComparisonResultType.MISSING_IN_UI for fc in r.field_comparisons)
        )
        records_with_missing_api = sum(
            1 for r in comparisons
            if any(fc.result_type == ComparisonResultType.MISSING_IN_API for fc in r.field_comparisons)
        )
        
        total_fields = sum(len(r.field_comparisons) for r in comparisons)
        matched_fields = sum(
            sum(1 for fc in r.field_comparisons if fc.result_type == ComparisonResultType.MATCH)
            for r in comparisons
        )
        mismatched_fields = sum(
            sum(1 for fc in r.field_comparisons if fc.result_type == ComparisonResultType.MISMATCH)
            for r in comparisons
        )
        missing_in_ui_fields = sum(
            sum(1 for fc in r.field_comparisons if fc.result_type == ComparisonResultType.MISSING_IN_UI)
            for r in comparisons
        )
        missing_in_api_fields = sum(
            sum(1 for fc in r.field_comparisons if fc.result_type == ComparisonResultType.MISSING_IN_API)
            for r in comparisons
        )
        
        return ComparisonSummary(
            total_records=total_records,
            matched_records=matched_records,
            mismatched_records=mismatched_records,
            records_with_missing_ui=records_with_missing_ui,
            records_with_missing_api=records_with_missing_api,
            total_fields_compared=total_fields,
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            missing_in_ui_fields=missing_in_ui_fields,
            missing_in_api_fields=missing_in_api_fields,
        )
    
    def group_by_section(
        self,
        comparisons: List[RecordComparison]
    ) -> Dict[str, List[RecordComparison]]:
        """
        Group comparisons by section (table, page, etc.).
        
        For now, returns a single "all" section.
        Can be extended to group by table/page if that info is available.
        
        Args:
            comparisons: List of RecordComparison objects
        
        Returns:
            Dict mapping section name to list of comparisons
        """
        return {"all": comparisons}
