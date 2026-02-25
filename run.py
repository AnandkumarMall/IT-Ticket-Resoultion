"""
run.py
------
Starts both the FastAPI backend and the Flask frontend together.

Usage:
    python run.py
"""

import subprocess
import sys
import os
import time
import signal

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT      = os.path.dirname(os.path.abspath(__file__))
BACKEND   = os.path.join(ROOT, "backend")
FLASK_APP = os.path.join(ROOT, "flask_app")
PYTHON    = sys.executable   # same interpreter / venv that ran this script

# ── Launch processes ──────────────────────────────────────────────────────────
print("=" * 55)
print("  IT Ticket Resolution Engine — Launcher")
print("=" * 55)

# Use --reload only in development (DEV_MODE=true), never in production/cloud
dev_mode = os.environ.get("DEV_MODE", "true").lower() == "true"
uvicorn_cmd = [PYTHON, "-m", "uvicorn", "main:app", "--port", "8000"]
if dev_mode:
    uvicorn_cmd.append("--reload")

backend_proc = subprocess.Popen(uvicorn_cmd, cwd=BACKEND)
print("  ✅ FastAPI backend  →  http://127.0.0.1:8000")
print("     API Docs         →  http://127.0.0.1:8000/docs")

time.sleep(1)   # give the backend a second to bind the port

flask_env = os.environ.copy()
flask_env["WERKZEUG_RELOADER_TYPE"] = "stat"   # avoid watchdog watching Python stdlib on Windows

flask_proc = subprocess.Popen(
    [PYTHON, "app.py"],
    cwd=FLASK_APP,
    env=flask_env,
)
print("  ✅ Flask frontend   →  http://127.0.0.1:5000")
print("=" * 55)
print("  Press Ctrl+C to stop both servers.")
print("=" * 55)

# ── Wait / Cleanup ────────────────────────────────────────────────────────────
def shutdown(sig, frame):
    print("\n[Launcher] Shutting down both servers…")
    flask_proc.terminate()
    backend_proc.terminate()
    flask_proc.wait()
    backend_proc.wait()
    print("[Launcher] Done. Goodbye!")
    sys.exit(0)

signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)

# Block until either process exits
flask_proc.wait()
backend_proc.wait()
