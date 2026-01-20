"""
SQLite database operations for kudos storage.
"""

import sqlite3
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

DATABASE_PATH = "kudos.db"


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kudos (
                id INTEGER PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                thread_ts TEXT,
                channel_id TEXT,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_receiver ON kudos(receiver_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON kudos(created_at)")
        conn.commit()


def add_kudos(
    sender_id: str,
    receiver_id: str,
    summary: str,
    thread_ts: Optional[str] = None,
    channel_id: Optional[str] = None,
) -> int:
    """
    Store a new kudos record.
    Returns the id of the new record.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO kudos (sender_id, receiver_id, thread_ts, channel_id, summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sender_id, receiver_id, thread_ts, channel_id, summary),
        )
        conn.commit()
        return cursor.lastrowid


def get_kudos_count(receiver_id: str, month_only: bool = False) -> int:
    """
    Get the count of kudos received by a user.
    If month_only is True, only count kudos from the current month.
    """
    with get_connection() as conn:
        if month_only:
            # Get first day of current month
            now = datetime.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM kudos WHERE receiver_id = ? AND created_at >= ?",
                (receiver_id, month_start.isoformat()),
            )
        else:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM kudos WHERE receiver_id = ?",
                (receiver_id,),
            )
        return cursor.fetchone()[0]


from typing import List, Dict


def get_recent_kudos(receiver_id: str, limit: int = 3) -> List[Dict]:
    """
    Get the most recent kudos for a user.
    Returns a list of dicts with sender_id, summary, and created_at.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT sender_id, summary, created_at
            FROM kudos
            WHERE receiver_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (receiver_id, limit),
        )
        rows = cursor.fetchall()
        return [
            {
                "sender_id": row["sender_id"],
                "summary": row["summary"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


def get_user_stats(receiver_id: str) -> dict:
    """
    Get complete stats for a user's kudos history.
    Returns month count, all-time count, and recent kudos.
    """
    return {
        "month_count": get_kudos_count(receiver_id, month_only=True),
        "all_time_count": get_kudos_count(receiver_id, month_only=False),
        "recent_kudos": get_recent_kudos(receiver_id, limit=3),
    }
