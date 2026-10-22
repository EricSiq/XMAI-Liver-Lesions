#!/usr/bin/env python3
"""
Lightweight Academic Presentation Server for XMAI.
Serves the presentation frontend on localhost:8000 (or custom port).
Provides optional JSON API endpoints dynamically while supporting offline client-side execution.

Usage:
    python scripts/serve_frontend.py --port 8000
"""

import argparse
import http.server
import json
from pathlib import Path
import socketserver
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"


class XMAIHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler serving frontend with CORS and JSON API fallbacks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        # API endpoints routing
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status = {
                "status": "online",
                "framework": "XMAI Academic Console v2.0",
                "models": 9,
                "cohort_patients": 743,
                "external_patients": 120,
            }
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        # Serve static files from FRONTEND_DIR
        return super().do_GET()


def main():
    parser = argparse.ArgumentParser(description="Serve XMAI Academic Presentation Console.")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    args = parser.parse_args()

    if not FRONTEND_DIR.exists():
        FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

    port = args.port
    # Handle port in use gracefully
    while port < args.port + 10:
        try:
            with socketserver.TCPServer(("", port), XMAIHTTPHandler) as httpd:
                print(f"============================================================")
                print(f"  XMAI Academic Presentation Console Server")
                print(f"  Live at: http://localhost:{port}")
                print(f"  Root:    {FRONTEND_DIR}")
                print(f"============================================================")
                httpd.serve_forever()
                break
        except OSError as e:
            if "Address already in use" in str(e) or e.errno == 10048:
                port += 1
                continue
            else:
                raise


if __name__ == "__main__":
    main()
