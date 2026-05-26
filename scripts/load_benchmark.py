#!/usr/bin/env python
"""Benchmark the chat and code-run endpoints under concurrent load.

Default mode runs in-process against the Flask app with stubbed upstream AI and
code-execution calls so the benchmark stays fast and deterministic.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import random
import sqlite3
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "app.py"
DEFAULT_USERNAME = "benchmark_user"
DEFAULT_PASSWORD = "BenchmarkPass123!"
CHAT_MESSAGE = "Explain how a for loop works in Python."


@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    elapsed_seconds: float
    body_preview: str


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


def load_app_module():
    spec = importlib.util.spec_from_file_location("codebuddy_app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ensure_seed_user(module):
    conn = sqlite3.connect(module.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id FROM users WHERE username=?", (DEFAULT_USERNAME,)).fetchone()
    if row:
        user_id = row["id"]
    else:
        password_hash = module.bcrypt.generate_password_hash(DEFAULT_PASSWORD).decode()
        cursor = conn.execute(
            "INSERT INTO users(username, password) VALUES (?, ?)",
            (DEFAULT_USERNAME, password_hash),
        )
        user_id = cursor.lastrowid
    conn.execute(
        "INSERT OR IGNORE INTO user_stats(user_id, last_active) VALUES (?, datetime('now'))",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return user_id


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
            lines = [
                'data: {"choices":[{"delta":{"content":"Benchmark response."}}]}',
                'data: {"choices":[{"delta":{"content":" Another chunk."}}]}',
                "data: [DONE]",
            ]
            return FakeResponse(200, lines=lines)

        if "reply only: yes or no" in prompt_text or payload.get("max_tokens", 0) <= 5:
            content = "YES"
        elif "concise 3-5 word title" in prompt_text or "title" in prompt_text:
            content = "Benchmark Title"
        else:
            content = "Benchmark response"
        return FakeResponse(200, {"choices": [{"message": {"content": content}}]})

    return FakeResponse(404, {})


@contextlib.contextmanager
def stub_upstream_requests(module):
    original_post = module.requests.post
    module.requests.post = fake_post
    try:
        yield
    finally:
        module.requests.post = original_post


_thread_state = threading.local()


def build_worker(module, mode, base_url):
    if mode == "local":
        client = module.app.test_client()
        login_response = client.post(
            "/login",
            data={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
            follow_redirects=False,
        )
        if login_response.status_code not in (200, 302):
            raise RuntimeError(f"Login failed in local mode: {login_response.status_code}")
        chat_response = client.post("/new_chat", json={"mode": "general"})
        chat_id = chat_response.get_json()["chat_id"]
        return {"client": client, "chat_id": chat_id}

    import requests

    session = requests.Session()
    login_response = session.post(
        f"{base_url}/login",
        data={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        timeout=15,
    )
    if login_response.status_code not in (200, 302):
        raise RuntimeError(f"Login failed in live mode: {login_response.status_code}")
    chat_response = session.post(f"{base_url}/new_chat", json={"mode": "general"}, timeout=15)
    chat_id = chat_response.json()["chat_id"]
    return {"session": session, "chat_id": chat_id}


def get_worker(module, mode, base_url):
    worker = getattr(_thread_state, "worker", None)
    if worker is None:
        worker = build_worker(module, mode, base_url)
        _thread_state.worker = worker
    return worker


def percentile(values, target):
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * target))
    index = max(0, min(index, len(sorted_values) - 1))
    return sorted_values[index]


def execute_request(module, mode, base_url, endpoint):
    worker = get_worker(module, mode, base_url)
    start = time.perf_counter()

    if mode == "local":
        client = worker["client"]
        chat_id = worker["chat_id"]
        if endpoint == "chat":
            response = client.post(
                "/chat",
                data={
                    "message": CHAT_MESSAGE,
                    "conversation_id": str(chat_id),
                    "mode": "general",
                    "personality": "mentor",
                    "confidence": "0",
                    "lang": "en-US",
                },
            )
            body = response.get_data(as_text=True)
            status_code = response.status_code
        else:
            response = client.post(
                "/run_code",
                json={"language": "python", "code": "print('benchmark')"},
            )
            body = response.get_data(as_text=True)
            status_code = response.status_code
    else:
        session = worker["session"]
        chat_id = worker["chat_id"]
        if endpoint == "chat":
            response = session.post(
                f"{base_url}/chat",
                data={
                    "message": CHAT_MESSAGE,
                    "conversation_id": str(chat_id),
                    "mode": "general",
                    "personality": "mentor",
                    "confidence": "0",
                    "lang": "en-US",
                },
                timeout=120,
            )
            body = response.text
            status_code = response.status_code
        else:
            response = session.post(
                f"{base_url}/run_code",
                json={"language": "python", "code": "print('benchmark')"},
                timeout=120,
            )
            body = response.text
            status_code = response.status_code

    elapsed_seconds = time.perf_counter() - start
    return RequestResult(endpoint, status_code, elapsed_seconds, body[:120].replace("\n", " "))


def summarize(results, total_elapsed):
    print(f"Completed {len(results)} requests in {total_elapsed:.2f}s")
    print(f"Overall throughput: {len(results) / total_elapsed:.2f} req/s")
    print()

    by_endpoint = {}
    for result in results:
        by_endpoint.setdefault(result.endpoint, []).append(result)

    for endpoint, items in by_endpoint.items():
        durations = [item.elapsed_seconds for item in items]
        status_counts = {}
        for item in items:
            status_counts[item.status_code] = status_counts.get(item.status_code, 0) + 1
        ok_count = sum(1 for item in items if 200 <= item.status_code < 300)
        print(f"{endpoint}:")
        print(f"  requests: {len(items)}")
        print(f"  success: {ok_count}/{len(items)}")
        print(f"  p50: {statistics.median(durations):.3f}s")
        print(f"  p95: {percentile(durations, 0.95):.3f}s")
        print(f"  max: {max(durations):.3f}s")
        print(f"  statuses: {status_counts}")
        failures = [item for item in items if item.status_code >= 400]
        if failures:
            print(f"  sample failure: {failures[0].status_code} {failures[0].body_preview}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Benchmark CodeBuddy chat and code-run endpoints.")
    parser.add_argument("--mode", choices=("local", "live"), default="local")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--chat-requests", type=int, default=12)
    parser.add_argument("--code-requests", type=int, default=12)
    parser.add_argument(
        "--stub-upstreams",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Replace outbound AI/code-execution calls with deterministic local fakes.",
    )
    args = parser.parse_args()

    module = load_app_module()
    ensure_seed_user(module)

    if args.mode == "live":
        args.stub_upstreams = False

    tasks = ["chat"] * args.chat_requests + ["run_code"] * args.code_requests
    random.shuffle(tasks)

    start = time.perf_counter()
    results = []
    benchmark_context = stub_upstream_requests(module) if args.stub_upstreams else contextlib.nullcontext()
    with benchmark_context:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [executor.submit(execute_request, module, args.mode, args.base_url, endpoint) for endpoint in tasks]
            for future in as_completed(futures):
                results.append(future.result())
    total_elapsed = time.perf_counter() - start

    summarize(results, total_elapsed)


if __name__ == "__main__":
    main()