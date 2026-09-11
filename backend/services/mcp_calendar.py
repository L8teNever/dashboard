import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class MCPCalendarService:
    """
    Fetches calendar events/tasks by calling tools on a remote MCP
    server, instead of talking to the Google API directly. Configured
    entirely through environment variables, so no interactive browser
    OAuth is needed on a headless server:

      MCP_SERVER_URL    Streamable-HTTP endpoint of the MCP server (required to activate)
      MCP_SERVER_TOKEN  Optional bearer token, sent as an Authorization header
      MCP_EVENTS_TOOL   Tool name to call for events (default: "list-events")
      MCP_TASKS_TOOL    Tool name to call for tasks (optional, skipped if unset)
      MCP_TOOL_ARGS     Optional JSON object merged into every tool call
      MCP_TOOL_TIMEOUT  Seconds to wait for a tool call before giving up (default: 20)

    The called tool must return either structured content (MCP's
    `structuredContent`) or a JSON string as its first text block.
    Events are expected in a Google-Calendar-API-like shape
    (summary/title, start/end as {"dateTime"|"date": ...} or a plain
    ISO string, location, description/notes) since that is what most
    Google Calendar MCP servers mirror.
    """

    def __init__(self):
        self.server_url = os.getenv("MCP_SERVER_URL")
        self.token = os.getenv("MCP_SERVER_TOKEN")
        self.events_tool = os.getenv("MCP_EVENTS_TOOL", "list-events")
        self.tasks_tool = os.getenv("MCP_TASKS_TOOL")

        try:
            self.extra_args = json.loads(os.getenv("MCP_TOOL_ARGS", "{}"))
        except json.JSONDecodeError:
            logger.error("MCP_TOOL_ARGS ist kein gültiges JSON, wird ignoriert.")
            self.extra_args = {}

        try:
            self.timeout = float(os.getenv("MCP_TOOL_TIMEOUT", "20"))
        except ValueError:
            logger.error("MCP_TOOL_TIMEOUT ist keine gültige Zahl, verwende 20s.")
            self.timeout = 20.0

        self._connected = False

        if self.server_url and not MCP_AVAILABLE:
            logger.error("MCP_SERVER_URL ist gesetzt, aber das 'mcp' Paket ist nicht installiert.")

    def is_configured(self):
        return bool(MCP_AVAILABLE and self.server_url)

    def is_connected(self):
        return self._connected

    def get_events(self):
        payload = self._call_tool(self.events_tool)
        self._connected = payload is not None
        if payload is None:
            return []
        items = payload if isinstance(payload, list) else payload.get("events") or payload.get("items") or []
        if not items:
            logger.warning(
                f"MCP-Event-Tool '{self.events_tool}' lieferte JSON, aber keine erkennbare Liste "
                f"(Schlüssel 'events'/'items' fehlen oder sind leer). Rohdaten (gekürzt): {str(payload)[:1000]}"
            )
            return []
        parsed = [e for e in (self._parse_event(idx, item) for idx, item in enumerate(items)) if e is not None]
        if not parsed:
            logger.warning(
                f"MCP-Event-Tool '{self.events_tool}' lieferte {len(items)} Einträge, aber keiner hatte ein "
                f"erkennbares Start-/Datumsfeld. Beispiel-Eintrag (gekürzt): {str(items[0])[:1000]}"
            )
        return parsed

    def get_tasks(self):
        if not self.tasks_tool:
            return []
        payload = self._call_tool(self.tasks_tool)
        if payload is None:
            return []
        items = payload if isinstance(payload, list) else payload.get("tasks") or payload.get("items") or []
        if not items:
            logger.warning(
                f"MCP-Tasks-Tool '{self.tasks_tool}' lieferte JSON, aber keine erkennbare Liste "
                f"(Schlüssel 'tasks'/'items' fehlen oder sind leer). Rohdaten (gekürzt): {str(payload)[:1000]}"
            )
            return []
        return [self._parse_task(idx, item) for idx, item in enumerate(items)]

    def _call_tool(self, tool_name):
        if not self.is_configured() or not tool_name:
            return None

        def run():
            return asyncio.run(asyncio.wait_for(self._call_tool_async(tool_name), timeout=self.timeout))

        try:
            # asyncio.run() does NOT yield to gevent's hub even after monkey-patching
            # (verified: it blocks the whole process for its full duration), which
            # would freeze every other connected client (dashboard + Fernbedienung)
            # for up to MCP_TOOL_TIMEOUT seconds on every calendar fetch. Running it
            # in gevent's real threadpool keeps the rest of the app responsive.
            if os.environ.get("USE_GEVENT"):
                import gevent

                result = gevent.get_hub().threadpool.apply(run)
            else:
                result = run()
            logger.info(f"MCP-Tool '{tool_name}' auf {self.server_url} hat innerhalb von {self.timeout}s geantwortet.")
            return self._extract_payload(result)
        except asyncio.TimeoutError:
            logger.error(
                f"MCP-Tool-Aufruf '{tool_name}' auf {self.server_url} hat nach {self.timeout}s nicht "
                "geantwortet (Timeout) -- der Server hat entweder gar nicht reagiert, oder das Tool "
                "läuft ungewöhnlich lange. MCP_TOOL_TIMEOUT in der .env erhöhen, falls das erwartet ist."
            )
            return None
        except Exception as e:
            logger.error(f"MCP-Tool-Aufruf '{tool_name}' auf {self.server_url} fehlgeschlagen: {e}")
            return None

    async def _call_tool_async(self, tool_name):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        async with streamablehttp_client(self.server_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info(f"MCP-Session bereit, rufe Tool '{tool_name}' auf (Argumente: {self.extra_args})...")
                return await session.call_tool(tool_name, self.extra_args)

    @staticmethod
    def _extract_payload(result):
        if result is None:
            return None
        structured = getattr(result, "structuredContent", None)
        if structured:
            return structured
        texts = []
        for block in getattr(result, "content", None) or []:
            text = getattr(block, "text", None)
            if text:
                texts.append(text)
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    continue
        snippet = " | ".join(t[:500] for t in texts) if texts else "(kein Text-Content vorhanden)"
        logger.warning(f"MCP-Tool-Antwort enthielt keine auswertbaren JSON-Daten (nur Freitext?). Rohtext (gekürzt): {snippet}")
        return None

    @staticmethod
    def _first(item, *keys):
        for key in keys:
            value = item.get(key)
            if value:
                return value
        return None

    @classmethod
    def _minutes_and_date(cls, raw):
        """Accepts a Google-style {"dateTime"|"date": ...} dict or a plain ISO string."""
        import datetime

        if isinstance(raw, dict):
            raw = raw.get("dateTime") or raw.get("date")
        if not raw:
            return None, None
        try:
            if "T" in raw:
                dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d"), dt.hour * 60 + dt.minute
            return raw, None
        except ValueError:
            return None, None

    def _parse_event(self, idx, item):
        if not isinstance(item, dict):
            return None
        date_start, start_min = self._minutes_and_date(self._first(item, "start", "startTime", "start_time"))
        date_end, end_min = self._minutes_and_date(self._first(item, "end", "endTime", "end_time"))
        if date_start is None:
            return None
        if start_min is None:
            start_min, end_min = 480, 1020  # ganztägig -> Default 08:00-17:00

        return {
            "id": item.get("id", idx + 1),
            "date": date_start,
            "start": start_min,
            "end": max(end_min or start_min + 30, start_min + 30),
            "title": self._first(item, "title", "summary") or "Termin",
            "cat": self._first(item, "cat", "category") or "mcp",
            "location": self._first(item, "location") or "",
            "notes": self._first(item, "notes", "description") or "",
        }

    def _parse_task(self, idx, item):
        if not isinstance(item, dict):
            item = {"title": str(item)}
        done = item.get("done")
        if done is None:
            done = item.get("completed") or item.get("status") == "completed"
        return {
            "id": item.get("id", idx + 1),
            "title": self._first(item, "title", "name") or "Aufgabe",
            "done": bool(done),
            "type": item.get("type", "todo"),
        }
