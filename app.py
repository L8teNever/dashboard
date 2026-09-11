import os
import logging
from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from google_calendar import calendar_service
from weather_service import weather_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard_app")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dashboard_secret_key_12345')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Enable SocketIO with CORS allowed for all origins
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent' if os.environ.get('USE_GEVENT') else 'threading')

# Shared Server State
dashboard_state = {
    "anchorOffset": 0,
    "viewMode": "day",
    "weatherOpen": False,
    "mailOpen": False,
    "hwOpen": False,
    "todoOpen": False,
    "darkMode": False
}

@app.route('/')
@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory(BASE_DIR, 'Termine Dashboard.dc.html')

@app.route('/steuerung')
def serve_steuerung():
    return send_from_directory(BASE_DIR, 'Fernbedienung.dc.html')

@app.route('/support.js')
def serve_support_js():
    return send_from_directory(BASE_DIR, 'support.js')

@app.route('/api/weather')
def get_weather():
    weather_data = weather_service.get_weather()
    return jsonify(weather_data)

@app.route('/api/events')
def get_events():
    events = calendar_service.get_events()
    return jsonify({"events": events, "google_connected": calendar_service.is_connected()})

@app.route('/api/tasks')
def get_tasks():
    tasks = calendar_service.get_tasks()
    return jsonify({"tasks": tasks, "google_connected": calendar_service.is_connected()})

@app.route('/api/status')
def get_status():
    return jsonify({
        "status": "online",
        "state": dashboard_state,
        "google_calendar_connected": calendar_service.is_connected()
    })

# SocketIO Event Handlers
@socketio.on('connect')
def handle_connect():
    logger.info("Client connected to Socket.IO")
    emit('state_sync', dashboard_state)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected from Socket.IO")

@socketio.on('control_action')
def handle_control_action(data):
    logger.info(f"Received control action: {data}")
    action = data.get('action')

    if action == 'navPrev':
        step = 7 if dashboard_state['viewMode'] == 'week' else 3 if dashboard_state['viewMode'] == '3day' else 1
        dashboard_state['anchorOffset'] -= step
    elif action == 'navNext':
        step = 7 if dashboard_state['viewMode'] == 'week' else 3 if dashboard_state['viewMode'] == '3day' else 1
        dashboard_state['anchorOffset'] += step
    elif action == 'setMode':
        dashboard_state['viewMode'] = data.get('viewMode', 'day')
    elif action == 'toggleWeather':
        target = data.get('weatherOpen', not dashboard_state['weatherOpen'])
        dashboard_state['weatherOpen'] = target
        if target:
            dashboard_state['mailOpen'] = False
            dashboard_state['hwOpen'] = False
            dashboard_state['todoOpen'] = False
    elif action == 'toggleMail':
        target = data.get('mailOpen', not dashboard_state['mailOpen'])
        dashboard_state['mailOpen'] = target
        if target:
            dashboard_state['weatherOpen'] = False
            dashboard_state['hwOpen'] = False
            dashboard_state['todoOpen'] = False
    elif action == 'toggleHw':
        target = data.get('hwOpen', not dashboard_state['hwOpen'])
        dashboard_state['hwOpen'] = target
        if target:
            dashboard_state['weatherOpen'] = False
            dashboard_state['mailOpen'] = False
            dashboard_state['todoOpen'] = False
    elif action == 'toggleTodo':
        target = data.get('todoOpen', not dashboard_state['todoOpen'])
        dashboard_state['todoOpen'] = target
        if target:
            dashboard_state['weatherOpen'] = False
            dashboard_state['mailOpen'] = False
            dashboard_state['hwOpen'] = False
    elif action == 'closeAllModals':
        dashboard_state['weatherOpen'] = False
        dashboard_state['mailOpen'] = False
        dashboard_state['hwOpen'] = False
        dashboard_state['todoOpen'] = False
    elif action == 'toggleDarkMode':
        dashboard_state['darkMode'] = data.get('darkMode', not dashboard_state['darkMode'])
    elif action == 'setOffset':
        dashboard_state['anchorOffset'] = data.get('anchorOffset', 0)

    # Broadcast updated action & state to all connected clients (Dashboard + Fernbedienung)
    emit('control_action', data, broadcast=True)
    emit('state_sync', dashboard_state, broadcast=True)

if __name__ == '__main__':
    import socket
    port = int(os.getenv('PORT', 5000))
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'

    logger.info(f"Starting Dashboard & Steuerung Server on port {port}...")
    logger.info(f"Lokaler Zugriff: http://localhost:{port}")
    logger.info(f"Netzwerk Zugriff: http://{local_ip}:{port}")
    logger.info(f"Fernbedienung im Netzwerk: http://{local_ip}:{port}/steuerung")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
