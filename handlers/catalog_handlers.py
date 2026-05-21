# -*- coding: utf-8 -*-
"""
Katalog handlerlari: Kitoblar va To'plamlar
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import queries as db
from keyboards import user_keyboards as kb

logger = logging.getLogger(__name__)
router = Router()


# ==================== KITOBLAR ====================

@router.message(F.text == "📚 Kitoblar")
async def show_books_menu(message: Message):
    await message.answer(
        "📚 <b>KITOBLAR</b>\n\nMuqova turini tanlang:",
        reply_markup=kb.books_cover_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_books")
async def cb_back_books(callback: CallbackQuery):
    await callback.message.edit_text(
        "📚 <b>KITOBLAR</b>\n\nMuqova turini tanlang:",
        reply_markup=kb.books_cover_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("books_cover_"))
async def cb_books_cover(callback: CallbackQuery):
    cover = callback.data.replace("books_cover_", "")
    products = await db.get_products_by_cover(cover)
    if not products:
        await callback.answer("Hozircha kitoblar yo'q", show_alert=True)
        return

    cover_emoji = "📗" if cover == "qattiq" else "📘"
    cover_name = "QATTIQ MUQOVA" if cover == "qattiq" else "YUMSHOQ MUQOVA"

    text = f"{cover_emoji} <b>{cover_name}</b>\n\n"
    for idx, p in enumerate(products, 1):
        digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]
        em = digits[idx-1] if idx <= len(digits) else f"{idx}"
        text += (
            f"{em} <b>{p['name']}</b>\n"
            f"   <s>{p['original_price']:,} so'm</s> → <b>{p['discounted_price']:,} so'm</b>\n\n"
        )
    text += "Pastdagi raqamli tugmalardan tanlang ⬇️"

    await callback.message.edit_text(text, reply_markup=kb.books_list_kb(products, cover), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back_book_list")
async def cb_back_book_list(callback: CallbackQuery):
    """Kitob detalidan ro'yxatga qaytish"""
    await callback.message.answer(
        "📚 <b>KITOBLAR</b>\n\nMuqova turini tanlang:",
        reply_markup=kb.books_cover_kb(),
        parse_mode="HTML"
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("book_"))
async def cb_book_detail(callback: CallbackQuery):
    """Bitta kitob detali"""
    try:
        product_id = int(callback.data.replace("book_", ""))
    except ValueError:
        await callback.answer()
        return

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Kitob topilmadi", show_alert=True)
        return

    cover_label = "Qattiq muqova" if product["cover_type"] == "qattiq" else "Yumshoq muqova"

    # Stok statusi
    stock = product["stock"]
    if stock == 0:
        stock_text = "📦 Tugagan ❌"
        in_stock = False
    elif stock <= 5:
        stock_text = f"📦 Stokda: {stock} ta qoldi!"
        in_stock = True
    else:
        stock_text = f"📦 Stokda: {stock} ta"
        in_stock = True

    caption = (
        f"📖 <b>{product['name']}</b>\n"
        f"({cover_label})\n\n"
        f"<s>{product['original_price']:,} so'm</s>\n"
        f"✅ <b>{product['discounted_price']:,} so'm</b>\n\n"
        f"{stock_text}"
    )

    keyboard = kb.book_detail_kb(product_id, in_stock=in_stock)

    # Media bor bo'lsa ko'rsatish
    try:
        if product.get("media_file_id"):
            if product.get("media_type") == "video":
                await callback.message.answer_video(
                    product["media_file_id"], caption=caption,
                    reply_markup=keyboard, parse_mode="HTML"
                )
            else:
                await callback.message.answer_photo(
                    product["media_file_id"], caption=caption,
                    reply_markup=keyboard, parse_mode="HTML"
                )
            try:
                await callback.message.delete()
            except Exception:
                pass
        else:
            await callback.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Book detail error: {e}")
        await callback.message.answer(caption, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("add_book_"))
async def cb_add_book_to_cart(callback: CallbackQuery):
    """Kitobni savatga qo'shish"""
    try:
        product_id = int(callback.data.replace("add_book_", ""))
    except ValueError:
        await callback.answer()
        return

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Kitob topilmadi", show_alert=True)
        return

    if product["stock"] <= 0:
        await callback.answer("❌ Bu kitob hozir tugagan", show_alert=True)
        return

    await db.add_to_cart(callback.from_user.id, "product", product_id, 1)
    await callback.answer(f"✅ Savatga qo'shildi: {product['name']}", show_alert=True)


# ==================== TO'PLAMLAR ====================

@router.message(F.text == "🎁 To'plamlar")
async def show_bundles_menu(message: Message):
    await message.answer(
        "📦 <b>TO'PLAMLAR</b>\n\nMuqova turini tanlang:",
        reply_markup=kb.bundles_cover_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_bundles")
async def cb_back_bundles(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 <b>TO'PLAMLAR</b>\n\nMuqova turini tanlang:",
        reply_markup=kb.bundles_cover_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bundles_cover_"))
async def cb_bundles_cover(callback: CallbackQuery):
    cover = callback.data.replace("bundles_cover_", "")
    bundles = await db.get_bundles_by_cover(cover)
    if not bundles:
        await callback.answer("Hozircha to'plamlar yo'q", show_alert=True)
        return

    cover_emoji = "📗" if cover == "qattiq" else "📘"
    cover_name = "QATTIQ MUQOVA" if cover == "qattiq" else "YUMSHOQ MUQOVA"

    text = f"{cover_emoji} <b>TO'PLAMLAR — {cover_name}</b>\n\n"
    digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    for idx, b in enumerate(bundles, 1):
        em = digits[idx-1] if idx <= 4 else f"{idx}"
        text += (
            f"{em} <b>{b['name']}</b>\n"
            f"   <s>{b['original_price']:,} so'm</s> → <b>{b['discounted_price']:,} so'm</b>\n\n"
        )
    text += "Pastdagi raqamli tugmalardan tanlang ⬇️"

    await callback.message.edit_text(text, reply_markup=kb.bundles_list_kb(bundles, cover), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back_bundle_list")
async def cb_back_bundle_list(callback: CallbackQuery):
    await callback.message.answer(
        "📦 <b>TO'PLAMLAR</b>\n\nMuqova turini tanlang:",
        reply_markup=kb.bundles_cover_kb(),
        parse_mode="HTML"
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("bundle_"))
async def cb_bundle_detail(callback: CallbackQuery):
    try:
        bundle_id = int(callback.data.replace("bundle_", ""))
    except ValueError:
        await callback.answer()
        return

    bundle = await db.get_bundle(bundle_id)
    if not bundle:
        await callback.answer("To'plam topilmadi", show_alert=True)
        return

    cover_label = "Qattiq muqova" if bundle["cover_type"] == "qattiq" else "Yumshoq muqova"

    caption = (
        f"📦 <b>{bundle['name']}</b>\n"
        f"({cover_label})\n\n"
        f"<s>{bundle['original_price']:,} so'm</s>\n"
        f"✅ <b>{bundle['discounted_price']:,} so'm</b>"
    )

    keyboard = kb.bundle_detail_kb(bundle_id)

    try:
        if bundle.get("media_file_id"):
            if bundle.get("media_type") == "video":
                await callback.message.answer_video(
                    bundle["media_file_id"], caption=caption,
                    reply_markup=keyboard, parse_mode="HTML"
                )
            else:
                await callback.message.answer_photo(
                    bundle["media_file_id"], caption=caption,
                    reply_markup=keyboard, parse_mode="HTML"
                )
            try:
                await callback.message.delete()
            except Exception:
                pass
        else:
            await callback.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Bundle detail error: {e}")
        await callback.message.answer(caption, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("add_bundle_"))
async def cb_add_bundle_to_cart(callback: CallbackQuery):
    try:
        bundle_id = int(callback.data.replace("add_bundle_", ""))
    except ValueError:
        await callback.answer()
        return

    bundle = await db.get_bundle(bundle_id)
    if not bundle:
        await callback.answer("To'plam topilmadi", show_alert=True)
        return

    await db.add_to_cart(callback.from_user.id, "bundle", bundle_id, 1)
    await callback.answer(f"✅ Savatga qo'shildi: {bundle['name']}", show_alert=True)
