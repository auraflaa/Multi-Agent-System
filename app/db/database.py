"""Database initialization and connection management."""
import sqlite3
from pathlib import Path
from typing import Optional
from app.config import DB_PATH


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn


def _seed_minimum_data(cursor: sqlite3.Cursor) -> None:
    """Seed minimal demo data if tables are empty (keeps existing data)."""

    # Loyalty tiers
    cursor.execute("SELECT COUNT(*) AS c FROM loyalty_tiers")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            "INSERT INTO loyalty_tiers (tier, display_name, sort_order) VALUES (?, ?, ?)",
            [
                ("bronze", "Bronze", 1),
                ("silver", "Silver", 2),
                ("gold", "Gold", 3),
                ("platinum", "Platinum", 4),
            ],
        )

    # Users
    cursor.execute("SELECT COUNT(*) AS c FROM users")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            "INSERT INTO users (user_id, name, loyalty_tier) VALUES (?, ?, ?)",
            [
                ("001", "EY", "bronze"),
                ("002", "Priya", "silver"),
                ("003", "Raj", "gold"),
                ("004", "Anita", "platinum"),
                ("005", "John", "bronze"),
            ],
        )

    # Categories
    cursor.execute("SELECT COUNT(*) AS c FROM categories")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            "INSERT INTO categories (category_id, name) VALUES (?, ?)",
            [
                ("001", "fashion"),
                ("CAT-001", "Women's Fashion"),
                ("CAT-002", "Men's Fashion"),
                ("CAT-003", "Fashion"),
                ("CAT-004", "Electronics"),
            ],
        )

    # Products
    cursor.execute("SELECT COUNT(*) AS c FROM products")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            "INSERT INTO products (product_id, name, category, base_price, category_id) VALUES (?, ?, ?, ?, ?)",
            [
                ("002", "Men's Shirt", "fashion", 339.0, "001"),
                ("PROD-001", "Female Branded Top", "Women's Fashion", 559.0, "CAT-001"),
                ("PROD-002", "Men's Shirt", "Men's Fashion", 339.0, "CAT-002"),
                ("PROD-003", "Women's Casual Dress", "Women's Fashion", 899.0, "CAT-001"),
                ("PROD-004", "Men's Formal Shirt", "Men's Fashion", 1299.0, "CAT-002"),
                ("PROD-005", "Women's Designer Blouse", "Women's Fashion", 1499.0, "CAT-001"),
                ("PROD-006", "Men's T-Shirt", "Men's Fashion", 499.0, "CAT-002"),
                ("PROD-007", "Women's Jeans", "Women's Fashion", 1199.0, "CAT-001"),
                ("PROD-008", "Men's Jeans", "Men's Fashion", 1299.0, "CAT-002"),
                ("PROD-009", "Women's Skirt", "Women's Fashion", 699.0, "CAT-001"),
                ("PROD-010", "Men's Shorts", "Men's Fashion", 599.0, "CAT-002"),
                ("PROD-011", "Women's Jacket", "Women's Fashion", 2499.0, "CAT-001"),
                ("PROD-012", "Men's Jacket", "Men's Fashion", 2599.0, "CAT-002"),
                ("PROD-013", "Women's Sweater", "Women's Fashion", 1599.0, "CAT-001"),
                ("PROD-014", "Men's Sweater", "Men's Fashion", 1699.0, "CAT-002"),
                ("PROD-015", "Women's Leggings", "Women's Fashion", 499.0, "CAT-001"),
                ("PROD-016", "Men's Track Pants", "Men's Fashion", 799.0, "CAT-002"),
                ("PROD-017", "Women's Formal Blazer", "Women's Fashion", 2999.0, "CAT-001"),
                ("PROD-018", "Men's Formal Blazer", "Men's Fashion", 3499.0, "CAT-002"),
                ("PROD-019", "Women's Saree", "Women's Fashion", 1999.0, "CAT-001"),
                ("PROD-020", "Men's Kurta", "Men's Fashion", 1299.0, "CAT-002"),
            ],
        )

    # Inventory
    cursor.execute("SELECT COUNT(*) AS c FROM inventory")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            "INSERT INTO inventory (sku, product_id, size, quantity, location) VALUES (?, ?, ?, ?, ?)",
            [
                ("SKU-01", "PROD-001", "M", 56, "store-001"),
                ("SKU-001", "PROD-001", "XS", 5, "warehouse"),
                ("SKU-001", "PROD-001", "S", 10, "warehouse"),
                ("SKU-001", "PROD-001", "M", 15, "warehouse"),
                ("SKU-001", "PROD-001", "L", 12, "warehouse"),
                ("SKU-001", "PROD-001", "XL", 8, "warehouse"),
                ("SKU-002", "PROD-002", "S", 20, "warehouse"),
                ("SKU-002", "PROD-002", "M", 25, "warehouse"),
                ("SKU-002", "PROD-002", "L", 22, "warehouse"),
                ("SKU-002", "PROD-002", "XL", 18, "warehouse"),
                ("SKU-002", "PROD-002", "XXL", 10, "warehouse"),
                ("SKU-003", "PROD-003", "XS", 3, "warehouse"),
                ("SKU-003", "PROD-003", "S", 8, "warehouse"),
                ("SKU-003", "PROD-003", "M", 12, "warehouse"),
                ("SKU-003", "PROD-003", "L", 10, "warehouse"),
                ("SKU-004", "PROD-004", "S", 15, "warehouse"),
                ("SKU-004", "PROD-004", "M", 20, "warehouse"),
                ("SKU-004", "PROD-004", "L", 18, "warehouse"),
                ("SKU-004", "PROD-004", "XL", 15, "warehouse"),
                ("SKU-005", "PROD-005", "XS", 2, "warehouse"),
                ("SKU-005", "PROD-005", "S", 6, "warehouse"),
                ("SKU-005", "PROD-005", "M", 10, "warehouse"),
                ("SKU-005", "PROD-005", "L", 8, "warehouse"),
                ("SKU-006", "PROD-006", "S", 30, "warehouse"),
                ("SKU-006", "PROD-006", "M", 35, "warehouse"),
                ("SKU-006", "PROD-006", "L", 30, "warehouse"),
                ("SKU-006", "PROD-006", "XL", 25, "warehouse"),
                ("SKU-007", "PROD-007", "S", 8, "warehouse"),
                ("SKU-007", "PROD-007", "M", 12, "warehouse"),
                ("SKU-007", "PROD-007", "L", 10, "warehouse"),
                ("SKU-007", "PROD-007", "XL", 8, "warehouse"),
                ("SKU-008", "PROD-008", "S", 10, "warehouse"),
                ("SKU-008", "PROD-008", "M", 15, "warehouse"),
                ("SKU-008", "PROD-008", "L", 12, "warehouse"),
                ("SKU-008", "PROD-008", "XL", 10, "warehouse"),
                ("SKU-009", "PROD-009", "XS", 5, "warehouse"),
                ("SKU-009", "PROD-009", "S", 8, "warehouse"),
                ("SKU-009", "PROD-009", "M", 10, "warehouse"),
                ("SKU-009", "PROD-009", "L", 8, "warehouse"),
                ("SKU-010", "PROD-010", "S", 12, "warehouse"),
                ("SKU-010", "PROD-010", "M", 15, "warehouse"),
                ("SKU-010", "PROD-010", "L", 12, "warehouse"),
                ("SKU-010", "PROD-010", "XL", 10, "warehouse"),
                ("SKU-011", "PROD-011", "XS", 3, "warehouse"),
                ("SKU-011", "PROD-011", "S", 5, "warehouse"),
                ("SKU-011", "PROD-011", "M", 8, "warehouse"),
                ("SKU-011", "PROD-011", "L", 6, "warehouse"),
                ("SKU-012", "PROD-012", "S", 6, "warehouse"),
                ("SKU-012", "PROD-012", "M", 8, "warehouse"),
                ("SKU-012", "PROD-012", "L", 7, "warehouse"),
                ("SKU-012", "PROD-012", "XL", 5, "warehouse"),
                ("SKU-013", "PROD-013", "XS", 4, "warehouse"),
                ("SKU-013", "PROD-013", "S", 7, "warehouse"),
                ("SKU-013", "PROD-013", "M", 10, "warehouse"),
                ("SKU-013", "PROD-013", "L", 8, "warehouse"),
                ("SKU-014", "PROD-014", "S", 8, "warehouse"),
                ("SKU-014", "PROD-014", "M", 10, "warehouse"),
                ("SKU-014", "PROD-014", "L", 9, "warehouse"),
                ("SKU-014", "PROD-014", "XL", 7, "warehouse"),
                ("SKU-015", "PROD-015", "XS", 10, "warehouse"),
                ("SKU-015", "PROD-015", "S", 15, "warehouse"),
                ("SKU-015", "PROD-015", "M", 20, "warehouse"),
                ("SKU-015", "PROD-015", "L", 15, "warehouse"),
                ("SKU-016", "PROD-016", "S", 12, "warehouse"),
                ("SKU-016", "PROD-016", "M", 15, "warehouse"),
                ("SKU-016", "PROD-016", "L", 12, "warehouse"),
                ("SKU-016", "PROD-016", "XL", 10, "warehouse"),
                ("SKU-017", "PROD-017", "XS", 2, "warehouse"),
                ("SKU-017", "PROD-017", "S", 4, "warehouse"),
                ("SKU-017", "PROD-017", "M", 6, "warehouse"),
                ("SKU-017", "PROD-017", "L", 5, "warehouse"),
                ("SKU-018", "PROD-018", "S", 5, "warehouse"),
                ("SKU-018", "PROD-018", "M", 7, "warehouse"),
                ("SKU-018", "PROD-018", "L", 6, "warehouse"),
                ("SKU-018", "PROD-018", "XL", 4, "warehouse"),
                ("SKU-019", "PROD-019", "One Size", 8, "warehouse"),
                ("SKU-020", "PROD-020", "S", 6, "warehouse"),
                ("SKU-020", "PROD-020", "M", 8, "warehouse"),
                ("SKU-020", "PROD-020", "L", 7, "warehouse"),
                ("SKU-020", "PROD-020", "XL", 5, "warehouse"),
            ],
        )

    # Orders
    cursor.execute("SELECT COUNT(*) AS c FROM orders")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            "INSERT INTO orders (order_id, user_id, total_amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
            [
                ("ORD-001", "001", 559.0, "completed", "2024-01-15T10:30:00"),
                ("ORD-002", "001", 1299.0, "pending", "2024-01-20T14:20:00"),
                ("ORD-003", "002", 899.0, "completed", "2024-01-18T09:15:00"),
                ("ORD-004", "003", 2599.0, "completed", "2024-01-22T16:45:00"),
                ("ORD-005", "001", 1999.0, "processing", "2024-01-25T11:00:00"),
            ],
        )


def init_database():
    """Initialize the database with required schema and minimal seed data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create loyalty_tiers lookup table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS loyalty_tiers (
            tier TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            sort_order INTEGER NOT NULL
        )
        """
    )

    # Create users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            loyalty_tier TEXT
        )
        """
    )
    
    # Create categories table (normalized product categories)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            category_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        """
    )

    # Create products table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            base_price REAL,
            category_id TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
        """
    )

    # Backward-compatible migration: add category_id column if it doesn't exist
    try:
        cursor.execute("PRAGMA table_info(products)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "category_id" not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN category_id TEXT")
    except Exception as e:
        print(f"Warning: could not migrate products table to add category_id: {e}")
    
    # Create inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT,
            product_id TEXT,
            size TEXT,
            quantity INTEGER,
            location TEXT,
            PRIMARY KEY (sku, size),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # Create orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT,
            total_amount REAL,
            status TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Seed minimal demo data only if tables are empty
    _seed_minimum_data(cursor)

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

