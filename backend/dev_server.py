"""Thin HTTP wrapper around the Lambda handler for local development."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from hello.handler import handler


class LambdaHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _handle(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""

        event: dict[str, object] = {
            "httpMethod": self.command,
            "path": parsed.path,
            "queryStringParameters": dict(
                p.split("=", 1) for p in parsed.query.split("&") if "=" in p
            ),
            "headers": dict(self.headers),
            "body": body,
        }

        result = handler(event, None)

        status: int = result.get("statusCode", 200)  # type: ignore[assignment]
        headers: dict[str, str] = result.get("headers", {})  # type: ignore[assignment]
        response_body: str = result.get("body", "")  # type: ignore[assignment]

        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        encoded = response_body.encode()
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[backend] {fmt % args}")


if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("0.0.0.0", port), LambdaHandler)
    print(f"[backend] listening on http://localhost:{port}")
    server.serve_forever()
