"""Fulfillment options tool."""
from typing import List, Dict, Any


def get_fulfillment_options(location: str) -> List[Dict[str, Any]]:
    """
    Get available fulfillment options for a location (rule-based).
    
    Args:
        location: Delivery location/address
        
    Returns:
        List of fulfillment options with details
    """
    # Rule-based fulfillment logic
    options = []
    
    # Standard delivery (always available)
    options.append({
        "type": "standard_delivery",
        "description": "Standard delivery (5-7 business days)",
        "cost": 5.99,
        "estimated_days": 5
    })
    
    # Express delivery (always available)
    options.append({
        "type": "express_delivery",
        "description": "Express delivery (2-3 business days)",
        "cost": 12.99,
        "estimated_days": 2
    })
    
    # Free delivery for orders over $50
    options.append({
        "type": "free_standard_delivery",
        "description": "Free standard delivery (orders over $50)",
        "cost": 0.0,
        "estimated_days": 5,
        "min_order": 50.0
    })
    
    # Store pickup (if location is near a store)
    # Simple rule: if location contains certain keywords
    if any(keyword in location.lower() for keyword in ["store", "pickup", "near"]):
        options.append({
            "type": "store_pickup",
            "description": "Store pickup (available next day)",
            "cost": 0.0,
            "estimated_days": 1
        })
    
    return options

