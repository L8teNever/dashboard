import os
import datetime
import json
import logging

logger = logging.getLogger(__name__)

# Optional Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks.readonly'
]

class GoogleCalendarService:
    """
    Google Calendar & Tasks Integration Service.
    
    Provides calendar events and tasks to the Dashboard.
    If Google credentials are present, fetches live data from Google Calendar API.
    Otherwise, returns fallback data and offers an easy integration path.
    """
    def __init__(self):
        self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self.service = None
        self.tasks_service = None
        self._init_google_api()

    def _init_google_api(self):
        if not GOOGLE_API_AVAILABLE:
            logger.info("Google API libraries not installed. Operating in fallback mode.")
            return

        creds = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.error(f"Error loading token.json: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing Google OAuth token: {e}")
                    creds = None
            if not creds and os.path.exists(self.creds_path):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.error(f"Error authenticating Google API flow: {e}")

        if creds and creds.valid:
            try:
                self.service = build('calendar', 'v3', credentials=creds)
                self.tasks_service = build('tasks', 'v1', credentials=creds)
                logger.info("Successfully connected to Google Calendar API!")
            except Exception as e:
                logger.error(f"Failed to build Google API client: {e}")

    def is_connected(self):
        return self.service is not None

    def get_events(self):
        """
        Fetch calendar events. Returns a list of dicts in the dashboard format.
        """
        if self.service:
            try:
                now = datetime.datetime.utcnow().isoformat() + 'Z'
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=now,
                    maxResults=25,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                items = events_result.get('items', [])
                
                parsed_events = []
                for idx, item in enumerate(items):
                    start_raw = item['start'].get('dateTime', item['start'].get('date'))
                    end_raw = item['end'].get('dateTime', item['end'].get('date'))
                    
                    if 'T' in start_raw:
                        dt_start = datetime.datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
                        dt_end = datetime.datetime.fromisoformat(end_raw.replace('Z', '+00:00'))
                        date_iso = dt_start.strftime('%Y-%m-%d')
                        start_min = dt_start.hour * 60 + dt_start.minute
                        end_min = dt_end.hour * 60 + dt_end.minute
                    else:
                        date_iso = start_raw
                        start_min = 480  # Default 08:00 for all-day events
                        end_min = 1020   # Default 17:00

                    parsed_events.append({
                        "id": item.get('id', idx + 100),
                        "date": date_iso,
                        "start": start_min,
                        "end": max(end_min, start_min + 30),
                        "title": item.get('summary', 'Termin'),
                        "cat": self._guess_category(item.get('summary', '')),
                        "location": item.get('location', ''),
                        "notes": item.get('description', '')
                    })
                return parsed_events
            except Exception as e:
                logger.error(f"Error fetching live Google Calendar events: {e}")

        # Fallback / Initial default events relative to today
        today = datetime.date.today()
        def iso(offset):
            return (today + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')

        return [
            { "id": 1, "date": iso(0), "start": 480, "end": 795, "title": "Schule", "cat": "schule", "location": "Schule, Raum 12", "notes": "" },
            { "id": 2, "date": iso(0), "start": 840, "end": 885, "title": "Hausaufgaben: Mathe", "cat": "lernen", "location": "", "notes": "Seite 42, Aufgabe 3-6" },
            { "id": 3, "date": iso(0), "start": 960, "end": 1050, "title": "Fußballtraining", "cat": "sport", "location": "Sportplatz Nord", "notes": "Trikot nicht vergessen" },
            { "id": 4, "date": iso(0), "start": 1110, "end": 1155, "title": "Abendessen mit Familie", "cat": "familie", "location": "", "notes": "" },
            { "id": 5, "date": iso(0), "start": 1170, "end": 1200, "title": "Klavier üben", "cat": "lernen", "location": "", "notes": "" },
            { "id": 6, "date": iso(1), "start": 480, "end": 795, "title": "Schule", "cat": "schule", "location": "Schule, Raum 12", "notes": "" },
            { "id": 7, "date": iso(1), "start": 900, "end": 960, "title": "Zahnarzttermin", "cat": "sonstiges", "location": "Zahnarztpraxis Dr. Huber", "notes": "Bitte 10 Min. früher da sein" },
            { "id": 8, "date": iso(1), "start": 990, "end": 1050, "title": "Hausaufgaben: Englisch", "cat": "lernen", "location": "", "notes": "" },
            { "id": 9, "date": iso(2), "start": 480, "end": 750, "title": "Schule", "cat": "schule", "location": "Schule, Raum 12", "notes": "" },
            { "id": 10, "date": iso(2), "start": 810, "end": 900, "title": "Schwimmtraining", "cat": "sport", "location": "Hallenbad Mitte", "notes": "Schwimmbrille einpacken" },
            { "id": 11, "date": iso(3), "start": 480, "end": 795, "title": "Schule", "cat": "schule", "location": "Schule, Raum 12", "notes": "" },
            { "id": 12, "date": iso(3), "start": 1020, "end": 1080, "title": "Omas Geburtstag vorbereiten", "cat": "familie", "location": "", "notes": "Karte + Geschenk besorgen" },
            { "id": 13, "date": iso(4), "start": 480, "end": 795, "title": "Schule", "cat": "schule", "location": "Schule, Raum 12", "notes": "" },
            { "id": 14, "date": iso(4), "start": 930, "end": 990, "title": "Musikunterricht", "cat": "lernen", "location": "Musikschule, Raum 3", "notes": "" },
            { "id": 15, "date": iso(5), "start": 600, "end": 690, "title": "Fußballspiel", "cat": "sport", "location": "Sportplatz Nord", "notes": "" },
            { "id": 16, "date": iso(5), "start": 840, "end": 960, "title": "Familienausflug", "cat": "familie", "location": "", "notes": "" },
            { "id": 17, "date": iso(6), "start": 660, "end": 750, "title": "Familienessen", "cat": "familie", "location": "", "notes": "" }
        ]

    def get_tasks(self):
        """
        Fetch tasks. Returns a list of dicts for the dashboard tasks list.
        """
        if self.tasks_service:
            try:
                results = self.tasks_service.tasks().list(tasklist='@default').execute()
                items = results.get('items', [])
                parsed_tasks = []
                for idx, t in enumerate(items):
                    parsed_tasks.append({
                        "id": t.get('id', idx + 1),
                        "title": t.get('title', 'Aufgabe'),
                        "done": t.get('status') == 'completed',
                        "type": "todo"
                    })
                return parsed_tasks
            except Exception as e:
                logger.error(f"Error fetching Google Tasks: {e}")

        return [
            { "id": 1, "title": "Matheaufgaben S. 42 fertig machen", "done": False, "type": "hausaufgabe" },
            { "id": 2, "title": "Englisch Vokabeln lernen", "done": False, "type": "hausaufgabe" },
            { "id": 3, "title": "Buch für Deutsch mitbringen", "done": False, "type": "hausaufgabe" },
            { "id": 4, "title": "Sporttasche packen", "done": True, "type": "todo" },
            { "id": 5, "title": "Zimmer aufräumen", "done": False, "type": "todo" }
        ]

    def _guess_category(self, summary):
        summary_lower = summary.lower()
        if any(w in summary_lower for w in ['schule', 'unterricht', 'vorlesung', 'klausur']):
            return 'schule'
        if any(w in summary_lower for w in ['lernen', 'üben', 'hausaufgabe', 'referat']):
            return 'lernen'
        if any(w in summary_lower for w in ['sport', 'training', 'fußball', 'schwimmen', 'fitness']):
            return 'sport'
        if any(w in summary_lower for w in ['familie', 'geburtstag', 'oma', 'opa', 'eltern', 'essen']):
            return 'familie'
        return 'sonstiges'
