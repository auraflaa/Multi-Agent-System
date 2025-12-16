"""User profile management tool."""
from typing import Dict, Any, Optional
from app.db.database import get_db_connection


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieve user profile from database.
    
    Args:
        user_id: User identifier
        
    Returns:
        Dictionary containing user profile information
        Returns empty dict with loyalty_tier='bronze' if user not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT user_id, name, loyalty_tier FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "loyalty_tier": row["loyalty_tier"]
            }
        else:
            # Return default profile if user not found
            return {
                "user_id": user_id,
                "name": "Guest",
                "loyalty_tier": "bronze"
            }
    finally:
        conn.close()

