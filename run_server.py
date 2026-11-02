"""
EpiSense Backend Server Runner.
Adds src/ to sys.path and starts Uvicorn.
"""

from pathlib import Path
import sys
import uvicorn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent / "src"))

import os

if __name__ == "__main__":
    from episense.api.server import app
    port = int(os.environ.get("PORT", 8008))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, log_level="info")
