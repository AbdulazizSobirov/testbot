# -*- coding: utf-8 -*-
"""
Konfiguratsiya - .env faylidan o'zgaruvchilarni yuklaydi
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
    SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")

    # Kanallar
    CHANNEL_1_ID: str = os.getenv("CHANNEL_1_ID", "")
    CHANNEL_2_ID: str = os.getenv("CHANNEL_2_ID", "")

    # Bonus kanallar
    BONUS_CHANNEL_KOYLAK_ID: int = int(os.getenv("BONUS_CHANNEL_KOYLAK_ID", "0") or "0")
    BONUS_CHANNEL_JAKET_ID: int = int(os.getenv("BONUS_CHANNEL_JAKET_ID", "0") or "0")
    BONUS_CHANNEL_YUBKA_ID: int = int(os.getenv("BONUS_CHANNEL_YUBKA_ID", "0") or "0")

    # To'lov
    UZCARD_NUMBER: str = os.getenv("UZCARD_NUMBER", "")
    UZCARD_OWNER: str = os.getenv("UZCARD_OWNER", "")

    # BTC
    BTC_URL: str = os.getenv("BTC_URL", "https://btc.uz")

    # Database
    DB_PATH: str = "bot.db"

    # Chegirma foizlari
    DISCOUNT_BOOK: int = 3
    DISCOUNT_BUNDLE: int = 5
    DISCOUNT_PREMIUM: int = 8
    REFERRAL_CASHBACK: int = 3

    # Auto-cancel vaqt (daqiqa)
    AUTO_CANCEL_MINUTES: int = 30


config = Config()
