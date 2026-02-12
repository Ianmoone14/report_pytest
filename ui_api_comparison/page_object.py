"""
Page Object with label mapping (UI label = API key).

This defines how UI labels map to API keys for comparison.
"""

from typing import Dict, Optional, Any


class PageObject:
    """
    Page object that defines:
    - UI label to API key mapping
    - Field extraction rules
    - Normalization rules
    """
    
    def __init__(
        self,
        page_name: str,
        ui_to_api_mapping: Dict[str, str],
        extraction_type: str = "table",
        description: Optional[str] = None
    ):
        """
        Initialize page object.
        
        Args:
            page_name: Name of the page (e.g., "User List", "Product Details")
            ui_to_api_mapping: Dict mapping UI labels to API keys
                              e.g. {"Full Name": "name", "Email Address": "email"}
            extraction_type: Type of UI extraction ("table", "row_expansion", "page_navigation")
            description: Optional description of the page
        """
        self.page_name = page_name
        self.ui_to_api_mapping = ui_to_api_mapping
        self.extraction_type = extraction_type
        self.description = description
    
    def get_api_key_for_ui_label(self, ui_label: str) -> Optional[str]:
        """
        Get API key for a UI label.
        
        Args:
            ui_label: UI label (e.g., "Full Name")
        
        Returns:
            API key (e.g., "name") or None if not mapped
        """
        return self.ui_to_api_mapping.get(ui_label)
    
    def get_ui_label_for_api_key(self, api_key: str) -> Optional[str]:
        """
        Get UI label for an API key (reverse lookup).
        
        Args:
            api_key: API key (e.g., "name")
        
        Returns:
            UI label (e.g., "Full Name") or None if not mapped
        """
        reverse_mapping = {v: k for k, v in self.ui_to_api_mapping.items()}
        return reverse_mapping.get(api_key)
    
    def normalize_ui_data(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize UI data using the mapping.
        
        Args:
            ui_data: Raw UI data with UI labels as keys
        
        Returns:
            Normalized data with API keys as keys
        """
        normalized = {}
        for ui_label, value in ui_data.items():
            api_key = self.get_api_key_for_ui_label(ui_label)
            if api_key:
                normalized[api_key] = value
            else:
                # If no mapping, use label as-is (lowercased)
                normalized[ui_label.lower().replace(" ", "_")] = value
        return normalized
    
    def normalize_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize API data (pass through, but could apply transformations).
        
        Args:
            api_data: Raw API data
        
        Returns:
            Normalized API data
        """
        # For now, just return as-is. Could add transformations here.
        return api_data.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert page object to dict for serialization."""
        return {
            "page_name": self.page_name,
            "ui_to_api_mapping": self.ui_to_api_mapping,
            "extraction_type": self.extraction_type,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageObject":
        """Create page object from dict."""
        return cls(
            page_name=data["page_name"],
            ui_to_api_mapping=data["ui_to_api_mapping"],
            extraction_type=data.get("extraction_type", "table"),
            description=data.get("description"),
        )
