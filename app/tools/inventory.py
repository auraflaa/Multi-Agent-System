"""Inventory management tool."""
from typing import Dict, Any, List, Optional
from app.db.database import get_db_connection
from app.utils.size_mapping import normalize_size, format_size_list, format_size_for_display


def check_inventory(sku: Optional[str] = None, size: Optional[str] = None, product_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Check inventory availability for a specific SKU and size, or by product_id.
    
    Args:
        sku: Stock Keeping Unit identifier (optional if product_id is provided)
        size: Product size (optional)
        product_id: Product ID to check inventory for (optional if sku is provided)
        
    Returns:
        Dictionary containing inventory information:
        - available: boolean
        - quantity: integer
        - sku: string
        - size: string (or sizes: list if multiple sizes)
        - product_id: string (if found)
        - product_name: string (if found)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize size input (accept both abbreviations and full forms)
        normalized_size = normalize_size(size) if size else None
        
        # If product_id is provided, query by product_id instead of SKU
        if product_id and not sku:
            # Get all inventory entries for this product
            if normalized_size:
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
                    WHERE i.product_id = ? AND i.size = ?
                    """,
                    (product_id, normalized_size),
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
                        "sku": row["sku"] if row else None,
                        "size": size,
                        "product_id": product_id,
                        "location": row["location"] if row else None,
                        "product_name": row["name"] if row else None,
                    }
            else:
                # Get all sizes for this product
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
                    WHERE i.product_id = ?
                    ORDER BY i.size
                    """,
                    (product_id,),
                )
                rows = cursor.fetchall()
                if not rows:
                    return {
                        "available": False,
                        "quantity": 0,
                        "product_id": product_id,
                        "sizes": [],
                        "product_name": None,
                    }
                
                total_quantity = sum(r["quantity"] for r in rows)
                sizes_raw = [r["size"] for r in rows if r["size"] is not None]
                # Format sizes for display (abbreviation + full form)
                sizes = format_size_list(sizes_raw)
                first = rows[0]
                
                return {
                    "available": total_quantity > 0,
                    "quantity": total_quantity,
                    "sku": first["sku"],
                    "sizes": sizes,
                    "sizes_raw": sizes_raw,  # Keep raw abbreviations for internal use
                    "product_id": first["product_id"],
                    "location": first["location"],
                    "product_name": first["name"],
                    "category": first["category"],
                }
        
        # Original SKU-based logic (if sku is provided)
        if not sku:
            return {
                "available": False,
                "quantity": 0,
                "sku": None,
                "sizes": [],
                "product_id": product_id,
                "error": "Either sku or product_id must be provided"
            }
        if normalized_size:
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
                (sku, normalized_size),
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
        sizes_raw: List[str] = [r["size"] for r in rows if r["size"] is not None]
        # Format sizes for display (abbreviation + full form)
        sizes = format_size_list(sizes_raw)
        first = rows[0]

        return {
            "available": total_quantity > 0,
            "quantity": total_quantity,
            "sku": sku,
            "sizes": sizes,
            "sizes_raw": sizes_raw,  # Keep raw abbreviations for internal use
            "product_id": first["product_id"],
            "location": first["location"],
            "product_name": first["name"],
            "category": first["category"],
        }
    finally:
        conn.close()

