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


def init_database():
    """Initialize the database with required schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            loyalty_tier TEXT
        )
    """)
    
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
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

