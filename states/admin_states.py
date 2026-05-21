# -*- coding: utf-8 -*-
"""
Admin FSM states
"""
from aiogram.fsm.state import State, StatesGroup


class ProductStates(StatesGroup):
    """Yangi mahsulot qo'shish"""
    name = State()
    category = State()
    cover_type = State()
    original_price = State()
    discounted_price = State()
    stock = State()
    media = State()


class EditProductStates(StatesGroup):
    """Mahsulotni tahrirlash"""
    waiting_price = State()
    waiting_stock = State()
    waiting_media = State()


class ShipmentStates(StatesGroup):
    """Jo'natdim + vaqt yozish"""
    waiting_time = State()


class BroadcastStates(StatesGroup):
    """Hammaga xabar yuborish"""
    waiting_message = State()


class SingleMessageStates(StatesGroup):
    """Bitta userga xabar yuborish"""
    waiting_user_id = State()
    waiting_message = State()


class SettingsStates(StatesGroup):
    """Sozlamalarni o'zgartirish"""
    waiting_uzum_qr = State()
    waiting_uzum_video = State()
    waiting_copyright_doc = State()
    waiting_license_doc = State()
    waiting_channel_1 = State()
    waiting_channel_2 = State()
    waiting_price = State()
    waiting_discount = State()


class AdminManagementStates(StatesGroup):
    """Admin boshqaruvi"""
    waiting_admin_id = State()
    waiting_permissions = State()


class CancelOrderStates(StatesGroup):
    """Buyurtmani bekor qilish sababi"""
    waiting_reason = State()
