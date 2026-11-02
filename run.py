"""Install or run the frontend-only demo. No database initialization is needed."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "start", "check"], nargs="?", default="start")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    os.chdir(ROOT)
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")
    if not PYTHON.exists():
        print("Creating .venv...", flush=True)
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    if args.action == "setup" or subprocess.run([str(PYTHON), "-c", "import django"], capture_output=True).returncode:
        subprocess.run([str(PYTHON), "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    subprocess.run([str(PYTHON), "manage.py", "check"], check=True)
    if args.action in {"setup", "check"}:
        print("Ready. Login: ntub / 12345678. Data stays in this browser.")
        return
    print(f"Open http://localhost:{args.port}/  |  ntub / 12345678", flush=True)
    print("Keep this window open. Ctrl+C stops the server.", flush=True)
    try:
        subprocess.run([str(PYTHON), "manage.py", "runserver", f"127.0.0.1:{args.port}", "--noreload"], check=True)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
