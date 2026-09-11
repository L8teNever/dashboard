# MeinTag Dashboard & Remote Steuerung (Docker + Python + WebSockets)

Ein interaktives, modernes Dashboard mit Echtzeit-Fernbedienung (Steuerung) und vorbereiteter Google-Kalender-Integration, bereitgestellt als Docker-Container.

## 🚀 Funktionen

- **Echtzeit-Synchronisierung**: Aktionen auf der Fernbedienung (`/steuerung`) steuern sofort das echte Dashboard (`/`).
  - **Tab / Ansicht wechseln**: *Tag*, *3 Tage*, *Woche* umschalten.
  - **Datum navigieren**: *Zurück* / *Weiter* Tasten verschieben die angezeigte Zeitspanne live auf dem Dashboard.
  - **Wetter Pop-Up**: Klick auf "Wetter" öffnet/schließt das detaillierte Wetter-Popup-Modal direkt auf der Dashboard-Seite.
- **Google Calendar & Tasks Integration (`google_calendar.py`)**:
  - Modular strukturierter Service für automatischen Abruf von Google-Kalender-Terminen und Aufgaben.
  - Funktioniert out-of-the-box mit Beispieldaten; sobald `credentials.json` hinterlegt ist, holt das Backend automatisch Ihre echten Termine!
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

## 📅 Google Calendar API einrichten (später aktivieren)

Um Ihre echten Google Kalender-Termine und Aufgaben automatisch einzubinden:

1. In der Google Cloud Console ein Projekt erstellen und die **Google Calendar API** sowie **Google Tasks API** aktivieren.
2. Einen **OAuth 2.0 Client-ID** für Desktop-Anwendungen erstellen.
3. Die heruntergeladene JSON-Datei als `credentials.json` in diesem Ordner speichern (oder den Pfad in der `.env` Datei anpassen).
4. Nach dem Neustart des Servers wird beim ersten Aufruf der OAuth-Flow gestartet und ein `token.json` generiert. Ab dann werden Ihre Google-Termine automatisch im Dashboard angezeigt!
