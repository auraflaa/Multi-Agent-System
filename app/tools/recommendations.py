"""Product recommendation tool (rule-based, no ML)."""
from typing import List, Dict, Any
from app.db.database import get_db_connection


def recommend_products(category: str, price_range: str = "any") -> List[Dict[str, Any]]:
    """
    Recommend products based on category and price range (rule-based).
    
    Args:
        category: Product category
        price_range: Price range filter (e.g., "0-50", "50-100", "100-200", "any")
        
    Returns:
        List of product dictionaries with recommendations
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Parse price range
        min_price = 0
        max_price = float('inf')
        
        if price_range != "any" and "-" in price_range:
            try:
                parts = price_range.split("-")
                min_price = float(parts[0])
                max_price = float(parts[1])
            except (ValueError, IndexError):
                pass
        
        # Query products by category
        if price_range == "any":
            cursor.execute("""
                SELECT product_id, name, category, base_price
                FROM products
                WHERE category = ?
                ORDER BY base_price ASC
                LIMIT 10
            """, (category,))
        else:
            cursor.execute("""
                SELECT product_id, name, category, base_price
                FROM products
                WHERE category = ? AND base_price >= ? AND base_price <= ?
                ORDER BY base_price ASC
                LIMIT 10
            """, (category, min_price, max_price))
        
        rows = cursor.fetchall()
        
        recommendations = []
        for row in rows:
            recommendations.append({
                "product_id": row["product_id"],
                "name": row["name"],
                "category": row["category"],
                "base_price": row["base_price"]
            })
        
        return recommendations
    finally:
        conn.close()

