import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "app.py"
TEST_USERNAME = "smoke_user_test"
TEST_PASSWORD = "SmokePass123!"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, lines=None):
        self.status_code = status_code
        self._payload = payload or {}
        self._lines = lines or []

    def json(self):
        return self._payload

    def iter_lines(self):
        for line in self._lines:
            yield line.encode("utf-8")


def fake_post(url, headers=None, json=None, stream=False, timeout=None, **kwargs):
    payload = json or {}
    url_text = str(url).lower()

    if "piston" in url_text:
        return FakeResponse(
            200,
            {
                "run": {"stdout": "benchmark run ok\n", "stderr": ""},
                "compile": {"stdout": "", "stderr": ""},
            },
        )

    if "groq.com" in url_text or "openrouter.ai" in url_text:
        messages = payload.get("messages", [])
        prompt_text = " ".join(
            str(message.get("content", "")) for message in messages if isinstance(message, dict)
        ).lower()

        if stream:
            return FakeResponse(
                200,
                lines=[
                    'data: {"choices":[{"delta":{"content":"Hello"}}]}',
                    'data: {"choices":[{"delta":{"content":" world"}}]}',
                    "data: [DONE]",
                ],
            )

        if "reply only: yes or no" in prompt_text or payload.get("max_tokens", 0) <= 5:
            content = "YES"
        elif "concise 3-5 word title" in prompt_text or "title" in prompt_text:
            content = "Smoke Title"
        else:
            content = "Smoke response"
        return FakeResponse(200, {"choices": [{"message": {"content": content}}]})

    return FakeResponse(404, {})


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.db_path = os.path.join(cls.temp_dir.name, "codebuddy_test.db")
        os.environ["CODEBUDDY_DB_PATH"] = cls.db_path

        spec = importlib.util.spec_from_file_location("codebuddy_app", APP_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

        cls.requests_patch = patch.object(cls.module.requests, "post", side_effect=fake_post)
        cls.requests_patch.start()

        cls._seed_user(TEST_USERNAME, TEST_PASSWORD)

    @classmethod
    def tearDownClass(cls):
        cls.requests_patch.stop()
        cls.temp_dir.cleanup()

    @classmethod
    def _seed_user(cls, username, password):
        conn = sqlite3.connect(cls.module.DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        password_hash = cls.module.bcrypt.generate_password_hash(password).decode()
        if row:
            user_id = row["id"]
            conn.execute("UPDATE users SET password=? WHERE id=?", (password_hash, user_id))
        else:
            cursor = conn.execute(
                "INSERT INTO users(username, password) VALUES (?, ?)",
                (username, password_hash),
            )
            user_id = cursor.lastrowid
        conn.execute(
            "INSERT OR IGNORE INTO user_stats(user_id, last_active) VALUES (?, datetime('now'))",
            (user_id,),
        )
        conn.commit()
        conn.close()

    def setUp(self):
        self.client = self.module.app.test_client()

    def login(self):
        response = self.client.post(
            "/login",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            follow_redirects=False,
        )
        self.assertIn(response.status_code, (200, 302))

    def test_public_pages_and_status_routes(self):
        leaderboard = self.client.get("/leaderboard")
        self.assertEqual(leaderboard.status_code, 200)
        self.assertEqual(leaderboard.headers.get("Cache-Control"), "public, max-age=60")

        api_leaderboard = self.client.get("/api/leaderboard")
        self.assertEqual(api_leaderboard.status_code, 200)
        self.assertIn("leaderboard", api_leaderboard.get_json())

        manifest = self.client.get("/manifest.json")
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.headers.get("Cache-Control"), "public, max-age=600")

        service_worker = self.client.get("/sw.js")
        self.assertEqual(service_worker.status_code, 200)
        self.assertIn("CACHE_NAME", service_worker.get_data(as_text=True))

        features = self.client.get("/features")
        self.assertEqual(features.status_code, 302)

    def test_unauthenticated_api_routes_return_json(self):
        response = self.client.post(
            "/naming/suggest",
            json={"code": "print('hi')", "language": "python"},
        )
        self.assertEqual(response.status_code, 401)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        self.assertIn("error", payload)
        self.assertIn("log in", payload["error"].lower())

    def test_naming_suggest_falls_back_on_malformed_ai_json(self):
        self.login()

        malformed = '{"mode":"suggest","winner":"greeting_message","suggestions":[{"name":"greeting_message","score":92,"clarity":9,"convention":9,"searchability":8,"intent_match":9,"reasoning":"Uses "Hello" wording"}],"naming_principle":"Prefer descriptive names"}'

        def bad_post(url, headers=None, json=None, stream=False, timeout=None, **kwargs):
            url_text = str(url).lower()
            if "openrouter.ai" in url_text:
                return FakeResponse(200, {"choices": [{"message": {"content": malformed}}]})
            return fake_post(url, headers=headers, json=json, stream=stream, timeout=timeout, **kwargs)

        with patch.object(self.module.requests, "post", side_effect=bad_post):
            response = self.client.post(
                "/naming/suggest",
                json={
                    "code": "message = \"Hello, World!\"\nprint(message)",
                    "language": "python",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("suggestions", payload)
        self.assertGreaterEqual(len(payload["suggestions"]), 1)
        self.assertTrue(payload.get("winner"))
        self.assertTrue(payload["suggestions"][0].get("name"))
        self.assertTrue(payload["suggestions"][0].get("new_name"))
        self.assertNotIn("error", payload)

    def test_naming_suggest_falls_back_on_null_ai_content(self):
        self.login()

        def null_post(url, headers=None, json=None, stream=False, timeout=None, **kwargs):
            url_text = str(url).lower()
            if "groq.com" in url_text or "openrouter.ai" in url_text:
                return FakeResponse(200, {"choices": [{"message": {"content": None}}]})
            return fake_post(url, headers=headers, json=json, stream=stream, timeout=timeout, **kwargs)

        with patch.object(self.module.requests, "post", side_effect=null_post):
            response = self.client.post(
                "/naming/suggest",
                json={
                    "code": "message = \"Hello, World!\"\nprint(message)",
                    "language": "python",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("suggestions", payload)
        self.assertGreaterEqual(len(payload["suggestions"]), 1)
        self.assertTrue(payload.get("winner"))
        self.assertTrue(payload["suggestions"][0].get("name"))
        self.assertTrue(payload["suggestions"][0].get("new_name"))
        self.assertNotIn("error", payload)

    def test_dna_build_returns_friendly_empty_state(self):
        self.login()

        response = self.client.post("/dna/build")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNone(payload.get("profile"))
        self.assertEqual(payload.get("status"), "needs_samples")
        self.assertIn("paste some code", payload.get("message", "").lower())

    def test_authenticated_smoke_flow(self):
        self.login()

        profile = self.client.get("/profile")
        self.assertEqual(profile.status_code, 200)

        new_chat = self.client.post("/new_chat", json={"mode": "general"})
        self.assertEqual(new_chat.status_code, 200)
        chat_id = new_chat.get_json()["chat_id"]

        chat = self.client.post(
            "/chat",
            data={
                "message": "Explain a Python loop",
                "conversation_id": str(chat_id),
                "mode": "general",
                "personality": "mentor",
                "confidence": "0",
                "lang": "en-US",
            },
        )
        chat_text = chat.get_data(as_text=True)
        self.assertEqual(chat.status_code, 200)
        self.assertIn("Hello", chat_text)

        load_messages = self.client.get(f"/load_messages/{chat_id}")
        self.assertEqual(load_messages.status_code, 200)
        self.assertGreaterEqual(len(load_messages.get_json()["messages"]), 1)

        title = self.client.get(f"/get_chat_title/{chat_id}")
        self.assertEqual(title.status_code, 200)

        rename = self.client.post(
            "/rename_chat",
            json={"chat_id": chat_id, "title": "Smoke Chat"},
        )
        self.assertEqual(rename.status_code, 200)

        pin = self.client.post("/pin_chat", json={"chat_id": chat_id})
        self.assertEqual(pin.status_code, 200)
        self.assertEqual(pin.get_json()["status"], "pinned")

        share = self.client.post("/share_chat", json={"chat_id": chat_id})
        self.assertEqual(share.status_code, 200)
        share_url = share.get_json()["share_url"]
        token = share_url.rsplit("/", 1)[-1]

        public_chat = self.client.get(f"/public_chat/{token}")
        self.assertEqual(public_chat.status_code, 200)

        run_code = self.client.post(
            "/run_code",
            json={"language": "python", "code": "print('ok')"},
        )
        self.assertEqual(run_code.status_code, 200)
        self.assertIn("benchmark run ok", run_code.get_json()["output"])

        memory = self.client.get("/get_memory")
        self.assertEqual(memory.status_code, 200)

        set_memory = self.client.post(
            "/set_memory",
            json={"key": "preferred_language", "value": "python"},
        )
        self.assertEqual(set_memory.status_code, 200)

        clear_memory = self.client.post("/clear_memory")
        self.assertEqual(clear_memory.status_code, 200)

        update_profile = self.client.post(
            "/update_profile",
            json={"bio": "smoke", "avatar_color": "#00ffe0"},
        )
        self.assertEqual(update_profile.status_code, 200)

        collab = self.client.post("/collab/create", json={"chat_id": chat_id})
        self.assertEqual(collab.status_code, 200)
        room_code = collab.get_json()["room_code"]

        collab_page = self.client.get(f"/collab/{room_code}")
        self.assertEqual(collab_page.status_code, 200)

        stats = self.client.get("/get_stats")
        self.assertEqual(stats.status_code, 200)

    def test_feature_status_pages(self):
        self.login()

        routes = [
            "/learning_replay",
            "/focus_zone",
            "/karma/me",
            "/karma/leaderboard",
            "/mood/history",
            "/dna/me",
            "/prophecy/me",
            "/changelog/history",
            "/calibrate/history",
            "/error_autopsy/history",
            "/naming/history",
            "/duck/status",
            "/voice_clone/status",
            "/coqui/status",
            "/tts/diagnose",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)