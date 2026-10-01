"""Check a deployed application's health, version and homepage."""

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def check_application(base_url, environment, version):
    with urlopen(f"{base_url}/health", timeout=5) as response:
        health = json.load(response)

    expected = {
        "status": "healthy",
        "database": "connected",
        "environment": environment,
        "version": version,
    }

    for key, value in expected.items():
        if health.get(key) != value:
            raise ValueError(
                f"Health check mismatch for {key}: "
                f"expected {value!r}, received {health.get(key)!r}"
            )

    with urlopen(base_url + "/", timeout=5) as response:
        html = response.read().decode("utf-8")

    if 'name="csrf_token"' not in html:
        raise ValueError("Homepage did not contain the inventory form.")

    return health


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    last_error = None

    # Allow time for the container and database to start.
    for attempt in range(1, 13):
        try:
            health = check_application(
                base_url, args.environment, args.version
            )
            print(json.dumps(health, indent=2))
            print("Deployment checks passed: health, version and homepage.")
            return 0
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            last_error = error
            print(f"Attempt {attempt}/12: {error}")
            if attempt < 12:
                time.sleep(5)

    print(f"Deployment checks failed: {last_error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

