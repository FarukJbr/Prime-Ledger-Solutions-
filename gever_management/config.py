from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # Telegram
    telegram_bot_token: str
    telegram_chairman_chat_id: int

    # Meta
    meta_access_token: Optional[str] = None
    meta_page_id: Optional[str] = None
    instagram_account_id: Optional[str] = None

    # TikTok
    tiktok_access_token: Optional[str] = None
    tiktok_open_id: Optional[str] = None

    # Company
    company_name: str = "גבר יזמות ייעוץ עסקי והשקעות"
    company_name_en: str = "Gever Entrepreneurship Business Consulting and Investments"
    default_language: str = "he"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
