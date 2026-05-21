# -*- coding: utf-8 -*-
"""
Buyurtmalarim va status xabarlari handlerlari
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import queries as db
from keyboards import user_keyboards as kb
from utils.bonus import get_bonus_channels_for_order, create_invite_link

logger = logging.getLogger(__name__)
router = Router()


STATUS_EMOJI = {
    "pending": "⏳ Yangi",
    "confirmed": "✅ Tasdiqlangan",
    "preparing": "📦 Tayyorlanmoqda",
    "shipping": "🚚 Yo'lda",
    "completed": "✔️ Yakunlandi",
    "cancelled": "❌ Bekor qilindi",
}


def format_order_short(order: dict) -> str:
    items = order["items"]
    first_item = items[0]["name"] if items else "—"
    if len(items) > 1:
        first_item += f" + {len(items)-1} ta"

    return (
        f"🔢 <b>{order['order_code']}</b>\n"
        f"📚 {first_item}\n"
        f"💰 {order['final_price']:,} so'm\n"
        f"📊 Status: {STATUS_EMOJI.get(order['delivery_status'], '—')}\n"
        f"📅 {order['created_date'][:16]}"
    )


def format_order_full(order: dict) -> str:
    text = f"📦 <b>BUYURTMA: {order['order_code']}</b>\n\n"
    text += f"👤 {order['full_name']}\n"
    text += f"📱 {order['phone']}\n"
    text += f"📍 {order['region']} — {order['district']}\n"
    text += f"📦 {order['btc_point']}\n\n"

    text += "🛒 <b>BUYURTMA:</b>\n"
    for idx, it in enumerate(order["items"], 1):
        cover_label = "Qattiq" if it.get("cover") == "qattiq" else "Yumshoq"
        emoji = "📚" if it["type"] == "product" else "📦"
        subtotal = it["price"] * it["quantity"]
        text += f"{idx}. {emoji} {it['name']} ({cover_label}) ×{it['quantity']} — {subtotal:,} so'm\n"

    text += f"\n💰 Jami: {order['total_price']:,} so'm\n"
    if order["discount_amount"] > 0:
        text += f"🎯 Chegirma: -{order['discount_amount']:,} so'm\n"
    if order["cashback_used"] > 0:
        text += f"💎 Keshbek: -{order['cashback_used']:,} so'm\n"
    text += f"💳 <b>To'langan: {order['final_price']:,} so'm</b>\n"
    text += f"💳 To'lov usuli: {order['payment_method']}\n"
    text += f"📅 Sana: {order['created_date'][:16]}\n"
    text += f"📊 Status: <b>{STATUS_EMOJI.get(order['delivery_status'], '—')}</b>"

    if order.get("estimated_delivery"):
        text += f"\n📅 Yetkazilish vaqti: {order['estimated_delivery']}"

    return text


# ==================== BUYURTMALARIM ====================

@router.message(F.text == "📋 Buyurtmalarim")
async def show_my_orders(message: Message):
    await message.answer(
        "📋 <b>BUYURTMALARIM</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=kb.my_orders_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_my_orders")
async def cb_back_my_orders(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>BUYURTMALARIM</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=kb.my_orders_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "orders_active")
async def cb_orders_active(callback: CallbackQuery):
    orders = await db.get_user_orders(callback.from_user.id, active_only=True)
    if not orders:
        await callback.message.edit_text(
            "🔄 <b>FAOL BUYURTMALAR</b>\n\nFaol buyurtmangiz yo'q.",
            reply_markup=kb.my_orders_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "🔄 <b>FAOL BUYURTMALAR</b>\n\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()

    for idx, o in enumerate(orders, 1):
        text += f"{idx}. {format_order_short(o)}\n\n"
        builder.row(InlineKeyboardButton(
            text=f"👁 {o['order_code']}",
            callback_data=f"view_order_{o['id']}"
        ))

    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_my_orders"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "orders_history")
async def cb_orders_history(callback: CallbackQuery):
    all_orders = await db.get_user_orders(callback.from_user.id)
    orders = [o for o in all_orders if o["delivery_status"] in ("completed", "cancelled")]

    if not orders:
        await callback.message.edit_text(
            "📜 <b>BUYURTMALAR TARIXI</b>\n\nTarix bo'sh.",
            reply_markup=kb.my_orders_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "📜 <b>BUYURTMALAR TARIXI</b>\n\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()

    for idx, o in enumerate(orders[:10], 1):
        text += f"{idx}. {format_order_short(o)}\n\n"
        builder.row(InlineKeyboardButton(
            text=f"👁 {o['order_code']}",
            callback_data=f"view_order_{o['id']}"
        ))

    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_my_orders"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("view_order_"))
async def cb_view_order(callback: CallbackQuery):
    try:
        order_id = int(callback.data.replace("view_order_", ""))
    except ValueError:
        await callback.answer()
        return

    order = await db.get_order(order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return

    is_active = order["delivery_status"] not in ("completed", "cancelled")
    text = format_order_full(order)
    await callback.message.edit_text(text, reply_markup=kb.order_view_kb(order_id, is_active), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("contact_admin_"))
async def cb_contact_admin_for_order(callback: CallbackQuery, state: FSMContext):
    """Bitta buyurtma haqida adminga xabar"""
    from states.user_states import SupportStates
    try:
        order_id = int(callback.data.replace("contact_admin_", ""))
    except ValueError:
        await callback.answer()
        return

    await state.set_state(SupportStates.writing_message)
    await state.update_data(related_order_id=order_id)
    await callback.message.answer(
        f"✉️ Buyurtma haqida xabaringizni yozing:\n(Bekor qilish uchun /menu yozing)"
    )
    await callback.answer()


# ==================== STATUS XABARLARI (admin chaqiradi) ====================

async def notify_status_change(bot: Bot, order: dict, new_status: str):
    """Status o'zgargan paytda userga xabar"""
    user_id = order["user_id"]
    code = order["order_code"]

    messages = {
        "confirmed": f"✅ <b>{code}</b>\n\nTo'lovingiz tasdiqlandi! Buyurtmangiz tayyorlanishni boshlaydi.",
        "preparing": f"📦 <b>{code}</b>\n\nKitobingiz tayyorlanmoqda.",
        "shipping": (
            f"🚚 <b>{code}</b>\n\n"
            f"Kitobingiz jo'natildi!\n\n"
            f"📦 BTC punkt: {order['btc_point']}\n"
            f"📅 Yetkazilish vaqti: {order.get('estimated_delivery', '—')}\n\n"
            f"Kitobni punktdan olishda buyurtma raqamingizni ko'rsating: <code>{code}</code>"
        ),
        "completed": f"✅ <b>{code}</b>\n\nKitobingiz BTC punktga yetib bordi! Olib keling.",
        "cancelled": f"❌ <b>{code}</b>\n\nBuyurtmangiz bekor qilindi.",
    }

    text = messages.get(new_status)
    if not text:
        return

    # Bekor qilingan bo'lsa va keshbek ishlatilgan bo'lsa - qaytarish
    if new_status == "cancelled" and order.get("cashback_used", 0) > 0:
        await db.refund_cashback(user_id, order["cashback_used"], order["id"])
        text += f"\n💰 {order['cashback_used']:,} so'm keshbek balansingizga qaytarildi!"

    # Yakunlangan bo'lsa - bonus kanallarni avtomatik yuborish
    if new_status == "completed":
        bonus_channels = await get_bonus_channels_for_order(order["items"])
        if bonus_channels:
            text += "\n\n🎁 <b>BONUS KANALLAR:</b>\nQuyidagi maxsus kanallarga kirish huquqi berildi:"

        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"User {user_id} ga xabar yuborishda xato: {e}")
            return

        # Har bir bonus kanal uchun unikal link
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        any_link = False
        for ch_id in bonus_channels:
            link = await create_invite_link(bot, ch_id, user_id)
            if link:
                builder.row(InlineKeyboardButton(text="🔗 Bonus kanalga kirish", url=link))
                any_link = True

        if any_link:
            try:
                await bot.send_message(
                    user_id,
                    "📢 Pastdagi tugmalardan bonus kanallarga kiring:",
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logger.error(f"Bonus kanal link yuborishda xato: {e}")

        # Referal keshbek hisoblash (faqat UzCard/Humo bo'lsa)
        if order["payment_method"] == "UzCard/Humo":
            await process_referral_cashback(bot, order)
        return

    # Boshqa statuslar uchun
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"User {user_id} ga status xabar yuborishda xato: {e}")


async def process_referral_cashback(bot: Bot, order: dict):
    """Buyurtma yakunlangach referrerga keshbek qo'shish"""
    user = await db.get_user(order["user_id"])
    if not user or not user.get("referrer_id"):
        return

    cashback_amount = calculate_referral_cashback(order["final_price"])
    if cashback_amount <= 0:
        return

    referrer_id = user["referrer_id"]
    await db.add_cashback(referrer_id, order["user_id"], order["id"], cashback_amount)

    # Referrerga xabar
    try:
        await bot.send_message(
            referrer_id,
            f"💰 <b>YANGI KESHBEK!</b>\n\n"
            f"@{user.get('username', '—')} xarid qildi!\n"
            f"💳 Sizga {cashback_amount:,} so'm keshbek qo'shildi.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Referrer {referrer_id} ga xabar: {e}")

    # Google Sheets
    try:
        from utils.sheets import sheets
        await sheets.sync_cashback(
            referrer_id,
            user.get("username", ""),
            order["user_id"],
            cashback_amount
        )
    except Exception as e:
        logger.warning(f"Sheets cashback sync: {e}")


def calculate_referral_cashback(final_price: int) -> int:
    from utils.config import config
    return final_price * config.REFERRAL_CASHBACK // 100
