"""Verify monitoring services and fresh health probes."""

import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def check_monitoring():
    for url in (
        "http://127.0.0.1:9090/-/ready",
        "http://127.0.0.1:9093/-/ready",
        "http://127.0.0.1:9094/health",
    ):
        with urlopen(url, timeout=5) as response:
            if response.status != 200:
                raise ValueError(f"Service is not ready: {url}")

    # Require samples collected within the last 60 seconds.
    metric = 'probe_success{job="inventory-health"}'
    query = f"{metric} and (time() - timestamp({metric}) < 60)"
    url = "http://127.0.0.1:9090/api/v1/query?" + urlencode(
        {"query": query}
    )

    with urlopen(url, timeout=5) as response:
        payload = json.load(response)

    if payload.get("status") != "success":
        raise ValueError("Prometheus query failed")

    results = payload["data"]["result"]
    environments = {
        item["metric"]["environment"]: float(item["value"][1])
        for item in results
    }

    if len(results) != 2 or environments != {
        "staging": 1.0,
        "production": 1.0,
    }:
        raise ValueError(f"Health probes are not ready: {environments}")

    report = Path("reports/monitoring.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Monitoring checks passed: services ready and both probes healthy.")


def main():
    for attempt in range(1, 13):
        try:
            check_monitoring()
            return 0
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"Attempt {attempt}/12: {error}", flush=True)
            if attempt < 12:
                time.sleep(5)

    print("Monitoring checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())