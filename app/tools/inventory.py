"""Inventory management tool."""
from typing import Dict, Any, List, Optional
from app.db.database import get_db_connection


def check_inventory(sku: str, size: Optional[str] = None) -> Dict[str, Any]:
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
        if size:
            # Exact SKU + size lookup (current behavior)
            cursor.execute(
                """
                SELECT i.sku,
                       i.product_id,
                       i.size,
                       i.quantity,
                       i.location,
                       p.name,
                       p.category
                FROM inventory i
                LEFT JOIN products p ON i.product_id = p.product_id
                WHERE i.sku = ? AND i.size = ?
                """,
                (sku, size),
            )

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
                    "category": row["category"],
                }
            else:
                return {
                    "available": False,
                    "quantity": row["quantity"] if row else 0,
                    "sku": sku,
                    "size": size,
                    "product_id": row["product_id"] if row else None,
                    "location": row["location"] if row else None,
                }

        # No size provided: aggregate across all sizes for this SKU
        cursor.execute(
            """
            SELECT i.sku,
                   i.product_id,
                   i.size,
                   i.quantity,
                   i.location,
                   p.name,
                   p.category
            FROM inventory i
            LEFT JOIN products p ON i.product_id = p.product_id
            WHERE i.sku = ?
            """,
            (sku,),
        )

        rows = cursor.fetchall()
        if not rows:
            # Completely unknown SKU
            return {
                "available": False,
                "quantity": 0,
                "sku": sku,
                "sizes": [],
                "product_id": None,
                "location": None,
            }

        total_quantity = sum(r["quantity"] for r in rows)
        sizes: List[str] = [r["size"] for r in rows if r["size"] is not None]
        first = rows[0]

        return {
            "available": total_quantity > 0,
            "quantity": total_quantity,
            "sku": sku,
            "sizes": sizes,
            "product_id": first["product_id"],
            "location": first["location"],
            "product_name": first["name"],
            "category": first["category"],
        }
    finally:
        conn.close()

