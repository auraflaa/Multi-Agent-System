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
        # Normalize category to handle case variations
        category_normalized = category.strip()
        # Helper function to check if a product matches gender filter
        def matches_gender(product_name: str, product_category: str, target_gender: Optional[str]) -> bool:
            """Check if product matches gender filter by examining name and category."""
            if not target_gender:
                return True  # No filter, accept all
            
            target_gender_lower = target_gender.lower()
            name_lower = (product_name or "").lower()
            category_lower = (product_category or "").lower()
            combined_text = f"{name_lower} {category_lower}"
            
            # Male indicators (use word boundaries to avoid false matches like "man" in "female")
            male_indicators = ["male", "men", "men's", "mens", " man ", "man ", " man", "guy"]
            # Female indicators
            female_indicators = ["female", "women", "women's", "womens", "woman", "lady", "ladies", "girl"]
            
            # Use word boundary matching to avoid false positives (e.g., "man" in "female")
            def has_indicator(text: str, indicators: list) -> bool:
                """Check if text contains any indicator as a whole word."""
                text_lower = text.lower()
                for indicator in indicators:
                    # Check if indicator appears as a whole word (with word boundaries)
                    if indicator.strip() in text_lower:
                        # Additional check: ensure it's not a substring of another word
                        # For example, "man" should not match in "female" or "woman"
                        indicator_lower = indicator.strip().lower()
                        # Find all occurrences
                        idx = text_lower.find(indicator_lower)
                        while idx != -1:
                            # Check character before (if exists)
                            before_ok = idx == 0 or not text_lower[idx-1].isalnum()
                            # Check character after (if exists)
                            after_idx = idx + len(indicator_lower)
                            after_ok = after_idx >= len(text_lower) or not text_lower[after_idx].isalnum()
                            if before_ok and after_ok:
                                return True
                            # Find next occurrence
                            idx = text_lower.find(indicator_lower, idx + 1)
                return False
            
            if target_gender_lower in ["male", "m"]:
                # Must contain male indicator and NOT contain female indicator
                has_male = has_indicator(combined_text, male_indicators)
                has_female = has_indicator(combined_text, female_indicators)
                # STRICT: If it has female indicators, it's NOT a male product
                if has_female:
                    return False
                # If it has male indicators, it IS a male product
                if has_male:
                    return True
                # If neither, reject it (don't include ambiguous products when gender filter is active)
                return False
            elif target_gender_lower in ["female", "f"]:
                # Must contain female indicator and NOT contain male indicator
                has_female = has_indicator(combined_text, female_indicators)
                has_male = has_indicator(combined_text, male_indicators)
                # STRICT: If it has male indicators, it's NOT a female product
                if has_male:
                    return False
                # If it has female indicators, it IS a female product
                if has_female:
                    return True
                # If neither, reject it (don't include ambiguous products when gender filter is active)
                return False
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
        
        # Normalize category for matching
        category_normalized = category.strip()
        category_lower = category_normalized.lower()
        generalized_categories = []
        
        # Build search terms: original category + generalizations
        generalized_categories.append(category_normalized)  # Original category first
        generalized_categories.append(category_lower)  # Also try lowercase
        
        # Map common product types to broader categories
        if any(term in category_lower for term in ["shirt", "top", "blouse", "t-shirt", "tshirt", "tee"]):
            if gender == "female":
                generalized_categories.append("Women's Fashion")
            elif gender == "male":
                generalized_categories.append("Men's Fashion")
            else:
                generalized_categories.extend(["Women's Fashion", "Men's Fashion"])
        
        if any(term in category_lower for term in ["dress", "gown", "frock"]):
            generalized_categories.append("Women's Fashion")
        
        if any(term in category_lower for term in ["pant", "trouser", "jean", "short"]):
            if gender == "female":
                generalized_categories.append("Women's Fashion")
            elif gender == "male":
                generalized_categories.append("Men's Fashion")
            else:
                generalized_categories.extend(["Women's Fashion", "Men's Fashion"])
        
        if any(term in category_lower for term in ["clothing", "clothes", "fashion", "apparel", "wear", "garment"]):
            if gender == "female":
                generalized_categories.append("Women's Fashion")
                generalized_categories.append("fashion")  # Also try lowercase "fashion"
            elif gender == "male":
                generalized_categories.append("Men's Fashion")
                generalized_categories.append("fashion")  # Also try lowercase "fashion"
            else:
                generalized_categories.extend(["Women's Fashion", "Men's Fashion", "Fashion", "fashion"])
        
        # Always add "fashion" as a fallback if we're looking for fashion items
        if "fashion" in category_lower or any(term in category_lower for term in ["clothing", "clothes", "apparel", "wear"]):
            if "fashion" not in [c.lower() for c in generalized_categories]:
                generalized_categories.append("fashion")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_categories = []
        for cat in generalized_categories:
            if cat not in seen:
                seen.add(cat)
                unique_categories.append(cat)
        
        rows = []
        
        # 1) Try exact match first (case-insensitive)
        for cat in unique_categories:
            if price_range == "any":
                cursor.execute(
                    """
                    SELECT product_id, name, category, base_price
                    FROM products
                    WHERE LOWER(category) = LOWER(?)
                    ORDER BY base_price ASC
                    LIMIT 20
                    """,
                    (cat,),
                )
            else:
                cursor.execute(
                    """
                    SELECT product_id, name, category, base_price
                    FROM products
                    WHERE LOWER(category) = LOWER(?) AND base_price >= ? AND base_price <= ?
                    ORDER BY base_price ASC
                    LIMIT 20
                    """,
                    (cat, min_price, max_price),
                )
            new_rows = cursor.fetchall()
            if new_rows:
                rows.extend(new_rows)
                break  # Found results, stop searching
        
        # 2) If no exact match, try fuzzy search on category/name (case-insensitive)
        if not rows:
            search_terms = [cat.lower() for cat in unique_categories]
            search_terms.append(category_normalized.lower())  # Also try original category
            # Extract keywords from category for name search
            category_keywords = [w for w in category_normalized.lower().split() if len(w) > 2]
            search_terms.extend(category_keywords)
            
            for term in search_terms:
                like_term = f"%{term}%"
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
                new_rows = cursor.fetchall()
                if new_rows:
                    rows.extend(new_rows)
                    break  # Found results, stop searching
        
        # 2b) Also search product names directly if category search failed
        if not rows:
            # Search product names for keywords from the original category
            category_words = category_normalized.lower().split()
            # Also add common fashion terms based on gender
            if gender == "female":
                category_words.extend(["female", "women", "woman", "ladies", "top", "shirt", "dress"])
            elif gender == "male":
                category_words.extend(["male", "men", "man", "shirt", "top"])
            for word in category_words:
                if len(word) > 2:  # Skip very short words
                    like_term = f"%{word}%"
                    if price_range == "any":
                        cursor.execute(
                            """
                            SELECT product_id, name, category, base_price
                            FROM products
                            WHERE LOWER(name) LIKE ?
                            ORDER BY base_price ASC
                            LIMIT 20
                            """,
                            (like_term,),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT product_id, name, category, base_price
                            FROM products
                            WHERE LOWER(name) LIKE ? AND base_price >= ? AND base_price <= ?
                            ORDER BY base_price ASC
                            LIMIT 20
                            """,
                            (like_term, min_price, max_price),
                        )
                    new_rows = cursor.fetchall()
                    if new_rows:
                        rows.extend(new_rows)
                        break
        
        # 3) Final fallback: get all products (will be gender-filtered later)
        if not rows:
            if price_range == "any":
                cursor.execute(
                    """
                    SELECT product_id, name, category, base_price
                    FROM products
                    ORDER BY base_price ASC
                    LIMIT 50
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT product_id, name, category, base_price
                    FROM products
                    WHERE base_price >= ? AND base_price <= ?
                    ORDER BY base_price ASC
                    LIMIT 50
                    """,
                    (min_price, max_price),
                )
            rows = cursor.fetchall()

        # Filter by gender if specified (CRITICAL: prevent mixing male/female)
        recommendations: List[Dict[str, Any]] = []
        for row in rows:
            # If gender is specified, STRICTLY filter; otherwise include all
            if not gender:
                # No gender filter - include all
                recommendations.append(
                    {
                        "product_id": row["product_id"],
                        "name": row["name"],
                        "category": row["category"],
                        "base_price": row["base_price"],
                    }
                )
            else:
                # Gender filter is specified - ONLY include products that match
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
            if len(recommendations) >= 20:
                break

        # CRITICAL: NEVER fall back to showing all products if gender filter yields no results
        # This prevents mixing male/female products. If no matches found, return empty list.
        # The responder will handle the "no results" case appropriately.

        return recommendations
    finally:
        conn.close()

