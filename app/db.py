import datetime as dt
from contextlib import contextmanager
from typing import NamedTuple

import psycopg
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings


# ── connection helper ───────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
@contextmanager
def get_conn():
    # autocommit=True so each statement is committed immediately
    with psycopg.connect(settings.DATABASE_URL, autocommit=True) as conn:
        yield conn


# ── helper #1: check subscriber status ──────────────────────────
def is_active_subscriber(phone: str) -> bool:
    """Return True if the phone number exists in subscribers and is_active."""
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT 1
            FROM subscribers
            WHERE phone = %s
              AND is_active = TRUE
            """,
            (phone,),
        )
        return cur.fetchone() is not None


# ── helper #2: tokens used this month ───────────────────────────
def tokens_used_this_month(phone: str) -> int:
    """Return the sum of input+output tokens for the current month.
    Falls back to 0 if the user hasn't used any tokens yet.
    """
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(tokens_month, 0)
            FROM usage_tokens_month
            WHERE phone_fk = %s
            """,
            (phone,),
        )
        row = cur.fetchone()
        return row[0] if row else 0


# ── helper #3: log a usage row ──────────────────────────────────
def log_usage(phone: str, input_tokens: int, output_tokens: int) -> None:
    """Insert a usage_log row for this interaction."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO usage_log (phone_fk, input_tokens, output_tokens)
            VALUES (%s, %s, %s)
            """,
            (phone, input_tokens, output_tokens),
        )


# ── helper #4: fetch session metadata ───────────────────────────
class SessionRow(NamedTuple):
    last_response_id: str
    last_seen_utc: dt.datetime


def get_session(phone: str) -> SessionRow | None:
    """Return the current session row for this phone number or None if absent."""
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT last_response_id, last_seen_utc
            FROM user_sessions
            WHERE phone = %s
            """,
            (phone,),
        )
        row = cur.fetchone()
        return SessionRow(*row) if row else None


# ── helper #5: upsert session metadata ──────────────────────────
def upsert_session(phone: str, response_id: str) -> None:
    """Insert a new session row or update the existing one, bumping last_seen_utc."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO user_sessions (phone, last_response_id)
            VALUES (%s, %s)
            ON CONFLICT (phone) DO UPDATE
               SET last_response_id = EXCLUDED.last_response_id,
                   last_seen_utc    = NOW();
            """,
            (phone, response_id),
        )
