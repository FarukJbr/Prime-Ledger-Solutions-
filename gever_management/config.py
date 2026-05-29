import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # Telegram (optional)
    telegram_bot_token: str = "optional"
    telegram_chairman_chat_id: int = 0

    # Meta (optional)
    meta_access_token: Optional[str] = None
    meta_page_id: Optional[str] = None
    instagram_account_id: Optional[str] = None

    # TikTok (optional)
    tiktok_access_token: Optional[str] = None
    tiktok_open_id: Optional[str] = None

    # Company
    company_name: str = "Gever Entrepreneurship"
    company_name_en: str = "Gever Entrepreneurship Business Consulting and Investments"
    default_language: str = "he"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # Dashboard
    dashboard_user: str = "chairman"
    dashboard_password: str = "gever2024"

    # Email notifications (Gmail)
    # Create app password at: https://myaccount.google.com/apppasswords
    gmail_user: str = ""
    gmail_app_password: str = ""
    chairman_email: str = "farukjaber34@gmail.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
