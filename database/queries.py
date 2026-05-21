# -*- coding: utf-8 -*-
"""
Database so'rovlari - barcha DB operatsiyalari
"""
import aiosqlite
import json
from datetime import datetime
from utils.config import config


# ==================== USERS ====================

async def get_user(telegram_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_user(telegram_id: int, username: str = None, referrer_id: int = None):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, referrer_id) VALUES (?, ?, ?)",
            (telegram_id, username, referrer_id)
        )
        await db.commit()


async def update_user_profile(telegram_id: int, **kwargs):
    """Profilning istalgan maydonlarini yangilash"""
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [telegram_id]
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE telegram_id = ?", values)
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY registration_date DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_user_cashback(telegram_id: int) -> int:
    user = await get_user(telegram_id)
    return user["cashback_balance"] if user else 0


async def add_cashback(user_id: int, from_user_id: int, order_id: int, amount: int, operation: str = "add"):
    """Keshbek qo'shish"""
    async with aiosqlite.connect(config.DB_PATH) as db:
        if operation == "add":
            await db.execute(
                "UPDATE users SET cashback_balance = cashback_balance + ? WHERE telegram_id = ?",
                (amount, user_id)
            )
        await db.execute(
            "INSERT INTO cashback_history (user_id, from_user_id, order_id, amount, operation) VALUES (?, ?, ?, ?, ?)",
            (user_id, from_user_id, order_id, amount, operation)
        )
        await db.commit()


async def deduct_cashback(user_id: int, amount: int, order_id: int):
    """Keshbekni kamaytirish (xarid uchun)"""
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET cashback_balance = cashback_balance - ? WHERE telegram_id = ?",
            (amount, user_id)
        )
        await db.execute(
            "INSERT INTO cashback_history (user_id, from_user_id, order_id, amount, operation) VALUES (?, ?, ?, ?, 'deduct')",
            (user_id, user_id, order_id, amount)
        )
        await db.commit()


async def refund_cashback(user_id: int, amount: int, order_id: int):
    """Keshbekni qaytarish (bekor qilingan buyurtmadan)"""
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET cashback_balance = cashback_balance + ? WHERE telegram_id = ?",
            (amount, user_id)
        )
        await db.execute(
            "INSERT INTO cashback_history (user_id, from_user_id, order_id, amount, operation) VALUES (?, ?, ?, ?, 'refund')",
            (user_id, user_id, order_id, amount)
        )
        await db.commit()


async def get_cashback_history(user_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM cashback_history WHERE user_id = ? ORDER BY created_date DESC LIMIT 10",
            (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_referrals(user_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE referrer_id = ?",
            (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ==================== PRODUCTS ====================

async def get_products_by_cover(cover_type: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE cover_type = ? AND is_active = 1 ORDER BY id",
            (cover_type,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_product(product_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_product(product_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [product_id]
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(f"UPDATE products SET {fields} WHERE id = ?", values)
        await db.commit()


async def insert_product(**kwargs):
    keys = ", ".join(kwargs.keys())
    placeholders = ", ".join("?" for _ in kwargs)
    values = list(kwargs.values())
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(f"INSERT INTO products ({keys}) VALUES ({placeholders})", values)
        await db.commit()
        return cur.lastrowid


async def decrease_stock(product_id: int, quantity: int = 1):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (quantity, product_id)
        )
        await db.commit()


# ==================== BUNDLES ====================

async def get_bundles_by_cover(cover_type: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bundles WHERE cover_type = ? AND is_active = 1 ORDER BY id",
            (cover_type,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_bundle(bundle_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bundles WHERE id = ?", (bundle_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_bundle(bundle_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [bundle_id]
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(f"UPDATE bundles SET {fields} WHERE id = ?", values)
        await db.commit()


# ==================== CART ====================

async def add_to_cart(user_id: int, item_type: str, item_id: int, quantity: int = 1):
    async with aiosqlite.connect(config.DB_PATH) as db:
        # Avval shu mahsulot allaqachon savatda bor-yo'qligini tekshirish
        async with db.execute(
            "SELECT id, quantity FROM cart WHERE user_id = ? AND item_type = ? AND item_id = ?",
            (user_id, item_type, item_id)
        ) as cur:
            existing = await cur.fetchone()

        if existing:
            await db.execute(
                "UPDATE cart SET quantity = quantity + ? WHERE id = ?",
                (quantity, existing[0])
            )
        else:
            await db.execute(
                "INSERT INTO cart (user_id, item_type, item_id, quantity) VALUES (?, ?, ?, ?)",
                (user_id, item_type, item_id, quantity)
            )
        await db.commit()


async def get_cart(user_id: int):
    """Savatni to'liq ma'lumotlar bilan qaytaradi"""
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM cart WHERE user_id = ? ORDER BY id",
            (user_id,)
        ) as cur:
            cart_items = [dict(r) for r in await cur.fetchall()]

    # Har bir item uchun mahsulot ma'lumotlarini olish
    result = []
    for item in cart_items:
        if item["item_type"] == "product":
            product = await get_product(item["item_id"])
            if product:
                result.append({**item, "details": product})
        elif item["item_type"] == "bundle":
            bundle = await get_bundle(item["item_id"])
            if bundle:
                result.append({**item, "details": bundle})
    return result


async def update_cart_quantity(cart_id: int, quantity: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        if quantity <= 0:
            await db.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
        else:
            await db.execute("UPDATE cart SET quantity = ? WHERE id = ?", (quantity, cart_id))
        await db.commit()


async def remove_from_cart(cart_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
        await db.commit()


async def clear_cart(user_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_cart_total(user_id: int) -> int:
    cart = await get_cart(user_id)
    return sum(item["details"]["discounted_price"] * item["quantity"] for item in cart)


# ==================== ORDERS ====================

async def generate_order_code() -> str:
    """Buyurtma kodi: ORD-2026-001"""
    year = datetime.now().year
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE order_code LIKE ?",
            (f"ORD-{year}-%",)
        ) as cur:
            count = (await cur.fetchone())[0]
    return f"ORD-{year}-{count + 1:03d}"


async def create_order(data: dict) -> int:
    """Yangi buyurtma yaratish, ID qaytaradi"""
    order_code = await generate_order_code()
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO orders (
                order_code, user_id, full_name, phone, region, district, btc_point, btc_point_kod,
                items, total_price, discount_amount, cashback_used, final_price, payment_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_code,
            data["user_id"],
            data["full_name"],
            data["phone"],
            data["region"],
            data["district"],
            data["btc_point"],
            data.get("btc_point_kod"),
            json.dumps(data["items"], ensure_ascii=False),
            data["total_price"],
            data.get("discount_amount", 0),
            data.get("cashback_used", 0),
            data["final_price"],
            data["payment_method"],
        ))
        await db.commit()
        return cur.lastrowid


async def get_order(order_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            if row:
                d = dict(row)
                d["items"] = json.loads(d["items"])
                return d
            return None


async def get_order_by_code(order_code: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE order_code = ?", (order_code,)) as cur:
            row = await cur.fetchone()
            if row:
                d = dict(row)
                d["items"] = json.loads(d["items"])
                return d
            return None


async def update_order(order_id: int, **kwargs):
    if not kwargs:
        return
    kwargs["updated_date"] = datetime.now().isoformat()
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [order_id]
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(f"UPDATE orders SET {fields} WHERE id = ?", values)
        await db.commit()


async def get_user_orders(user_id: int, active_only: bool = False):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if active_only:
            query = """SELECT * FROM orders WHERE user_id = ? 
                       AND delivery_status NOT IN ('completed', 'cancelled')
                       ORDER BY created_date DESC"""
        else:
            query = "SELECT * FROM orders WHERE user_id = ? ORDER BY created_date DESC"
        async with db.execute(query, (user_id,)) as cur:
            result = []
            for r in await cur.fetchall():
                d = dict(r)
                d["items"] = json.loads(d["items"])
                result.append(d)
            return result


async def get_orders_by_status(status: str):
    """status: pending|confirmed|preparing|shipping|completed|cancelled"""
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE delivery_status = ? ORDER BY created_date DESC",
            (status,)
        ) as cur:
            result = []
            for r in await cur.fetchall():
                d = dict(r)
                d["items"] = json.loads(d["items"])
                result.append(d)
            return result


async def get_all_orders():
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders ORDER BY created_date DESC") as cur:
            result = []
            for r in await cur.fetchall():
                d = dict(r)
                d["items"] = json.loads(d["items"])
                result.append(d)
            return result


async def get_pending_orders_older_than(minutes: int):
    """30 daqiqadan ko'p kutib turgan buyurtmalar"""
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM orders 
               WHERE payment_status = 'pending' AND delivery_status = 'pending'
               AND datetime(created_date) <= datetime('now', ?)""",
            (f"-{minutes} minutes",)
        ) as cur:
            result = []
            for r in await cur.fetchall():
                d = dict(r)
                d["items"] = json.loads(d["items"])
                result.append(d)
            return result


# ==================== SETTINGS ====================

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


# ==================== ADMINS ====================

async def is_admin(telegram_id: int) -> bool:
    if telegram_id in config.ADMIN_IDS:
        return True
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute("SELECT id FROM admins WHERE telegram_id = ?", (telegram_id,)) as cur:
            return (await cur.fetchone()) is not None


async def is_superadmin(telegram_id: int) -> bool:
    if telegram_id in config.ADMIN_IDS:
        return True
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM admins WHERE telegram_id = ? AND role = 'superadmin'",
            (telegram_id,)
        ) as cur:
            return (await cur.fetchone()) is not None


async def get_admin(telegram_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins WHERE telegram_id = ?", (telegram_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_admins():
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins ORDER BY added_date") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_admin(telegram_id: int, username: str, added_by: int, **permissions):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO admins 
               (telegram_id, username, role, can_confirm_orders, can_manage_users, 
                can_edit_products, can_broadcast, can_manage_settings, added_by)
               VALUES (?, ?, 'admin', ?, ?, ?, ?, ?, ?)""",
            (
                telegram_id, username,
                permissions.get("can_confirm_orders", 1),
                permissions.get("can_manage_users", 0),
                permissions.get("can_edit_products", 0),
                permissions.get("can_broadcast", 0),
                permissions.get("can_manage_settings", 0),
                added_by
            )
        )
        await db.commit()


async def remove_admin(telegram_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE telegram_id = ? AND role != 'superadmin'", (telegram_id,))
        await db.commit()


# ==================== STATISTICS ====================

async def get_statistics():
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM orders WHERE delivery_status = 'completed'"
        ) as cur:
            buyers = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL"
        ) as cur:
            referrals = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM orders") as cur:
            total_orders = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COALESCE(SUM(final_price), 0) FROM orders WHERE payment_status = 'confirmed'"
        ) as cur:
            total_revenue = (await cur.fetchone())[0]

    return {
        "total_users": total_users,
        "buyers": buyers,
        "referrals": referrals,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
    }


async def get_top_buyers(limit: int = 10):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.telegram_id, u.username, u.full_name,
                   COUNT(o.id) as order_count, COALESCE(SUM(o.final_price), 0) as total_spent
            FROM users u
            JOIN orders o ON o.user_id = u.telegram_id
            WHERE o.payment_status = 'confirmed'
            GROUP BY u.telegram_id
            ORDER BY total_spent DESC
            LIMIT ?
        """, (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]
