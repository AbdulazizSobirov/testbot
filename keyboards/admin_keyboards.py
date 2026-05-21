# -*- coding: utf-8 -*-
"""
Admin uchun klaviaturalar
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def admin_main_kb(is_super: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 Buyurtmalar", callback_data="adm_orders"),
        InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm_users"),
    )
    builder.row(
        InlineKeyboardButton(text="📚 Mahsulotlar", callback_data="adm_products"),
        InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data="adm_broadcast"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="adm_settings"),
    )
    if is_super:
        builder.row(InlineKeyboardButton(text="👥 Adminlar boshqaruvi", callback_data="adm_admins"))
    return builder.as_markup()


def admin_orders_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏳ Yangi buyurtmalar", callback_data="orders_pending"))
    builder.row(InlineKeyboardButton(text="✅ Tasdiqlangan", callback_data="orders_confirmed"))
    builder.row(InlineKeyboardButton(text="📦 Tayyorlanmoqda", callback_data="orders_preparing"))
    builder.row(InlineKeyboardButton(text="🚚 Yo'lda", callback_data="orders_shipping"))
    builder.row(InlineKeyboardButton(text="✔️ Yakunlangan", callback_data="orders_completed"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilingan", callback_data="orders_cancelled"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back_main"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def order_actions_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Buyurtma statusiga qarab tugmalar"""
    builder = InlineKeyboardBuilder()

    if status == "pending":
        builder.row(
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"ord_confirm_{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"ord_cancel_{order_id}"),
        )
    elif status == "confirmed":
        builder.row(
            InlineKeyboardButton(text="📦 Tayyorlanmoqda", callback_data=f"ord_preparing_{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"ord_cancel_{order_id}"),
        )
    elif status == "preparing":
        builder.row(
            InlineKeyboardButton(text="🚚 Jo'natdim + vaqt", callback_data=f"ord_ship_{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"ord_cancel_{order_id}"),
        )
    elif status == "shipping":
        builder.row(InlineKeyboardButton(text="✔️ Yetkazildi", callback_data=f"ord_delivered_{order_id}"))
    # completed yoki cancelled — tugmalar yo'q

    builder.row(InlineKeyboardButton(text="✉️ Mijozga yozish", callback_data=f"ord_msg_{order_id}"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_orders"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def admin_users_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Barcha foydalanuvchilar", callback_data="users_all"))
    builder.row(InlineKeyboardButton(text="🏆 Top 10 xaridorlar", callback_data="users_top"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back_main"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def admin_products_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Yangi mahsulot qo'shish", callback_data="prod_add"))
    builder.row(InlineKeyboardButton(text="📗 Kitoblar", callback_data="prod_books"))
    builder.row(InlineKeyboardButton(text="📦 To'plamlar", callback_data="prod_bundles"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back_main"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def product_edit_kb(product_id: int, item_type: str = "product") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    prefix = "p" if item_type == "product" else "b"
    builder.row(InlineKeyboardButton(text="💰 Narxni o'zgartirish", callback_data=f"{prefix}edit_price_{product_id}"))
    if item_type == "product":
        builder.row(InlineKeyboardButton(text="📦 Stokni o'zgartirish", callback_data=f"{prefix}edit_stock_{product_id}"))
    builder.row(InlineKeyboardButton(text="🖼️ Rasm/Video o'zgartirish", callback_data=f"{prefix}edit_media_{product_id}"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_products"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def admin_broadcast_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Hammaga xabar yuborish", callback_data="bc_all"))
    builder.row(InlineKeyboardButton(text="👤 Bitta userga xabar yuborish", callback_data="bc_one"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back_main"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def admin_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 Narx va chegirmalar", callback_data="set_prices"))
    builder.row(InlineKeyboardButton(text="📢 Telegram kanallar", callback_data="set_channels"))
    builder.row(InlineKeyboardButton(text="🛍️ Uzum Nasiya sozlamalari", callback_data="set_uzum"))
    builder.row(InlineKeyboardButton(text="📄 Rasmiy hujjatlar", callback_data="set_docs"))
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back_main"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def admin_settings_channels_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Kanal 1 o'zgartirish", callback_data="ch1_edit"))
    builder.row(InlineKeyboardButton(text="✏️ Kanal 2 o'zgartirish", callback_data="ch2_edit"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_settings"))
    return builder.as_markup()


def admin_settings_uzum_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📱 QR kodni almashtirish", callback_data="uzum_qr_set"))
    builder.row(InlineKeyboardButton(text="🎬 Videoni almashtirish", callback_data="uzum_video_set"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_settings"))
    return builder.as_markup()


def admin_settings_docs_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Mualliflik huquqi hujjatini almashtirish", callback_data="doc_copyright_set"))
    builder.row(InlineKeyboardButton(text="📋 Litsenziya hujjatini almashtirish", callback_data="doc_license_set"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_settings"))
    return builder.as_markup()


def admin_admins_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="adm_add"))
    builder.row(InlineKeyboardButton(text="📋 Adminlar ro'yxati", callback_data="adm_list"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back_main"))
    return builder.as_markup()


def admin_permissions_kb(perms: dict) -> InlineKeyboardMarkup:
    """Toggle qilinadigan permissionlar"""
    builder = InlineKeyboardBuilder()
    def mark(v): return "✅" if v else "❌"
    builder.row(InlineKeyboardButton(text=f"{mark(perms['can_confirm_orders'])} Buyurtmalarni tasdiqlash", callback_data="perm_orders"))
    builder.row(InlineKeyboardButton(text=f"{mark(perms['can_manage_users'])} Userlarni boshqarish", callback_data="perm_users"))
    builder.row(InlineKeyboardButton(text=f"{mark(perms['can_edit_products'])} Mahsulotlarni tahrirlash", callback_data="perm_products"))
    builder.row(InlineKeyboardButton(text=f"{mark(perms['can_broadcast'])} Xabar yuborish", callback_data="perm_broadcast"))
    builder.row(InlineKeyboardButton(text=f"{mark(perms['can_manage_settings'])} Sozlamalar", callback_data="perm_settings"))
    builder.row(InlineKeyboardButton(text="✅ Saqlash", callback_data="perm_save"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="perm_cancel"))
    return builder.as_markup()


def back_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back_main"),
        InlineKeyboardButton(text="🏠 Bosh panel", callback_data="adm_home"),
    )
    return builder.as_markup()


def confirm_cancel_kb(callback_yes: str, callback_no: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=callback_yes),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=callback_no),
    )
    return builder.as_markup()


def category_choice_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📚 Kitob", callback_data="cat_book"),
        InlineKeyboardButton(text="📦 To'plam", callback_data="cat_bundle"),
    )
    return builder.as_markup()


def cover_choice_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📗 Qattiq", callback_data="cov_qattiq"),
        InlineKeyboardButton(text="📘 Yumshoq", callback_data="cov_yumshoq"),
    )
    return builder.as_markup()


def cancel_fsm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_cancel_fsm"))
    return builder.as_markup()
