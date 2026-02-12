"""
UI vs API Comparison Module

This module provides:
- UI data extraction (table, row expansion, page navigation)
- API data extraction
- Data sorting
- Comparison engine (mismatches, missing labels/keys)
- Page object mapping (UI label = API key)
- Report generation compatible with pytest report viewer
"""

from .extractor import UIExtractor, APIExtractor, UIExtractionType
from .comparator import Comparator
from .page_object import PageObject
from .report_generator import generate_comparison_report
from .example import generate_example_data

__all__ = [
    "UIExtractor",
    "APIExtractor",
    "UIExtractionType",
    "Comparator",
    "PageObject",
    "generate_comparison_report",
    "generate_example_data",
]
