"""SQLite store-and-forward queue for inspection pushes. A network drop never loses a roll;
replays are safe because the ERPNext methods are idempotent per job_card."""
import json
import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_card TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at TEXT
)
"""


class Outbox:
    def __init__(self, db_path, max_attempts=5):
        self.db_path = db_path
        self.max_attempts = max_attempts
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute(_SCHEMA)

    def _conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def enqueue(self, kind, job_card, payload):
        with self._lock, self._conn() as c:
            cur = c.execute(
                "INSERT INTO outbox (job_card, kind, payload_json) VALUES (?,?,?)",
                (job_card, kind, json.dumps(payload)))
            return cur.lastrowid

    def pending(self, limit=50):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM outbox WHERE status IN ('pending','failed') "
                "ORDER BY id LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_sent(self, row_id):
        with self._lock, self._conn() as c:
            c.execute("UPDATE outbox SET status='sent', sent_at=datetime('now') WHERE id=?",
                      (row_id,))

    def mark_failed(self, row_id, error):
        with self._lock, self._conn() as c:
            row = c.execute("SELECT attempts FROM outbox WHERE id=?", (row_id,)).fetchone()
            attempts = (row["attempts"] if row else 0) + 1
            status = "deadletter" if attempts >= self.max_attempts else "failed"
            c.execute("UPDATE outbox SET attempts=?, status=?, last_error=? WHERE id=?",
                      (attempts, status, str(error)[:500], row_id))

    def counts(self):
        with self._conn() as c:
            rows = c.execute("SELECT status, COUNT(*) n FROM outbox GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}


def drain(outbox, sender, limit=50):
    """sender(kind, job_card, payload_dict); raises on failure. Returns (sent, failed)."""
    sent = failed = 0
    for row in outbox.pending(limit=limit):
        try:
            sender(row["kind"], row["job_card"], json.loads(row["payload_json"]))
            outbox.mark_sent(row["id"])
            sent += 1
        except Exception as e:  # noqa: BLE001 - any failure re-queues, never crashes the loop
            outbox.mark_failed(row["id"], e)
            failed += 1
    return sent, failed
