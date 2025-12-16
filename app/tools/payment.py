"""Payment calculation tool."""
from typing import Dict, Any, List


def calculate_payment(cart: List[Dict[str, Any]], discounts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate final payment amount after discounts.
    
    Args:
        cart: List of cart items
        discounts: Dictionary from apply_offers containing discount information
        
    Returns:
        Dictionary containing:
        - subtotal: cart subtotal
        - total_discount: total discount amount
        - tax: calculated tax (assume 10%)
        - final_amount: final payable amount
    """
    # Calculate subtotal
    subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart)
    
    # Get total discount
    total_discount = discounts.get("total_discount", 0.0)
    
    # Calculate amount after discount
    amount_after_discount = subtotal - total_discount
    
    # Apply tax (10% assumed)
    tax_rate = 0.10
    tax = amount_after_discount * tax_rate
    
    # Final amount
    final_amount = amount_after_discount + tax
    
    return {
        "subtotal": subtotal,
        "total_discount": total_discount,
        "amount_after_discount": amount_after_discount,
        "tax_rate": tax_rate * 100,
        "tax": tax,
        "final_amount": final_amount,
        "currency": "INR"
    }

