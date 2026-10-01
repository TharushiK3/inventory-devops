"""Receive Alertmanager notifications and retain the latest 100 deliveries."""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

STORE = Path("/data/notifications.json")


def read_notifications():
    if STORE.exists():
        return json.loads(STORE.read_text(encoding="utf-8"))
    return []


class AlertInbox(BaseHTTPRequestHandler):
    def respond(self, status, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"status": "healthy"})
        elif self.path in ("/", "/notifications"):
            self.respond(200, read_notifications())
        else:
            self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/webhook":
            self.respond(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1_000_000:
                raise ValueError("Invalid notification size")

            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
        except (ValueError, UnicodeDecodeError):
            self.respond(400, {"error": "Invalid notification"})
            return

        notifications = read_notifications()
        notifications.append({
            "received_at": datetime.now(timezone.utc).isoformat(),
            "notification": payload,
        })

        STORE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STORE.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(notifications[-100:], indent=2),
            encoding="utf-8",
        )
        temporary.replace(STORE)

        print(
            f"Alert delivered: status={payload.get('status')} "
            f"alerts={len(payload.get('alerts', []))}",
            flush=True,
        )
        self.respond(200, {"received": True})


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), AlertInbox).serve_forever()