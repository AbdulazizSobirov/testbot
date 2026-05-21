# -*- coding: utf-8 -*-
"""
Admin handlers: Admin paneli to'liq funksionalligi
- Buyurtmalar boshqaruvi (status o'zgartirish)
- Foydalanuvchilar
- Mahsulotlar (CRUD)
- Statistika
- Xabar yuborish
- Sozlamalar
- Adminlar boshqaruvi (super admin)
"""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import queries as db
from keyboards import admin_keyboards as akb
from states.admin_states import (
    ProductStates, EditProductStates, ShipmentStates,
    BroadcastStates, SingleMessageStates, SettingsStates,
    AdminManagementStates, CancelOrderStates
)
from utils.config import config
from utils.sheets import sheets

logger = logging.getLogger(__name__)
router = Router()


# ==================== ADMIN ACCESS DECORATOR ====================

async def check_admin(user_id: int) -> bool:
    return await db.is_admin(user_id)


# ==================== /admin COMMAND ====================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return

    await state.clear()
    is_super = await db.is_superadmin(message.from_user.id)
    await message.answer(
        "👨‍💼 <b>ADMIN PANEL</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=akb.admin_main_kb(is_super=is_super),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_back_main")
@router.callback_query(F.data == "adm_home")
async def cb_admin_home(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    is_super = await db.is_superadmin(callback.from_user.id)
    try:
        await callback.message.edit_text(
            "👨‍💼 <b>ADMIN PANEL</b>\n\nKerakli bo'limni tanlang:",
            reply_markup=akb.admin_main_kb(is_super=is_super),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "👨‍💼 <b>ADMIN PANEL</b>\n\nKerakli bo'limni tanlang:",
            reply_markup=akb.admin_main_kb(is_super=is_super),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "adm_cancel_fsm")
async def cb_adm_cancel_fsm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_super = await db.is_superadmin(callback.from_user.id)
    await callback.message.answer(
        "❌ Bekor qilindi.\n\n👨‍💼 <b>ADMIN PANEL</b>",
        reply_markup=akb.admin_main_kb(is_super=is_super),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== BUYURTMALAR ====================

@router.callback_query(F.data == "adm_orders")
async def cb_adm_orders(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📦 <b>BUYURTMALAR</b>\n\nStatusni tanlang:",
        reply_markup=akb.admin_orders_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("orders_") & F.data.in_({
    "orders_pending", "orders_confirmed", "orders_preparing",
    "orders_shipping", "orders_completed", "orders_cancelled"
}))
async def cb_orders_by_status(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    status_map = {
        "orders_pending": ("pending", "⏳ YANGI BUYURTMALAR"),
        "orders_confirmed": ("confirmed", "✅ TASDIQLANGAN"),
        "orders_preparing": ("preparing", "📦 TAYYORLANMOQDA"),
        "orders_shipping": ("shipping", "🚚 YO'LDA"),
        "orders_completed": ("completed", "✔️ YAKUNLANGAN"),
        "orders_cancelled": ("cancelled", "❌ BEKOR QILINGAN"),
    }
    status, label = status_map[callback.data]
    orders = await db.get_orders_by_status(status)

    if not orders:
        await callback.message.edit_text(
            f"<b>{label}</b>\n\nBu kategoriyada buyurtmalar yo'q.",
            reply_markup=akb.admin_orders_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"<b>{label}</b>\n\nJami: {len(orders)} ta\n\n"
    builder = InlineKeyboardBuilder()
    for o in orders[:15]:
        text += f"• <code>{o['order_code']}</code> — {o['full_name']} — {o['final_price']:,} so'm\n"
        builder.row(InlineKeyboardButton(
            text=f"👁 {o['order_code']}",
            callback_data=f"adm_view_order_{o['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_orders"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_view_order_"))
async def cb_adm_view_order(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    try:
        order_id = int(callback.data.replace("adm_view_order_", ""))
    except ValueError:
        await callback.answer()
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Topilmadi", show_alert=True)
        return

    from handlers.bonus_handlers import format_order_full
    text = format_order_full(order)
    keyboard = akb.order_actions_kb(order["id"], order["delivery_status"])

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ==================== BUYURTMA STATUSINI O'ZGARTIRISH ====================

@router.callback_query(F.data.startswith("ord_confirm_"))
async def cb_confirm_order(callback: CallbackQuery, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return
    try:
        order_id = int(callback.data.replace("ord_confirm_", ""))
    except ValueError:
        await callback.answer()
        return

    await db.update_order(order_id, payment_status="confirmed", delivery_status="confirmed")
    order = await db.get_order(order_id)

    # Userga xabar
    from handlers.bonus_handlers import notify_status_change
    await notify_status_change(bot, order, "confirmed")

    # Adminga - keyboardni yangilash
    try:
        keyboard = akb.order_actions_kb(order["id"], "confirmed")
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass

    # Sheets
    try:
        await sheets.sync_order_status(order["order_code"], "confirmed")
        await sheets.sync_payment(order)
    except Exception as e:
        logger.warning(f"Sheets sync: {e}")

    await callback.answer("✅ Tasdiqlandi va keyingi statusga o'tdi")


@router.callback_query(F.data.startswith("ord_preparing_"))
async def cb_preparing_order(callback: CallbackQuery, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return
    try:
        order_id = int(callback.data.replace("ord_preparing_", ""))
    except ValueError:
        await callback.answer()
        return

    await db.update_order(order_id, delivery_status="preparing")
    order = await db.get_order(order_id)
    # Stockni kamaytirish (faqat product uchun)
    for it in order["items"]:
        if it["type"] == "product":
            await db.decrease_stock(it["id"], it["quantity"])

    from handlers.bonus_handlers import notify_status_change
    await notify_status_change(bot, order, "preparing")

    try:
        keyboard = akb.order_actions_kb(order["id"], "preparing")
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass

    try:
        await sheets.sync_order_status(order["order_code"], "preparing")
    except Exception as e:
        logger.warning(f"Sheets sync: {e}")

    await callback.answer("📦 Tayyorlanmoqda statusiga o'tdi")


@router.callback_query(F.data.startswith("ord_ship_"))
async def cb_ship_order(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    try:
        order_id = int(callback.data.replace("ord_ship_", ""))
    except ValueError:
        await callback.answer()
        return

    await state.set_state(ShipmentStates.waiting_time)
    await state.update_data(order_id=order_id)
    await callback.message.answer(
        "🚚 <b>JO'NATISH</b>\n\n"
        "Yetkazilish taxminiy vaqtini yozing:\n"
        "(Masalan: 2-3 kun ichida, yoki 2026-05-10 gacha)",
        reply_markup=akb.cancel_fsm_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ShipmentStates.waiting_time)
async def process_ship_time(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")
    delivery_time = message.text.strip()

    await db.update_order(
        order_id,
        delivery_status="shipping",
        estimated_delivery=delivery_time
    )
    order = await db.get_order(order_id)

    from handlers.bonus_handlers import notify_status_change
    await notify_status_change(bot, order, "shipping")

    try:
        await sheets.sync_order_status(order["order_code"], "shipping")
    except Exception as e:
        logger.warning(f"Sheets sync: {e}")

    await message.answer(
        f"✅ Jo'natildi va mijozga xabar yetkazildi.\n\nVaqt: {delivery_time}",
    )
    await state.clear()


@router.callback_query(F.data.startswith("ord_delivered_"))
async def cb_delivered_order(callback: CallbackQuery, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return
    try:
        order_id = int(callback.data.replace("ord_delivered_", ""))
    except ValueError:
        await callback.answer()
        return

    await db.update_order(order_id, delivery_status="completed")
    order = await db.get_order(order_id)

    from handlers.bonus_handlers import notify_status_change
    await notify_status_change(bot, order, "completed")

    try:
        keyboard = akb.order_actions_kb(order["id"], "completed")
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass

    try:
        await sheets.sync_order_status(order["order_code"], "completed")
    except Exception as e:
        logger.warning(f"Sheets sync: {e}")

    await callback.answer("✅ Yakunlandi! Bonuslar va keshbek qo'shildi")


@router.callback_query(F.data.startswith("ord_cancel_"))
async def cb_cancel_order(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    try:
        order_id = int(callback.data.replace("ord_cancel_", ""))
    except ValueError:
        await callback.answer()
        return

    await state.set_state(CancelOrderStates.waiting_reason)
    await state.update_data(order_id=order_id)
    await callback.message.answer(
        "❌ <b>BEKOR QILISH</b>\n\nBekor qilish sababini yozing:",
        reply_markup=akb.cancel_fsm_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CancelOrderStates.waiting_reason)
async def process_cancel_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")
    reason = message.text.strip()

    await db.update_order(order_id, delivery_status="cancelled", admin_notes=reason)
    order = await db.get_order(order_id)

    from handlers.bonus_handlers import notify_status_change
    await notify_status_change(bot, order, "cancelled")

    try:
        await sheets.sync_order_status(order["order_code"], "cancelled")
    except Exception as e:
        logger.warning(f"Sheets sync: {e}")

    await message.answer(f"❌ Buyurtma bekor qilindi.\nSabab: {reason}")
    await state.clear()


@router.callback_query(F.data.startswith("ord_msg_"))
async def cb_msg_customer(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    try:
        order_id = int(callback.data.replace("ord_msg_", ""))
    except ValueError:
        await callback.answer()
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer()
        return

    await state.set_state(SingleMessageStates.waiting_message)
    await state.update_data(target_user_id=order["user_id"])
    await callback.message.answer(
        f"✉️ Mijoz <code>{order['full_name']}</code> ga yubormoqchi bo'lgan xabaringizni yozing:",
        reply_markup=akb.cancel_fsm_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== FOYDALANUVCHILAR ====================

@router.callback_query(F.data == "adm_users")
async def cb_adm_users(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "👥 <b>FOYDALANUVCHILAR</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=akb.admin_users_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "users_all")
async def cb_users_all(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    users = await db.get_all_users()
    text = f"📋 <b>BARCHA FOYDALANUVCHILAR</b> ({len(users)} ta)\n\n"

    # Maksimum 20 ta ko'rsatish
    for u in users[:20]:
        username = f"@{u['username']}" if u.get("username") else "—"
        text += f"• {username} | {u.get('full_name') or '—'} — ID: <code>{u['telegram_id']}</code>\n"

    if len(users) > 20:
        text += f"\n... va yana {len(users) - 20} ta foydalanuvchi"

    await callback.message.edit_text(text, reply_markup=akb.back_admin_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "users_top")
async def cb_users_top(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    top = await db.get_top_buyers(10)
    text = "🏆 <b>TOP 10 XARIDORLAR</b>\n\n"
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

    if not top:
        text += "Hozircha xaridorlar yo'q."
    else:
        for i, u in enumerate(top):
            medal = medals[i] if i < len(medals) else "•"
            username = f"@{u['username']}" if u.get("username") else u.get("full_name", "—")
            text += f"{i+1}. {medal} {username} — {u['order_count']} xarid — {u['total_spent']:,} so'm\n"

    await callback.message.edit_text(text, reply_markup=akb.back_admin_kb(), parse_mode="HTML")
    await callback.answer()


# ==================== MAHSULOTLAR (CRUD) ====================

@router.callback_query(F.data == "adm_products")
async def cb_adm_products(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📚 <b>MAHSULOTLAR</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=akb.admin_products_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "prod_books")
async def cb_prod_books(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    qattiq = await db.get_products_by_cover("qattiq")
    yumshoq = await db.get_products_by_cover("yumshoq")

    text = "📗 <b>KITOBLAR — QATTIQ MUQOVA</b>\n\n"
    builder = InlineKeyboardBuilder()
    for p in qattiq:
        text += f"• <b>{p['name']}</b>\n  💰 {p['discounted_price']:,} so'm | 📦 {p['stock']} ta\n\n"
        builder.row(InlineKeyboardButton(
            text=f"✏️ {p['name'][:30]}",
            callback_data=f"prod_edit_{p['id']}"
        ))

    text += "\n📘 <b>KITOBLAR — YUMSHOQ MUQOVA</b>\n\n"
    for p in yumshoq:
        text += f"• <b>{p['name']}</b>\n  💰 {p['discounted_price']:,} so'm | 📦 {p['stock']} ta\n\n"
        builder.row(InlineKeyboardButton(
            text=f"✏️ {p['name'][:30]}",
            callback_data=f"prod_edit_{p['id']}"
        ))

    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_products"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "prod_bundles")
async def cb_prod_bundles(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    qattiq = await db.get_bundles_by_cover("qattiq")
    yumshoq = await db.get_bundles_by_cover("yumshoq")

    text = "📦 <b>TO'PLAMLAR — QATTIQ MUQOVA</b>\n\n"
    builder = InlineKeyboardBuilder()
    for b in qattiq:
        text += f"• <b>{b['name']}</b>\n  💰 {b['discounted_price']:,} so'm\n\n"
        builder.row(InlineKeyboardButton(
            text=f"✏️ {b['name'][:30]}",
            callback_data=f"bundle_edit_{b['id']}"
        ))

    text += "\n📘 <b>TO'PLAMLAR — YUMSHOQ MUQOVA</b>\n\n"
    for b in yumshoq:
        text += f"• <b>{b['name']}</b>\n  💰 {b['discounted_price']:,} so'm\n\n"
        builder.row(InlineKeyboardButton(
            text=f"✏️ {b['name'][:30]}",
            callback_data=f"bundle_edit_{b['id']}"
        ))

    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_products"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("prod_edit_"))
async def cb_prod_edit(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    try:
        pid = int(callback.data.replace("prod_edit_", ""))
    except ValueError:
        await callback.answer()
        return

    p = await db.get_product(pid)
    if not p:
        await callback.answer()
        return

    text = (
        f"📚 <b>{p['name']}</b>\n\n"
        f"💰 Narx: {p['discounted_price']:,} so'm (asl: {p['original_price']:,})\n"
        f"📦 Stok: {p['stock']} ta\n"
        f"🎨 Muqova: {p['cover_type']}\n\n"
        f"Nima qilmoqchisiz?"
    )
    await callback.message.edit_text(text, reply_markup=akb.product_edit_kb(pid, "product"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("bundle_edit_"))
async def cb_bundle_edit(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    try:
        bid = int(callback.data.replace("bundle_edit_", ""))
    except ValueError:
        await callback.answer()
        return

    b = await db.get_bundle(bid)
    if not b:
        await callback.answer()
        return

    text = (
        f"📦 <b>{b['name']}</b>\n\n"
        f"💰 Narx: {b['discounted_price']:,} so'm (asl: {b['original_price']:,})\n"
        f"🎨 Muqova: {b['cover_type']}\n\n"
        f"Nima qilmoqchisiz?"
    )
    await callback.message.edit_text(text, reply_markup=akb.product_edit_kb(bid, "bundle"), parse_mode="HTML")
    await callback.answer()


# Narxni o'zgartirish
@router.callback_query(F.data.startswith("pedit_price_"))
async def cb_pedit_price(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.replace("pedit_price_", ""))
    await state.set_state(EditProductStates.waiting_price)
    await state.update_data(product_id=pid, item_type="product")
    await callback.message.answer(
        "💰 Yangi narxni kiriting:\nFormat: asl_narx chegirma_narx\n(Masalan: 500000 340000)",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bedit_price_"))
async def cb_bedit_price(callback: CallbackQuery, state: FSMContext):
    bid = int(callback.data.replace("bedit_price_", ""))
    await state.set_state(EditProductStates.waiting_price)
    await state.update_data(product_id=bid, item_type="bundle")
    await callback.message.answer(
        "💰 Yangi narxni kiriting:\nFormat: asl_narx chegirma_narx\n(Masalan: 1230000 860000)",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.message(EditProductStates.waiting_price)
async def process_edit_price(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer("⚠️ Format: asl_narx chegirma_narx\n(Masalan: 500000 340000)")
        return

    orig, disc = int(parts[0]), int(parts[1])
    if disc > orig:
        await message.answer("⚠️ Chegirma narxi asl narxdan kichik bo'lishi kerak")
        return

    data = await state.get_data()
    if data["item_type"] == "product":
        await db.update_product(data["product_id"], original_price=orig, discounted_price=disc)
    else:
        await db.update_bundle(data["product_id"], original_price=orig, discounted_price=disc)

    await message.answer(f"✅ Narx yangilandi: {orig:,} → {disc:,} so'm")
    await state.clear()


# Stokni o'zgartirish
@router.callback_query(F.data.startswith("pedit_stock_"))
async def cb_pedit_stock(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.replace("pedit_stock_", ""))
    await state.set_state(EditProductStates.waiting_stock)
    await state.update_data(product_id=pid)
    await callback.message.answer(
        "📦 Yangi stok sonini kiriting (raqam):",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.message(EditProductStates.waiting_stock)
async def process_edit_stock(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, raqam kiriting")
        return
    stock = int(message.text.strip())
    data = await state.get_data()
    await db.update_product(data["product_id"], stock=stock)
    await message.answer(f"✅ Stok yangilandi: {stock} ta")
    await state.clear()


# Media o'zgartirish
@router.callback_query(F.data.startswith("pedit_media_"))
async def cb_pedit_media(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.replace("pedit_media_", ""))
    await state.set_state(EditProductStates.waiting_media)
    await state.update_data(product_id=pid, item_type="product")
    await callback.message.answer(
        "🖼 Yangi rasm yoki video yuboring:",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bedit_media_"))
async def cb_bedit_media(callback: CallbackQuery, state: FSMContext):
    bid = int(callback.data.replace("bedit_media_", ""))
    await state.set_state(EditProductStates.waiting_media)
    await state.update_data(product_id=bid, item_type="bundle")
    await callback.message.answer(
        "🖼 Yangi rasm yoki video yuboring:",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.message(EditProductStates.waiting_media, F.photo | F.video)
async def process_edit_media(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    else:
        file_id = message.video.file_id
        media_type = "video"

    if data["item_type"] == "product":
        await db.update_product(data["product_id"], media_file_id=file_id, media_type=media_type)
    else:
        await db.update_bundle(data["product_id"], media_file_id=file_id, media_type=media_type)

    await message.answer(f"✅ Media yangilandi! ({media_type})")
    await state.clear()


# ==================== YANGI MAHSULOT QO'SHISH (FSM) ====================

@router.callback_query(F.data == "prod_add")
async def cb_prod_add(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    await state.set_state(ProductStates.name)
    await callback.message.answer(
        "➕ <b>YANGI MAHSULOT QO'SHISH</b>\n\n"
        "Mahsulot nomini kiriting:",
        reply_markup=akb.cancel_fsm_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ProductStates.name)
async def process_new_prod_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductStates.category)
    await message.answer("Kategoriyani tanlang:", reply_markup=akb.category_choice_kb())


@router.callback_query(ProductStates.category, F.data.in_({"cat_book", "cat_bundle"}))
async def cb_new_prod_cat(callback: CallbackQuery, state: FSMContext):
    cat = "book" if callback.data == "cat_book" else "bundle"
    await state.update_data(category=cat)
    await state.set_state(ProductStates.cover_type)
    await callback.message.answer("Muqova turini tanlang:", reply_markup=akb.cover_choice_kb())
    await callback.answer()


@router.callback_query(ProductStates.cover_type, F.data.in_({"cov_qattiq", "cov_yumshoq"}))
async def cb_new_prod_cover(callback: CallbackQuery, state: FSMContext):
    cover = "qattiq" if callback.data == "cov_qattiq" else "yumshoq"
    await state.update_data(cover_type=cover)
    await state.set_state(ProductStates.original_price)
    await callback.message.answer("Asl narxni kiriting (faqat raqam):", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


@router.message(ProductStates.original_price)
async def process_new_prod_orig(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Faqat raqam kiriting")
        return
    await state.update_data(original_price=int(message.text.strip()))
    await state.set_state(ProductStates.discounted_price)
    await message.answer("Chegirma narxini kiriting (faqat raqam):", reply_markup=akb.cancel_fsm_kb())


@router.message(ProductStates.discounted_price)
async def process_new_prod_disc(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Faqat raqam kiriting")
        return
    await state.update_data(discounted_price=int(message.text.strip()))

    data = await state.get_data()
    if data["category"] == "book":
        await state.set_state(ProductStates.stock)
        await message.answer("Stok sonini kiriting:", reply_markup=akb.cancel_fsm_kb())
    else:
        # Bundle uchun stok yo'q - to'g'ridan media
        await state.set_state(ProductStates.media)
        await message.answer("Rasm yoki video yuboring (yoki /skip):", reply_markup=akb.cancel_fsm_kb())


@router.message(ProductStates.stock)
async def process_new_prod_stock(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Faqat raqam kiriting")
        return
    await state.update_data(stock=int(message.text.strip()))
    await state.set_state(ProductStates.media)
    await message.answer("Rasm yoki video yuboring (yoki /skip):", reply_markup=akb.cancel_fsm_kb())


@router.message(ProductStates.media, F.photo | F.video)
async def process_new_prod_media(message: Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    else:
        file_id = message.video.file_id
        media_type = "video"
    await state.update_data(media_file_id=file_id, media_type=media_type)
    await finalize_new_product(message, state)


@router.message(ProductStates.media, Command("skip"))
async def process_new_prod_media_skip(message: Message, state: FSMContext):
    await state.update_data(media_file_id=None, media_type="photo")
    await finalize_new_product(message, state)


async def finalize_new_product(message: Message, state: FSMContext):
    data = await state.get_data()
    if data["category"] == "book":
        pid = await db.insert_product(
            name=data["name"],
            category="book",
            cover_type=data["cover_type"],
            original_price=data["original_price"],
            discounted_price=data["discounted_price"],
            stock=data["stock"],
            media_file_id=data.get("media_file_id"),
            media_type=data.get("media_type", "photo"),
        )
        await message.answer(f"✅ Kitob qo'shildi (ID: {pid})\n📚 {data['name']}")
    else:
        # Bundle uchun
        from database.queries import config as cfg
        import aiosqlite
        async with aiosqlite.connect(cfg.DB_PATH) as ddb:
            cur = await ddb.execute(
                """INSERT INTO bundles (name, cover_type, original_price, discounted_price, media_file_id, media_type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (data["name"], data["cover_type"], data["original_price"], data["discounted_price"],
                 data.get("media_file_id"), data.get("media_type", "video"))
            )
            await ddb.commit()
            bid = cur.lastrowid
        await message.answer(f"✅ To'plam qo'shildi (ID: {bid})\n📦 {data['name']}")
    await state.clear()


# ==================== STATISTIKA ====================

@router.callback_query(F.data == "adm_stats")
async def cb_adm_stats(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    stats = await db.get_statistics()
    text = (
        "📊 <b>STATISTIKA</b>\n\n"
        f"👥 Umumiy foydalanuvchilar: <b>{stats['total_users']:,}</b> ta\n"
        f"🛒 Xarid qilganlar: <b>{stats['buyers']:,}</b> ta\n"
        f"👥 Referal orqali kelganlar: <b>{stats['referrals']:,}</b> ta\n"
        f"📦 Jami buyurtmalar: <b>{stats['total_orders']:,}</b> ta\n"
        f"💰 Jami daromad: <b>{stats['total_revenue']:,}</b> so'm"
    )
    await callback.message.edit_text(text, reply_markup=akb.back_admin_kb(), parse_mode="HTML")
    await callback.answer()


# ==================== XABAR YUBORISH ====================

@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "✉️ <b>XABAR YUBORISH</b>\n\nKerakli turni tanlang:",
        reply_markup=akb.admin_broadcast_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "bc_all")
async def cb_bc_all(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_message)
    await callback.message.answer(
        "📢 Hammaga yubormoqchi bo'lgan xabarni yozing (matn, rasm, video):",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    users = await db.get_all_users()
    sent, failed = 0, 0

    await message.answer(f"📤 Yuborilmoqda... ({len(users)} ta foydalanuvchi)")

    for u in users:
        try:
            if message.photo:
                await bot.send_photo(u["telegram_id"], message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await bot.send_video(u["telegram_id"], message.video.file_id, caption=message.caption or "")
            elif message.text:
                await bot.send_message(u["telegram_id"], message.text)
            else:
                await bot.copy_message(u["telegram_id"], message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"✅ Yuborildi: {sent}\n❌ Yetkazib bo'lmadi: {failed}")
    await state.clear()


@router.callback_query(F.data == "bc_one")
async def cb_bc_one(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SingleMessageStates.waiting_user_id)
    await callback.message.answer(
        "👤 Mijozning Telegram ID raqamini kiriting:",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.message(SingleMessageStates.waiting_user_id)
async def process_one_user_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Faqat raqam kiriting")
        return
    target_id = int(text)
    user = await db.get_user(target_id)
    if not user:
        await message.answer("⚠️ Bunday ID bilan foydalanuvchi topilmadi")
        return

    await state.update_data(target_user_id=target_id)
    await state.set_state(SingleMessageStates.waiting_message)
    await message.answer(f"✅ {user.get('full_name') or '@'+user.get('username','—')} ga xabaringizni yozing:")


@router.message(SingleMessageStates.waiting_message)
async def process_one_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_id = data.get("target_user_id")
    try:
        if message.photo:
            await bot.send_photo(target_id, message.photo[-1].file_id, caption=message.caption or "")
        elif message.video:
            await bot.send_video(target_id, message.video.file_id, caption=message.caption or "")
        elif message.text:
            await bot.send_message(target_id, message.text)
        else:
            await bot.copy_message(target_id, message.chat.id, message.message_id)
        await message.answer("✅ Yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Yuborib bo'lmadi: {e}")
    await state.clear()


# ==================== ADMIN REPLY TO USER ====================

@router.callback_query(F.data.startswith("admin_reply_"))
async def cb_admin_reply(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    try:
        target_id = int(callback.data.replace("admin_reply_", ""))
    except ValueError:
        await callback.answer()
        return
    await state.set_state(SingleMessageStates.waiting_message)
    await state.update_data(target_user_id=target_id)
    await callback.message.answer(f"↩️ Mijozga javobingizni yozing:", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


# ==================== SOZLAMALAR ====================

@router.callback_query(F.data == "adm_settings")
async def cb_adm_settings(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "⚙️ <b>SOZLAMALAR</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=akb.admin_settings_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_channels")
async def cb_set_channels(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    ch1 = await db.get_setting("channel_1_id") or "—"
    ch2 = await db.get_setting("channel_2_id") or "—"
    text = (
        f"📢 <b>TELEGRAM KANALLAR</b>\n\n"
        f"Kanal 1: <code>{ch1}</code>\n"
        f"Kanal 2: <code>{ch2}</code>"
    )
    await callback.message.edit_text(text, reply_markup=akb.admin_settings_channels_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "ch1_edit")
async def cb_ch1_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_channel_1)
    await callback.message.answer("Yangi Kanal 1 ID/usernamini kiriting (@username yoki -100...):", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


@router.message(SettingsStates.waiting_channel_1)
async def process_ch1(message: Message, state: FSMContext):
    await db.set_setting("channel_1_id", message.text.strip())
    await message.answer("✅ Kanal 1 yangilandi")
    await state.clear()


@router.callback_query(F.data == "ch2_edit")
async def cb_ch2_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_channel_2)
    await callback.message.answer("Yangi Kanal 2 ID/usernamini kiriting:", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


@router.message(SettingsStates.waiting_channel_2)
async def process_ch2(message: Message, state: FSMContext):
    await db.set_setting("channel_2_id", message.text.strip())
    await message.answer("✅ Kanal 2 yangilandi")
    await state.clear()


@router.callback_query(F.data == "set_uzum")
async def cb_set_uzum(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛍️ <b>UZUM NASIYA SOZLAMALARI</b>",
        reply_markup=akb.admin_settings_uzum_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "uzum_qr_set")
async def cb_uzum_qr_set(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_uzum_qr)
    await callback.message.answer("📱 Yangi QR kodi rasmini yuboring:", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


@router.message(SettingsStates.waiting_uzum_qr, F.photo)
async def process_uzum_qr(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await db.set_setting("uzum_qr_file_id", file_id)
    await message.answer("✅ QR kod yangilandi")
    await state.clear()


@router.callback_query(F.data == "uzum_video_set")
async def cb_uzum_video_set(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_uzum_video)
    await callback.message.answer("🎬 Yangi video yo'riqnomani yuboring:", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


@router.message(SettingsStates.waiting_uzum_video, F.video)
async def process_uzum_video(message: Message, state: FSMContext):
    file_id = message.video.file_id
    await db.set_setting("uzum_video_file_id", file_id)
    await message.answer("✅ Video yangilandi")
    await state.clear()


@router.callback_query(F.data == "set_docs")
async def cb_set_docs(callback: CallbackQuery):
    await callback.message.edit_text(
        "📄 <b>RASMIY HUJJATLAR SOZLAMALARI</b>",
        reply_markup=akb.admin_settings_docs_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "doc_copyright_set")
async def cb_doc_copyright_set(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_copyright_doc)
    await callback.message.answer("📋 Yangi mualliflik huquqi hujjatini yuboring (PDF):", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


@router.message(SettingsStates.waiting_copyright_doc, F.document)
async def process_doc_copyright(message: Message, state: FSMContext):
    await db.set_setting("doc_copyright_file_id", message.document.file_id)
    await message.answer("✅ Hujjat yangilandi")
    await state.clear()


@router.callback_query(F.data == "doc_license_set")
async def cb_doc_license_set(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_license_doc)
    await callback.message.answer("📋 Yangi litsenziya hujjatini yuboring (PDF):", reply_markup=akb.cancel_fsm_kb())
    await callback.answer()


@router.message(SettingsStates.waiting_license_doc, F.document)
async def process_doc_license(message: Message, state: FSMContext):
    await db.set_setting("doc_license_file_id", message.document.file_id)
    await message.answer("✅ Hujjat yangilandi")
    await state.clear()


@router.callback_query(F.data == "set_prices")
async def cb_set_prices(callback: CallbackQuery):
    text = (
        "💰 <b>NARX VA CHEGIRMALAR</b>\n\n"
        f"📚 Kitob chegirmasi: <b>{config.DISCOUNT_BOOK}%</b>\n"
        f"📦 To'plam chegirmasi: <b>{config.DISCOUNT_BUNDLE}%</b>\n"
        f"💎 Premium chegirmasi: <b>{config.DISCOUNT_PREMIUM}%</b>\n"
        f"👥 Referal keshbeki: <b>{config.REFERRAL_CASHBACK}%</b>\n\n"
        "Narxlarni o'zgartirish uchun har bir mahsulot sahifasidan amalga oshiring."
    )
    await callback.message.edit_text(text, reply_markup=akb.back_admin_kb(), parse_mode="HTML")
    await callback.answer()


# ==================== ADMIN BOSHQARUVI ====================

@router.callback_query(F.data == "adm_admins")
async def cb_adm_admins(callback: CallbackQuery):
    if not await db.is_superadmin(callback.from_user.id):
        await callback.answer("⛔ Faqat super admin", show_alert=True)
        return
    await callback.message.edit_text(
        "👥 <b>ADMINLAR BOSHQARUVI</b>",
        reply_markup=akb.admin_admins_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "adm_list")
async def cb_adm_list(callback: CallbackQuery):
    if not await db.is_superadmin(callback.from_user.id):
        return
    admins = await db.get_all_admins()
    text = "📋 <b>ADMINLAR RO'YXATI</b>\n\n"
    builder = InlineKeyboardBuilder()
    for a in admins:
        role = "👑" if a["role"] == "superadmin" else "👤"
        text += f"{role} <code>{a['telegram_id']}</code> @{a['username'] or '—'}\n"
        if a["role"] != "superadmin":
            builder.row(InlineKeyboardButton(
                text=f"❌ {a['telegram_id']} ni o'chirish",
                callback_data=f"adm_del_{a['telegram_id']}"
            ))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_admins"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_"))
async def cb_adm_del(callback: CallbackQuery):
    if not await db.is_superadmin(callback.from_user.id):
        return
    try:
        target = int(callback.data.replace("adm_del_", ""))
    except ValueError:
        await callback.answer()
        return
    await db.remove_admin(target)
    await callback.answer("✅ Admin o'chirildi", show_alert=True)
    # Ro'yxatni qayta yuklash
    await cb_adm_list(callback)


@router.callback_query(F.data == "adm_add")
async def cb_adm_add(callback: CallbackQuery, state: FSMContext):
    if not await db.is_superadmin(callback.from_user.id):
        return
    await state.set_state(AdminManagementStates.waiting_admin_id)
    await callback.message.answer(
        "➕ Yangi admin Telegram ID raqamini kiriting:",
        reply_markup=akb.cancel_fsm_kb()
    )
    await callback.answer()


@router.message(AdminManagementStates.waiting_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Faqat raqam kiriting")
        return
    target_id = int(text)
    target = await db.get_user(target_id)
    username = target["username"] if target else ""

    await state.update_data(
        target_id=target_id,
        target_username=username,
        permissions={
            "can_confirm_orders": 1,
            "can_manage_users": 0,
            "can_edit_products": 0,
            "can_broadcast": 0,
            "can_manage_settings": 0,
        }
    )
    await state.set_state(AdminManagementStates.waiting_permissions)
    data = await state.get_data()
    await message.answer(
        f"👤 ID: <code>{target_id}</code> @{username or '—'}\n\n"
        "Quyidagi ruxsatlarni belgilang (toggle):",
        reply_markup=akb.admin_permissions_kb(data["permissions"]),
        parse_mode="HTML"
    )


@router.callback_query(AdminManagementStates.waiting_permissions, F.data.startswith("perm_"))
async def cb_toggle_perm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    perms = data["permissions"]

    if callback.data == "perm_save":
        await db.add_admin(
            telegram_id=data["target_id"],
            username=data["target_username"],
            added_by=callback.from_user.id,
            **perms
        )
        await callback.message.answer(f"✅ Admin qo'shildi: <code>{data['target_id']}</code>", parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return

    if callback.data == "perm_cancel":
        await state.clear()
        await callback.message.answer("❌ Bekor qilindi")
        await callback.answer()
        return

    key_map = {
        "perm_orders": "can_confirm_orders",
        "perm_users": "can_manage_users",
        "perm_products": "can_edit_products",
        "perm_broadcast": "can_broadcast",
        "perm_settings": "can_manage_settings",
    }
    k = key_map.get(callback.data)
    if k:
        perms[k] = 1 - perms[k]
        await state.update_data(permissions=perms)
        await callback.message.edit_reply_markup(reply_markup=akb.admin_permissions_kb(perms))
    await callback.answer()
