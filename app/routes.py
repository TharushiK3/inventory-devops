"""Web routes for inventory management and health checks."""

import hmac
import secrets
import sqlite3

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.db import get_connection
from app.services import (
    create_product,
    delete_product,
    list_products,
    list_sales,
    record_sale,
    update_product,
)


bp = Blueprint("inventory", __name__)
INDEX_ENDPOINT = "inventory.index"


@bp.before_request
def protect_forms():
    """Reject POST requests without the browser session's form token."""
    if request.method == "POST":
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "")

        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400, description="Invalid form token. Refresh and try again.")


def product_form_values():
    """Read product fields; validation happens in the service layer."""
    return (
        request.form.get("sku", ""),
        request.form.get("name", ""),
        request.form.get("price", ""),
        request.form.get("quantity", ""),
        request.form.get("threshold", ""),
    )


@bp.get("/")
def index():
    """Display products, stock summaries and sales history."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    database = current_app.config["DATABASE"]
    products = list_products(database)
    sales = list_sales(database)

    return render_template(
        "index.html",
        products=products,
        sales=sales,
        csrf_token=session["csrf_token"],
        total_units=sum(product["quantity"] for product in products),
        low_stock_count=sum(
            product["quantity"] <= product["low_stock_threshold"]
            for product in products
        ),
        revenue_cents=sum(sale["total_cents"] for sale in sales),
    )


@bp.post("/products")
def add_product():
    """Create a product from the dashboard form."""
    try:
        create_product(
            current_app.config["DATABASE"],
            *product_form_values(),
        )
        flash("Product added successfully.", "success")
    except ValueError as error:
        flash(str(error), "error")

    return redirect(url_for(INDEX_ENDPOINT))


@bp.post("/products/<int:product_id>/update")
def edit_product(product_id):
    """Update product details and stock."""
    try:
        update_product(
            current_app.config["DATABASE"],
            product_id,
            *product_form_values(),
        )
        flash("Product updated successfully.", "success")
    except ValueError as error:
        flash(str(error), "error")

    return redirect(url_for(INDEX_ENDPOINT))


@bp.post("/products/<int:product_id>/delete")
def remove_product(product_id):
    """Delete a product without sales history."""
    try:
        delete_product(current_app.config["DATABASE"], product_id)
        flash("Product deleted successfully.", "success")
    except ValueError as error:
        flash(str(error), "error")

    return redirect(url_for(INDEX_ENDPOINT))


@bp.post("/products/<int:product_id>/sell")
def sell_product(product_id):
    """Record a sale and deduct stock."""
    try:
        record_sale(
            current_app.config["DATABASE"],
            product_id,
            request.form.get("quantity", ""),
        )
        flash("Sale recorded and stock updated.", "success")
    except ValueError as error:
        flash(str(error), "error")

    return redirect(url_for(INDEX_ENDPOINT))


@bp.get("/health")
def health():
    """Check that the application can read its database."""
    connection = None

    try:
        connection = get_connection(current_app.config["DATABASE"])
        connection.execute("SELECT COUNT(*) FROM products").fetchone()
    except sqlite3.Error:
        current_app.logger.exception("Database health check failed")
        return jsonify(
            status="unhealthy",
            database="unavailable",
        ), 503
    finally:
        if connection is not None:
            connection.close()

    return jsonify(
        status="healthy",
        database="connected",
        environment=current_app.config["APP_ENV"],
        version=current_app.config["APP_VERSION"],
    ), 200