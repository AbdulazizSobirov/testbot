# -*- coding: utf-8 -*-
"""
User FSM states - foydalanuvchi uchun FSM holatlari
"""
from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """Buyurtmani rasmiylashtirish (1/4-4/4)"""
    full_name = State()
    phone = State()
    region = State()
    district = State()
    btc_point = State()
    cashback_choice = State()
    cashback_amount = State()
    payment_method = State()
    waiting_receipt = State()
    uzum_waiting_receipt = State()
    confirm = State()


class ProfileStates(StatesGroup):
    """Profilni tahrirlash"""
    edit_name = State()
    edit_phone = State()
    edit_region = State()
    edit_district = State()
    edit_btc_point = State()


class SupportStates(StatesGroup):
    """Adminga xabar yuborish"""
    writing_message = State()


class AdminReplyStates(StatesGroup):
    """Admin javobini kutish (har bir user uchun)"""
    waiting_reply = State()
