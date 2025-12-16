"""User profile management tool."""
from typing import Dict, Any
from app.db.database import get_db_connection


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieve user profile from database.

    Args:
        user_id: User identifier

    Returns:
        Dictionary containing user profile information.
        Returns default profile with loyalty_tier='bronze' if user not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT user_id, name, loyalty_tier FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()

        if row:
            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "loyalty_tier": row["loyalty_tier"],
            }
        else:
            # Return default profile if user not found
            return {
                "user_id": user_id,
                "name": "Guest",
                "loyalty_tier": "bronze",
            }
    finally:
        conn.close()


def update_user_name(user_id: str, name: str) -> Dict[str, Any]:
    """
    Update the user's display name in the database.

    This deterministic tool is used when the user asks the agent
    to change how they are addressed (e.g. "Call me Priya").
    """
    if not user_id:
        raise ValueError("user_id is required")
    if not name or not name.strip():
        raise ValueError("name must be a non-empty string")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET name = ?
            WHERE user_id = ?
            """,
            (name.strip(), user_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"User '{user_id}' does not exist in users table")
        conn.commit()

        cursor.execute(
            "SELECT user_id, name, loyalty_tier FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "loyalty_tier": row["loyalty_tier"],
        }
    finally:
        conn.close()

