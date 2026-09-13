from unittest.mock import MagicMock, patch

import httpx

from app.services import process_whatsapp_event
from app.whatsapp import HEADERS, WA_URL, send_whatsapp_text

DEST = "15551234567"
TEXT = "Unit-test message"


def build_text_payload(text: str = "Hi bot!", phone: str = "15551234567") -> dict:
    """Build a WhatsApp webhook payload for a text message."""
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": phone, "text": {"body": text}, "type": "text"},
                            ],
                        },
                    },
                ],
            },
        ],
    }


def build_media_payload(media_type: str = "image", phone: str = "15551234567") -> dict:
    """Build a WhatsApp webhook payload for a media message."""
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "id": "wamid...",
                                    "timestamp": "1687423123",
                                    "type": media_type,
                                    media_type: {"id": "media-id-string"},
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }


@patch("app.whatsapp.httpx.post")
def test_send_whatsapp_happy_path(mock_post: object) -> None:
    """Test sending a WhatsApp message with a successful 200 response."""
    # Fake a 200 OK from Meta
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"messages": [{"id": "wamid.TEST"}]}

    send_whatsapp_text(DEST, TEXT)

    # --- assertions ---
    mock_post.assert_called_once()
    url_passed = mock_post.call_args[0][0]
    json_passed = mock_post.call_args.kwargs["json"]
    headers_passed = mock_post.call_args.kwargs["headers"]

    assert url_passed == WA_URL
    assert headers_passed == HEADERS
    assert json_passed["to"] == DEST
    assert json_passed["text"]["body"] == TEXT


@patch("app.whatsapp.httpx.post")
def test_send_whatsapp_non_200(mock_post: object, caplog: object) -> None:
    """Test sending a WhatsApp message with a non-200 response triggers logging."""
    mock_response = MagicMock(status_code=400, text="Bad Request")
    fake_request = httpx.Request("POST", WA_URL)
    fake_response = httpx.Response(400, request=fake_request)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Client Error",
        request=fake_request,
        response=fake_response,
    )
    mock_post.return_value = mock_response

    send_whatsapp_text(DEST, TEXT)

    assert "WhatsApp send failed" in caplog.text


@patch("app.services.send_whatsapp_text")
def test_media_message_triggers_warning(mock_send: object) -> None:
    """Test that a media message triggers a warning to the user."""
    payload = build_media_payload()
    result = process_whatsapp_event(payload)
    mock_send.assert_called_once_with(
        "15551234567",
        "⚠️ No momento, só aceitamos mensagens de texto. Por favor, envie sua dúvida como texto.",
    )
    assert result == {"status": "media_not_supported"}


@patch("app.services.send_whatsapp_text")
def test_empty_text_triggers_prompt(mock_send: object) -> None:
    """Test that an empty text message triggers a prompt to the user."""
    payload = build_text_payload("")
    result = process_whatsapp_event(payload)
    mock_send.assert_called_once_with(
        "15551234567",
        "❓ Por favor, envie uma mensagem para que eu possa responder.",
    )
    assert result == {"status": "empty_text"}


@patch("app.services.is_active_subscriber", return_value=False)
@patch("app.services.send_whatsapp_text")
def test_inactive_subscriber(mock_send: object, _mock_active: object) -> None:
    """Test that an inactive subscriber receives the correct warning."""
    payload = build_text_payload("Hi")
    result = process_whatsapp_event(payload)
    mock_send.assert_called_once_with(
        "15551234567",
        "⚠️ Você não possui uma assinatura ativa. Entre em contato com um de nossos representantes para ativá-la.",
    )
    assert result == {"status": "not_subscribed"}


@patch("app.services.tokens_used_this_month", return_value=999_999)
@patch("app.services.is_active_subscriber", return_value=True)
@patch("app.services.send_whatsapp_text")
def test_quota_exceeded(
    mock_send: object,
    _mock_active: object,
    _mock_used: object,
) -> None:
    """Test that a user exceeding their quota receives the correct warning."""
    payload = build_text_payload("Hi")
    result = process_whatsapp_event(payload)
    mock_send.assert_called_once_with(
        "15551234567",
        "🚫 Você atingiu o limite mensal da sua assinatura.",
    )
    assert result == {"status": "quota_exceeded"}


@patch("app.services.log_usage")
@patch("app.services.call_openai", return_value=("Hello!", 5, 7, "resp_id"))
@patch("app.services.tokens_used_this_month", return_value=0)
@patch("app.services.is_active_subscriber", return_value=True)
@patch("app.services.send_whatsapp_text")
def test_post_happy_path(
    mock_send: object,
    _mock_active: object,
    _mock_used: object,
    mock_call: object,
    mock_log: object,
) -> None:
    """Test the happy path for posting a WhatsApp message and logging usage."""
    payload = build_text_payload("Hi bot!")
    result = process_whatsapp_event(payload)
    mock_call.assert_called_once_with("Hi bot!", previous_response_id=None)
    mock_log.assert_called_once_with("15551234567", 5, 7)
    mock_send.assert_called_with("15551234567", "Hello!")
    assert result == {"status": "ok"}


@patch("app.services.call_openai", side_effect=Exception("OpenAI down"))
@patch("app.services.tokens_used_this_month", return_value=0)
@patch("app.services.is_active_subscriber", return_value=True)
@patch("app.services.send_whatsapp_text")
def test_openai_failure_path(
    mock_send: object,
    _mock_active: object,
    _mock_used: object,
    _mock_call: object,
) -> None:
    """Test that an OpenAI failure triggers the correct error message to the user."""
    payload = build_text_payload("Hi")
    result = process_whatsapp_event(payload)
    mock_send.assert_called_once_with(
        "15551234567",
        "😔 Estamos enfrentando instabilidades no momento. Tente novamente mais tarde.",
    )
    assert result == {"status": "openai_error"}
