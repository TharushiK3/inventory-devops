"""Automated business-rule and web integration tests."""

import pytest

from app import create_app
from app.services import (
    create_product,
    delete_product,
    list_products,
    list_sales,
    price_to_cents,
    record_sale,
    update_product,
)


# Each test receives a fresh application and temporary database.
@pytest.fixture
def application(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "automated-tests-only",
        "DATABASE": str(tmp_path / "test_inventory.db"),
        "APP_ENV": "testing",
        "APP_VERSION": "test",
    })


@pytest.fixture
def database(application):
    return application.config["DATABASE"]


@pytest.fixture
def client(application):
    return application.test_client()


@pytest.fixture
def product_id(database):
    return create_product(
        database, "PRD-001", "Notebook", "250.00", "10", "5"
    )


def post_form(client, path, data):
    """Submit a form with a valid token from the browser session."""
    client.get("/")

    with client.session_transaction() as browser_session:
        token = browser_session["csrf_token"]

    return client.post(
        path,
        data={**data, "csrf_token": token},
        follow_redirects=True,
    )


# ---------- Business-rule tests ----------

def test_create_product(database, product_id):
    products = list_products(database)

    assert len(products) == 1
    assert products[0]["id"] == product_id
    assert products[0]["sku"] == "PRD-001"
    assert products[0]["price_cents"] == 25000
    assert products[0]["quantity"] == 10


def test_duplicate_sku_rejected(database, product_id):
    with pytest.raises(ValueError, match="duplicate SKU"):
        create_product(
            database, "prd-001", "Another notebook", "100", "3", "1"
        )

    assert len(list_products(database)) == 1


@pytest.mark.parametrize("price", ["-1", "abc", "NaN", "Infinity", "1.001"])
def test_invalid_prices_rejected(price):
    with pytest.raises(ValueError):
        price_to_cents(price)


@pytest.mark.parametrize("quantity", ["-1", "1.5", "abc"])
def test_invalid_stock_rejected(database, quantity):
    with pytest.raises(ValueError):
        create_product(
            database, "PRD-002", "Pen", "50", quantity, "5"
        )

    assert list_products(database) == []


def test_update_product(database, product_id):
    update_product(
        database, product_id, "PRD-001", "Premium notebook",
        "300.00", "5", "5",
    )

    product = list_products(database)[0]

    assert product["name"] == "Premium notebook"
    assert product["price_cents"] == 30000
    assert product["quantity"] == 5


def test_sale_reduces_stock_and_records_revenue(database, product_id):
    record_sale(database, product_id, "2")

    assert list_products(database)[0]["quantity"] == 8

    sales = list_sales(database)
    assert len(sales) == 1
    assert sales[0]["quantity"] == 2
    assert sales[0]["total_cents"] == 50000


def test_insufficient_stock_leaves_database_unchanged(database, product_id):
    with pytest.raises(ValueError, match="Insufficient stock"):
        record_sale(database, product_id, "20")

    assert list_products(database)[0]["quantity"] == 10
    assert list_sales(database) == []


@pytest.mark.parametrize("quantity", ["0", "-1", "1.5", "abc"])
def test_invalid_sale_quantity_rejected(database, product_id, quantity):
    with pytest.raises(ValueError):
        record_sale(database, product_id, quantity)

    assert list_products(database)[0]["quantity"] == 10
    assert list_sales(database) == []


def test_delete_product_without_sales(database, product_id):
    delete_product(database, product_id)

    assert list_products(database) == []


def test_product_with_sales_cannot_be_deleted(database, product_id):
    record_sale(database, product_id, "1")

    with pytest.raises(ValueError, match="recorded sales"):
        delete_product(database, product_id)

    assert len(list_products(database)) == 1
    assert len(list_sales(database)) == 1


def test_sale_keeps_original_price(database, product_id):
    record_sale(database, product_id, "2")

    update_product(
        database, product_id, "PRD-001", "Notebook",
        "300.00", "8", "5",
    )

    assert list_sales(database)[0]["unit_price_cents"] == 25000
    assert list_sales(database)[0]["total_cents"] == 50000


def test_sale_for_missing_product_rejected(database):
    with pytest.raises(ValueError, match="Product not found"):
        record_sale(database, 999, "1")

    assert list_sales(database) == []


# ---------- Web integration tests ----------

def test_homepage_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Velvet Stock" in response.data


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"
    assert response.json["database"] == "connected"
    assert response.json["environment"] == "testing"


def test_create_product_through_form(client, database):
    response = post_form(client, "/products", {
        "sku": "PRD-003",
        "name": "Pencil",
        "price": "30.00",
        "quantity": "12",
        "threshold": "5",
    })

    assert response.status_code == 200
    assert b"Product added successfully." in response.data
    assert list_products(database)[0]["name"] == "Pencil"


def test_sale_through_form(client, database, product_id):
    response = post_form(
        client,
        f"/products/{product_id}/sell",
        {"quantity": "2"},
    )

    assert response.status_code == 200
    assert b"Sale recorded and stock updated." in response.data
    assert list_products(database)[0]["quantity"] == 8
    assert len(list_sales(database)) == 1


def test_overselling_shows_error(client, database, product_id):
    response = post_form(
        client,
        f"/products/{product_id}/sell",
        {"quantity": "20"},
    )

    assert b"Insufficient stock" in response.data
    assert list_products(database)[0]["quantity"] == 10
    assert list_sales(database) == []


def test_low_stock_indicator(client, database, product_id):
    update_product(
        database, product_id, "PRD-001", "Notebook",
        "250.00", "5", "5",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Low stock" in response.data


def test_form_without_token_rejected(client, database):
    response = client.post("/products", data={
        "sku": "PRD-004",
        "name": "Eraser",
        "price": "20",
        "quantity": "10",
        "threshold": "5",
    })

    assert response.status_code == 400
    assert list_products(database) == []
    