import unittest
from pathlib import Path
from unittest.mock import patch

import app as movie_app


class MovieMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        movie_app.app.config.update(TESTING=True)
        movie_app.TMDB_API_KEY = None
        cls.client = movie_app.app.test_client()

    def test_health_reports_ready_artifacts(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertTrue(response.get_json()["artifacts_ready"])

    def test_home_page_loads(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MovieMatch", response.data)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_known_title_returns_ten_local_recommendations(self):
        response = self.client.post("/similarity", data={"name": "Inception"})
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["source"], "local-ml")
        self.assertEqual(len(payload["recommendations"]), 10)

    def test_empty_title_is_rejected(self):
        response = self.client.post("/similarity", data={"name": ""})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Please enter", response.get_json()["error"])

    @patch("app.tmdb_recommendations", return_value=(None, []))
    def test_unknown_title_returns_not_found_when_tmdb_has_no_match(self, _mock_tmdb):
        response = self.client.post("/similarity", data={"name": "A totally unknown title"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "No movie was found with that title.")

    def test_browser_bundle_contains_no_tmdb_key(self):
        bundle = (Path(movie_app.BASE_DIR) / "static" / "recommend.js").read_text(encoding="utf-8")

        self.assertNotIn("TMDB_BROWSER_API_KEY", bundle)
        self.assertNotIn("api_key", bundle)


if __name__ == "__main__":
    unittest.main()
