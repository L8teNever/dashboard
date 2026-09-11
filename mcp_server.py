"""
Eigener MCP-Server des Dashboards (zweiter Port, getrennt von app.py).

Hierüber kann eine KI (z.B. ein Mail-Assistent) Termine sowie
Hausaufgaben/Todos auf dem Dashboard anlegen, bearbeiten und löschen --
z.B. um automatisch einen Termin aus einer wichtigen E-Mail zu erzeugen.
Die Daten landen in derselben SQLite-Datenbank (backend/store.py), die
app.py für /api/events und /api/tasks mitliest, und erscheinen dadurch
auf dem Dashboard.

Nicht zu verwechseln mit MCP_SERVER_URL (siehe backend/services/mcp_calendar.py):
das ist der umgekehrte Weg, bei dem DIESES Dashboard Kalenderdaten von
einem FREMDEN MCP-Server abruft. Hier dagegen ist das Dashboard selbst
der Server, mit den DASHBOARD_MCP_*-Variablen konfiguriert.

Start: python mcp_server.py  (siehe docker-compose.yml, Service "mcp-server")
"""

import logging
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

from backend import store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard_mcp")

AUTH_TOKEN = os.getenv("DASHBOARD_MCP_AUTH_TOKEN")
HOST = os.getenv("DASHBOARD_MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("DASHBOARD_MCP_PORT", "5001"))

mcp = FastMCP(
    name="MeinTag Dashboard",
    instructions=(
        "Werkzeuge, um Termine sowie Hausaufgaben/Todos auf dem MeinTag-Dashboard "
        "zu verwalten -- z.B. um automatisch einen Termin aus einer wichtigen "
        "E-Mail anzulegen. Änderungen erscheinen innerhalb weniger Minuten auf "
        "dem Dashboard (Polling-Intervall der Anzeige)."
    ),
    host=HOST,
    port=PORT,
    stateless_http=True,
)


def _hhmm_to_minutes(value: str) -> int:
    hours, minutes = value.strip().split(":")
    return int(hours) * 60 + int(minutes)


def _minutes_to_hhmm(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _event_out(event: dict) -> dict:
    return {**event, "start": _minutes_to_hhmm(event["start"]), "end": _minutes_to_hhmm(event["end"])}


@mcp.tool()
def list_events() -> list[dict]:
    """Listet alle über diesen MCP-Server angelegten Termine (nicht die aus Google Calendar / MCP_SERVER_URL)."""
    return [_event_out(e) for e in store.list_events()]


@mcp.tool()
def create_event(
    date: str,
    start_time: str,
    end_time: str,
    title: str,
    cat: str = "sonstiges",
    location: str = "",
    notes: str = "",
) -> dict:
    """
    Legt einen neuen Termin auf dem Dashboard an.

    date: Datum im Format YYYY-MM-DD
    start_time / end_time: Uhrzeit im Format HH:MM (24h)
    cat: eine von "schule", "lernen", "sport", "familie", "sonstiges"
    """
    event = store.create_event(
        date=date,
        start=_hhmm_to_minutes(start_time),
        end=_hhmm_to_minutes(end_time),
        title=title,
        cat=cat,
        location=location,
        notes=notes,
    )
    return _event_out(event)


@mcp.tool()
def update_event(
    event_id: str,
    date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    title: Optional[str] = None,
    cat: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Bearbeitet einen bestehenden, über diesen Server angelegten Termin (event_id aus list_events)."""
    event = store.update_event(
        event_id,
        date=date,
        start=_hhmm_to_minutes(start_time) if start_time else None,
        end=_hhmm_to_minutes(end_time) if end_time else None,
        title=title,
        cat=cat,
        location=location,
        notes=notes,
    )
    if event is None:
        raise ValueError(f"Termin '{event_id}' wurde nicht gefunden.")
    return _event_out(event)


@mcp.tool()
def delete_event(event_id: str) -> dict:
    """Löscht einen über diesen Server angelegten Termin (event_id aus list_events)."""
    if not store.delete_event(event_id):
        raise ValueError(f"Termin '{event_id}' wurde nicht gefunden.")
    return {"deleted": event_id}


@mcp.tool()
def list_tasks() -> list[dict]:
    """Listet alle Hausaufgaben und Todos auf dem Dashboard."""
    return store.list_tasks()


@mcp.tool()
def create_task(title: str, type: str = "todo", done: bool = False) -> dict:
    """
    Legt eine neue Hausaufgabe oder ein Todo an.

    type: "hausaufgabe" oder "todo"
    """
    return store.create_task(title=title, type=type, done=done)


@mcp.tool()
def update_task(
    task_id: str,
    title: Optional[str] = None,
    done: Optional[bool] = None,
    type: Optional[str] = None,
) -> dict:
    """Bearbeitet eine bestehende Hausaufgabe/Todo (task_id aus list_tasks), z.B. um sie abzuhaken."""
    task = store.update_task(task_id, title=title, done=done, type=type)
    if task is None:
        raise ValueError(f"Aufgabe '{task_id}' wurde nicht gefunden.")
    return task


@mcp.tool()
def delete_task(task_id: str) -> dict:
    """Löscht eine Hausaufgabe/Todo (task_id aus list_tasks)."""
    if not store.delete_task(task_id):
        raise ValueError(f"Aufgabe '{task_id}' wurde nicht gefunden.")
    return {"deleted": task_id}


class BearerAuthMiddleware:
    """Reines ASGI-Middleware (kein BaseHTTPMiddleware), damit Streamable-HTTP-Streaming unangetastet bleibt."""

    def __init__(self, app, token):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if self.token and scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {self.token}":
                response = JSONResponse({"error": "unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def main():
    import uvicorn

    if not AUTH_TOKEN:
        logger.warning("DASHBOARD_MCP_AUTH_TOKEN ist nicht gesetzt -- der MCP-Server läuft ohne Zugriffsschutz!")

    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token=AUTH_TOKEN)

    logger.info(f"Dashboard-MCP-Server läuft auf http://{HOST}:{PORT}{mcp.settings.streamable_http_path}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
