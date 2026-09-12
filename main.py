import asyncio
import io
import nest_asyncio
from PIL import Image
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart

nest_asyncio.apply()

BOT_TOKEN = ""
GEMINI_API_KEY = ""

SYSTEM_PROMPT = """
Sening isming - Zehno AI. Sen barcha fanlar bo'yicha maktab va universitet o'quvchilari uchun universal, mehribon va mahoratli Sokratik o'qituvchisiz.

SENING ASOSIY MAQSADING:
Murakkab va qiyin tuyulgan har qanday mavzu, formula, rasm, masala yoki hodisani O'QUVCHIGA JUDA SODDA, TUSHUNARLI VA HAYOTIY MISOL LAR BILAN TUSHUNTIRISH.

O'QITISH QOIDALARI:
1. UNIVERSALLIK:
   - Matematika, Fizika, Kimyo, Biologiya, Tarix, Ona tili, Ingliz tili, Dasturlash va boshqa barcha fanlar bo'yicha birdek mukammal yordam ber.

2. SODDALASHTIRISH VA HAYOTIY O'XSHATISHLAR:
   - Har qanday murakkab tushunchani hayotiy sodda misollar bilan tushuntir.

3. RASM BILAN ISHLASH (VISION):
   - Agar o'quvchi rasm yuborsa (daftardagi misol, kitob sahifasi yoki sxema), rasmdagi matn va masalani aniq o'qi.
   - HECH QACHON tayyor oxirgi javobni shartta berib qo'yma!
   - Masala qayerida xatolik borligini yoki birinchi bo'lib qaysi qadamdan boshlash kerakligini ko'rsatib, yo'naltiruvchi savol ber.

4. MOSLASHUVCHANLIK:
   - O'quvchi "Tushunmadim" desa, tushuntirishni YANADA SODDALASHTIR va osonroq qadamlar ber.
"""

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-3.6-flash",
    system_instruction=SYSTEM_PROMPT
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_sessions = {}

def get_user_chat(user_id: int):
    if user_id not in user_sessions:
        user_sessions[user_id] = model.start_chat(history=[])
    return user_sessions[user_id]

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        f"Salom, {message.from_user.first_name}! 🧠 **Zehno AI**ga xush kelibsiz!\n\n"
        "Menga matnli savol yuborishingiz yoki daftaringizdagi masala/misol rasmga olib yuborishingiz mumkin. Birgalikda oson va sodda qilib o'rganamiz!"
    )

# MATNLI XABARLAR UCHUN HANDLER
@dp.message(F.text)
async def handle_text(message: types.Message):
    chat = get_user_chat(message.from_user.id)
    for attempt in range(3):
        try:
            response = chat.send_message(message.text)
            await message.answer(response.text)
            return
        except Exception as e:
            if attempt == 2:
                await message.answer("Serverda biroz uzilish bo'ldi, iltimos qayta yozing.")
            else:
                await asyncio.sleep(1)

# RASMLI XABARLAR UCHUN HANDLER (VISION)
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    processing_msg = await message.answer("📷 Rasmni tahlil qilyapman, biroz kuting...")
    try:
        # Eng yuqori sifatli rasmni olish
        photo = message.photo[-1]
        photo_bytes = io.BytesIO()
        await bot.download(photo, destination=photo_bytes)
        photo_bytes.seek(0)
        
        # PIL orqali rasmni ochish
        img = Image.open(photo_bytes)
        
        # Caption (rasm ostidagi matn) bo'lsa uni ham qo'shish
        user_caption = message.caption if message.caption else "Ushbu rasmdagi masalani tushunishga yordam ber."
        
        chat = get_user_chat(message.from_user.id)
        response = chat.send_message([user_caption, img])
        
        await processing_msg.delete()
        await message.answer(response.text)
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"Rasmni o'qishda xatolik bo'ldi: {e}")

async def main():
    print("Zehno AI Universal (Text + Vision) Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
