# -*- coding: utf-8 -*-
"""
MONS Academy Kitob Savdo Boti
Asosiy ishga tushirish fayli
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, MenuButtonCommands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.config import config
from database.models import init_db, insert_default_settings
from database import queries as db
from handlers import (
    user_handlers,
    catalog_handlers,
    cart_handlers,
    order_handlers,
    payment_handlers,
    bonus_handlers,
    admin_handlers,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def auto_cancel_pending_orders(bot: Bot):
    """30 daqiqadan keyin to'lov qilinmagan buyurtmalarni avtomatik bekor qiladi"""
    try:
        old_orders = await db.get_pending_orders_older_than(config.AUTO_CANCEL_MINUTES)
        for order in old_orders:
            await db.update_order(
                order["id"],
                delivery_status="cancelled",
                admin_notes="Avtomatik bekor (30 daqiqada to'lov bo'lmadi)"
            )
            # Keshbek qaytarish
            if order.get("cashback_used", 0) > 0:
                await db.refund_cashback(order["user_id"], order["cashback_used"], order["id"])

            try:
                msg = (
                    f"❌ <b>{order['order_code']}</b>\n\n"
                    f"Buyurtmangiz avtomatik bekor qilindi (30 daqiqa ichida to'lov amalga oshmadi).\n"
                )
                if order.get("cashback_used", 0) > 0:
                    msg += f"💰 {order['cashback_used']:,} so'm keshbek qaytarildi."
                await bot.send_message(order["user_id"], msg, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Auto-cancel xabar yuborishda xato: {e}")

            logger.info(f"Auto-cancelled order: {order['order_code']}")
    except Exception as e:
        logger.error(f"Auto-cancel jarayonida xato: {e}")


async def on_startup(bot: Bot):
    """Bot ishga tushganda commandlar va menyu tugmasini sozlash"""
    commands = [
        BotCommand(command="start", description="🚀 Ishni boshlash"),
        BotCommand(command="menu", description="🏠 Asosiy menyu"),
        BotCommand(command="admin", description="👨‍💼 Admin panel"),
    ]
    await bot.set_my_commands(commands)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Bot commandlari va menu button sozlandi")


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN .env da yo'q! Iltimos sozlang.")
        return

    # Database yaratish
    await init_db()
    await insert_default_settings()
    logger.info("Database tayyor")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ulash
    dp.include_router(admin_handlers.router)
    dp.include_router(payment_handlers.router)
    dp.include_router(order_handlers.router)
    dp.include_router(cart_handlers.router)
    dp.include_router(catalog_handlers.router)
    dp.include_router(bonus_handlers.router)
    dp.include_router(user_handlers.router)

    # Scheduler — auto-cancel
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        auto_cancel_pending_orders,
        "interval",
        minutes=5,  # har 5 daqiqada tekshiramiz
        args=[bot],
        id="auto_cancel",
    )
    scheduler.start()
    logger.info("Scheduler ishga tushdi")

    # Startup
    await on_startup(bot)

    logger.info("🚀 Bot ishga tushdi (polling)")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
