import os
import sqlite3
import asyncio
import logging
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import google.generativeai as genai
from PIL import Image

# Logging
logging.basicConfig(level=logging.INFO)

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Admin Telegram ID
ADMIN_ID = 1167476251  

# Gemini AI sozlamasi
genai.configure(api_key=GEMINI_API_KEY)

# Haqiqiy Professional O'qituvchi Prompti
SYSTEM_PROMPT = (
    "Siz Zehno AI - professional, mehirli va har tomonlama bilimdon AI-o'qituvchisiz. "
    "Sizning vazifangiz foydalanuvchilarning har qanday savoliga to'liq, ishonchli, tushunarli va aniq javob berish. "
    "Agar foydalanuvchi matematik, fizikaviy yoki mantiqiy masala yuborsa: "
    "1. Avval masalaning yechilish formulasini va qoidasini ko'rsating. "
    "2. Masalani bosqichma-bosqich (step-by-step) ishlanishini tushuntiring. "
    "3. Yakuniy aniq javobni taqdim eting. "
    "Muloqotda o'zingizni sabr-toqatli, samimiy va bilim berishga tayyor haqiqiy o'qituvchidek tuting. "
    "Muloqot tili: O'zbek tili."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# SQLite Ma'lumotlar bazasi (/tmp papkasida)
DB_PATH = "/tmp/bot_database.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logging.info("SQLite DB tayyor.")
    except Exception as e:
        logging.error(f"DB init xatosi: {e}")

def add_or_update_user(user: types.User):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_active = CURRENT_TIMESTAMP
        """, (user.id, user.username, user.first_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB update xatosi: {e}")

# /start komandasi
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    add_or_update_user(message.from_user)
    await message.answer(
        "Assalomu alaykum! Men Zehno AI – sizning shaxsiy AI-o'qituvchingizman. 🎓\n\n"
        "Menga har qanday sohadan savol berishingiz, matematik misol va masalalaringizni yuborishingiz mumkin. "
        "Men sizga formulalar, bosqichma-bosqich yechimlar va to'liq javoblar berishga tayyorman!"
    )

# /stat komandasi (Faqat Admin uchun)
@dp.message(Command("stat"))
async def stat_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer(f"Siz admin emassiz! Sizning ID: `{user_id}`", parse_mode="Markdown")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active >= datetime('now', '-1 day')")
        active_24h = cursor.fetchone()[0]
        conn.close()

        stat_text = (
            "📊 **Zehno AI Bot Statistikasi:**\n\n"
            f"👥 **Jami foydalanuvchilar:** {total_users} ta\n"
            f"⚡ **Oxirgi 24 soatda faol:** {active_24h} ta"
        )
        await message.answer(stat_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Stat xatosi: {e}")
        await message.answer(f"Statistikani olishda xatolik: {e}")

# Rasmli masalalarni va savollarni tahlil qilish
@dp.message(F.photo)
async def photo_handler(message: types.Message):
    add_or_update_user(message.from_user)
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        photo_bytes = await bot.download_file(file_info.file_path)
        
        image = Image.open(io.BytesIO(photo_bytes.read()))
        caption = message.caption if message.caption else "Ushbu rasmdagi savol yoki masalani to'liq, formulalari va bosqichma-bosqich yechimi bilan tushuntirib ber."
        
        response = model.generate_content([caption, image])
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Rasm xatosi: {e}")
        await message.answer("Rasmni o'qishda xatolik yuz berdi. Iltimos, qaytadan aniqroq tushirib yuboring.")

# Matnli savollarga to'liq va professional javob berish
@dp.message()
async def ai_handler(message: types.Message):
    add_or_update_user(message.from_user)
    try:
        response = model.generate_content(message.text)
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Gemini AI xatosi: {e}")
        await message.answer("Xatolik yuz berdi, iltimos birozdan so'ng qayta urinib ko'ring.")

async def main():
    init_db()
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
