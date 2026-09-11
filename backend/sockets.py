import logging

from flask_socketio import emit

from . import socketio
from .state import dashboard_state

logger = logging.getLogger("dashboard_app")


@socketio.on("connect")
def handle_connect():
    logger.info("Client connected to Socket.IO")
    emit("state_sync", dashboard_state)


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Client disconnected from Socket.IO")


@socketio.on("control_action")
def handle_control_action(data):
    logger.info(f"Received control action: {data}")
    action = data.get("action")

    if action == "navPrev":
        step = 7 if dashboard_state["viewMode"] == "week" else 3 if dashboard_state["viewMode"] == "3day" else 1
        dashboard_state["anchorOffset"] -= step
    elif action == "navNext":
        step = 7 if dashboard_state["viewMode"] == "week" else 3 if dashboard_state["viewMode"] == "3day" else 1
        dashboard_state["anchorOffset"] += step
    elif action == "setMode":
        dashboard_state["viewMode"] = data.get("viewMode", "day")
    elif action == "toggleWeather":
        target = data.get("weatherOpen", not dashboard_state["weatherOpen"])
        dashboard_state["weatherOpen"] = target
        if target:
            dashboard_state["mailOpen"] = False
            dashboard_state["hwOpen"] = False
            dashboard_state["todoOpen"] = False
    elif action == "toggleMail":
        target = data.get("mailOpen", not dashboard_state["mailOpen"])
        dashboard_state["mailOpen"] = target
        if target:
            dashboard_state["weatherOpen"] = False
            dashboard_state["hwOpen"] = False
            dashboard_state["todoOpen"] = False
    elif action == "toggleHw":
        target = data.get("hwOpen", not dashboard_state["hwOpen"])
        dashboard_state["hwOpen"] = target
        if target:
            dashboard_state["weatherOpen"] = False
            dashboard_state["mailOpen"] = False
            dashboard_state["todoOpen"] = False
    elif action == "toggleTodo":
        target = data.get("todoOpen", not dashboard_state["todoOpen"])
        dashboard_state["todoOpen"] = target
        if target:
            dashboard_state["weatherOpen"] = False
            dashboard_state["mailOpen"] = False
            dashboard_state["hwOpen"] = False
    elif action == "closeAllModals":
        dashboard_state["weatherOpen"] = False
        dashboard_state["mailOpen"] = False
        dashboard_state["hwOpen"] = False
        dashboard_state["todoOpen"] = False
    elif action == "toggleDarkMode":
        dashboard_state["darkMode"] = data.get("darkMode", not dashboard_state["darkMode"])
    elif action == "setOffset":
        dashboard_state["anchorOffset"] = data.get("anchorOffset", 0)
    elif action == "setDashboardRotation":
        dashboard_state["dashboardRotation"] = data.get("rotation", 0) if data.get("rotation") in (0, 90, 180, 270) else 0
    elif action == "setSteuerungRotation":
        dashboard_state["steuerungRotation"] = data.get("rotation", 0) if data.get("rotation") in (0, 90, 180, 270) else 0

    # Broadcast updated action & state to all connected clients (Dashboard + Fernbedienung)
    emit("control_action", data, broadcast=True)
    emit("state_sync", dashboard_state, broadcast=True)
