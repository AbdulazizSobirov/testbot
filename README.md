# MONS Academy Kitob Savdo Boti

Telegram bot - O'zbekiston bo'ylab kitob va to'plamlarni BTC pochta orqali yetkazib berish.

## ✨ Asosiy xususiyatlar

- 📚 7 ta kitob va 8 ta to'plam (Qattiq + Yumshoq muqova)
- 🛒 Savat tizimi (qty +/- inline tugmalari)
- 📋 To'liq rasmiylashtirish FSM (Ism → Telefon → Viloyat → Tuman → BTC punkt)
- 📦 **374 ta BTC pochta punkti** 14 viloyat/respublikada
- 🗺 Har bir punkt uchun Google Maps va Yandex Maps tugmalari
- 📍 Lokatsiya orqali eng yaqin 3 ta punktni topish
- 💳 UzCard/Humo (3-8% chegirma) va Uzum Nasiya (3 oyga foizsiz)
- 💰 Keshbek tizimi va Referal dasturi
- 🎁 Avtomatik bonus kanallar
- 👨‍💼 Super admin va oddiy admin (5 ta ruxsat)
- 📊 Google Sheets sinxronizatsiya
- ⏰ 30 daqiqalik auto-cancel timer

## 📋 Texnik stack

- Python 3.11+
- aiogram 3.7.0
- SQLite + aiosqlite
- gspread (Google Sheets)
- APScheduler
- python-dotenv

## 🚀 O'rnatish

### 1. Loyihani yuklash
```bash
cd /root
# Loyihani VPS ga yuklang (scp yoki git clone)
cd mons_bot
```

### 2. Virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. .env sozlash
```bash
cp .env.example .env
nano .env
```
Quyidagilarni to'ldiring:
- `BOT_TOKEN` - @BotFather dan oling
- `ADMIN_IDS` - super admin telegram ID lari (vergul bilan)
- `SPREADSHEET_ID` - Google Sheets ID (xohlasangiz)
- Kanallar va bonus kanallar
- UzCard kartani

### 4. Google Sheets (ixtiyoriy)
- Google Cloud Console da Service Account yarating
- `credentials.json` ni loyiha papkasiga qo'ying
- Spreadsheet ni service account email'iga "Editor" sifatida ulashing

### 5. Botni ishga tushirish

**Test qilish:**
```bash
python main.py
```

**Production (Supervisor):**
```bash
sudo cp supervisor_bot.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start mons_bot
```

## 📁 Fayl strukturasi

```
mons_bot/
├── main.py                      # Asosiy ishga tushirish
├── handlers/
│   ├── user_handlers.py         # /start, profil, yordam, referal, bonus
│   ├── admin_handlers.py        # Admin panel (to'liq)
│   ├── catalog_handlers.py      # Kitoblar va to'plamlar
│   ├── cart_handlers.py         # Savat
│   ├── order_handlers.py        # Rasmiylashtirish FSM
│   ├── payment_handlers.py      # UzCard, Uzum Nasiya
│   └── bonus_handlers.py        # Buyurtmalarim, status xabarlari
├── database/
│   ├── models.py                # Jadvallar yaratish
│   └── queries.py               # Barcha DB so'rovlari
├── keyboards/
│   ├── user_keyboards.py
│   └── admin_keyboards.py
├── states/
│   ├── user_states.py           # User FSM
│   └── admin_states.py          # Admin FSM
├── utils/
│   ├── config.py
│   ├── sheets.py                # Google Sheets sync
│   ├── btc_parser.py            # BTC funksiyalari
│   └── bonus.py                 # Chegirma, keshbek, kanallar
├── data/
│   ├── btc_points.py            # 374 ta BTC punkt
│   └── regions.py               # 14 viloyat va tumanlar
├── .env                         # Sozlamalar
├── requirements.txt
└── supervisor_bot.conf
```

## 🎯 BTC Punktlar tizimi

Bot 374 ta BTC pochta punktini quyidagi viloyatlarda qamrab oladi:

| Viloyat | Punktlar | Tumanlar |
|---|---|---|
| Andijon | 31 | 16 |
| Buxoro | 25 | 13 |
| Farg'ona | 29 | 17 |
| Jizzax | 15 | 13 |
| Namangan | 16 | 12 |
| Navoiy | 15 | 9 |
| Qashqadaryo | 26 | 15 |
| Qoraqalpog'iston Resp. | 14 | 11 |
| Samarqand | 37 | 16 |
| Sirdaryo | 12 | 10 |
| Surxondaryo | 15 | 12 |
| **Toshkent shahri** | **87** | 13 |
| Toshkent viloyati | 36 | 21 |
| Xorazm | 16 | 12 |
| **JAMI** | **374** | **190** |

### Mijoz uchun BTC punkt tanlash jarayoni:

1. **Viloyat tanlash** (14 ta tugma, 2 ustun)
2. **Tuman tanlash** (viloyatga qarab, 2 ustun)
3. **BTC punkt tanlash** (raqamli tugmalar yoki lokatsiya yuborish)
4. **Punkt ma'lumotlarini ko'rish** + Xaritada ko'rish:
   - 🗺 Google Maps tugmasi
   - 🗺 Yandex Maps tugmasi
   - ✅ Shu punktni tanlash

## 👨‍💼 Admin Panel

`/admin` buyrug'i orqali kirish.

**Bo'limlar:**
- 📦 Buyurtmalar (statuslar bo'yicha filtrlash)
- 👥 Foydalanuvchilar (top 10 xaridorlar)
- 📚 Mahsulotlar (CRUD)
- 📊 Statistika
- ✉️ Xabar yuborish (broadcast yoki bitta userga)
- ⚙️ Sozlamalar (kanallar, Uzum, hujjatlar)
- 👥 Adminlar boshqaruvi (super admin uchun)

## 📊 Buyurtma statuslari

```
⏳ pending     → Yangi, to'lov tekshirilmoqda
✅ confirmed   → To'lov qabul qilindi
📦 preparing   → Kitob tayyorlanmoqda
🚚 shipping    → BTC ga jo'natildi
✔️ completed   → Mijoz oldi (bonus kanallar avtomatik)
❌ cancelled   → Bekor qilindi (keshbek qaytarildi)
```

## 💰 Chegirmalar

- 📚 Kitob: **3%**
- 📦 To'plam: **5%**
- 💎 Premium to'plam: **8%**
- 👥 Referal keshbek: **3%**
- ⚠️ Uzum Nasiya: chegirma yo'q, keshbek yo'q

## 🐛 Loglarni ko'rish

```bash
tail -f /var/log/mons_bot.log
```

## ❓ Yordam

Loyiha bilan bog'liq savollar uchun adminlarga murojaat qiling.
