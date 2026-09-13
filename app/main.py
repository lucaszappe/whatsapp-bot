import logging

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from starlette.requests import ClientDisconnect

from app.api import router
from app.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)

app = FastAPI()
app.include_router(router)


@app.exception_handler(ClientDisconnect)
async def _client_disconnect_handler(request: Request, _exc: ClientDisconnect):
    logging.warning(
        "Client disconnected early: %s %s",
        request.method,
        request.url.path,
    )
    return PlainTextResponse("client disconnected", status_code=200)
