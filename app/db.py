"""SQLite database setup for the inventory application."""

import sqlite3
from pathlib import Path


def get_connection(database_path):
    """Open a database connection with foreign-key checks enabled."""
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database(database_path):
    """Create the database directory and tables if they do not exist."""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    connection = get_connection(database_path)

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                price_cents INTEGER NOT NULL
                    CHECK (price_cents >= 0),
                quantity INTEGER NOT NULL DEFAULT 0
                    CHECK (quantity >= 0),
                low_stock_threshold INTEGER NOT NULL DEFAULT 5
                    CHECK (low_stock_threshold >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (length(trim(sku)) > 0),
                CHECK (length(trim(name)) > 0)
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL
                    CHECK (quantity > 0),
                unit_price_cents INTEGER NOT NULL
                    CHECK (unit_price_cents >= 0),
                sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id)
                    REFERENCES products(id)
                    ON DELETE RESTRICT
            );
        """)
        connection.commit()
    finally:
        connection.close()
        