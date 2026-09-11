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
- **Eigener MCP-Server** (`mcp_server.py`, zweiter Port): Eine KI kann darüber Termine/Hausaufgaben/Todos anlegen, bearbeiten und löschen — z.B. automatisch aus wichtigen E-Mails. Siehe [MCP-Server des Dashboards](#-mcp-server-des-dashboards-für-eine-ki).
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

> Der Service `mcp-server` startet nur, wenn `DASHBOARD_MCP_AUTH_TOKEN` in der `.env` gesetzt ist (siehe [MCP-Server des Dashboards](#-mcp-server-des-dashboards-für-eine-ki)) — ohne Token bricht `docker compose up` für diesen einen Service kontrolliert ab, `dashboard` läuft trotzdem normal weiter.

### URLs nach dem Start:
- **Dashboard**: [http://localhost:5000/](http://localhost:5000/) (oder [http://localhost:5000/dashboard](http://localhost:5000/dashboard))
- **Fernbedienung / Steuerung**: [http://localhost:5000/steuerung](http://localhost:5000/steuerung)
- **MCP-Server (für eine KI, nicht für den Browser)**: `http://localhost:5001/mcp`

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
3. Optional: den MCP-Server separat starten (siehe [MCP-Server des Dashboards](#-mcp-server-des-dashboards-für-eine-ki)):
   ```bash
   DASHBOARD_MCP_AUTH_TOKEN=dein-token python mcp_server.py
   ```

---

## 📁 Projektstruktur

```
Dashboard/
├── app.py                          # Dashboard-Einstiegspunkt (Port 5000, erstellt App, startet SocketIO-Server)
├── mcp_server.py                   # Eigener MCP-Server des Dashboards (Port 5001, für eine KI)
├── backend/
│   ├── __init__.py                 # App-Factory (create_app), Flask- & SocketIO-Setup
│   ├── routes.py                   # HTTP-Routen (/, /steuerung, /api/*)
│   ├── sockets.py                  # SocketIO-Event-Handler (Echtzeit-Sync)
│   ├── state.py                    # Gemeinsamer Dashboard-Zustand
│   ├── store.py                    # SQLite-Ablage für per MCP angelegte Termine/Tasks/Mails
│   └── services/
│       ├── calendar_provider.py    # Wählt MCP- oder Google-OAuth-Kalenderquelle
│       ├── mcp_calendar.py         # Kalenderdaten via fremden MCP-Server (Server-Deployment)
│       ├── google_calendar.py      # Kalenderdaten via Google OAuth (lokale Nutzung)
│       └── weather_service.py      # Open-Meteo Wetter-Anbindung
├── templates/
│   ├── dashboard.html              # Dashboard-Seite
│   └── steuerung.html              # Fernbedienung-Seite
├── static/
│   └── js/
│       └── support.js              # Gemeinsames Frontend-JS
├── data/                           # SQLite-Datenbank (Volume, nicht im Image/Git)
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

---

## 🤖 MCP-Server des Dashboards (für eine KI)

`mcp_server.py` ist ein **eigener MCP-Server**, getrennt vom Dashboard selbst, auf einem zweiten Port. Er ist die Umkehrung von `MCP_SERVER_URL` oben: dort holt sich *dieses* Dashboard Daten von einem fremden Server, hier ist *dieses* Dashboard selbst der Server, mit dem sich eine KI (z.B. ein Mail-Assistent mit Gmail-Zugriff) verbindet, um Termine, Hausaufgaben/Todos sowie wichtige Mails direkt auf dem Dashboard anzulegen, zu bearbeiten und zu löschen.

**Typischer Anwendungsfall:** Eine KI mit Zugriff auf ein Postfach erkennt eine wichtige E-Mail (z.B. Einladung zum Elternabend) und ruft darauf `create_event` auf diesem MCP-Server auf. Der Termin taucht danach **sofort** auf allen offenen Dashboard-Seiten auf (Live-Update per Socket.IO, kein Warten auf das Polling-Intervall nötig — das läuft als Sicherheitsnetz alle 5 Minuten trotzdem mit, z.B. falls kurz kein Client verbunden war). Das Lesen der E-Mails übernimmt die KI selbst (z.B. über ein Gmail-MCP) — dieses Projekt stellt nur die Werkzeuge zum Schreiben auf das Dashboard bereit.

Technisch: nach jeder erfolgreichen Änderung ruft `mcp_server.py` intern `POST /internal/notify-update` auf der `dashboard`-Seite auf (per Docker-Compose-internem Hostnamen `dashboard`, siehe `DASHBOARD_INTERNAL_URL`), die App broadcastet daraufhin ein `data_changed`-Socket.IO-Event an alle verbundenen Browser. Schlägt dieser interne Aufruf mal fehl (z.B. Dashboard startet gerade neu), ist das egal — die Änderung ist trotzdem gespeichert, sie erscheint dann beim nächsten Poll.

### Angebotene Tools

| Tool | Zweck |
|---|---|
| `list_events` / `create_event` / `update_event` / `delete_event` | Termine verwalten. `date` = `YYYY-MM-DD`, `start_time`/`end_time` = `HH:MM`, `cat` ∈ `schule, lernen, sport, familie, sonstiges` |
| `list_tasks` / `create_task` / `update_task` / `delete_task` | Hausaufgaben/Todos verwalten. `type` ∈ `hausaufgabe, todo` |
| `list_mails` / `create_mail` / `update_mail` / `delete_mail` | "Wichtige Mails"-Bereich verwalten. `sender`, `subject`, optional `body` |

Die Daten liegen in einer eigenen SQLite-Datenbank (`backend/store.py`, Volume `dashboard-data`). Termine/Tasks werden in `/api/events` bzw. `/api/tasks` mit den Kalender-Terminen (Option A/B oben) zusammengeführt — beide Quellen laufen parallel, unabhängig voneinander. Mails kommen ausschließlich aus dieser lokalen Ablage (`/api/mails`), es gibt keine externe Mail-Quelle in diesem Projekt.

### Einrichten

1. Token erzeugen und in der `.env` eintragen:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   ```bash
   # .env
   DASHBOARD_MCP_AUTH_TOKEN=<erzeugtes Token>
   ```
2. `docker compose up -d` — der Service `mcp-server` startet zusätzlich zu `dashboard` und ist unter Port `5001` erreichbar (Streamable-HTTP-Endpunkt: `http://<server>:5001/mcp`).
3. Die KI/den Client verbinden — das Token kann wahlweise als URL-Parameter oder als Header mitgegeben werden (praktisch, wenn der Client wie bei "Ida - Google" nur eine einzelne URL akzeptiert):
   ```
   http://<server>:5001/mcp?token=<Token>
   ```
   oder gleichwertig `http://<server>:5001/mcp` mit Header `Authorization: Bearer <Token>`.

**Sicherheit:** Ohne `DASHBOARD_MCP_AUTH_TOKEN` startet der `mcp-server`-Container gar nicht erst (siehe `docker-compose.yml`) — jede Anfrage ohne oder mit falschem Token (URL-Parameter oder Bearer-Header) bekommt `401 Unauthorized`. Den Port `5001` nur erreichbar machen, wenn die KI, die ihn nutzen soll, auch wirklich von dort zugreifen kann/soll (z.B. per Firewall/Reverse-Proxy einschränken, falls der Server öffentlich erreichbar ist).
