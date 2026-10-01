"""Business rules for products, stock and sales."""

import sqlite3
from decimal import Decimal, InvalidOperation

from app.db import get_connection


def non_negative_integer(value, field_name):
    """Validate whole-number values such as stock quantities."""
    try:
        number = int(str(value))
    except (ValueError, TypeError):
        raise ValueError(
            f"{field_name} must be a whole number."
        ) from None

    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")

    return number


def price_to_cents(value):
    """Convert a valid price into integer cents without rounding."""
    try:
        price = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Price must be a valid number.") from None

    if not price.is_finite() or price < 0:
        raise ValueError("Price must be a finite, non-negative number.")

    cents = price * 100

    if cents != cents.to_integral_value():
        raise ValueError("Price can have at most two decimal places.")

    if cents > 1_000_000_000:
        raise ValueError("Price is too large.")

    return int(cents)


def validate_product(sku, name, price, quantity, threshold):
    """Validate and normalise product input."""
    sku = str(sku).strip().upper()
    name = str(name).strip()

    if not sku or len(sku) > 40:
        raise ValueError("SKU must contain 1–40 characters.")

    if not name or len(name) > 100:
        raise ValueError("Product name must contain 1–100 characters.")

    return (
        sku,
        name,
        price_to_cents(price),
        non_negative_integer(quantity, "Quantity"),
        non_negative_integer(threshold, "Low-stock threshold"),
    )


def list_products(database_path):
    """Return all products, ordered by name."""
    connection = get_connection(database_path)

    try:
        return connection.execute(
            "SELECT * FROM products ORDER BY name, id"
        ).fetchall()
    finally:
        connection.close()


def create_product(database_path, sku, name, price, quantity, threshold):
    """Create a product and return its ID."""
    values = validate_product(sku, name, price, quantity, threshold)
    connection = get_connection(database_path)

    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO products
                    (sku, name, price_cents, quantity, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?)
                """,
                values,
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(
            "Product could not be saved. Check for a duplicate SKU."
        ) from None
    finally:
        connection.close()


def update_product(
    database_path, product_id, sku, name, price, quantity, threshold
):
    """Update product details and the current stock quantity."""
    values = validate_product(sku, name, price, quantity, threshold)
    connection = get_connection(database_path)

    try:
        with connection:
            cursor = connection.execute(
                """
                UPDATE products
                SET sku = ?, name = ?, price_cents = ?,
                    quantity = ?, low_stock_threshold = ?
                WHERE id = ?
                """,
                (*values, product_id),
            )

            if cursor.rowcount == 0:
                raise ValueError("Product not found.")
    except sqlite3.IntegrityError:
        raise ValueError(
            "Product could not be updated. Check for a duplicate SKU."
        ) from None
    finally:
        connection.close()


def delete_product(database_path, product_id):
    """Delete a product only if it has no sales history."""
    connection = get_connection(database_path)

    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,),
            )

            if cursor.rowcount == 0:
                raise ValueError("Product not found.")
    except sqlite3.IntegrityError:
        raise ValueError(
            "Cannot delete a product with recorded sales."
        ) from None
    finally:
        connection.close()


def record_sale(database_path, product_id, quantity):
    """Reduce stock and record a sale in one database transaction."""
    quantity = non_negative_integer(quantity, "Sale quantity")

    if quantity == 0:
        raise ValueError("Sale quantity must be greater than zero.")

    connection = get_connection(database_path)

    try:
        with connection:
            # Lock writes before reading stock to prevent competing sales
            # from both using the same available quantity.
            connection.execute("BEGIN IMMEDIATE")

            product = connection.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()

            if product is None:
                raise ValueError("Product not found.")

            if quantity > product["quantity"]:
                raise ValueError("Insufficient stock for this sale.")

            connection.execute(
                "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                (quantity, product_id),
            )

            cursor = connection.execute(
                """
                INSERT INTO sales
                    (product_id, quantity, unit_price_cents)
                VALUES (?, ?, ?)
                """,
                (product_id, quantity, product["price_cents"]),
            )

            return cursor.lastrowid
    finally:
        connection.close()


def list_sales(database_path):
    """Return sales with product details, newest first."""
    connection = get_connection(database_path)

    try:
        return connection.execute(
            """
            SELECT sales.*, products.name, products.sku,
                   sales.quantity * sales.unit_price_cents AS total_cents
            FROM sales
            JOIN products ON products.id = sales.product_id
            ORDER BY sales.id DESC
            """
        ).fetchall()
    finally:
        connection.close()