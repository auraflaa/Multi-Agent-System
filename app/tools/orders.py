"""Orders retrieval tool."""
from typing import List, Dict
from app.db.database import get_db_connection


def get_orders(user_id: str) -> List[Dict]:
    """
    Fetch all orders for a given user_id.

    Returns a list of dicts with keys:
    - order_id
    - user_id
    - total_amount
    - status
    - created_at
    """
    conn = get_db_connection()
    conn.row_factory = None  # Use tuple rows for performance; map manually
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT order_id, user_id, total_amount, status, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "order_id": r[0],
                "user_id": r[1],
                "total_amount": r[2],
                "status": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()

