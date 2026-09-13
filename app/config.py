from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Environment variables
    VECTOR_STORE_ID: str
    DATABASE_URL: str
    VERIFY_TOKEN: str
    WHATSAPP_TOKEN: str
    PHONE_NUMBER_ID: str
    LOG_LEVEL: str = "INFO"
    # WhatsApp API
    WHATSAPP_API_VERSION: str = "v22.0"
    WHATSAPP_TIMEOUT_SECONDS: int = 10
    # App
    MONTHLY_FALLBACK_LIMIT: int = 50000
    SESSION_TIMEOUT_HOURS: int = 12

    @property
    def whatsapp_api_url(self) -> str:
        return f"https://graph.facebook.com/{self.WHATSAPP_API_VERSION}/{self.PHONE_NUMBER_ID}/messages"

    @property
    def whatsapp_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.WHATSAPP_TOKEN}"}


settings = Settings()
