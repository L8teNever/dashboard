import logging
import os
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
