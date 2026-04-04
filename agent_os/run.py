"""
Dallas dev server — starts uvicorn with auto-reload.

Usage:
    python run.py              # default: port 8080
    python run.py --port 3000  # custom port
    python run.py --host 0.0.0.0 --port 8080  # expose on network (phone access)
    python run.py --no-reload  # disable auto-reload (production)

On Railway, the PORT env var is set automatically and takes priority.
"""
import argparse
import os
import uvicorn

parser = argparse.ArgumentParser(description="Run the Dallas web server")
parser.add_argument("--host",      default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
parser.add_argument("--port",      default=8080, type=int, help="Port to listen on (default: 8080)")
parser.add_argument("--no-reload", action="store_true",   help="Disable auto-reload")
args = parser.parse_args()

# Railway (and most cloud platforms) inject PORT — always honour it
port = int(os.environ.get("PORT", args.port))
host = os.environ.get("HOST", args.host)

uvicorn.run(
    "web.app:app",
    host=host,
    port=port,
    reload=not args.no_reload,
    reload_dirs=["web", "agents", "orchestrator", "tools", "config"],
    log_level="info",
)

