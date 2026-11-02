"""
Unified Full-Stack Launcher for EpiSense Surveillance Intelligence System.
Starts both the FastAPI backend (with pre-loaded corpus) and the Vite frontend concurrently.
"""

import os
from pathlib import Path
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = ROOT_DIR / "frontend"


def main():
    print("=" * 80)
    print("EpiSense Surveillance Intelligence System: Full-Stack Launcher")
    print("=" * 80)

    # Check python environment
    python_exe = sys.executable
    port = os.environ.get("PORT", "8008")

    # 1. Start backend server
    print(f"\n[1/2] Starting EpiSense FastAPI Backend on http://127.0.0.1:{port} ...")
    backend_proc = subprocess.Popen(
        [python_exe, "run_server.py"],
        cwd=str(ROOT_DIR),
    )

    # 2. Start frontend dev server
    print("\n[2/2] Starting EpiSense React Operations Console ...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    print("\n" + "=" * 80)
    print("Both servers started successfully!")
    print("  • Operations Console (UI): Check Vite terminal output for local port (e.g. http://localhost:5173 or 5174)")
    print(f"  • REST API Documentation:  http://127.0.0.1:{port}/docs")
    print(f"  • WebSocket Feed Endpoint: ws://127.0.0.1:{port}/api/v1/ws/surveillance")
    print("Press CTRL+C to terminate both servers.")
    print("=" * 80 + "\n")

    try:
        while True:
            time.sleep(1)
            # Check if any process terminated unexpectedly
            if backend_proc.poll() is not None:
                print("Backend server terminated unexpectedly.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend server terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping servers...")
    finally:
        print("Stopping servers...")
        for proc in [backend_proc, frontend_proc]:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                else:
                    proc.terminate()
            except Exception:
                pass
        print("EpiSense shutdown complete.")


if __name__ == "__main__":
    main()
