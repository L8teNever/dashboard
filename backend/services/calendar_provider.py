import logging
import os

from .google_calendar import GoogleCalendarService
from .mcp_calendar import MCPCalendarService


logger = logging.getLogger(__name__)


def _build_calendar_service():
    mcp_service = MCPCalendarService()
    if mcp_service.is_configured():
        logger.info(f"Kalenderdaten werden über den MCP-Server bezogen: {mcp_service.server_url}")
        return mcp_service

    if os.getenv("MCP_SERVER_URL"):
        logger.error("MCP_SERVER_URL ist gesetzt, aber nicht nutzbar (siehe vorherige Fehlermeldung). Falle auf Google OAuth zurück.")

    return GoogleCalendarService()


calendar_service = _build_calendar_service()
