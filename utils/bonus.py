# -*- coding: utf-8 -*-
"""
Chegirma, keshbek va bonus kanallarni hisoblash
"""
import logging
from utils.config import config

logger = logging.getLogger(__name__)


def calculate_discount(cart_items: list) -> int:
    """
    Chegirma hisoblash:
    - Faqat kitob → 3%
    - To'plam → 5%
    - Premium to'plam → 8%
    - Aralash → har birini alohida
    """
    total_discount = 0
    for item in cart_items:
        details = item["details"]
        price = details["discounted_price"] * item["quantity"]
        
        if item["item_type"] == "product":
            # Kitob: 3%
            total_discount += price * config.DISCOUNT_BOOK // 100
        elif item["item_type"] == "bundle":
            name = details["name"]
            # Premium to'plam: 8%
            if "PREMIUM" in name.upper() or "💎" in name:
                total_discount += price * config.DISCOUNT_PREMIUM // 100
            else:
                # Oddiy to'plam: 5%
                total_discount += price * config.DISCOUNT_BUNDLE // 100
    return total_discount


def calculate_total(cart_items: list) -> int:
    return sum(item["details"]["discounted_price"] * item["quantity"] for item in cart_items)


def calculate_cashback(amount: int) -> int:
    """Referal uchun keshbek (xarid summasidan 3%)"""
    return amount * config.REFERRAL_CASHBACK // 100


async def get_bonus_channels_for_order(order_items: list) -> list:
    """
    Buyurtmadagi kitob/to'plamlarga mos bonus kanallar IDlari
    """
    channels = set()
    for item in order_items:
        name = item.get("name", "").lower()
        # Ko'ylaklar va koftalar
        if "ko'ylak" in name or "koylak" in name:
            if config.BONUS_CHANNEL_KOYLAK_ID:
                channels.add(config.BONUS_CHANNEL_KOYLAK_ID)
        # Jaketlar va paltolar
        if "jaket" in name or "palto" in name:
            if config.BONUS_CHANNEL_JAKET_ID:
                channels.add(config.BONUS_CHANNEL_JAKET_ID)
        # Yubka va shimlar
        if "yubka" in name or "shim" in name:
            if config.BONUS_CHANNEL_YUBKA_ID:
                channels.add(config.BONUS_CHANNEL_YUBKA_ID)
        # PREMIUM to'plam → barchasi
        if "premium" in name:
            if config.BONUS_CHANNEL_KOYLAK_ID:
                channels.add(config.BONUS_CHANNEL_KOYLAK_ID)
            if config.BONUS_CHANNEL_JAKET_ID:
                channels.add(config.BONUS_CHANNEL_JAKET_ID)
            if config.BONUS_CHANNEL_YUBKA_ID:
                channels.add(config.BONUS_CHANNEL_YUBKA_ID)
    return list(channels)


async def create_invite_link(bot, channel_id: int, user_id: int) -> str | None:
    """Unikal invite link yaratish"""
    try:
        result = await bot.create_chat_invite_link(
            chat_id=channel_id,
            name=f"user_{user_id}",
            member_limit=1,
        )
        return result.invite_link
    except Exception as e:
        logger.error(f"Invite link yaratishda xato: {e}")
        return None


async def check_user_subscription(bot, channel_id: str, user_id: int) -> bool:
    """User kanalga obuna bo'lganini tekshirish"""
    if not channel_id:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ("creator", "administrator", "member")
    except Exception as e:
        logger.error(f"Subscription check xato ({channel_id}, {user_id}): {e}")
        return False
