import logging

import httpx

from app.config import settings

WA_URL = settings.whatsapp_api_url
HEADERS = settings.whatsapp_headers


def send_whatsapp_text(to: str, text: str) -> None:
    """Send a WhatsApp text message using the Meta API."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    try:
        response = httpx.post(
            WA_URL,
            json=payload,
            headers=HEADERS,
            timeout=settings.WHATSAPP_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logging.error(
                "WhatsApp send failed (%s): %s",
                response.status_code,
                response.text,
            )
            return
        logging.info("⬆️ sent msg id %s", response.json()["messages"][0]["id"])
    except Exception as e:
        logging.error("WA send error: %s", e, exc_info=True)


# ── helper: extract phone + text from WhatsApp JSON -------------
def parse_whatsapp_payload(payload: dict) -> tuple[str | None, str | None, str | None]:
    """Returns (phone, text, msg_type) or (None, None, None) if payload isn't a user message."""
    try:
        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        msg_type = msg.get("type")
        phone = msg.get("from")
        if msg_type == "text":
            return phone, msg["text"]["body"], "text"
        return phone, None, msg_type
    except (KeyError, IndexError, TypeError):
        return None, None, None
