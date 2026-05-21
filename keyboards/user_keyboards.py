# -*- coding: utf-8 -*-
"""
Foydalanuvchi uchun klaviaturalar
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from data.btc_points import get_btc_points, get_viloyatlar, get_tumanlar
from data.regions import REGIONS


# ==================== ASOSIY MENYU ====================

def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📚 Kitoblar"), KeyboardButton(text="🎁 To'plamlar"))
    builder.row(KeyboardButton(text="🛒 Savat"), KeyboardButton(text="💰 Bonus"))
    builder.row(KeyboardButton(text="📋 Buyurtmalarim"), KeyboardButton(text="👥 Referal"))
    builder.row(KeyboardButton(text="👤 Profil"), KeyboardButton(text="❓ Yordam"))
    return builder.as_markup(resize_keyboard=True, persistent=True)


def start_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚀 BOSHLASH", callback_data="start_begin"))
    builder.row(InlineKeyboardButton(text="📄 Rasmiy hujjatlar bilan tanishish", callback_data="start_docs"))
    return builder.as_markup()


def docs_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Mualliflik huquqi hujjati", callback_data="doc_copyright"))
    builder.row(InlineKeyboardButton(text="📋 Litsenziya hujjati", callback_data="doc_license"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_start"))
    return builder.as_markup()


# ==================== KITOBLAR ====================

def books_cover_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📗 Qattiq muqova", callback_data="books_cover_qattiq"))
    builder.row(InlineKeyboardButton(text="📘 Yumshoq muqova", callback_data="books_cover_yumshoq"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"))
    return builder.as_markup()


def books_list_kb(products: list, cover: str) -> InlineKeyboardMarkup:
    """Kitoblar ro'yxati uchun raqamli tugmalar"""
    builder = InlineKeyboardBuilder()
    # Raqamlar (har qatorda 4 ta)
    digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    row = []
    for idx, p in enumerate(products):
        emoji = digits[idx] if idx < len(digits) else f"{idx+1}"
        row.append(InlineKeyboardButton(text=emoji, callback_data=f"book_{p['id']}"))
        if len(row) == 4:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_books"))
    return builder.as_markup()


def book_detail_kb(product_id: int, in_stock: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if in_stock:
        builder.row(InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_book_{product_id}"))
    else:
        builder.row(InlineKeyboardButton(text="❌ Tugagan", callback_data="noop"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"back_book_list"))
    return builder.as_markup()


# ==================== TO'PLAMLAR ====================

def bundles_cover_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📗 Qattiq muqova", callback_data="bundles_cover_qattiq"))
    builder.row(InlineKeyboardButton(text="📘 Yumshoq muqova", callback_data="bundles_cover_yumshoq"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"))
    return builder.as_markup()


def bundles_list_kb(bundles: list, cover: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    row = []
    for idx, b in enumerate(bundles):
        emoji = digits[idx] if idx < len(digits) else f"{idx+1}"
        row.append(InlineKeyboardButton(text=emoji, callback_data=f"bundle_{b['id']}"))
    if row:
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_bundles"))
    return builder.as_markup()


def bundle_detail_kb(bundle_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_bundle_{bundle_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_bundle_list"))
    return builder.as_markup()


# ==================== SAVAT ====================

def cart_kb(cart_items: list) -> InlineKeyboardMarkup:
    """Savat - har bir mahsulot uchun ➖ qty ➕ va ❌ tugmalari"""
    builder = InlineKeyboardBuilder()
    for item in cart_items:
        cart_id = item["id"]
        qty = item["quantity"]
        builder.row(
            InlineKeyboardButton(text="➖", callback_data=f"cart_minus_{cart_id}"),
            InlineKeyboardButton(text=f"{qty}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_plus_{cart_id}"),
            InlineKeyboardButton(text="❌", callback_data=f"cart_remove_{cart_id}"),
        )
    if cart_items:
        builder.row(InlineKeyboardButton(text="✅ Rasmiylashtirish", callback_data="checkout"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return builder.as_markup()


# ==================== RASMIYLASHTIRISH ====================

def phone_request_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Telefonni yuborish", request_contact=True))
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def regions_kb() -> InlineKeyboardMarkup:
    """14 viloyat - 2 ustun bo'lib"""
    builder = InlineKeyboardBuilder()
    regions = list(REGIONS.keys())
    for i in range(0, len(regions), 2):
        row = [InlineKeyboardButton(text=regions[i], callback_data=f"region_{i}")]
        if i + 1 < len(regions):
            row.append(InlineKeyboardButton(text=regions[i+1], callback_data=f"region_{i+1}"))
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_checkout"))
    return builder.as_markup()


def districts_kb(region: str) -> InlineKeyboardMarkup:
    """Tanlangan viloyatdagi tumanlar"""
    builder = InlineKeyboardBuilder()
    districts = REGIONS.get(region, [])
    for i in range(0, len(districts), 2):
        row = [InlineKeyboardButton(text=districts[i], callback_data=f"district_{i}")]
        if i + 1 < len(districts):
            row.append(InlineKeyboardButton(text=districts[i+1], callback_data=f"district_{i+1}"))
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_region"))
    return builder.as_markup()


def btc_points_kb(region: str, district: str) -> InlineKeyboardMarkup:
    """Tanlangan tumandagi BTC punktlar"""
    builder = InlineKeyboardBuilder()
    points = get_btc_points(region, district)

    # Punktlar uchun raqamli tugmalar (har qatorda 5 ta)
    digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    row = []
    for idx, p in enumerate(points):
        if idx < 10:
            emoji = digits[idx]
        else:
            emoji = f"{idx+1}"
        row.append(InlineKeyboardButton(text=emoji, callback_data=f"btc_{p['kod']}"))
        if len(row) == 5:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    builder.row(InlineKeyboardButton(text="📍 Lokatsiya yuborish", callback_data="send_location"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_district"))
    return builder.as_markup()


def location_request_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True))
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def btc_point_view_kb(kod: int) -> InlineKeyboardMarkup:
    """Tanlangan BTC punkt uchun: xaritada ko'rish + tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗺 Google Maps", callback_data=f"map_g_{kod}"),
        InlineKeyboardButton(text="🗺 Yandex Maps", callback_data=f"map_y_{kod}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Shu punktni tanlash", callback_data=f"confirm_btc_{kod}"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_btc_list"))
    return builder.as_markup()


def cashback_choice_kb(balance: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if balance > 0:
        builder.row(InlineKeyboardButton(text=f"💰 Keshbekdan foydalanish ({balance:,} so'm)", callback_data="use_cashback"))
    builder.row(InlineKeyboardButton(text="➡️ O'tkazib yuborish", callback_data="skip_cashback"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_confirm"))
    return builder.as_markup()


def confirm_order_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order"))
    builder.row(InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_order"))
    builder.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"))
    return builder.as_markup()


def payment_method_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 UzCard / Humo (3% - 8% chegirma)", callback_data="pay_uzcard"))
    builder.row(InlineKeyboardButton(text="🛍️ Uzum Nasiya (3 oyga foizsiz)", callback_data="pay_uzum"))
    builder.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"))
    return builder.as_markup()


def uzcard_payment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_payment"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_payment_method"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return builder.as_markup()


def uzum_payment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📱 QR kodni olish", callback_data="uzum_qr"))
    builder.row(InlineKeyboardButton(text="🎬 Video yo'riqnoma", callback_data="uzum_video"))
    builder.row(InlineKeyboardButton(text="📷 Chekni yuborish", callback_data="uzum_send_receipt"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_payment"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_payment_method"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return builder.as_markup()


# ==================== BUYURTMALARIM ====================

def my_orders_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📜 Buyurtmalar tarixi", callback_data="orders_history"))
    builder.row(InlineKeyboardButton(text="🔄 Faol buyurtmalar", callback_data="orders_active"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"))
    return builder.as_markup()


def order_view_kb(order_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.row(InlineKeyboardButton(text="✉️ Adminga yozish", callback_data=f"contact_admin_{order_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_my_orders"))
    return builder.as_markup()


# ==================== PROFIL ====================

def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Ism", callback_data="edit_name"),
        InlineKeyboardButton(text="📱 Telefon", callback_data="edit_phone"),
    )
    builder.row(InlineKeyboardButton(text="📍 Manzil", callback_data="edit_address"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return builder.as_markup()


# ==================== BONUS ====================

def bonus_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 Bepul yopiq kanalga qo'shilish", callback_data="bonus_free"))
    builder.row(InlineKeyboardButton(text="📢 Mening bonus kanallarim", callback_data="bonus_my"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"))
    return builder.as_markup()


def bonus_check_kb(channel_1: str, channel_2: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Channel link-larini t.me formatiga keltirish
    def to_link(ch):
        if ch.startswith("@"):
            return f"https://t.me/{ch[1:]}"
        return ch
    builder.row(InlineKeyboardButton(text="📢 Kanal 1", url=to_link(channel_1)))
    builder.row(InlineKeyboardButton(text="📢 Kanal 2", url=to_link(channel_2)))
    builder.row(InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_bonus"))
    return builder.as_markup()


# ==================== YORDAM ====================

def help_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✉️ Adminga yozish", callback_data="write_admin"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"))
    return builder.as_markup()


# ==================== UMUMIY ====================

def back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main"))
    return builder.as_markup()


def home_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"))
    return builder.as_markup()
