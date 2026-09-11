import os

from flask import Blueprint, jsonify, send_from_directory

from .services.google_calendar import calendar_service
from .services.weather_service import weather_service
from .state import dashboard_state

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_JS_DIR = os.path.join(BASE_DIR, "static", "js")

routes_bp = Blueprint("routes", __name__)


@routes_bp.route("/")
@routes_bp.route("/dashboard")
def serve_dashboard():
    return send_from_directory(TEMPLATES_DIR, "dashboard.html")


@routes_bp.route("/steuerung")
def serve_steuerung():
    return send_from_directory(TEMPLATES_DIR, "steuerung.html")


@routes_bp.route("/support.js")
def serve_support_js():
    return send_from_directory(STATIC_JS_DIR, "support.js")


@routes_bp.route("/api/weather")
def get_weather():
    return jsonify(weather_service.get_weather())


@routes_bp.route("/api/events")
def get_events():
    events = calendar_service.get_events()
    return jsonify({"events": events, "google_connected": calendar_service.is_connected()})


@routes_bp.route("/api/tasks")
def get_tasks():
    tasks = calendar_service.get_tasks()
    return jsonify({"tasks": tasks, "google_connected": calendar_service.is_connected()})


@routes_bp.route("/api/status")
def get_status():
    return jsonify(
        {
            "status": "online",
            "state": dashboard_state,
            "google_calendar_connected": calendar_service.is_connected(),
        }
    )
