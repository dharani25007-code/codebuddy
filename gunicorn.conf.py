"""Gunicorn defaults for CodeBuddy production deployments."""

import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
workers = int(os.getenv("WEB_CONCURRENCY", "4"))
threads = int(os.getenv("GUNICORN_THREADS", "8"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
capture_output = True