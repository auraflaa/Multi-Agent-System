"""Size mapping utilities for converting between abbreviations and full forms."""
from typing import List

# Size abbreviation to full form mapping
SIZE_MAPPING = {
    "XS": "Extra Small",
    "S": "Small",
    "M": "Medium",
    "L": "Large",
    "XL": "Extra Large",
    "XXL": "Extra Extra Large",
}

# Reverse mapping: full form to abbreviation (case-insensitive)
FULL_TO_ABBREV = {
    "extra small": "XS",
    "small": "S",
    "medium": "M",
    "large": "L",
    "extra large": "XL",
    "extra extra large": "XXL",
    "xxl": "XXL",  # Handle lowercase
    "xl": "XL",
    "xs": "XS",
    "s": "S",
    "m": "M",
    "l": "L",
}


def get_full_size(size: str) -> str:
    """
    Convert size abbreviation to full form.
    
    Args:
        size: Size abbreviation (e.g., "M", "S", "XL")
        
    Returns:
        Full form (e.g., "Medium", "Small", "Extra Large")
        If not found, returns the original size
    """
    if not size:
        return size
    
    size_upper = size.upper().strip()
    return SIZE_MAPPING.get(size_upper, size)


def get_size_abbrev(size: str) -> str:
    """
    Convert full size form to abbreviation.
    
    Args:
        size: Full form or abbreviation (e.g., "Medium", "M", "medium")
        
    Returns:
        Abbreviation (e.g., "M", "S", "XL")
        If not found, returns the original size (uppercased)
    """
    if not size:
        return size
    
    size_lower = size.lower().strip()
    
    # Check reverse mapping first
    abbrev = FULL_TO_ABBREV.get(size_lower)
    if abbrev:
        return abbrev
    
    # If already an abbreviation, return uppercase
    size_upper = size.upper().strip()
    if size_upper in SIZE_MAPPING:
        return size_upper
    
    # Not found, return original (uppercased)
    return size_upper


def normalize_size(size: str) -> str:
    """
    Normalize size to standard abbreviation format.
    Accepts both abbreviations and full forms, returns abbreviation.
    
    Args:
        size: Size in any format
        
    Returns:
        Standard abbreviation (XS, S, M, L, XL, XXL)
    """
    return get_size_abbrev(size)


def format_size_list(sizes: List[str]) -> List[str]:
    """
    Format a list of sizes, converting abbreviations to full forms.
    
    Args:
        sizes: List of size abbreviations
        
    Returns:
        List of full form sizes
    """
    return [get_full_size(size) for size in sizes if size]


def format_size_for_display(size: str) -> str:
    """
    Format a single size for display (abbreviation + full form).
    
    Args:
        size: Size abbreviation
        
    Returns:
        Formatted string like "M (Medium)" or just "Medium" if already full form
    """
    if not size:
        return size
    
    size_upper = size.upper().strip()
    full_form = SIZE_MAPPING.get(size_upper)
    
    if full_form:
        return f"{size_upper} ({full_form})"
    
    # If it's already a full form, return as is
    return size

