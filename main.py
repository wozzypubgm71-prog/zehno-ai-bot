import os
import sqlite3
import asyncio
import logging
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import google.generativeai as genai
from PIL import Image

# Terminal va Render Logs'da xatoliklarni aniq ko'rish uchun logging
logging.basicConfig(level=logging.INFO)

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ⚠️ ADMIN_ID ni qat'iy int turiga o'tkazamiz
ADMIN_ID = 1167476251  

# Gemini AI sozlamasi
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = (
    "Siz Zehno AI - sokratik usulda dars beruvchi intellektual repetitorsiz. "
    "Foydalanuvchiga hech qachon to'g'ridan-to'g'ri tayyor javobni bermang! "
    "Buning o'rniga qisqa, yo'naltiruvchi savollar berib, uni mustaqil fikrlashga va javobni o'zi topishiga undang. "
    "Muloqot tili: O'zbek tili."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# SQLite Ma'lumotlar bazasini sozlash (/tmp papkasiga xatosiz yozish uchun)
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
        logging.info("SQLite DB muvaffaqiyatli ishga tushirildi.")
    except Exception as e:
        logging.error(f"DB init xatosi: {e}")

# Foydalanuvchini bazaga qo'shish / Yangilash
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
        "Salom! Men Zehno AI sokratik repetitor botiman. Qanday savolingiz yoki misolingiz bor? Yoki rasmga olib yuboring!"
    )

# /stat komandasi (Faqat Admin uchun)
@dp.message(Command("stat"))
async def stat_handler(message: types.Message):
    user_id = message.from_user.id
    logging.info(f"/stat buyrug'i keldi. Foydalanuvchi ID: {user_id}")
    
    # Admin ID tekshiruvi
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
        await message.answer(f"Statistikani olishda xatolik yuz berdi: {e}")

# Rasmli xabarlarni tahlil qilish
@dp.message(F.photo)
async def photo_handler(message: types.Message):
    add_or_update_user(message.from_user)
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        photo_bytes = await bot.download_file(file_info.file_path)
        
        image = Image.open(io.BytesIO(photo_bytes.read()))
        caption = message.caption if message.caption else "Ushbu rasmdagi masalani/savolni tahlil qilib, menga sokratik usulda yordam ber."
        
        response = model.generate_content([caption, image])
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Rasm xatosi: {e}")
        await message.answer("Rasmni o'qishda xatolik yuz berdi. Iltimos, qaytadan aniqroq tushirib yuboring.")

# Matnli xabarlarni AI ga yuborish
@dp.message()
async def ai_handler(message: types.Message):
    add_or_update_user(message.from_user)
    try:
        response = model.generate_content(message.text)
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Gemini AI xatosi: {e}")
        await message.answer("Ayni vaqtda xatolik yuz berdi, iltimos birozdan so'ng qayta urinib ko'ring.")

async def main():
    init_db()
    logging.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
