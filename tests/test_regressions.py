"""Regression tests for the security, AI-fallback, and DB money paths.

Covers the fixes made in this pass:
  - The hardcoded 999999 delete-account OTP backdoor is gone.
  - OTP expiry always applies (unless an explicit OTP_FALLBACK_CODE env is set).
  - SMTP failure no longer leaks a static bypass code to the client.
  - bump_stat reuses a caller-provided connection (no "database is locked").
  - Local AI fallback is deterministic when providers are down.
"""
import importlib.util
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

# Keep tests hermetic: app.py's load_dotenv() would otherwise pull DATABASE_URL
# from the developer's real .env and route test writes to production Neon.
# load_dotenv() uses override=False, so pre-seeding empty wins.
os.environ["DATABASE_URL"] = ""

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "app.py"
TEST_PASSWORD = "SmokePass123!"


def _load_module():
    """Import app.py as a fresh module object with a temp SQLite DB."""
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = os.path.join(temp_dir.name, "codebuddy_test.db")
    os.environ["CODEBUDDY_DB_PATH"] = db_path
    spec = importlib.util.spec_from_file_location("codebuddy_reg", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, temp_dir


class DeleteAccountOtpSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.temp_dir = _load_module()
        cls.module.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _seed_user(self, email):
        conn = sqlite3.connect(self.module.DB_PATH)
        try:
            conn.row_factory = sqlite3.Row
            password_hash = self.module.bcrypt.generate_password_hash(TEST_PASSWORD).decode()
            cursor = conn.execute(
                "INSERT INTO users(username, password, email) VALUES (?, ?, ?)",
                (email.split("@")[0], password_hash, email),
            )
            user_id = cursor.lastrowid
            conn.execute(
                "INSERT OR IGNORE INTO user_stats(user_id, last_active) VALUES (?, datetime('now'))",
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()
        return user_id

    def _login(self, client, email):
        response = client.post(
            "/login",
            data={"email": email, "password": TEST_PASSWORD},
            follow_redirects=False,
        )
        self.assertIn(response.status_code, (200, 302))

    def _request_otp(self, client, email):
        with patch.object(self.module, "send_delete_otp_email", return_value=None):
            return client.post("/delete_account/request_otp", data={"email": email})

    def _delete_otp_from_session(self, client):
        with client.session_transaction() as sess:
            return sess.get("delete_otp")

    def _expire_otp_in_session(self, client):
        with client.session_transaction() as sess:
            sess["delete_otp_expires"] = time.time() - 100

    def test_999999_backdoor_is_rejected(self):
        email = "backdoor@example.com"
        self._seed_user(email)
        client = self.module.app.test_client()
        self._login(client, email)
        # No OTP_FALLBACK_CODE configured and no OTP requested: 999999 must be
        # rejected as an invalid code — this is the old hardcoded backdoor.
        response = client.post(
            "/delete_account",
            data={"email": email, "password": TEST_PASSWORD, "otp": "999999"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())
        self.assertIn("Invalid verification code", response.get_json()["error"])

    def test_request_otp_smtp_failure_does_not_leak_static_code(self):
        email = "smtpdown@example.com"
        self._seed_user(email)
        client = self.module.app.test_client()
        self._login(client, email)
        with patch.object(self.module, "send_delete_otp_email", side_effect=RuntimeError("SMTP down")):
            response = client.post("/delete_account/request_otp", data={"email": email})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))
        # No static, publicly-disclosable bypass code should ever be returned.
        self.assertNotIn("999999", response.get_data(as_text=True))

    def test_valid_otp_deletes_account(self):
        email = "valid@example.com"
        self._seed_user(email)
        client = self.module.app.test_client()
        self._login(client, email)

        otp_response = self._request_otp(client, email)
        self.assertEqual(otp_response.status_code, 200)
        otp = self._delete_otp_from_session(client)
        self.assertTrue(otp and len(otp) == 6, "expected a real OTP in the session")

        response = client.post(
            "/delete_account",
            data={"email": email, "password": TEST_PASSWORD, "otp": otp},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

        # The user row should actually be gone.
        conn = sqlite3.connect(self.module.DB_PATH)
        row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        self.assertIsNone(row)

    def test_expired_otp_is_rejected(self):
        email = "expired@example.com"
        self._seed_user(email)
        client = self.module.app.test_client()
        self._login(client, email)

        self._request_otp(client, email)
        otp = self._delete_otp_from_session(client)
        self.assertTrue(otp)
        self._expire_otp_in_session(client)

        response = client.post(
            "/delete_account",
            data={"email": email, "password": TEST_PASSWORD, "otp": otp},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("expired", response.get_json()["error"].lower())

    def test_fallback_code_only_works_when_configured(self):
        email = "fallback@example.com"
        self._seed_user(email)
        client = self.module.app.test_client()
        self._login(client, email)

        with patch.dict(os.environ, {"OTP_FALLBACK_CODE": "AB12CD"}):
            response = client.post(
                "/delete_account",
                data={"email": email, "password": TEST_PASSWORD, "otp": "AB12CD"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))


class AiFallbackChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.temp_dir = _load_module()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_local_chat_fallback_is_deterministic_and_offline(self):
        result = self.module._local_chat_response(
            "```python\ndef foo():\n    return 1\n```",
            "debug",
            "en-US",
            "mentor",
        )
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())
        self.assertIn("local best-effort", result)

    def test_local_explain_fallback_returns_content(self):
        result = self.module._local_quick_explain("def add(a, b):\n    return a + b")
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())


class DbHelperRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.temp_dir = _load_module()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _seed_user(self, email):
        conn = sqlite3.connect(self.module.DB_PATH)
        try:
            conn.row_factory = sqlite3.Row
            password_hash = self.module.bcrypt.generate_password_hash(TEST_PASSWORD).decode()
            cursor = conn.execute(
                "INSERT INTO users(username, password, email) VALUES (?, ?, ?)",
                (email.split("@")[0], password_hash, email),
            )
            user_id = cursor.lastrowid
            conn.execute(
                "INSERT OR IGNORE INTO user_stats(user_id, last_active) VALUES (?, datetime('now'))",
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()
        return user_id

    def test_bump_stat_reuses_caller_conn_without_lock(self):
        # Regression for the "database is locked" bug: bump_stat must honor a
        # caller-provided connection instead of opening a second one while the
        # caller holds an uncommitted write.
        user_id = self._seed_user("bumpstats@example.com")
        conn = sqlite3.connect(self.module.DB_PATH)
        conn.execute(
            "INSERT INTO conversations(user_id,title,mode,created_at,updated_at) "
            "VALUES (?,?,?,?,?)",
            (user_id, "t", "general", "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        # This used to raise sqlite3.OperationalError: database is locked.
        self.module.bump_stat(user_id, "total_chats", conn=conn)
        conn.commit()
        conn.close()

        conn = sqlite3.connect(self.module.DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT total_chats FROM user_stats WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        self.assertGreaterEqual(row["total_chats"], 1)

    def test_memory_helpers_roundtrip(self):
        user_id = self._seed_user("memory@example.com")
        self.module.set_user_memory(user_id, "preferred_language", "python")
        mem = self.module.get_user_memory(user_id)
        self.assertEqual(mem.get("preferred_language"), "python")

    def test_update_streak_initializes_row(self):
        user_id = self._seed_user("streak@example.com")
        self.module.update_streak(user_id)
        conn = sqlite3.connect(self.module.DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT streak_days FROM user_stats WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertGreaterEqual(row["streak_days"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
