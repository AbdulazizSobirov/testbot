# -*- coding: utf-8 -*-
"""
User handlers: /start, /menu, asosiy menyu, profil, yordam, referal, bonus
"""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from database import queries as db
from keyboards import user_keyboards as kb
from states.user_states import ProfileStates, SupportStates
from utils.config import config
from utils.sheets import sheets
from utils.bonus import create_invite_link, check_user_subscription

logger = logging.getLogger(__name__)
router = Router()


WELCOME_TEXT = """🌿 <b>Assalomu aleykum, kanalimizga xush kelibsiz!</b>

📋 <b>Rasmiy ma'lumot</b>
Ushbu kanal O'zbekiston va Germaniya hamkorligida faoliyat yuritadi.
Biz "M. Müller & Sohn" tikuvchilik metodikasi bo'yicha O'zbekistondagi ilk va yagona rasmiy sherikmiz.

🏅 Ushbu metodika bo'yicha eksklyuziv litsenziyaga egamiz.

📘 Shu sababli mazkur metodika asosidagi kitoblarni faqat biz orqali qonuniy va rasmiy tarzda olish mumkin.

🎓 Kitoblar mutlaqo 0 (nol) darajadan boshlab o'rganish uchun mos bo'lib, o'qish jarayonida qo'shimcha bonus darslar ham taqdim etiladi.

📄 Yuqorida joylashtirilgan rasmiy hujjatlar bilan tanishib chiqishingiz mumkin. Ushbu hujjatlarda bizga berilgan huquq va imkoniyatlar, hamkorlik doirasi hamda litsenziya shartlari aniq ko'rsatib berilgan."""


MAIN_MENU_TEXT = "🏠 <b>Asosiy menyu</b>\n\nKerakli bo'limni tanlang:"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Boshlash - registratsiya va xush kelibsiz xabari"""
    await state.clear()

    # Referal linkidan kelganmi?
    args = message.text.split(maxsplit=1)
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1][4:])
            if referrer_id == message.from_user.id:
                referrer_id = None
        except ValueError:
            referrer_id = None

    # Userni yaratish (agar yo'q bo'lsa)
    existing = await db.get_user(message.from_user.id)
    if not existing:
        await db.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            referrer_id=referrer_id,
        )
        # Google Sheets ga yangi user
        try:
            user = await db.get_user(message.from_user.id)
            if user:
                await sheets.sync_new_user(user)
        except Exception as e:
            logger.warning(f"Sheets sync error: {e}")

    await message.answer(WELCOME_TEXT, reply_markup=kb.start_kb(), parse_mode="HTML")


@router.callback_query(F.data == "start_begin")
async def cb_start_begin(callback: CallbackQuery):
    """BOSHLASH bosildi - asosiy menyuga"""
    await callback.message.delete()
    await callback.message.answer(
        MAIN_MENU_TEXT,
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "start_docs")
async def cb_start_docs(callback: CallbackQuery):
    """Rasmiy hujjatlar menyusi"""
    await callback.message.edit_text(
        "📄 <b>RASMIY HUJJATLAR</b>\n\nKerakli hujjatni tanlang:",
        reply_markup=kb.docs_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_start")
async def cb_back_start(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=kb.start_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "doc_copyright")
async def cb_doc_copyright(callback: CallbackQuery):
    file_id = await db.get_setting("doc_copyright_file_id")
    if file_id:
        try:
            await callback.message.answer_document(file_id, caption="📋 Mualliflik huquqi hujjati")
        except Exception:
            await callback.answer("Hujjat hozircha yuklanmagan", show_alert=True)
    else:
        await callback.answer("Hujjat hozircha yuklanmagan", show_alert=True)


@router.callback_query(F.data == "doc_license")
async def cb_doc_license(callback: CallbackQuery):
    file_id = await db.get_setting("doc_license_file_id")
    if file_id:
        try:
            await callback.message.answer_document(file_id, caption="📋 Litsenziya hujjati")
        except Exception:
            await callback.answer("Hujjat hozircha yuklanmagan", show_alert=True)
    else:
        await callback.answer("Hujjat hozircha yuklanmagan", show_alert=True)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """Asosiy menyuga qaytish"""
    await state.clear()
    await message.answer(MAIN_MENU_TEXT, reply_markup=kb.main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(MAIN_MENU_TEXT, reply_markup=kb.main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(MAIN_MENU_TEXT, reply_markup=kb.main_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ==================== PROFIL ====================

@router.message(F.text == "👤 Profil")
async def show_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Iltimos, /start bosing.")
        return

    text = (
        f"👤 <b>PROFIL</b>\n\n"
        f"👤 Ism Familya: {user.get('full_name') or '— (kiritilmagan)'}\n"
        f"📱 Telefon: {user.get('phone') or '— (kiritilmagan)'}\n"
        f"📍 Manzil: {user.get('region') or '—'}, {user.get('district') or '—'}\n"
        f"📦 BTC punkt: {user.get('btc_point') or '—'}\n"
        f"📅 A'zolik: {user.get('registration_date', '')[:10]}\n"
        f"💰 Keshbek balans: {user.get('cashback_balance', 0):,} so'm"
    )
    await message.answer(text, reply_markup=kb.profile_kb(), parse_mode="HTML")


# ==================== YORDAM ====================

@router.message(F.text == "❓ Yordam")
async def show_help(message: Message):
    text = (
        "❓ <b>YORDAM</b>\n\n"
        "📞 Telefon: +998 91 222 83 12\n\n"
        "💬 Adminlar:\n"
        "@MB_Academiya\n"
        "@Muhayyo_Bobomurodova_Admini"
    )
    await message.answer(text, reply_markup=kb.help_kb(), parse_mode="HTML")


@router.callback_query(F.data == "write_admin")
async def cb_write_admin(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.writing_message)
    await callback.message.answer(
        "✉️ Adminga yubormoqchi bo'lgan xabaringizni yozing:\n\n"
        "(Bekor qilish uchun /menu yozing)"
    )
    await callback.answer()


@router.message(SupportStates.writing_message)
async def process_admin_message(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() in ("/menu", "/start"):
        await state.clear()
        await message.answer(MAIN_MENU_TEXT, reply_markup=kb.main_menu_kb(), parse_mode="HTML")
        return

    user = message.from_user
    user_link = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
    username = f"@{user.username}" if user.username else "—"

    admin_text = (
        f"📨 <b>YANGI XABAR (User → Admin)</b>\n\n"
        f"👤 Foydalanuvchi: {user_link}\n"
        f"💬 Username: {username}\n"
        f"🆔 ID: <code>{user.id}</code>"
    )

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
            # Asl xabarni forward qilish
            await bot.forward_message(admin_id, message.chat.id, message.message_id)
            # Javob berish uchun reply tugmasi
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton
            reply_kb = InlineKeyboardBuilder()
            reply_kb.row(InlineKeyboardButton(
                text="↩️ Javob yozish",
                callback_data=f"admin_reply_{user.id}"
            ))
            await bot.send_message(admin_id, "↑ Yuqoridagi xabarga javob bering:", reply_markup=reply_kb.as_markup())
        except Exception as e:
            logger.error(f"Admin xabar yuborishda xato (admin_id={admin_id}): {e}")

    await message.answer("✅ Xabaringiz adminlarga yetkazildi! Tez orada javob beriladi.")
    await state.clear()


# ==================== REFERAL ====================

@router.message(F.text == "👥 Referal")
async def show_referral(message: Message, bot: Bot):
    me = await bot.get_me()
    user_id = message.from_user.id
    referrals = await db.get_referrals(user_id)
    history = await db.get_cashback_history(user_id)
    user = await db.get_user(user_id)

    total_cashback = sum(h["amount"] for h in history if h["operation"] == "add")
    balance = user["cashback_balance"] if user else 0

    text = (
        f"👥 <b>REFERAL</b>\n\n"
        f"🔗 Sizning referal linkingiz:\n"
        f"<code>https://t.me/{me.username}?start=ref_{user_id}</code>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"👤 Taklif qilganlar: {len(referrals)} nafar\n"
        f"💰 Jami keshbek: {total_cashback:,} so'm\n"
        f"💳 Mavjud balans: {balance:,} so'm\n\n"
    )

    if history:
        text += "💰 <b>KESHBEK TARIXI:</b>\n"
        for i, h in enumerate(history[:5], 1):
            if h["operation"] == "add":
                text += f"{i}. Referal xaridi → +{h['amount']:,} so'm\n"
            elif h["operation"] == "deduct":
                text += f"{i}. Xaridda ishlatildi → −{h['amount']:,} so'm\n"
            elif h["operation"] == "refund":
                text += f"{i}. Qaytarildi → +{h['amount']:,} so'm\n"

    text += (
        "\nℹ️ Har bir taklif qilgan odamingiz xarid qilsa, "
        f"xarid summasining {config.REFERRAL_CASHBACK}% sizga keshbek bo'lib yig'iladi!\n"
        "(Uzum Nasiya orqali xaridlarda keshbek hisoblanmaydi)"
    )

    await message.answer(text, reply_markup=kb.back_kb(), parse_mode="HTML")


# ==================== BONUS ====================

@router.message(F.text == "💰 Bonus")
async def show_bonus(message: Message):
    text = (
        "💰 <b>BONUS VA CHEGIRMALAR</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎁 <b>1. BEPUL YOPIQ KANAL</b>\n"
        "2 ta kanalga obuna bo'ling va maxsus yopiq kanalga kiring!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📢 <b>2. BONUS KANALLAR</b>\n"
        "Sotib olgan kitoblaringizga mos video darsliklar!"
    )
    await message.answer(text, reply_markup=kb.bonus_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "back_bonus")
async def cb_back_bonus(callback: CallbackQuery):
    text = (
        "💰 <b>BONUS VA CHEGIRMALAR</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎁 <b>1. BEPUL YOPIQ KANAL</b>\n"
        "2 ta kanalga obuna bo'ling va maxsus yopiq kanalga kiring!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📢 <b>2. BONUS KANALLAR</b>\n"
        "Sotib olgan kitoblaringizga mos video darsliklar!"
    )
    await callback.message.edit_text(text, reply_markup=kb.bonus_main_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "bonus_free")
async def cb_bonus_free(callback: CallbackQuery):
    ch1 = await db.get_setting("channel_1_id") or config.CHANNEL_1_ID
    ch2 = await db.get_setting("channel_2_id") or config.CHANNEL_2_ID

    text = (
        "🎁 <b>BEPUL YOPIQ KANAL</b>\n\n"
        "Quyidagi 2 ta kanalga obuna bo'ling va keyin \"Obunani tekshirish\" tugmasini bosing:"
    )
    await callback.message.edit_text(text, reply_markup=kb.bonus_check_kb(ch1, ch2), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "check_subscription")
async def cb_check_sub(callback: CallbackQuery, bot: Bot):
    ch1 = await db.get_setting("channel_1_id") or config.CHANNEL_1_ID
    ch2 = await db.get_setting("channel_2_id") or config.CHANNEL_2_ID

    user_id = callback.from_user.id
    sub1 = await check_user_subscription(bot, ch1, user_id) if ch1 else True
    sub2 = await check_user_subscription(bot, ch2, user_id) if ch2 else True

    if sub1 and sub2:
        # Yopiq kanalga link beriladi (qaysi kanal? — koylakni misol qilamiz)
        if config.BONUS_CHANNEL_KOYLAK_ID:
            link = await create_invite_link(bot, config.BONUS_CHANNEL_KOYLAK_ID, user_id)
            if link:
                await callback.message.answer(
                    f"✅ Tabriklaymiz! Yopiq kanalga kiring:\n{link}",
                    reply_markup=kb.back_kb()
                )
            else:
                await callback.answer("Link yaratishda xato. Adminga murojaat qiling.", show_alert=True)
        else:
            await callback.answer("Yopiq kanal sozlanmagan.", show_alert=True)
    else:
        await callback.answer("⚠️ Hali ikkala kanalga ham obuna bo'lmadingiz!", show_alert=True)


@router.callback_query(F.data == "bonus_my")
async def cb_bonus_my(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    orders = await db.get_user_orders(user_id)
    completed = [o for o in orders if o["delivery_status"] == "completed"]

    if not completed:
        await callback.message.edit_text(
            "📢 <b>MENING BONUS KANALLARIM</b>\n\n"
            "Hali xarid qilmagansiz! Avval kitob xarid qiling.",
            reply_markup=kb.back_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    from utils.bonus import get_bonus_channels_for_order

    all_items = []
    for o in completed:
        all_items.extend(o["items"])

    channels = await get_bonus_channels_for_order(all_items)
    if not channels:
        await callback.message.edit_text(
            "📢 <b>MENING BONUS KANALLARIM</b>\n\n"
            "Bonus kanallar topilmadi.",
            reply_markup=kb.back_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for i, ch_id in enumerate(channels, 1):
        link = await create_invite_link(bot, ch_id, user_id)
        if link:
            builder.row(InlineKeyboardButton(text=f"🔗 Bonus kanal {i}", url=link))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_bonus"))

    await callback.message.edit_text(
        "📢 <b>MENING BONUS KANALLARIM</b>\n\n"
        "Sotib olgan kitoblaringizga mos bonus kanallar:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== PROFIL TAHRIRLASH ====================

@router.callback_query(F.data == "edit_name")
async def cb_edit_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.edit_name)
    await callback.message.answer(
        "✏️ Yangi Ism Familyangizni kiriting:\n(Masalan: Abdulaziz Karimov)\n\n"
        "⚠️ 2 ta so'z bo'lishi shart!"
    )
    await callback.answer()


@router.message(ProfileStates.edit_name)
async def process_edit_name(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    parts = text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Iltimos, 2 ta so'z kiriting (Ism va Familya)")
        return
    await db.update_user_profile(message.from_user.id, full_name=text)
    await state.clear()
    await message.answer("✅ Ism familya o'zgartirildi!", reply_markup=kb.main_menu_kb())


@router.callback_query(F.data == "edit_phone")
async def cb_edit_phone(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.edit_phone)
    await callback.message.answer(
        "📱 Yangi telefon raqamingizni kiriting:\n(Masalan: +998901234567)",
        reply_markup=kb.phone_request_kb()
    )
    await callback.answer()


@router.message(ProfileStates.edit_phone, F.contact)
async def process_edit_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await db.update_user_profile(message.from_user.id, phone=phone)
    await state.clear()
    await message.answer(f"✅ Telefon raqami yangilandi: {phone}", reply_markup=kb.main_menu_kb())


@router.message(ProfileStates.edit_phone, F.text)
async def process_edit_phone_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.main_menu_kb())
        return
    # Telefon validatsiya
    digits = "".join(c for c in text if c.isdigit())
    if len(digits) < 9:
        await message.answer("⚠️ Iltimos, to'g'ri telefon raqam kiriting:\n(Masalan: +998901234567)")
        return
    if not text.startswith("+"):
        text = "+" + digits
    await db.update_user_profile(message.from_user.id, phone=text)
    await state.clear()
    await message.answer(f"✅ Telefon raqami yangilandi: {text}", reply_markup=kb.main_menu_kb())


@router.callback_query(F.data == "edit_address")
async def cb_edit_address(callback: CallbackQuery, state: FSMContext):
    """Manzil tahrirlash - region tanlashdan boshlanadi"""
    await state.set_state(ProfileStates.edit_region)
    await state.update_data(edit_mode="address")
    await callback.message.answer(
        "📍 Yangi manzilingizni tanlang.\n\nViloyatni tanlang:",
        reply_markup=kb.regions_kb()
    )
    await callback.answer()


# ==================== MENU YORDAMCHI ====================

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
