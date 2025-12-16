"""Inventory management tool."""
from typing import Dict, Any
from app.db.database import get_db_connection


def check_inventory(sku: str, size: str) -> Dict[str, Any]:
    """
    Check inventory availability for a specific SKU and size.
    
    Args:
        sku: Stock Keeping Unit identifier
        size: Product size
        
    Returns:
        Dictionary containing inventory information:
        - available: boolean
        - quantity: integer
        - sku: string
        - size: string
        - product_id: string (if found)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT i.sku, i.product_id, i.size, i.quantity, i.location, p.name, p.category
            FROM inventory i
            LEFT JOIN products p ON i.product_id = p.product_id
            WHERE i.sku = ? AND i.size = ?
        """, (sku, size))
        
        row = cursor.fetchone()
        
        if row and row["quantity"] > 0:
            return {
                "available": True,
                "quantity": row["quantity"],
                "sku": row["sku"],
                "size": row["size"],
                "product_id": row["product_id"],
                "location": row["location"],
                "product_name": row["name"],
                "category": row["category"]
            }
        else:
            return {
                "available": False,
                "quantity": row["quantity"] if row else 0,
                "sku": sku,
                "size": size,
                "product_id": row["product_id"] if row else None,
                "location": row["location"] if row else None
            }
    finally:
        conn.close()

