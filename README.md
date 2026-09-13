# WhatsApp Bot

This project is a FastAPI-based WhatsApp assistant for subscribed users. It listens for Meta WhatsApp webhook events, validates the webhook, checks subscription and usage limits, and answers customer questions using OpenAI with a vector-store-backed file search.

## What it does

- Receives incoming WhatsApp messages through the webhook endpoint at `/webhook`
- Verifies the webhook using the configured `VERIFY_TOKEN`
- Rejects non-text or empty messages with a guided response
- Checks whether the sender is an active subscriber
- Enforces a monthly token usage cap in Postgres
- Retries conversation context using the stored `last_response_id`
- Calls the OpenAI Responses API with a vector store search tool
- Sends the final answer back to the user via the WhatsApp Graph API
- Stores usage and session state in PostgreSQL

## Main components

- `app.main`: FastAPI app bootstrap
- `app.api`: webhook routes (`/` and `/webhook`)
- `app.services`: core message-processing flow
- `app.ai`: OpenAI Responses API integration
- `app.whatsapp`: WhatsApp payload parsing and sending logic
- `app.db`: PostgreSQL access for users, usage, and session state
- `migrations/`: database schema setup scripts
- `scripts/manage_db.py`: helper script for managing subscribers

## Required environment variables

Copy `.env.example` to `.env` and fill in the real values from your local environment:

- `OPENAI_API_KEY`
- `DATABASE_URL`
- `WHATSAPP_TOKEN`
- `PHONE_NUMBER_ID`
- `VERIFY_TOKEN`
- `VECTOR_STORE_ID`

These are the variables actually stored in the local git-ignored environment file for this project.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .\.venv\Scripts\activate on Windows
pip install -e '.[dev]'
cp .env.example .env
# edit .env with your real credentials
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Database

The project expects PostgreSQL tables for subscribers, usage logs, and per-user session state. The SQL files in `migrations/` create the initial schema.

## Webhook flow

1. Meta sends a WhatsApp event to `/webhook`
2. The app extracts the sender phone and message text
3. It validates the sender is a subscribed user and within quota
4. It calls OpenAI with the active vector store
5. It sends the answer back over WhatsApp

## Notes

This project is tailored for a business/field-support use case, where agricultural or operational knowledge is stored in an OpenAI vector store and accessed through the bot.
