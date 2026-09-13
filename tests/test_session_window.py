"""Session-window tests for the 12 h idle timeout.

Scenarios:
1) Chat continues when last_seen_utc < 12 h
2) Chat resets when last_seen_utc
 12 h
3) Brand-new user (no session row)
"""

import datetime as dt
import uuid
from unittest.mock import patch

from app.db import SessionRow
from app.services import process_whatsapp_event
from tests.test_whatsapp import build_text_payload


# --------------------------------------------------------------------------- #
# Utility: generate a unique test phone number each time
def random_phone() -> str:
    return "1555" + uuid.uuid4().hex[:6]


# --------------------------------------------------------------------------- #
@patch("app.services.upsert_session")
@patch("app.services.log_usage")
@patch("app.services.send_whatsapp_text")
@patch("app.services.tokens_used_this_month", return_value=0)
@patch("app.services.is_active_subscriber", return_value=True)
@patch("app.services.call_openai", return_value=("👍", 3, 2, "resp_new"))
def test_reuse_within_window(
    mock_call: object,
    _sub: object,
    _tok: object,
    _send: object,
    _log: object,
    mock_upsert: object,
) -> None:
    """Test that chat continues when last_seen_utc is within the 12h window."""
    phone = random_phone()
    # build payload for this phone
    payload = build_text_payload("Oi!", phone=phone)

    with patch(
        "app.services.get_session",
        return_value=SessionRow(
            last_response_id="resp_old",
            last_seen_utc=dt.datetime.now(dt.UTC) - dt.timedelta(hours=1),
        ),
    ):
        result = process_whatsapp_event(payload)

    mock_call.assert_called_once_with("Oi!", previous_response_id="resp_old")
    mock_upsert.assert_called_once_with(phone, "resp_new")
    assert result == {"status": "ok"}


# --------------------------------------------------------------------------- #
@patch("app.services.upsert_session")
@patch("app.services.log_usage")
@patch("app.services.send_whatsapp_text")
@patch("app.services.tokens_used_this_month", return_value=0)
@patch("app.services.is_active_subscriber", return_value=True)
@patch("app.services.call_openai", return_value=("👍", 3, 2, "resp_new"))
def test_reset_after_timeout(
    mock_call: object,
    _sub: object,
    _tok: object,
    _send: object,
    _log: object,
    mock_upsert: object,
) -> None:
    """Test that chat resets when last_seen_utc is more than 12h ago."""
    phone = random_phone()
    payload = build_text_payload("Oi!", phone=phone)

    with patch(
        "app.services.get_session",
        return_value=SessionRow(
            last_response_id="resp_old",
            last_seen_utc=dt.datetime.now(dt.UTC) - dt.timedelta(hours=13),
        ),
    ):
        result = process_whatsapp_event(payload)

    mock_call.assert_called_once_with("Oi!", previous_response_id=None)
    mock_upsert.assert_called_once_with(phone, "resp_new")
    assert result == {"status": "ok"}


# --------------------------------------------------------------------------- #
@patch("app.services.upsert_session")
@patch("app.services.log_usage")
@patch("app.services.send_whatsapp_text")
@patch("app.services.tokens_used_this_month", return_value=0)
@patch("app.services.is_active_subscriber", return_value=True)
@patch("app.services.call_openai", return_value=("👍", 3, 2, "resp_new"))
def test_first_time_user(
    mock_call: object,
    _sub: object,
    _tok: object,
    _send: object,
    _log: object,
    mock_upsert: object,
) -> None:
    """Test that a brand-new user (no session row) gets a new session and response."""
    phone = random_phone()
    payload = build_text_payload("Oi!", phone=phone)

    with patch("app.services.get_session", return_value=None):
        result = process_whatsapp_event(payload)

    mock_call.assert_called_once_with("Oi!", previous_response_id=None)
    mock_upsert.assert_called_once_with(phone, "resp_new")
    assert result == {"status": "ok"}
