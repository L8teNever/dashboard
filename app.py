import os

if os.environ.get("USE_GEVENT"):
    # Must run before any other import: patches the stdlib (socket, ssl,
    # threading, ...) so blocking calls elsewhere (e.g. the MCP calendar
    # fetch, which can take up to MCP_TOOL_TIMEOUT seconds) cooperate with
    # gevent's event loop instead of freezing the whole server -- without
    # this, one slow request blocks every other connected client (dashboard
    # AND Fernbedienung), which is exactly the "two remote controls break
    # it" symptom this fixes.
    from gevent import monkey

    monkey.patch_all()

import logging
import socket

from backend import create_app, socketio

logger = logging.getLogger("dashboard_app")

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    logger.info(f"Starting Dashboard & Steuerung Server on port {port}...")
    logger.info(f"Lokaler Zugriff: http://localhost:{port}")
    logger.info(f"Netzwerk Zugriff: http://{local_ip}:{port}")
    logger.info(f"Fernbedienung im Netzwerk: http://{local_ip}:{port}/steuerung")
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
