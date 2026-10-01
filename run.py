"""Run the inventory application using Waitress."""

import os

from waitress import serve

from app import create_app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("APP_HOST", "127.0.0.1")
    port = int(os.environ.get("APP_PORT", "5000"))

    print(f"Inventory application starting at http://{host}:{port}")

    serve(app, host=host, port=port)
    