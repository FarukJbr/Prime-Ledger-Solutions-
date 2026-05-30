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
    company_name: str = "Jabr Entrepreneurship"
    company_name_en: str = "Jabr Entrepreneurship Business Consulting and Investments"
    default_language: str = "he"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # Dashboard
    dashboard_user: str = "chairman"
    dashboard_password: str = "jabr2024"

    # Email notifications
    # OPTION 1 (Recommended – no password needed): Resend.com
    #   Sign up free at resend.com → get API key → add domain or use @resend.dev
    resend_api_key: str = ""
    sender_email: str = "notifications@resend.dev"   # or your business email after domain verified

    # OPTION 2 (Gmail fallback): Gmail App Password
    #   Create at: myaccount.google.com/apppasswords
    gmail_user: str = ""
    gmail_app_password: str = ""

    # Chairman receives all notifications (change to your business email)
    chairman_email: str = "farukjaber34@gmail.com"

    # Portal (Client Portal) Supabase – for cash flow data
    portal_supabase_url: str = ""
    portal_supabase_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
