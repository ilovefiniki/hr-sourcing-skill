import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server as srv


def _post_json(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    return urllib.request.urlopen(req)


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp()
        # Write a minimal form.html so GET / works
        with open(os.path.join(cls.test_dir, "form.html"), "w") as f:
            f.write("<html><body>form</body></html>")
        srv.SCRIPT_DIR = cls.test_dir
        cls.httpd = srv.make_server(18765)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        shutil.rmtree(cls.test_dir)

    def test_get_root_serves_form(self):
        resp = urllib.request.urlopen("http://localhost:18765/")
        self.assertEqual(resp.status, 200)
        self.assertIn(b"form", resp.read())

    def test_get_unknown_path_returns_404(self):
        try:
            urllib.request.urlopen("http://localhost:18765/unknown")
            self.fail("Expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_post_submit_writes_submission_json(self):
        payload = {
            "job_title": "ML Engineer",
            "company_name": "Celonis",
            "search_tier": "1",
            "manual_companies": "",
        }
        resp = _post_json("http://localhost:18765/submit", payload)
        self.assertEqual(resp.status, 200)
        result = json.loads(resp.read())
        self.assertEqual(result["status"], "received")

        path = os.path.join(srv.SCRIPT_DIR, "submission.json")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            saved = json.load(f)
        self.assertEqual(saved["job_title"], "ML Engineer")
        self.assertEqual(saved["search_tier"], "1")

    def test_post_save_missing_env_returns_500(self):
        os.environ.pop("AIRTABLE_TOKEN", None)
        os.environ.pop("AIRTABLE_BASE_ID", None)
        try:
            _post_json("http://localhost:18765/save", {"candidates": []})
            self.fail("Expected 500")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 500)
            body = json.loads(e.read())
            self.assertIn("error", body)

    def test_post_submit_empty_body_returns_400(self):
        req = urllib.request.Request(
            "http://localhost:18765/submit",
            data=b"",
            headers={"Content-Type": "application/json", "Content-Length": "0"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            self.fail("Expected 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_options_returns_cors_headers(self):
        req = urllib.request.Request(
            "http://localhost:18765/submit", method="OPTIONS"
        )
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)

    def test_post_save_malformed_body_returns_400(self):
        os.environ["AIRTABLE_TOKEN"] = "tok"
        os.environ["AIRTABLE_BASE_ID"] = "base"
        req = urllib.request.Request(
            "http://localhost:18765/save",
            data=b"[1,2,3]",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            self.fail("Expected 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
        finally:
            os.environ.pop("AIRTABLE_TOKEN", None)
            os.environ.pop("AIRTABLE_BASE_ID", None)
