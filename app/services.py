import datetime as dt
import logging

from app.ai import call_openai
from app.config import settings
from app.db import (
    get_session,
    is_active_subscriber,
    log_usage,
    tokens_used_this_month,
    upsert_session,
)
from app.whatsapp import parse_whatsapp_payload, send_whatsapp_text


def process_whatsapp_event(body: dict) -> dict:
    phone, text, msg_type = parse_whatsapp_payload(body)
    if phone is None:
        return {"status": "ignored"}  # not a user message

    if msg_type != "text":
        send_whatsapp_text(
            phone,
            "⚠️ No momento, só aceitamos mensagens de texto. Por favor, envie sua dúvida como texto.",
        )
        return {"status": "media_not_supported"}

    if not text or not text.strip():
        send_whatsapp_text(
            phone,
            "❓ Por favor, envie uma mensagem para que eu possa responder.",
        )
        return {"status": "empty_text"}

    # 1. subscription check
    if not is_active_subscriber(phone):
        send_whatsapp_text(
            phone,
            "⚠️ Você não possui uma assinatura ativa. Entre em contato com um de nossos representantes para ativá-la.",
        )
        return {"status": "not_subscribed"}

    # 2. quota check
    used = tokens_used_this_month(phone)
    limit = settings.MONTHLY_FALLBACK_LIMIT  # TODO: fetch from DB for each plan
    if used >= limit:
        send_whatsapp_text(phone, "🚫 Você atingiu o limite mensal da sua assinatura.")
        return {"status": "quota_exceeded"}

    # 3. session lookup (12 h idle-timeout)
    session = get_session(phone)
    previous_response_id = None
    if session and (dt.datetime.now(dt.UTC) - session.last_seen_utc) < dt.timedelta(
        hours=12,
    ):
        previous_response_id = session.last_response_id

    # 4. call OpenAI
    try:
        answer, input_tokens, output_tokens, response_id = call_openai(
            text,
            previous_response_id=previous_response_id,
        )
    except Exception as e:
        logging.error("OpenAI error: %s", e, exc_info=True)
        send_whatsapp_text(
            phone,
            "😔 Estamos enfrentando instabilidades no momento. Tente novamente mais tarde.",
        )
        return {"status": "openai_error"}

    if not answer or not answer.strip():
        answer = (
            "🤖 Desculpe, não consegui encontrar uma resposta no momento. "
            "Pode tentar reformular a pergunta?"
        )

    # 5. log tokens & reply
    try:
        log_usage(phone, input_tokens, output_tokens)
    except Exception as e:
        logging.error("DB log_usage failed: %s", e, exc_info=True)

    try:
        send_whatsapp_text(phone, answer)
    except Exception as e:
        logging.error("send_whatsapp_text failed: %s", e, exc_info=True)

    # 6. upsert session with latest response ID
    try:
        upsert_session(phone, response_id)
    except Exception as e:
        logging.error("upsert_session failed: %s", e, exc_info=True)

    return {"status": "ok"}
