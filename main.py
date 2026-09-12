import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import google.generativeai as genai

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ⚠️ O'zingizning Telegram ID-ingizni kiriting (@userinfobot orqali bilib olishingiz mumkin)
ADMIN_ID = 1167476251  

# AI va Botni sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# SQLite Ma'lumotlar bazasini sozlash
def init_db():
    conn = sqlite3.connect("bot_database.db")
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

# Foydalanuvchini bazaga qo'shish / Yangilash
def add_or_update_user(user: types.User):
    conn = sqlite3.connect("bot_database.db")
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

# /start komandasi
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    add_or_update_user(message.from_user)
    await message.answer(
        "Salom! Men Zehno AI sokratik repetitor botiman. Qanday savolingiz bor?"
    )

# /stat komandasi (Faqat Admin uchun)
@dp.message(Command("stat"))
async def stat_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return  # Admin bo'lmaganlarga javob qaytarilmaydi

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    # Jami foydalanuvchilar soni
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # Oxirgi 24 soat ichida faol bo'lganlar
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_active >= datetime('now', '-1 day')")
    active_24h = cursor.fetchone()[0]
    
    conn.close()

    stat_text = (
        "📊 **Zehno AI Bot Statistikasi:**\n\n"
        f"👥 **Jami foydalanuvchilar:** {total_users} ta\n"
        f"⚡ **Oxirgi 24 soatda faol:** {active_24h} ta"
    )
    await message.answer(stat_text, parse_mode="Markdown")

# Barcha matnli xabarlarni AI ga yuborish
@dp.message()
async def ai_handler(message: types.Message):
    add_or_update_user(message.from_user)
    try:
        response = model.generate_content(message.text)
        await message.answer(response.text)
    except Exception as e:
        await message.answer("Xatolik yuz berdi, qaytadan urinib ko'ring.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
