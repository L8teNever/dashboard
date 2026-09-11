import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DASHBOARD_DB_PATH", os.path.join(BASE_DIR, "data", "dashboard.db"))

VALID_EVENT_CATEGORIES = {"schule", "lernen", "sport", "familie", "sonstiges"}
VALID_TASK_TYPES = {"hausaufgabe", "todo"}


def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                start INTEGER NOT NULL,
                end INTEGER NOT NULL,
                title TEXT NOT NULL,
                cat TEXT NOT NULL DEFAULT 'sonstiges',
                location TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                type TEXT NOT NULL DEFAULT 'todo',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                received_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _local_id(row_id):
    return f"local-{row_id}"


def _row_id(local_id):
    """Accepts either the raw int PK or the 'local-<id>' public id."""
    if isinstance(local_id, str) and local_id.startswith("local-"):
        local_id = local_id[len("local-"):]
    return int(local_id)


# --- Events ---------------------------------------------------------------

def list_events():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY date, start").fetchall()
    return [_event_dict(r) for r in rows]


def create_event(date, start, end, title, cat="sonstiges", location="", notes=""):
    cat = cat if cat in VALID_EVENT_CATEGORIES else "sonstiges"
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO events (date, start, end, title, cat, location, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, int(start), int(end), title, cat, location, notes),
        )
        row = conn.execute("SELECT * FROM events WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _event_dict(row)


def update_event(event_id, **fields):
    row_id = _row_id(event_id)
    allowed = {"date", "start", "end", "title", "cat", "location", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if "cat" in updates and updates["cat"] not in VALID_EVENT_CATEGORIES:
        updates["cat"] = "sonstiges"
    if not updates:
        return get_event(event_id)
    with _connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE events SET {set_clause} WHERE id = ?", (*updates.values(), row_id))
        row = conn.execute("SELECT * FROM events WHERE id = ?", (row_id,)).fetchone()
    return _event_dict(row) if row else None


def get_event(event_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (_row_id(event_id),)).fetchone()
    return _event_dict(row) if row else None


def delete_event(event_id):
    row_id = _row_id(event_id)
    with _connect() as conn:
        cur = conn.execute("DELETE FROM events WHERE id = ?", (row_id,))
    return cur.rowcount > 0


def _event_dict(row):
    return {
        "id": _local_id(row["id"]),
        "date": row["date"],
        "start": row["start"],
        "end": row["end"],
        "title": row["title"],
        "cat": row["cat"],
        "location": row["location"],
        "notes": row["notes"],
    }


# --- Tasks ------------------------------------------------------------

def list_tasks():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [_task_dict(r) for r in rows]


def create_task(title, type="todo", done=False):
    type = type if type in VALID_TASK_TYPES else "todo"
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, done, type) VALUES (?, ?, ?)",
            (title, int(bool(done)), type),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _task_dict(row)


def update_task(task_id, **fields):
    row_id = _row_id(task_id)
    allowed = {"title", "done", "type"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if "type" in updates and updates["type"] not in VALID_TASK_TYPES:
        updates["type"] = "todo"
    if "done" in updates:
        updates["done"] = int(bool(updates["done"]))
    if not updates:
        return get_task(task_id)
    with _connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", (*updates.values(), row_id))
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (row_id,)).fetchone()
    return _task_dict(row) if row else None


def get_task(task_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (_row_id(task_id),)).fetchone()
    return _task_dict(row) if row else None


def delete_task(task_id):
    row_id = _row_id(task_id)
    with _connect() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (row_id,))
    return cur.rowcount > 0


def _task_dict(row):
    return {
        "id": _local_id(row["id"]),
        "title": row["title"],
        "done": bool(row["done"]),
        "type": row["type"],
    }


# --- Mails ------------------------------------------------------------

def list_mails():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM mails ORDER BY received_at DESC, id DESC").fetchall()
    return [_mail_dict(r) for r in rows]


def create_mail(sender, subject, body=""):
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO mails (sender, subject, body) VALUES (?, ?, ?)",
            (sender, subject, body),
        )
        row = conn.execute("SELECT * FROM mails WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _mail_dict(row)


def update_mail(mail_id, **fields):
    row_id = _row_id(mail_id)
    allowed = {"sender", "subject", "body"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_mail(mail_id)
    with _connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE mails SET {set_clause} WHERE id = ?", (*updates.values(), row_id))
        row = conn.execute("SELECT * FROM mails WHERE id = ?", (row_id,)).fetchone()
    return _mail_dict(row) if row else None


def get_mail(mail_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM mails WHERE id = ?", (_row_id(mail_id),)).fetchone()
    return _mail_dict(row) if row else None


def delete_mail(mail_id):
    row_id = _row_id(mail_id)
    with _connect() as conn:
        cur = conn.execute("DELETE FROM mails WHERE id = ?", (row_id,))
    return cur.rowcount > 0


def _mail_dict(row):
    return {
        "id": _local_id(row["id"]),
        "sender": row["sender"],
        "subject": row["subject"],
        "body": row["body"],
        "received_at": row["received_at"],
    }


_init_db()
