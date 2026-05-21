# -*- coding: utf-8 -*-
"""
Database modellari - SQLite jadvallarini yaratish
"""
import aiosqlite
from utils.config import config


async def init_db():
    """Barcha jadvallarni yaratish"""
    async with aiosqlite.connect(config.DB_PATH) as db:
        # users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                region TEXT,
                district TEXT,
                btc_point TEXT,
                btc_point_kod INTEGER,
                referrer_id INTEGER,
                cashback_balance INTEGER DEFAULT 0,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # products
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                cover_type TEXT NOT NULL,
                original_price INTEGER NOT NULL,
                discounted_price INTEGER NOT NULL,
                media_type TEXT DEFAULT 'photo',
                media_file_id TEXT,
                stock INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)

        # bundles
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bundles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                cover_type TEXT NOT NULL,
                original_price INTEGER NOT NULL,
                discounted_price INTEGER NOT NULL,
                media_type TEXT DEFAULT 'video',
                media_file_id TEXT,
                bonus_channels TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # cart
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # orders
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                region TEXT NOT NULL,
                district TEXT NOT NULL,
                btc_point TEXT NOT NULL,
                btc_point_kod INTEGER,
                items TEXT NOT NULL,
                total_price INTEGER NOT NULL,
                discount_amount INTEGER DEFAULT 0,
                cashback_used INTEGER DEFAULT 0,
                final_price INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                payment_status TEXT DEFAULT 'pending',
                delivery_status TEXT DEFAULT 'pending',
                estimated_delivery TEXT,
                receipt_file_id TEXT,
                admin_notes TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # cashback_history
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cashback_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                operation TEXT DEFAULT 'add',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # settings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # admins
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                role TEXT DEFAULT 'admin',
                can_confirm_orders INTEGER DEFAULT 1,
                can_manage_users INTEGER DEFAULT 0,
                can_edit_products INTEGER DEFAULT 0,
                can_broadcast INTEGER DEFAULT 0,
                can_manage_settings INTEGER DEFAULT 0,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()


async def insert_default_settings():
    """Default settings va mahsulotlarni qo'shish"""
    default_settings = {
        "uzum_qr_file_id": "",
        "uzum_video_file_id": "",
        "doc_copyright_file_id": "",
        "doc_license_file_id": "",
        "channel_1_id": config.CHANNEL_1_ID,
        "channel_2_id": config.CHANNEL_2_ID,
    }

    async with aiosqlite.connect(config.DB_PATH) as db:
        for k, v in default_settings.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (k, v)
            )

        # Default kitoblar (agar bo'sh bo'lsa)
        async with db.execute("SELECT COUNT(*) FROM products") as cur:
            count = (await cur.fetchone())[0]

        if count == 0:
            # Qattiq muqova kitoblari
            qattiq_books = [
                ("Ko'ylaklar va koftalar 1 qism", 500000, 340000),
                ("Ko'ylaklar va koftalar 2 qism", 500000, 340000),
                ("Jaketlar va paltolar", 500000, 340000),
                ("Yubka va shimlar", 500000, 340000),
            ]
            for name, orig, disc in qattiq_books:
                await db.execute(
                    "INSERT INTO products (name, category, cover_type, original_price, discounted_price, stock) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, "book", "qattiq", orig, disc, 50)
                )

            # Yumshoq muqova kitoblari (7 ta)
            yumshoq_books = [
                ("Ko'ylaklar va koftalar 1 qism", 450000, 300000),
                ("Ko'ylaklar va koftalar 2 qism", 450000, 300000),
                ("Jaketlar va paltolar", 450000, 300000),
                ("Yubka va shimlar", 450000, 300000),
                ("Hisob kitob formulasi", 230000, 155000),
                ("Shimlar uchun hisob kitob formulasi", 230000, 155000),
                ("Ko'ylaklar uchun 15 ta modellashtirishlar", 280000, 195000),
            ]
            for name, orig, disc in yumshoq_books:
                await db.execute(
                    "INSERT INTO products (name, category, cover_type, original_price, discounted_price, stock) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, "book", "yumshoq", orig, disc, 50)
                )

        # Default to'plamlar
        async with db.execute("SELECT COUNT(*) FROM bundles") as cur:
            count = (await cur.fetchone())[0]

        if count == 0:
            qattiq_bundles = [
                ("Ko'ylaklar va koftalar (1+2 qism) + Hisob kitob formulasi", 1230000, 860000, "koylak"),
                ("Jaketlar va paltolar + Hisob kitob formulasi", 680000, 465000, "jaket"),
                ("Yubka va shimlar + Shimlar uchun hisob kitob formulasi", 730000, 515000, "yubka"),
                ("💎 PREMIUM TO'PLAM (Barcha kitoblar)", 2535000, 1765000, "koylak,jaket,yubka"),
            ]
            for name, orig, disc, channels in qattiq_bundles:
                await db.execute(
                    "INSERT INTO bundles (name, cover_type, original_price, discounted_price, bonus_channels) VALUES (?, ?, ?, ?, ?)",
                    (name, "qattiq", orig, disc, channels)
                )

            yumshoq_bundles = [
                ("Ko'ylaklar va koftalar (1+2 qism) + Hisob kitob formulasi", 1130000, 755000, "koylak"),
                ("Jaketlar va paltolar + Hisob kitob formulasi", 630000, 425000, "jaket"),
                ("Yubka va shimlar + Shimlar uchun hisob kitob formulasi", 680000, 455000, "yubka"),
                ("💎 PREMIUM TO'PLAM (Barcha kitoblar)", 2335000, 1565000, "koylak,jaket,yubka"),
            ]
            for name, orig, disc, channels in yumshoq_bundles:
                await db.execute(
                    "INSERT INTO bundles (name, cover_type, original_price, discounted_price, bonus_channels) VALUES (?, ?, ?, ?, ?)",
                    (name, "yumshoq", orig, disc, channels)
                )

        # Super adminlarni qo'shish
        for admin_id in config.ADMIN_IDS:
            await db.execute(
                """INSERT OR IGNORE INTO admins 
                (telegram_id, role, can_confirm_orders, can_manage_users, can_edit_products, can_broadcast, can_manage_settings) 
                VALUES (?, 'superadmin', 1, 1, 1, 1, 1)""",
                (admin_id,)
            )

        await db.commit()
