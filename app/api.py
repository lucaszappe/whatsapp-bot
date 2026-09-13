import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.requests import ClientDisconnect

from app.config import settings
from app.services import process_whatsapp_event

router = APIRouter()


@router.get("/")
async def root():
    return {"status": "alive"}


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    challenge = request.query_params.get("hub.challenge")
    token_sent = request.query_params.get("hub.verify_token")

    if mode == "subscribe" and token_sent == settings.VERIFY_TOKEN:
        logging.info("✅  Webhook verified.")
        return challenge or ""
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook", status_code=200)
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
    except ClientDisconnect:
        logging.warning("⚠️ Webhook client disconnected before sending full body.")
        return JSONResponse({"status": "client_disconnect"}, status_code=200)
    except Exception as e:
        logging.error("Failed to parse webhook body: %s", e, exc_info=True)
        return JSONResponse({"status": "bad_request"}, status_code=200)

    logging.info("📩 Payload: %s", body)
    background_tasks.add_task(process_whatsapp_event, body)
    return {"status": "accepted"}
