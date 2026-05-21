# -*- coding: utf-8 -*-
"""
BTC punktlar bilan ishlash uchun yordamchi funksiyalar
Promtga ko'ra: bot scraping qilmaydi, to'g'ridan to'g'ri data/btc_points.py dan o'qiydi
"""
from data.btc_points import (
    BTC_POINTS,
    get_viloyatlar,
    get_tumanlar,
    get_btc_points,
    get_point_by_kod,
    get_nearest_points as _get_nearest,
)


def format_point(point: dict) -> str:
    """Punktni chiroyli matn shaklida formatlash"""
    return (
        f"📦 <b>{point['nomi']}</b>\n"
        f"📍 Manzil: {point['manzil']}\n"
        f"🎯 Mo'ljal: {point['moljal']}\n"
        f"🕐 Ish vaqti: {point['ish_vaqti']}\n"
        f"📞 Telefon: {point['telefon']}"
    )


def format_point_short(point: dict, idx: int = None) -> str:
    """Punktni qisqa formatda - ro'yxat uchun"""
    prefix = f"{idx}. " if idx is not None else ""
    return f"{prefix}<b>{point['nomi']}</b> — {point['manzil']}"


def get_nearest_points(lat: float, lon: float, limit: int = 3):
    """Eng yaqin N ta punkt"""
    return _get_nearest(lat, lon, limit)


# Re-export
__all__ = [
    "BTC_POINTS",
    "get_viloyatlar",
    "get_tumanlar",
    "get_btc_points",
    "get_point_by_kod",
    "get_nearest_points",
    "format_point",
    "format_point_short",
]
