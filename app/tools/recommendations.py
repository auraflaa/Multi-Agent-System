"""Product recommendation tool (rule-based, no ML)."""
from typing import List, Dict, Any, Optional
from app.db.database import get_db_connection


def recommend_products(category: str, price_range: str = "any", gender: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Recommend products based on category and price range (rule-based).
    Gender filtering ensures male and female products are NOT mixed.
    
    Args:
        category: Product category
        price_range: Price range filter (e.g., "0-50", "50-100", "100-200", "any")
        gender: Optional gender filter ("male", "female", "other"). If provided, only returns products matching this gender.
                Filters by checking category/name for gender indicators (male/men/male's vs female/women/female's).
        
    Returns:
        List of product dictionaries with recommendations (gender-filtered if gender is provided)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Helper function to check if a product matches gender filter
        def matches_gender(product_name: str, product_category: str, target_gender: Optional[str]) -> bool:
            """Check if product matches gender filter by examining name and category."""
            if not target_gender:
                return True  # No filter, accept all
            
            target_gender_lower = target_gender.lower()
            name_lower = (product_name or "").lower()
            category_lower = (product_category or "").lower()
            combined_text = f"{name_lower} {category_lower}"
            
            # Male indicators
            male_indicators = ["male", "men", "men's", "mens", "man", "guy"]
            # Female indicators
            female_indicators = ["female", "women", "women's", "womens", "woman", "lady", "ladies", "girl"]
            
            if target_gender_lower in ["male", "m"]:
                # Must contain male indicator and NOT contain female indicator
                has_male = any(indicator in combined_text for indicator in male_indicators)
                has_female = any(indicator in combined_text for indicator in female_indicators)
                return has_male and not has_female
            elif target_gender_lower in ["female", "f"]:
                # Must contain female indicator and NOT contain male indicator
                has_female = any(indicator in combined_text for indicator in female_indicators)
                has_male = any(indicator in combined_text for indicator in male_indicators)
                return has_female and not has_male
            else:
                # For "other" or unknown, accept all (or could implement specific logic)
                return True
        
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
        
        # 1) Primary: exact category match
        if price_range == "any":
            cursor.execute(
                """
                SELECT product_id, name, category, base_price
                FROM products
                WHERE category = ?
                ORDER BY base_price ASC
                LIMIT 20
                """,
                (category,),
            )
        else:
            cursor.execute(
                """
                SELECT product_id, name, category, base_price
                FROM products
                WHERE category = ? AND base_price >= ? AND base_price <= ?
                ORDER BY base_price ASC
                LIMIT 20
                """,
                (category, min_price, max_price),
            )

        rows = cursor.fetchall()

        # 2) Fallback: fuzzy match on category/name if no exact hits
        if not rows:
            like_term = f"%{category.lower()}%"
            if price_range == "any":
                cursor.execute(
                    """
                    SELECT product_id, name, category, base_price
                    FROM products
                    WHERE LOWER(category) LIKE ? OR LOWER(name) LIKE ?
                    ORDER BY base_price ASC
                    LIMIT 20
                    """,
                    (like_term, like_term),
                )
            else:
                cursor.execute(
                    """
                    SELECT product_id, name, category, base_price
                    FROM products
                    WHERE (LOWER(category) LIKE ? OR LOWER(name) LIKE ?)
                      AND base_price >= ? AND base_price <= ?
                    ORDER BY base_price ASC
                    LIMIT 20
                    """,
                    (like_term, like_term, min_price, max_price),
                )
            rows = cursor.fetchall()

        # 3) Final fallback: popular items across all categories
        if not rows:
            cursor.execute(
                """
                SELECT product_id, name, category, base_price
                FROM products
                ORDER BY base_price ASC
                LIMIT 20
                """
            )
            rows = cursor.fetchall()

        # Filter by gender if specified (CRITICAL: prevent mixing male/female)
        recommendations: List[Dict[str, Any]] = []
        for row in rows:
            if matches_gender(row["name"], row["category"], gender):
                recommendations.append(
                    {
                        "product_id": row["product_id"],
                        "name": row["name"],
                        "category": row["category"],
                        "base_price": row["base_price"],
                    }
                )
            # Stop once we have enough gender-filtered results
            if len(recommendations) >= 10:
                break

        return recommendations
    finally:
        conn.close()

