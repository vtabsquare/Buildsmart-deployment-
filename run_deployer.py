"""BuildSmart 360 - Standalone Render Deployment Application Runner."""
import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Also ensure BuildSmart_New/.venv is considered if running with system Python
VENV_PYTHON = ROOT.parent / "BuildSmart_New" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if VENV_PYTHON.is_file() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    try:
        import flask
        import requests
    except ImportError:
        import subprocess
        sys.exit(subprocess.call([str(VENV_PYTHON), str(ROOT / "run_deployer.py"), *sys.argv[1:]]))

from deployer.app import app


def open_browser_when_ready(url: str):
    from urllib.request import urlopen
    for _ in range(40):
        try:
            with urlopen(f"{url}/api/config", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.4)


def find_available_port(start_port: int = 5500) -> int:
    port = start_port
    while port < 6000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return start_port


def main():
    parser = argparse.ArgumentParser(description="BuildSmart 360 Standalone Deployment Application")
    parser.add_argument("--port", type=int, default=5500, help="Port to run the deployment application on")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    env_port = os.environ.get("PORT")
    env_host = os.environ.get("HOST")
    port = int(env_port) if env_port else find_available_port(args.port)
    host = env_host or ("0.0.0.0" if env_port else args.host)
    should_open_browser = not args.no_browser and not bool(env_port)

    url = f"http://{host}:{port}"

    print("=" * 64)
    print("  BuildSmart 360 — Standalone Render Deployment Application")
    print(f"  Access URL : {url}")
    print("=" * 64)

    if should_open_browser:
        threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    try:
        from waitress import serve
        serve(app, host=host, port=port)
    except ImportError:
        app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
