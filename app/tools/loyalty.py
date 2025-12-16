"""Loyalty and offers management tool."""
from typing import Dict, Any, List


def apply_offers(cart: List[Dict[str, Any]], loyalty_tier: str) -> Dict[str, Any]:
    """
    Apply loyalty-based discounts and offers to cart.
    
    Args:
        cart: List of cart items, each with 'product_id', 'quantity', 'price'
        loyalty_tier: User's loyalty tier (bronze, silver, gold, platinum)
        
    Returns:
        Dictionary containing:
        - discounts: list of applied discounts
        - total_discount: total discount amount
        - discount_percentage: discount percentage applied
    """
    tier_discounts = {
        "bronze": 0.0,
        "silver": 0.05,  # 5% discount
        "gold": 0.10,    # 10% discount
        "platinum": 0.15  # 15% discount
    }
    
    discount_percentage = tier_discounts.get(loyalty_tier.lower(), 0.0)
    
    # Calculate cart subtotal
    subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart)
    
    # Apply tier discount
    total_discount = subtotal * discount_percentage
    
    discounts = []
    if discount_percentage > 0:
        discounts.append({
            "type": "loyalty_tier",
            "description": f"{loyalty_tier.capitalize()} member discount",
            "percentage": discount_percentage * 100,
            "amount": total_discount
        })
    
    # Apply bulk discount (10% off for orders over ₹1000)
    if subtotal > 1000:
        bulk_discount = subtotal * 0.10
        discounts.append({
            "type": "bulk",
            "description": "Bulk order discount (10% off orders over ₹1000)",
            "percentage": 10.0,
            "amount": bulk_discount
        })
        total_discount += bulk_discount
    
    return {
        "discounts": discounts,
        "total_discount": total_discount,
        "discount_percentage": discount_percentage * 100,
        "subtotal": subtotal
    }

