# -*- coding: utf-8 -*-
"""
Savat handlerlari: ko'rish, qty +/-, o'chirish
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import queries as db
from keyboards import user_keyboards as kb

logger = logging.getLogger(__name__)
router = Router()


def format_cart_text(cart_items: list) -> str:
    if not cart_items:
        return "🛒 <b>SAVAT BO'SH</b>\n\nKitoblar yoki to'plamlardan qo'shing!"

    text = "🛒 <b>SAVAT</b>\n\n"
    total = 0
    for idx, item in enumerate(cart_items, 1):
        d = item["details"]
        cover_label = "Qattiq" if d.get("cover_type") == "qattiq" else "Yumshoq"
        item_emoji = "📚" if item["item_type"] == "product" else "📦"
        subtotal = d["discounted_price"] * item["quantity"]
        total += subtotal
        text += (
            f"{idx}. {item_emoji} <b>{d['name']}</b> ({cover_label})\n"
            f"   ✅ {d['discounted_price']:,} so'm × {item['quantity']} = <b>{subtotal:,} so'm</b>\n\n"
        )
    text += "─────────────────────\n"
    text += f"💰 <b>Jami: {total:,} so'm</b>"
    return text


@router.message(F.text == "🛒 Savat")
async def show_cart(message: Message):
    cart = await db.get_cart(message.from_user.id)
    text = format_cart_text(cart)
    await message.answer(text, reply_markup=kb.cart_kb(cart), parse_mode="HTML")


@router.callback_query(F.data == "back_cart")
async def cb_back_cart(callback: CallbackQuery):
    cart = await db.get_cart(callback.from_user.id)
    text = format_cart_text(cart)
    try:
        await callback.message.edit_text(text, reply_markup=kb.cart_kb(cart), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.cart_kb(cart), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("cart_plus_"))
async def cb_cart_plus(callback: CallbackQuery):
    try:
        cart_id = int(callback.data.replace("cart_plus_", ""))
    except ValueError:
        await callback.answer()
        return

    # Joriy quantity ni olish
    cart = await db.get_cart(callback.from_user.id)
    item = next((c for c in cart if c["id"] == cart_id), None)
    if not item:
        await callback.answer("Savatda topilmadi", show_alert=True)
        return

    new_qty = item["quantity"] + 1

    # Mahsulot bo'lsa stokni tekshirish
    if item["item_type"] == "product":
        if new_qty > item["details"]["stock"]:
            await callback.answer("⚠️ Stokda yetarli emas", show_alert=True)
            return

    await db.update_cart_quantity(cart_id, new_qty)

    cart = await db.get_cart(callback.from_user.id)
    text = format_cart_text(cart)
    try:
        await callback.message.edit_text(text, reply_markup=kb.cart_kb(cart), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("cart_minus_"))
async def cb_cart_minus(callback: CallbackQuery):
    try:
        cart_id = int(callback.data.replace("cart_minus_", ""))
    except ValueError:
        await callback.answer()
        return

    cart = await db.get_cart(callback.from_user.id)
    item = next((c for c in cart if c["id"] == cart_id), None)
    if not item:
        await callback.answer()
        return

    new_qty = item["quantity"] - 1
    await db.update_cart_quantity(cart_id, new_qty)

    cart = await db.get_cart(callback.from_user.id)
    text = format_cart_text(cart)
    try:
        await callback.message.edit_text(text, reply_markup=kb.cart_kb(cart), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("cart_remove_"))
async def cb_cart_remove(callback: CallbackQuery):
    try:
        cart_id = int(callback.data.replace("cart_remove_", ""))
    except ValueError:
        await callback.answer()
        return

    await db.remove_from_cart(cart_id)

    cart = await db.get_cart(callback.from_user.id)
    text = format_cart_text(cart)
    try:
        await callback.message.edit_text(text, reply_markup=kb.cart_kb(cart), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("❌ Mahsulot savatdan o'chirildi")
