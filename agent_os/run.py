"""
Dallas dev server — starts uvicorn with auto-reload.

Usage:
    python run.py              # default: port 8000
    python run.py --port 3000  # custom port
    python run.py --host 0.0.0.0 --port 8000  # expose on network (phone access)
    python run.py --no-reload  # disable auto-reload (production)
"""
import argparse
import uvicorn

parser = argparse.ArgumentParser(description="Run the Dallas web server")
parser.add_argument("--host",     default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
parser.add_argument("--port",     default=8000, type=int, help="Port to listen on (default: 8000)")
parser.add_argument("--no-reload", action="store_true",  help="Disable auto-reload")
args = parser.parse_args()

uvicorn.run(
    "web.app:app",
    host=args.host,
    port=args.port,
    reload=not args.no_reload,
    reload_dirs=["web", "agents", "orchestrator", "tools", "config"],
    log_level="info",
)
