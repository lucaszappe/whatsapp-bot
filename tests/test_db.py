import datetime as dt
import uuid

import psycopg
import pytest

from app.db import (
    get_conn,
    get_session,
    is_active_subscriber,
    log_usage,
    tokens_used_this_month,
    upsert_session,
)


# ------------------------------------------------------------------
# helpers
def random_phone() -> str:
    """Generate a new random phone number for testing."""
    return "1555" + uuid.uuid4().hex[:6]


TEST_PHONE = random_phone()  # baseline subscriber for the “happy-path” tests


# ------------------------------------------------------------------
def setup_module(_: object) -> None:
    """Runs once per module: insert the baseline subscriber."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (phone, plan, monthly_token_limit)
            VALUES (%s, 'pro', 1000)
            ON CONFLICT (phone) DO NOTHING
            """,
            (TEST_PHONE,),
        )


# ------------------------------------------------------------------
# 1. happy-path tests
def test_is_active_subscriber() -> None:
    """Test that is_active_subscriber returns True for active and False for inactive."""
    assert is_active_subscriber(TEST_PHONE) is True
    assert is_active_subscriber("19999999999") is False


def test_usage_logging_and_count() -> None:
    """Test logging usage and counting tokens used this month."""
    start = tokens_used_this_month(TEST_PHONE)
    log_usage(TEST_PHONE, input=10, output=20)
    after = tokens_used_this_month(TEST_PHONE)
    assert after - start == 30  # 10 + 20 tokens just logged


# ------------------------------------------------------------------
# 2. edge-case tests
def test_inactive_subscriber() -> None:
    """Test that an inactive subscriber is not considered active."""
    phone = random_phone()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (phone, plan, monthly_token_limit, is_active)
            VALUES (%s, 'basic', 1000, FALSE)
            """,
            (phone,),
        )
    assert is_active_subscriber(phone) is False


def test_monthly_limit_edge() -> None:
    """Test that token usage does not exceed the monthly limit."""
    phone = random_phone()
    limit = 30
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (phone, plan, monthly_token_limit)
            VALUES (%s, 'pro', %s)
            """,
            (phone, limit),
        )
    # log 20 tokens (10 + 10)
    log_usage(phone, 10, 10)
    assert tokens_used_this_month(phone) == 20
    # log another 10 tokens to hit the exact limit
    log_usage(phone, 5, 5)
    assert tokens_used_this_month(phone) == limit


def test_cross_month_reset() -> None:
    """Test that usage from previous months does not count toward the current month."""
    phone = random_phone()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (phone, plan, monthly_token_limit)
            VALUES (%s, 'pro', 1000)
            """,
            (phone,),
        )
        # Insert a usage row dated last month
        last_month = (
            dt.datetime.now(dt.UTC).replace(day=1) - dt.timedelta(days=1)
        ).replace(hour=12, minute=0)
        conn.execute(
            """
            INSERT INTO usage_log (phone_fk, ts, input_tokens, output_tokens)
            VALUES (%s, %s, 10, 10)
            """,
            (phone, last_month),
        )
    assert tokens_used_this_month(phone) == 0  # old usage shouldn’t count


def test_foreign_key_integrity() -> None:
    """log_usage() on a phone that isn't in subscribers should raise FK error."""
    phone = random_phone()  # not inserted in subscribers
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        log_usage(phone, 5, 5)


def test_token_logging_and_monthly_count() -> None:
    """Test logging tokens and monthly count increments as expected."""
    phone = random_phone()
    # Insert the subscriber first
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (phone, plan, monthly_token_limit)
            VALUES (%s, 'pro', 1000)
            """,
            (phone,),
        )
    # Should start at zero
    assert tokens_used_this_month(phone) == 0

    # Log some usage and check increments
    log_usage(phone, 5, 10)  # 15 tokens
    assert tokens_used_this_month(phone) == 15

    log_usage(phone, 8, 4)  # +12 tokens
    assert tokens_used_this_month(phone) == 27


def seed_subscriber(phone: str) -> None:
    """Insert or activate a subscriber for testing."""
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO subscribers (phone, plan, monthly_token_limit)
            VALUES (%s, 'pro', 1000)
            ON CONFLICT (phone) DO UPDATE SET is_active = TRUE
        """,
            (phone,),
        )


def test_upsert_and_get_session() -> None:
    """Test upserting and retrieving a session for a phone number."""
    phone = random_phone()
    seed_subscriber(phone)
    upsert_session(phone, "resp_1")
    row = get_session(phone)
    assert row is not None, "get_session returned None"
    assert row.last_response_id == "resp_1"


def test_timestamp_updates() -> None:
    """Test that upserting a session updates the timestamp."""
    phone = random_phone()
    seed_subscriber(phone)
    upsert_session(phone, "resp_1")
    session1 = get_session(phone)
    assert session1 is not None, "get_session returned None after first upsert"
    first_seen = session1.last_seen_utc
    upsert_session(phone, "resp_2")
    session2 = get_session(phone)
    assert session2 is not None, "get_session returned None after second upsert"
    second_seen = session2.last_seen_utc
    assert second_seen > first_seen
