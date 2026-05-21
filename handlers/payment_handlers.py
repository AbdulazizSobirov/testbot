# -*- coding: utf-8 -*-
"""
Payment handlers: UzCard/Humo va Uzum Nasiya to'lov jarayonlari
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import queries as db
from keyboards import user_keyboards as kb
from states.user_states import OrderStates
from utils.config import config
from utils.bonus import calculate_discount, calculate_total, calculate_cashback
from utils.sheets import sheets

logger = logging.getLogger(__name__)
router = Router()


# ==================== UZCARD / HUMO ====================

@router.callback_query(OrderStates.payment_method, F.data == "pay_uzcard")
async def cb_pay_uzcard(callback: CallbackQuery, state: FSMContext):
    """UzCard/Humo to'lov - karta ma'lumotlarini ko'rsatish"""
    data = await state.get_data()
    final_price = data.get("final_price", 0)
    cart_total = data.get("cart_total", 0)
    discount = data.get("discount", 0)

    await state.update_data(payment_method="UzCard/Humo")
    await state.set_state(OrderStates.waiting_receipt)

    text = (
        f"💳 <b>UZCARD / HUMO</b>\n\n"
        f"Quyidagi kartaga o'tkazing:\n\n"
        f"💳 <code>{config.UZCARD_NUMBER}</code>\n"
        f"👤 {config.UZCARD_OWNER}\n\n"
        f"💰 To'lov summasi: <s>{cart_total:,} so'm</s>\n"
    )
    if discount > 0:
        text += f"🎯 Chegirma: -{discount:,} so'm\n"
    text += (
        f"✅ <b>To'lash kerak: {final_price:,} so'm</b>\n\n"
        f"📷 To'lovni amalga oshirgach, chek (rasm yoki PDF) yuboring!"
    )

    await callback.message.answer(text, reply_markup=kb.uzcard_payment_kb(), parse_mode="HTML")
    await callback.answer()


# ==================== UZUM NASIYA ====================

@router.callback_query(OrderStates.payment_method, F.data == "pay_uzum")
async def cb_pay_uzum(callback: CallbackQuery, state: FSMContext):
    """Uzum Nasiya - chegirma va keshbek ishlatmaslik"""
    data = await state.get_data()
    cart = await db.get_cart(callback.from_user.id)
    cart_total = calculate_total(cart)

    # Uzum Nasiya - chegirma yo'q, keshbek yo'q
    await state.update_data(
        payment_method="Uzum Nasiya",
        final_price=cart_total,
        discount=0,
        cashback_used=0,
    )
    await state.set_state(OrderStates.uzum_waiting_receipt)

    monthly = cart_total // 3
    text = (
        f"🛍️ <b>UZUM NASIYA — 3 oyga foizsiz!</b>\n\n"
        f"💰 To'lov summasi: <b>{cart_total:,} so'm</b>\n"
        f"📅 Har oyda: <b>{monthly:,} so'm × 3 oy</b>\n\n"
        f"⚠️ Uzum Nasiya orqali chegirma va keshbek qo'llanilmaydi.\n\n"
        f"Quyidagi tugmalardan foydalaning:"
    )
    await callback.message.answer(text, reply_markup=kb.uzum_payment_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "uzum_qr")
async def cb_uzum_qr(callback: CallbackQuery):
    file_id = await db.get_setting("uzum_qr_file_id")
    if file_id:
        try:
            await callback.message.answer_photo(file_id, caption="📱 Uzum Nasiya QR kodi")
        except Exception as e:
            logger.error(f"QR yuborishda xato: {e}")
            await callback.answer("QR kod yuklanmagan", show_alert=True)
    else:
        await callback.answer("QR kod hozircha yuklanmagan", show_alert=True)


@router.callback_query(F.data == "uzum_video")
async def cb_uzum_video(callback: CallbackQuery):
    file_id = await db.get_setting("uzum_video_file_id")
    if file_id:
        try:
            await callback.message.answer_video(file_id, caption="🎬 Uzum Nasiya video yo'riqnoma")
        except Exception as e:
            logger.error(f"Video yuborishda xato: {e}")
            await callback.answer("Video yuklanmagan", show_alert=True)
    else:
        await callback.answer("Video hozircha yuklanmagan", show_alert=True)


@router.callback_query(F.data == "uzum_send_receipt")
async def cb_uzum_send_receipt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📷 Chekni (rasm yoki PDF) yuboring:\n\n"
        "Bekor qilish uchun \"❌ Bekor qilish\" tugmasini bosing"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_payment")
async def cb_cancel_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("❌ To'lov bekor qilindi.", reply_markup=kb.main_menu_kb())
    await callback.answer()


# ==================== CHEK QABUL QILISH ====================

@router.message(OrderStates.waiting_receipt, F.photo | F.document)
@router.message(OrderStates.uzum_waiting_receipt, F.photo | F.document)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    """Chek qabul qilish (rasm yoki PDF) va buyurtma yaratish"""
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        # Faqat PDF yoki rasm
        mime = (message.document.mime_type or "").lower()
        if "pdf" in mime or "image" in mime:
            file_id = message.document.file_id
        else:
            await message.answer("⚠️ Iltimos, chek rasmi yoki PDF yuboring")
            return

    if not file_id:
        await message.answer("⚠️ Iltimos, chek rasmi yoki PDF yuboring")
        return

    data = await state.get_data()

    # Buyurtma yaratish
    cart = await db.get_cart(message.from_user.id)
    if not cart:
        await message.answer("Savat bo'sh, qaytadan boshlang.", reply_markup=kb.main_menu_kb())
        await state.clear()
        return

    items = []
    for item in cart:
        d = item["details"]
        items.append({
            "type": item["item_type"],
            "id": d["id"],
            "name": d["name"],
            "cover": d.get("cover_type", ""),
            "price": d["discounted_price"],
            "quantity": item["quantity"],
        })

    order_data = {
        "user_id": message.from_user.id,
        "full_name": data.get("full_name", ""),
        "phone": data.get("phone", ""),
        "region": data.get("region", ""),
        "district": data.get("district", ""),
        "btc_point": data.get("btc_point", ""),
        "btc_point_kod": data.get("btc_point_kod"),
        "items": items,
        "total_price": data.get("cart_total", 0),
        "discount_amount": data.get("discount", 0),
        "cashback_used": data.get("cashback_used", 0),
        "final_price": data.get("final_price", 0),
        "payment_method": data.get("payment_method", "UzCard/Humo"),
    }

    order_id = await db.create_order(order_data)
    await db.update_order(order_id, receipt_file_id=file_id)

    # Keshbekni kamaytirish (ishlatilgan bo'lsa)
    if order_data["cashback_used"] > 0:
        await db.deduct_cashback(message.from_user.id, order_data["cashback_used"], order_id)

    # Profilni yangilash (agar yangi user bo'lsa)
    await db.update_user_profile(
        message.from_user.id,
        full_name=order_data["full_name"],
        phone=order_data["phone"],
        region=order_data["region"],
        district=order_data["district"],
        btc_point=order_data["btc_point"],
        btc_point_kod=order_data["btc_point_kod"],
    )

    # Savatni tozalash
    await db.clear_cart(message.from_user.id)

    # Buyurtma ma'lumotlarini olish
    order = await db.get_order(order_id)

    # Google Sheets sync
    try:
        await sheets.sync_new_order(order)
    except Exception as e:
        logger.warning(f"Sheets sync error: {e}")

    # Userga rasmiy javob
    await message.answer(
        f"✅ <b>BUYURTMA QABUL QILINDI!</b>\n\n"
        f"🔢 Buyurtma raqami: <code>{order['order_code']}</code>\n"
        f"💰 Summa: {order['final_price']:,} so'm\n\n"
        f"⏳ To'lovingiz tekshirilmoqda. Tasdiqlanganidan keyin xabar yuboramiz.",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

    # Adminlarga yuborish
    await send_order_to_admins(bot, order, file_id)

    await state.clear()


async def send_order_to_admins(bot: Bot, order: dict, receipt_file_id: str):
    """Yangi buyurtmani adminlarga yuborish"""
    items_text = ""
    for idx, it in enumerate(order["items"], 1):
        cover_label = "Qattiq" if it.get("cover") == "qattiq" else "Yumshoq"
        emoji = "📚" if it["type"] == "product" else "📦"
        subtotal = it["price"] * it["quantity"]
        items_text += f"{idx}. {emoji} {it['name']} ({cover_label}) ×{it['quantity']} — {subtotal:,} so'm\n"

    text = (
        f"🔔 <b>YANGI BUYURTMA! {order['order_code']}</b>\n\n"
        f"👤 {order['full_name']}\n"
        f"📱 {order['phone']}\n"
        f"📍 {order['region']} — {order['district']}\n"
        f"📦 {order['btc_point']}\n\n"
        f"🛒 <b>BUYURTMA:</b>\n{items_text}\n"
        f"💰 Jami: {order['total_price']:,} so'm\n"
    )
    if order["discount_amount"] > 0:
        text += f"🎯 Chegirma: -{order['discount_amount']:,} so'm\n"
    if order["cashback_used"] > 0:
        text += f"💎 Keshbek: -{order['cashback_used']:,} so'm\n"
    text += (
        f"💳 <b>To'langan: {order['final_price']:,} so'm</b>\n"
        f"💳 To'lov usuli: {order['payment_method']}"
    )

    # Admin uchun action keyboardi
    from keyboards.admin_keyboards import order_actions_kb
    keyboard = order_actions_kb(order["id"], order["delivery_status"])

    for admin_id in config.ADMIN_IDS:
        try:
            # Avval chek
            if receipt_file_id:
                try:
                    await bot.send_photo(admin_id, receipt_file_id, caption="📷 Chek")
                except Exception:
                    try:
                        await bot.send_document(admin_id, receipt_file_id, caption="📷 Chek")
                    except Exception as e:
                        logger.error(f"Receipt yuborishda xato: {e}")
            # Buyurtma matni va tugmalar
            await bot.send_message(admin_id, text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Adminga buyurtma yuborishda xato: {e}")

    # Database admin adminlarga ham
    other_admins = await db.get_all_admins()
    for adm in other_admins:
        if adm["telegram_id"] in config.ADMIN_IDS:
            continue
        try:
            if receipt_file_id:
                try:
                    await bot.send_photo(adm["telegram_id"], receipt_file_id, caption="📷 Chek")
                except Exception:
                    try:
                        await bot.send_document(adm["telegram_id"], receipt_file_id, caption="📷 Chek")
                    except Exception:
                        pass
            await bot.send_message(adm["telegram_id"], text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Admin {adm['telegram_id']} ga yuborishda xato: {e}")


@router.message(OrderStates.waiting_receipt)
@router.message(OrderStates.uzum_waiting_receipt)
async def receipt_invalid(message: Message):
    """Boshqa turdagi xabarlar uchun"""
    if message.text and message.text.startswith("/"):
        return  # commandlarga aralashmaymiz
    await message.answer("⚠️ Iltimos, to'lov chekini rasm yoki PDF shaklida yuboring")
