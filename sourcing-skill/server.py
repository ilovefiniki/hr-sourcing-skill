import json
import os
import ssl
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# macOS Python ships without system keychain certs; skip verification for
# localhost→Airtable calls (known trusted endpoint, no MITM risk here).
_SSL_CTX = ssl._create_unverified_context()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def make_server(port=8765):
    return HTTPServer(("localhost", port), SourcingHandler)


def load_env(path=None):
    env_path = path or os.path.join(SCRIPT_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


class SourcingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._serve_file("form.html", "text/html; charset=utf-8")
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/submit":
            self._handle_submit()
        elif self.path == "/save":
            self._handle_save()
        else:
            self._respond(404, {"error": "not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_file(self, filename, content_type):
        path = os.path.join(SCRIPT_DIR, filename)
        try:
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._respond(404, {"error": f"{filename} not found"})

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            return {}

    def _respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress default access log

    # ── route handlers ────────────────────────────────────────────────────────

    def _handle_submit(self):
        data = self._read_body()
        if not data:
            self._respond(400, {"error": "empty or malformed request body"})
            return
        path = os.path.join(SCRIPT_DIR, "submission.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._respond(200, {"status": "received"})

    def _handle_save(self):
        token = os.environ.get("AIRTABLE_TOKEN", "")
        base_id = os.environ.get("AIRTABLE_BASE_ID", "")
        if not token or not base_id:
            self._respond(
                500,
                {
                    "error": "AIRTABLE_TOKEN or AIRTABLE_BASE_ID not set — check sourcing-skill/.env"
                },
            )
            return

        data = self._read_body()
        if not isinstance(data, dict):
            self._respond(400, {"error": "malformed request body"})
            return
        candidates = data.get("candidates", [])
        url = f"https://api.airtable.com/v0/{base_id}/Candidates"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        saved = 0
        errors = []
        for c in candidates:
            record = {
                "fields": {
                    "Full Name": c.get("full_name", ""),
                    "LI Profile": c.get("linkedin_url", ""),
                    "Location": c.get("location", ""),
                    "Current Position": c.get("current_title", ""),
                    "Current Company": c.get("current_company", ""),
                    "Source": c.get("source", ""),
                    "Mandate ID": c.get("mandate_id", ""),
                    "Job Title (Mandate)": c.get("job_title", ""),
                    "Company (Mandate)": c.get("company_name", ""),
                    "Added Date": c.get("added_date", "")[:10],
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(record).encode(),
                headers=headers,
                method="POST",
            )
            try:
                urllib.request.urlopen(req, context=_SSL_CTX)
                saved += 1
            except urllib.error.HTTPError as e:
                errors.append(f"HTTP {e.code}: {e.read().decode()[:200]}")
            except Exception as e:
                errors.append(str(e))

        self._respond(200, {"saved": saved, "errors": errors})


if __name__ == "__main__":
    load_env()
    port = 8765
    httpd = make_server(port)
    print(f"Sourcing server → http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
