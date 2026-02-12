"""
Data extraction logic for UI and API.

UI extraction supports 3 types:
1. Table extraction - extract data from table rows
2. Row expansion - open row, extract data next to labels
3. Page navigation - open each row, navigate to new page, extract, go back
"""

from typing import Any, Dict, List, Optional
from enum import Enum


class UIExtractionType(Enum):
    """Types of UI extraction methods."""
    TABLE = "table"  # Extract from table directly
    ROW_EXPANSION = "row_expansion"  # Open row, extract from expanded view
    PAGE_NAVIGATION = "page_navigation"  # Open row, navigate to page, extract, go back


class UIExtractor:
    """
    Extract data from UI.
    
    Note: Actual UI navigation (Selenium/Playwright) is left to the user.
    This class provides the data structure and extraction logic.
    """
    
    def __init__(self, extraction_type: UIExtractionType):
        """
        Initialize UI extractor.
        
        Args:
            extraction_type: Type of extraction (TABLE, ROW_EXPANSION, PAGE_NAVIGATION)
        """
        self.extraction_type = extraction_type
    
    def extract_from_table(
        self,
        table_data: List[Dict[str, Any]],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract data from table rows.
        
        Args:
            table_data: List of dicts, each representing a table row
                       e.g. [{"Name": "John", "Age": "30"}, ...]
            field_mapping: Optional mapping from UI column names to normalized names
                         e.g. {"Full Name": "name", "Age (years)": "age"}
        
        Returns:
            List of extracted records with normalized field names
        """
        if field_mapping is None:
            field_mapping = {}
        
        extracted = []
        for row in table_data:
            normalized = {}
            for ui_key, value in row.items():
                # Use mapping if available, otherwise use key as-is (lowercased)
                normalized_key = field_mapping.get(ui_key, ui_key.lower().replace(" ", "_"))
                normalized[normalized_key] = value
            extracted.append(normalized)
        
        return extracted
    
    def extract_from_expanded_row(
        self,
        row_data: Dict[str, Any],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Extract data from expanded row (label-value pairs).
        
        Args:
            row_data: Dict with label-value pairs
                     e.g. {"Full Name": "John Doe", "Email Address": "john@example.com"}
            field_mapping: Optional mapping from UI labels to normalized names
        
        Returns:
            Normalized record dict
        """
        if field_mapping is None:
            field_mapping = {}
        
        normalized = {}
        for ui_label, value in row_data.items():
            normalized_key = field_mapping.get(ui_label, ui_label.lower().replace(" ", "_"))
            normalized[normalized_key] = value
        
        return normalized
    
    def extract_from_page(
        self,
        page_data: Dict[str, Any],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Extract data from a full page (after navigating to detail page).
        
        Args:
            page_data: Dict with all data from the page
                     e.g. {"Title": "User Details", "Name": "John", "Email": "john@example.com"}
            field_mapping: Optional mapping from UI labels to normalized names
        
        Returns:
            Normalized record dict
        """
        return self.extract_from_expanded_row(page_data, field_mapping)
    
    def extract(
        self,
        raw_data: Any,
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract data based on extraction type.
        
        Args:
            raw_data: Raw data from UI (format depends on extraction_type)
            field_mapping: Optional mapping from UI labels to normalized names
        
        Returns:
            List of normalized records
        """
        if self.extraction_type == UIExtractionType.TABLE:
            if not isinstance(raw_data, list):
                raw_data = [raw_data]
            return self.extract_from_table(raw_data, field_mapping)
        elif self.extraction_type == UIExtractionType.ROW_EXPANSION:
            if isinstance(raw_data, list):
                return [self.extract_from_expanded_row(row, field_mapping) for row in raw_data]
            return [self.extract_from_expanded_row(raw_data, field_mapping)]
        elif self.extraction_type == UIExtractionType.PAGE_NAVIGATION:
            if isinstance(raw_data, list):
                return [self.extract_from_page(row, field_mapping) for row in raw_data]
            return [self.extract_from_page(raw_data, field_mapping)]
        else:
            raise ValueError(f"Unknown extraction type: {self.extraction_type}")


class APIExtractor:
    """
    Extract data from API responses.
    
    Note: Actual API calls (requests/httpx) are left to the user.
    This class provides the data structure and extraction logic.
    """
    
    def extract(
        self,
        api_responses: List[Dict[str, Any]],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract and normalize data from API responses.
        
        Args:
            api_responses: List of API response dicts
                         e.g. [{"id": 1, "name": "John", "age": 30}, ...]
            field_mapping: Optional mapping from API keys to normalized names
                         e.g. {"full_name": "name", "years": "age"}
        
        Returns:
            List of normalized records
        """
        if field_mapping is None:
            field_mapping = {}
        
        extracted = []
        for response in api_responses:
            normalized = {}
            for api_key, value in response.items():
                # Use mapping if available, otherwise use key as-is
                normalized_key = field_mapping.get(api_key, api_key)
                normalized[normalized_key] = value
            extracted.append(normalized)
        
        return extracted
