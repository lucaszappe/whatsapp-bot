from fastapi.testclient import TestClient

from app.config import settings
from app.main import app as fastapi_app

client = TestClient(fastapi_app)
VALID_TOKEN = "my-secret-token"


# ---------------------------------------------------------------
def test_webhook_get_success(monkeypatch):
    monkeypatch.setattr(settings, "VERIFY_TOKEN", VALID_TOKEN)
    r = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VALID_TOKEN,
            "hub.challenge": "123",
        },
    )
    assert r.status_code == 200
    assert r.text == "123"


def test_webhook_get_bad_token():
    r = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------
def build_payload(text: str | None) -> dict:
    """Build a webhook payload for a text message or delivery event."""
    if text is None:
        return {"entry": [{"changes": [{"value": {}}]}]}  # simulate delivery
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "text": {"body": text},
                                    "type": "text",
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }


def build_media_payload(media_type: str = "image") -> dict:
    """Build a webhook payload for a media message."""
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15551234567",
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


def test_post_happy_path() -> None:
    """Test posting a normal text message to the webhook."""
    payload = build_payload("Hi bot!")
    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_post_empty_text() -> None:
    """Test posting an empty text message to the webhook."""
    payload = build_payload("")
    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_post_non_message() -> None:
    """Test posting a non-message (e.g., delivery event) to the webhook."""
    r = client.post("/webhook", json=build_payload(None))
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_post_media_message() -> None:
    """Test posting a media message to the webhook."""
    r = client.post("/webhook", json=build_media_payload())
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
