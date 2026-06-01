"""Gunicorn defaults for CodeBuddy low-cost deployments.

These defaults bias toward a single small instance so the app stays usable on
free or hobby-tier hosting. Increase the environment variables when you move to
heavier traffic.
"""

import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "180"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
capture_output = True