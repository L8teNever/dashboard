import os
import logging

from flask import Flask
from flask_socketio import SocketIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard_app")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dashboard_secret_key_12345")
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    from .routes import routes_bp
    app.register_blueprint(routes_bp)

    socketio.init_app(app, async_mode="gevent" if os.environ.get("USE_GEVENT") else "threading")

    from . import sockets  # noqa: F401  (registers SocketIO event handlers)

    return app
