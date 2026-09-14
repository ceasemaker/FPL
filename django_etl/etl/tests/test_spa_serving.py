import tempfile
from pathlib import Path

from django.test import TestCase, override_settings


class SpaServingTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dist = Path(self.tmp.name)
        (self.dist / "index.html").write_text("<!doctype html><title>AeroFPL</title><div id=root></div>")

    def tearDown(self):
        self.tmp.cleanup()

    def test_deep_client_routes_return_index_html(self):
        with override_settings(FRONTEND_DIST=self.dist):
            for route in ("/players", "/decision-lab?mode=optimizer", "/compare"):
                r = self.client.get(route)
                self.assertEqual(r.status_code, 200, route)
                self.assertIn(b"<title>AeroFPL</title>", r.content)
                self.assertIn("no-cache", r["Cache-Control"])

    def test_root_is_served(self):
        # "/" is WhiteNoise's index file when a real build exists (it indexes
        # WHITENOISE_ROOT at startup, so override_settings cannot redirect it);
        # otherwise it falls through to spa_index. Either way the app shell loads.
        with override_settings(FRONTEND_DIST=self.dist):
            r = self.client.get("/")
            self.assertEqual(r.status_code, 200)
            body = b"".join(r.streaming_content) if r.streaming else r.content
            self.assertIn(b'<div id="root">', body)

    def test_api_routes_are_not_swallowed(self):
        with override_settings(FRONTEND_DIST=self.dist):
            self.assertEqual(self.client.get("/api/landing/").status_code, 200)
            self.assertEqual(self.client.get("/api/does-not-exist/").status_code, 404)
            self.assertNotIn(b"<title>AeroFPL</title>", self.client.get("/api/does-not-exist/").content)

    def test_missing_bundle_is_explicit(self):
        with override_settings(FRONTEND_DIST=self.dist / "nope"):
            r = self.client.get("/players")
            self.assertEqual(r.status_code, 404)
            self.assertIn(b"npm run build", r.content)
