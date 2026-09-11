# MeinTag Dashboard & Remote Steuerung (Docker + Python + WebSockets)

Ein interaktives, modernes Dashboard mit Echtzeit-Fernbedienung (Steuerung) und vorbereiteter Google-Kalender-Integration, bereitgestellt als Docker-Container.

## 🚀 Funktionen

- **Echtzeit-Synchronisierung**: Aktionen auf der Fernbedienung (`/steuerung`) steuern sofort das echte Dashboard (`/`).
  - **Tab / Ansicht wechseln**: *Tag*, *3 Tage*, *Woche* umschalten.
  - **Datum navigieren**: *Zurück* / *Weiter* Tasten verschieben die angezeigte Zeitspanne live auf dem Dashboard.
  - **Wetter Pop-Up**: Klick auf "Wetter" öffnet/schließt das detaillierte Wetter-Popup-Modal direkt auf der Dashboard-Seite.
- **Kalender & Tasks Integration** (`backend/services/`):
  - Funktioniert out-of-the-box mit Beispieldaten.
  - Termine/Aufgaben wahlweise über einen **MCP-Server** (`MCP_SERVER_URL` in `.env`, empfohlen für Server-Deployment) oder klassisch per **Google OAuth** (`credentials.json`, nur lokal) einbinden.
- **Docker Ready**: Vollständig vorkonfiguriert mit `Dockerfile` und `docker-compose.yml`.

---

## 🛠️ Schnellstart mit Docker

Das Image wird automatisch per GitHub Actions gebaut und nach [ghcr.io/l8tenever/dashboard](https://github.com/L8teNever/dashboard/pkgs/container/dashboard) veröffentlicht, sobald etwas auf `main` gepusht wird. `docker-compose.yml` zieht dieses Image direkt — kein lokaler Build nötig.

### Starten per Docker Compose:
```bash
docker compose pull
docker compose up -d
```

> Hinweis: Beim allerersten Push muss das Package in den GitHub-Paket-Einstellungen einmalig auf "Public" gestellt werden, sonst ist `docker compose pull` ohne Login nicht möglich.

### URLs nach dem Start:
- **Dashboard**: [http://localhost:5000/](http://localhost:5000/) (oder [http://localhost:5000/dashboard](http://localhost:5000/dashboard))
- **Fernbedienung / Steuerung**: [http://localhost:5000/steuerung](http://localhost:5000/steuerung)

---

## 🐍 Lokal ohne Docker ausführen

1. Python-Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
2. Python Server starten:
   ```bash
   python app.py
   ```

---

## 📁 Projektstruktur

```
Dashboard/
├── app.py                          # Einstiegspunkt (erstellt App, startet SocketIO-Server)
├── backend/
│   ├── __init__.py                 # App-Factory (create_app), Flask- & SocketIO-Setup
│   ├── routes.py                   # HTTP-Routen (/, /steuerung, /api/*)
│   ├── sockets.py                  # SocketIO-Event-Handler (Echtzeit-Sync)
│   ├── state.py                    # Gemeinsamer Dashboard-Zustand
│   └── services/
│       ├── calendar_provider.py    # Wählt MCP- oder Google-OAuth-Kalenderquelle
│       ├── mcp_calendar.py         # Kalenderdaten via MCP-Server (Server-Deployment)
│       ├── google_calendar.py      # Kalenderdaten via Google OAuth (lokale Nutzung)
│       └── weather_service.py      # Open-Meteo Wetter-Anbindung
├── templates/
│   ├── dashboard.html              # Dashboard-Seite
│   └── steuerung.html              # Fernbedienung-Seite
├── static/
│   └── js/
│       └── support.js              # Gemeinsames Frontend-JS
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/docker-publish.yml
```

---

## 📅 Kalenderdaten einrichten

Es gibt zwei Wege, echte Termine/Aufgaben statt der Beispieldaten anzuzeigen. `backend/services/calendar_provider.py` wählt automatisch: Ist `MCP_SERVER_URL` gesetzt, wird **immer** MCP verwendet; sonst fällt die App auf Google OAuth zurück (und ohne beides auf die eingebauten Beispieldaten).

### Option A: MCP-Server (empfohlen für Docker / Server-Deployment)

Kein Browser-Login nötig, funktioniert headless. In der `.env`:

```bash
MCP_SERVER_URL=https://dein-mcp-server.example.com/mcp
MCP_SERVER_TOKEN=          # optional, falls der Server Auth verlangt
MCP_EVENTS_TOOL=list-events
MCP_TASKS_TOOL=            # optional, leer lassen wenn der Server keine Tasks anbietet
MCP_TOOL_ARGS={}           # optionale JSON-Argumente für jeden Tool-Aufruf
```

Danach `docker compose up -d` (oder `docker compose restart`, falls der Container schon läuft) — `docker-compose.yml` reicht die Variablen automatisch aus der `.env` durch.

**Wichtig:** Das aufgerufene Tool muss strukturierte Daten liefern — entweder als MCP `structuredContent` oder als JSON-String im ersten Text-Block der Antwort. Reiner Freitext (viele MCP-Server formulieren Antworten für ein LLM, nicht als API) kann nicht automatisch geparst werden; in dem Fall bleiben Events/Tasks leer und es wird eine Warnung geloggt (`docker compose logs -f dashboard`). Events werden im Google-Calendar-API-Format erwartet (`summary`/`title`, `start`/`end` als `{"dateTime"|"date": ...}` oder ISO-String, `location`, `description`/`notes`).

### Option B: Google OAuth (nur lokal, ohne MCP_SERVER_URL)

1. In der Google Cloud Console ein Projekt erstellen und die **Google Calendar API** sowie **Google Tasks API** aktivieren.
2. Einen **OAuth 2.0 Client-ID** für Desktop-Anwendungen erstellen.
3. Die heruntergeladene JSON-Datei als `credentials.json` in diesem Ordner speichern (oder den Pfad in der `.env` Datei anpassen).
4. Nach dem Neustart des Servers wird beim ersten Aufruf der OAuth-Flow gestartet und ein `token.json` generiert. Ab dann werden Ihre Google-Termine automatisch im Dashboard angezeigt!

> Der OAuth-Flow öffnet einen Browser (`run_local_server`) — das funktioniert nur bei lokaler Ausführung, nicht headless in einem Docker-Container auf einem Server. Für Server-Deployment daher Option A verwenden.
