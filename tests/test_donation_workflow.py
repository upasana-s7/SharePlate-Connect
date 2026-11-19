"""End-to-end tests for the SharePlate donation workflow.

Run with: python -m unittest discover -s tests -v
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

_TEST_DIR = tempfile.TemporaryDirectory(prefix="shareplate-tests-")
os.environ["SHAREPLATE_DB_PATH"] = os.path.join(_TEST_DIR.name, "test.db")
os.environ["SECRET_KEY"] = "shareplate-test-secret"
os.environ["COOKIE_SECURE"] = "false"
os.environ["SEED_DEMO_DATA"] = "false"

import app as shareplate  # noqa: E402


class DonationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = shareplate.app.test_client()
        response = self.client.get("/donate")
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.csrf_token = session["_csrf_token"]

    def _valid_donation(self):
        ready = datetime.now(shareplate.APP_TIMEZONE).replace(second=0, microsecond=0) + timedelta(hours=1)
        deadline = ready + timedelta(hours=3)
        return {
            "csrf_token": self.csrf_token,
            "donor_name": "Test College Cafeteria",
            "food_name": "Test Vegetable Biryani",
            "food_type": "prepared_meals",
            "quantity": "4",
            "servings": "40",
            "location": "Indiranagar, Bengaluru",
            "available_from": ready.strftime("%Y-%m-%dT%H:%M"),
            "available_until": deadline.strftime("%Y-%m-%dT%H:%M"),
            "storage_info": "Packed safely",
            "notes": "Automated workflow test",
        }

    def test_submitted_donation_is_saved_and_browsable(self):
        response = self.client.post("/donate", data=self._valid_donation())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Vegetable Biryani", response.data)

        browse = self.client.get("/donations")
        self.assertEqual(browse.status_code, 200)
        self.assertIn(b"Test Vegetable Biryani", browse.data)
        self.assertIn(b"Test College Cafeteria", browse.data)

        with shareplate.get_connection() as conn:
            row = conn.execute(
                "SELECT food_name, status, servings FROM donations WHERE food_name = ?",
                ("Test Vegetable Biryani",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["servings"], 40)

    def test_invalid_donation_is_not_saved(self):
        response = self.client.post(
            "/donate",
            data={"csrf_token": self.csrf_token, "donor_name": "Incomplete"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn(b"Please fix the following", response.data)
        with shareplate.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM donations WHERE donor_name = 'Incomplete'"
            ).fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
