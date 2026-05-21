# -*- coding: utf-8 -*-
"""
Google Sheets sinxronizatsiya
4 ta varaq: Foydalanuvchilar, Buyurtmalar, To'lovlar, Referal
"""
import asyncio
import logging
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from utils.config import config

logger = logging.getLogger(__name__)

_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


class SheetsManager:
    def __init__(self):
        self._client = None
        self._sheet = None
        self._enabled = False

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                config.GOOGLE_SHEETS_CREDENTIALS, _SCOPE
            )
            self._client = gspread.authorize(creds)
            self._sheet = self._client.open_by_key(config.SPREADSHEET_ID)
            self._ensure_worksheets()
            self._enabled = True
            logger.info("Google Sheets ulandi")
        except Exception as e:
            logger.warning(f"Google Sheets ulanishda xato (kechirib o'tiladi): {e}")
            self._enabled = False

    def _ensure_worksheets(self):
        """Kerakli varaqlar mavjud bo'lishini ta'minlash"""
        needed = {
            "Foydalanuvchilar": ["User ID", "Ism", "Telefon", "Username", "Viloyat", "Tuman", "BTC punkt", "Sana"],
            "Buyurtmalar": ["Order Code", "User ID", "Ism", "Telefon", "Kitoblar", "Summa", "To'lov", "Status", "Viloyat", "Tuman", "BTC", "Sana"],
            "To'lovlar": ["Order Code", "User ID", "Summa", "Usul", "Chegirma", "Sana"],
            "Referal": ["Taklif qilgan ID", "Username", "Taklif qilingan ID", "Keshbek", "Sana"],
        }
        existing = [ws.title for ws in self._sheet.worksheets()]
        for title, headers in needed.items():
            if title not in existing:
                ws = self._sheet.add_worksheet(title=title, rows=1000, cols=len(headers))
                ws.append_row(headers)
            else:
                ws = self._sheet.worksheet(title)
                if not ws.row_values(1):
                    ws.update("A1", [headers])

    async def _run(self, fn):
        """Sync funksiyani async-da ishga tushirish"""
        if not self._enabled:
            self._ensure_client()
            if not self._enabled:
                return
        try:
            await asyncio.to_thread(fn)
        except Exception as e:
            logger.error(f"Sheets sync xato: {e}")

    async def sync_new_user(self, user: dict):
        def _do():
            ws = self._sheet.worksheet("Foydalanuvchilar")
            ws.append_row([
                user.get("telegram_id", ""),
                user.get("full_name", ""),
                user.get("phone", ""),
                user.get("username", ""),
                user.get("region", ""),
                user.get("district", ""),
                user.get("btc_point", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ])
        await self._run(_do)

    async def sync_new_order(self, order: dict):
        def _do():
            ws = self._sheet.worksheet("Buyurtmalar")
            items_str = "; ".join([f"{i['name']} x{i['quantity']}" for i in order.get("items", [])])
            ws.append_row([
                order.get("order_code", ""),
                order.get("user_id", ""),
                order.get("full_name", ""),
                order.get("phone", ""),
                items_str,
                order.get("final_price", 0),
                order.get("payment_method", ""),
                order.get("delivery_status", ""),
                order.get("region", ""),
                order.get("district", ""),
                order.get("btc_point", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ])
        await self._run(_do)

    async def sync_order_status(self, order_code: str, status: str):
        def _do():
            ws = self._sheet.worksheet("Buyurtmalar")
            try:
                cell = ws.find(order_code)
                if cell:
                    ws.update_cell(cell.row, 8, status)  # Status ustuni 8-da
            except Exception as e:
                logger.error(f"Order status update xato: {e}")
        await self._run(_do)

    async def sync_payment(self, order: dict):
        def _do():
            ws = self._sheet.worksheet("To'lovlar")
            ws.append_row([
                order.get("order_code", ""),
                order.get("user_id", ""),
                order.get("final_price", 0),
                order.get("payment_method", ""),
                order.get("discount_amount", 0),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ])
        await self._run(_do)

    async def sync_cashback(self, user_id: int, username: str, from_user_id: int, amount: int):
        def _do():
            ws = self._sheet.worksheet("Referal")
            ws.append_row([
                user_id,
                username,
                from_user_id,
                amount,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ])
        await self._run(_do)


sheets = SheetsManager()
