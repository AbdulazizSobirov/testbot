# -*- coding: utf-8 -*-
"""
Order handlers: Buyurtmani rasmiylashtirish to'liq FSM jarayoni
Qadamlar: Ism → Telefon → Viloyat → Tuman → BTC punkt → Keshbek → Tasdiqlash → To'lov
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from database import queries as db
from keyboards import user_keyboards as kb
from keyboards.user_keyboards import phone_request_kb
from states.user_states import OrderStates, ProfileStates
from utils.config import config
from utils.bonus import calculate_discount, calculate_total
from utils.sheets import sheets
from utils.btc_parser import (
    get_btc_points, get_point_by_kod, get_nearest_points,
    format_point, format_point_short
)
from data.regions import REGIONS

logger = logging.getLogger(__name__)
router = Router()


# ==================== RASMIYLASHTIRISH BOSHLANISH ====================

@router.callback_query(F.data == "checkout")
async def cb_checkout(callback: CallbackQuery, state: FSMContext):
    """Savatdan rasmiylashtirishga o'tish"""
    cart = await db.get_cart(callback.from_user.id)
    if not cart:
        await callback.answer("Savat bo'sh!", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)

    # Avval ism kiritilganmi?
    if user and user.get("full_name"):
        # Profili to'liq → to'g'ridan tasdiqlash bosqichiga
        await state.update_data(
            full_name=user["full_name"],
            phone=user["phone"],
            region=user["region"],
            district=user["district"],
            btc_point=user["btc_point"],
            btc_point_kod=user.get("btc_point_kod"),
        )
        if user.get("region") and user.get("district") and user.get("btc_point"):
            await go_to_cashback_choice(callback.message, state, callback.from_user.id)
            await callback.answer()
            return

    # Yo'q bo'lsa - boshidan boshlash
    await state.set_state(OrderStates.full_name)
    await callback.message.answer(
        "📋 <b>RASMIYLASHTIRISH (1/4)</b>\n\n"
        "Ism va Familyangizni kiriting:\n"
        "(Masalan: Abdulaziz Karimov)\n\n"
        "⚠️ 2 ta so'z bo'lishi shart!",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(OrderStates.full_name)
async def process_full_name(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    parts = text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Iltimos, 2 ta so'z kiriting (Ism va Familya)")
        return

    await state.update_data(full_name=text)
    await state.set_state(OrderStates.phone)
    await message.answer(
        "📋 <b>RASMIYLASHTIRISH (2/4)</b>\n\n"
        "📱 Telefon raqamingizni kiriting:\n"
        "(Masalan: +998901234567)",
        reply_markup=phone_request_kb(),
        parse_mode="HTML"
    )


@router.message(OrderStates.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await message.answer(
        "✅ Telefon qabul qilindi",
        reply_markup=ReplyKeyboardRemove()
    )
    await go_to_region(message, state)


@router.message(OrderStates.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.main_menu_kb())
        return

    digits = "".join(c for c in text if c.isdigit())
    if len(digits) < 9:
        await message.answer("⚠️ Iltimos, to'g'ri telefon raqam kiriting:\n(Masalan: +998901234567)")
        return
    if not text.startswith("+"):
        text = "+" + digits
    await state.update_data(phone=text)
    await message.answer("✅ Telefon qabul qilindi", reply_markup=ReplyKeyboardRemove())
    await go_to_region(message, state)


async def go_to_region(message: Message, state: FSMContext):
    """Viloyat tanlash bosqichi"""
    await state.set_state(OrderStates.region)
    await message.answer(
        "📋 <b>RASMIYLASHTIRISH (3/4)</b>\n\n"
        "📍 Viloyatingizni tanlang:",
        reply_markup=kb.regions_kb(),
        parse_mode="HTML"
    )


# ==================== VILOYAT TANLASH ====================

@router.callback_query(OrderStates.region, F.data.startswith("region_"))
@router.callback_query(ProfileStates.edit_region, F.data.startswith("region_"))
async def cb_select_region(callback: CallbackQuery, state: FSMContext):
    try:
        idx = int(callback.data.replace("region_", ""))
    except ValueError:
        await callback.answer()
        return

    regions = list(REGIONS.keys())
    if idx >= len(regions):
        await callback.answer("Xato")
        return

    region = regions[idx]
    await state.update_data(region=region)

    # Edit mode uchun
    data = await state.get_data()
    is_edit_mode = data.get("edit_mode") == "address"

    await state.set_state(OrderStates.district if not is_edit_mode else ProfileStates.edit_district)

    text = (
        f"📋 <b>{'MANZIL TAHRIRLASH' if is_edit_mode else 'RASMIYLASHTIRISH (3/4)'}</b>\n\n"
        f"📍 Viloyat: <b>{region}</b>\n\n"
        f"🏘️ Tumanni tanlang:"
    )
    await callback.message.edit_text(text, reply_markup=kb.districts_kb(region), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back_region")
async def cb_back_region(callback: CallbackQuery, state: FSMContext):
    """Tumandan viloyatga qaytish"""
    cur_state = await state.get_state()
    if cur_state in (OrderStates.district.state, OrderStates.btc_point.state):
        await state.set_state(OrderStates.region)
        title = "RASMIYLASHTIRISH (3/4)"
    else:
        await state.set_state(ProfileStates.edit_region)
        title = "MANZIL TAHRIRLASH"

    await callback.message.edit_text(
        f"📋 <b>{title}</b>\n\n📍 Viloyatingizni tanlang:",
        reply_markup=kb.regions_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== TUMAN TANLASH ====================

@router.callback_query(OrderStates.district, F.data.startswith("district_"))
@router.callback_query(ProfileStates.edit_district, F.data.startswith("district_"))
async def cb_select_district(callback: CallbackQuery, state: FSMContext):
    try:
        idx = int(callback.data.replace("district_", ""))
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    region = data.get("region")
    if not region:
        await callback.answer("Avval viloyat tanlang")
        return

    districts = REGIONS.get(region, [])
    if idx >= len(districts):
        await callback.answer("Xato")
        return

    district = districts[idx]
    await state.update_data(district=district)

    # BTS punkt tanlash bosqichiga
    is_edit_mode = data.get("edit_mode") == "address"
    await state.set_state(OrderStates.btc_point if not is_edit_mode else ProfileStates.edit_btc_point)

    points = get_btc_points(region, district)

    if not points:
        await callback.message.edit_text(
            f"⚠️ <b>{region} — {district}</b>\n\n"
            f"Bu tumanda BTC punkt topilmadi. Iltimos boshqa tumanni tanlang.",
            reply_markup=kb.districts_kb(region),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = build_btc_list_text(region, district, points)
    await callback.message.edit_text(text, reply_markup=kb.btc_points_kb(region, district), parse_mode="HTML")
    await callback.answer()


def build_btc_list_text(region: str, district: str, points: list) -> str:
    text = f"📦 <b>{region.upper()} — {district.upper()}</b>\n"
    text += "BTC PUNKTLARI:\n\n"
    digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for idx, p in enumerate(points, 1):
        emoji = digits[idx-1] if idx <= 10 else f"{idx}."
        text += f"{emoji} <b>{p['nomi']}</b>\n   📍 {p['manzil']}\n   🎯 {p['moljal']}\n\n"
    text += "⬇️ Pastdagi raqamli tugmalardan tanlang yoki lokatsiyangizni yuboring"
    return text


@router.callback_query(F.data == "back_district")
async def cb_back_district(callback: CallbackQuery, state: FSMContext):
    """BTC ro'yxatidan tumanga qaytish"""
    data = await state.get_data()
    region = data.get("region")
    if not region:
        await callback.answer()
        return

    cur_state = await state.get_state()
    is_edit_mode = data.get("edit_mode") == "address"
    if is_edit_mode:
        await state.set_state(ProfileStates.edit_district)
        title = "MANZIL TAHRIRLASH"
    else:
        await state.set_state(OrderStates.district)
        title = "RASMIYLASHTIRISH (3/4)"

    text = (
        f"📋 <b>{title}</b>\n\n"
        f"📍 Viloyat: <b>{region}</b>\n\n"
        f"🏘️ Tumanni tanlang:"
    )
    await callback.message.edit_text(text, reply_markup=kb.districts_kb(region), parse_mode="HTML")
    await callback.answer()


# ==================== BTS PUNKT TANLASH ====================

@router.callback_query(F.data.startswith("btc_"))
async def cb_select_btc(callback: CallbackQuery, state: FSMContext):
    """BTC punkt detalini ko'rsatish + xaritada ko'rish tugmalari"""
    try:
        kod = int(callback.data.replace("btc_", ""))
    except ValueError:
        await callback.answer()
        return

    point = get_point_by_kod(kod)
    if not point:
        await callback.answer("Punkt topilmadi", show_alert=True)
        return

    text = (
        f"📦 <b>{point['nomi']}</b>\n\n"
        f"📍 <b>Manzil:</b> {point['manzil']}\n"
        f"🎯 <b>Mo'ljal:</b> {point['moljal']}\n"
        f"🕐 <b>Ish vaqti:</b> {point['ish_vaqti']}\n"
        f"📞 <b>Telefon:</b> {point['telefon']}\n\n"
        f"Xaritada ko'rish uchun pastdagi tugmalardan birini bosing,\n"
        f"yoki shu punktni tanlash uchun ✅ tugmasini bosing:"
    )

    await callback.message.edit_text(text, reply_markup=kb.btc_point_view_kb(kod), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("map_g_"))
async def cb_show_google_map(callback: CallbackQuery):
    """Google Maps linkini yuborish"""
    try:
        kod = int(callback.data.replace("map_g_", ""))
    except ValueError:
        await callback.answer()
        return

    point = get_point_by_kod(kod)
    if not point:
        await callback.answer("Topilmadi")
        return

    # Telegram location yuborish - bosilganda xaritada ochiladi
    await callback.message.answer_location(
        latitude=point["lat"],
        longitude=point["lon"]
    )
    # Bonus: link ham yuborish
    await callback.message.answer(
        f"🗺 <b>{point['nomi']}</b>\n\n"
        f"📍 {point['manzil']}\n\n"
        f"<a href='{point['google_maps']}'>🌐 Google Maps da ochish</a>",
        parse_mode="HTML",
        disable_web_page_preview=False
    )
    await callback.answer()


@router.callback_query(F.data.startswith("map_y_"))
async def cb_show_yandex_map(callback: CallbackQuery):
    """Yandex Maps linkini yuborish"""
    try:
        kod = int(callback.data.replace("map_y_", ""))
    except ValueError:
        await callback.answer()
        return

    point = get_point_by_kod(kod)
    if not point:
        await callback.answer("Topilmadi")
        return

    await callback.message.answer_location(latitude=point["lat"], longitude=point["lon"])
    await callback.message.answer(
        f"🗺 <b>{point['nomi']}</b>\n\n"
        f"📍 {point['manzil']}\n\n"
        f"<a href='{point['yandex_maps']}'>🌐 Yandex Maps da ochish</a>",
        parse_mode="HTML",
        disable_web_page_preview=False
    )
    await callback.answer()


@router.callback_query(F.data == "back_btc_list")
async def cb_back_btc_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    region = data.get("region")
    district = data.get("district")
    if not region or not district:
        await callback.answer()
        return

    points = get_btc_points(region, district)
    text = build_btc_list_text(region, district, points)
    await callback.message.edit_text(text, reply_markup=kb.btc_points_kb(region, district), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_btc_"))
async def cb_confirm_btc(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Punktni tanlash va keyingi bosqichga o'tish"""
    try:
        kod = int(callback.data.replace("confirm_btc_", ""))
    except ValueError:
        await callback.answer()
        return

    point = get_point_by_kod(kod)
    if not point:
        await callback.answer("Punkt topilmadi", show_alert=True)
        return

    btc_label = f"{point['nomi']} — {point['manzil']}"
    await state.update_data(btc_point=btc_label, btc_point_kod=kod)

    data = await state.get_data()
    is_edit_mode = data.get("edit_mode") == "address"

    if is_edit_mode:
        # Profil tahrirlash - saqlash
        await db.update_user_profile(
            callback.from_user.id,
            region=data["region"],
            district=data["district"],
            btc_point=btc_label,
            btc_point_kod=kod,
        )
        await state.clear()
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            f"✅ Manzil yangilandi!\n\n"
            f"📍 {data['region']}\n"
            f"🏘️ {data['district']}\n"
            f"📦 {point['nomi']}",
            reply_markup=kb.main_menu_kb()
        )
        await callback.answer()
        return

    # Buyurtma rasmiylashtirish - keshbek bosqichiga
    await go_to_cashback_choice(callback.message, state, callback.from_user.id)
    await callback.answer()


# ==================== LOKATSIYA YUBORISH ====================

@router.callback_query(F.data == "send_location")
async def cb_request_location(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📍 Lokatsiyangizni yuboring, men sizga eng yaqin 3 ta BTC punktni topib beraman:",
        reply_markup=kb.location_request_kb()
    )
    await callback.answer()


@router.message(OrderStates.btc_point, F.location)
@router.message(ProfileStates.edit_btc_point, F.location)
async def process_location(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude

    nearest = get_nearest_points(lat, lon, 3)
    if not nearest:
        await message.answer("Yaqin punktlar topilmadi", reply_markup=ReplyKeyboardRemove())
        return

    await message.answer("Eng yaqin punktlar:", reply_markup=ReplyKeyboardRemove())

    text = "🎯 <b>Sizga eng yaqin BTC punktlar:</b>\n\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for i, (dist, p) in enumerate(nearest, 1):
        text += (
            f"<b>{i}. {p['nomi']}</b> ({dist} km)\n"
            f"   📍 {p['manzil']}\n"
            f"   🎯 {p['moljal']}\n\n"
        )
        builder.row(InlineKeyboardButton(
            text=f"{i}. {p['nomi']} ({dist} km)",
            callback_data=f"btc_{p['kod']}"
        ))

    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_district"))
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ==================== KESHBEK TANLOV ====================

async def go_to_cashback_choice(message: Message, state: FSMContext, user_id: int):
    """Keshbek bor bo'lsa - ishlatish/skip"""
    balance = await db.get_user_cashback(user_id)

    if balance <= 0:
        # Keshbek yo'q → to'g'ridan tasdiqlashga
        await state.update_data(cashback_used=0)
        await show_confirm_order(message, state, user_id)
        return

    await state.set_state(OrderStates.cashback_choice)
    await message.answer(
        f"💰 <b>KESHBEK BALANSINGIZ</b>\n\n"
        f"Sizda <b>{balance:,} so'm</b> keshbek bor.\n\n"
        f"Foydalanasizmi?",
        reply_markup=kb.cashback_choice_kb(balance),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "use_cashback")
async def cb_use_cashback(callback: CallbackQuery, state: FSMContext):
    balance = await db.get_user_cashback(callback.from_user.id)
    cart = await db.get_cart(callback.from_user.id)
    cart_total = calculate_total(cart)
    discount = calculate_discount(cart)

    # Maksimal foydalanish mumkin bo'lgan keshbek
    max_use = min(balance, cart_total - discount)
    await state.update_data(cashback_used=max_use)
    await show_confirm_order(callback.message, state, callback.from_user.id)
    await callback.answer(f"✅ {max_use:,} so'm keshbek ishlatiladi")


@router.callback_query(F.data == "skip_cashback")
async def cb_skip_cashback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cashback_used=0)
    await show_confirm_order(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "back_confirm")
async def cb_back_confirm(callback: CallbackQuery, state: FSMContext):
    await show_confirm_order(callback.message, state, callback.from_user.id)
    await callback.answer()


# ==================== TASDIQLASH ====================

async def show_confirm_order(message: Message, state: FSMContext, user_id: int):
    """Buyurtma ma'lumotlarini tasdiqlash uchun ko'rsatish"""
    data = await state.get_data()
    cart = await db.get_cart(user_id)
    cart_total = calculate_total(cart)
    discount = calculate_discount(cart)
    cashback_used = data.get("cashback_used", 0)
    final = cart_total - discount - cashback_used

    await state.update_data(
        cart_total=cart_total,
        discount=discount,
        final_price=final
    )
    await state.set_state(OrderStates.confirm)

    text = (
        f"📋 <b>MA'LUMOTLARINGIZ</b>\n\n"
        f"👤 <b>Ism Familya:</b> {data.get('full_name', '—')}\n"
        f"📱 <b>Telefon:</b> {data.get('phone', '—')}\n"
        f"📍 <b>Viloyat:</b> {data.get('region', '—')}\n"
        f"🏘️ <b>Tuman:</b> {data.get('district', '—')}\n"
        f"📦 <b>BTC punkt:</b> {data.get('btc_point', '—')}\n\n"
        f"🛒 <b>BUYURTMA:</b>\n"
    )

    for idx, item in enumerate(cart, 1):
        d = item["details"]
        cover = "Qattiq" if d.get("cover_type") == "qattiq" else "Yumshoq"
        emoji = "📚" if item["item_type"] == "product" else "📦"
        text += (
            f"{idx}. {emoji} {d['name']} ({cover})\n"
            f"   ✅ {d['discounted_price']:,} so'm × {item['quantity']} = {d['discounted_price']*item['quantity']:,} so'm\n"
        )

    text += (
        f"\n💰 <b>Jami:</b> {cart_total:,} so'm\n"
    )
    if discount > 0:
        text += f"🎯 <b>Chegirma:</b> -{discount:,} so'm\n"
    if cashback_used > 0:
        text += f"💎 <b>Keshbek:</b> -{cashback_used:,} so'm\n"
    text += f"━━━━━━━━━━━━━━━━━━━\n💳 <b>To'lash kerak:</b> {final:,} so'm"

    await message.answer(text, reply_markup=kb.confirm_order_kb(), parse_mode="HTML")


@router.callback_query(F.data == "edit_order")
async def cb_edit_order(callback: CallbackQuery, state: FSMContext):
    """Tahrirlash - boshidan boshlash"""
    await state.set_state(OrderStates.full_name)
    await callback.message.answer(
        "📋 <b>RASMIYLASHTIRISH (1/4)</b>\n\n"
        "Ism va Familyangizni kiriting:\n(Masalan: Abdulaziz Karimov)",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_checkout")
async def cb_cancel_checkout(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("❌ Rasmiylashtirish bekor qilindi.", reply_markup=kb.main_menu_kb())
    await callback.answer()


@router.callback_query(OrderStates.confirm, F.data == "confirm_order")
async def cb_confirm_order(callback: CallbackQuery, state: FSMContext):
    """Tasdiqlandi → to'lov usulini tanlash"""
    await state.set_state(OrderStates.payment_method)
    data = await state.get_data()
    text = (
        f"💳 <b>TO'LOV USULINI TANLANG</b>\n\n"
        f"To'lash kerak: <b>{data.get('final_price', 0):,} so'm</b>"
    )
    await callback.message.answer(text, reply_markup=kb.payment_method_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back_payment_method")
async def cb_back_payment_method(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.payment_method)
    data = await state.get_data()
    text = (
        f"💳 <b>TO'LOV USULINI TANLANG</b>\n\n"
        f"To'lash kerak: <b>{data.get('final_price', 0):,} so'm</b>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb.payment_method_kb(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.payment_method_kb(), parse_mode="HTML")
    await callback.answer()
