import asyncio
import json
import http.server
import socketserver
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import config
from database import init_db, add_balance, process_purchase

# 1. Запуск локального веб-сервера для отдачи папки static
PORT = 8000
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="static", **kwargs)

def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# 2. Инициализация бота
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# 3. Обработка команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Актуальная ссылка на Web App
    web_app_url = "https://brown-teams-shine.loca.lt/index.html"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Донат кардан ✅", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    welcome_text = (
        f"👋 **Ассалому алейкум ва раҳматуллоҳи ва баракотуҳ, {message.from_user.first_name}!**\n\n"
        f"💎 **Хуш омадед ба платформаи расмӣ ва боэътимоди «Fors Almaz Bot»!**\n\n"
        f"⚡️ Ин ҷо беҳтарин ва арзонтарин макон барои хариди алмосҳои Free Fire ва дигар хизматрасониҳои рақамӣ бо кафолати 100% мебошад.\n\n"
        f"📌 **Афзалиятҳои мо:**\n"
        f"└ 🚀 **Хариди худкор:** Иҷрои фаврии фармоишҳо дар чанд сония\n"
        f"└ 🛡 **Бехатарии комил:** Ҳимояи пурраи аккаунти шумо\n"
        f"└ 💰 **Нархҳои дастрас:** Беҳтарин тарифҳо дар бозори Тоҷикистон\n"
        f"└ 🔥 **Бозиҳои маҳбуб:** Махсус барои бозингарони Free Fire ва дигар лоиҳаҳо\n"
        f"└ 👨‍💻 **Дастгирии 24/7:** Ҳамеша омодаем ба саволҳои шумо ҷавоб диҳем\n\n"
        f"👇 Барои ворид шудан ба мағоза ва харид, тугмаи зеринро пахш кунед:"
    )
    
    await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")

# 4. Обработка отправки чека (скриншота/фото)
@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Тасдиқ (20 TJS)", callback_data=f"app_{user_id}_20"),
            InlineKeyboardButton(text="❌ Рад кардан", callback_data=f"rej_{user_id}")
        ]
    ])
    
    await bot.send_photo(
        config.ADMIN_ID,
        photo=photo_id,
        caption=f"📥 Чек аз корбар: `{user_id}`\nСуммаро интихоб кунед ва тасдиқ кунед:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await message.answer("📩 Чеки шумо бо муваффақият ба админ фиристода шуд. Пас аз санҷиш баланси шумо пур карда мешавад.")

# 5. Обработка подтверждения оплаты администратором
@dp.callback_query(F.data.startswith("app_"))
async def approve(call: types.CallbackQuery):
    _, user_id, amount = call.data.split("_")
    add_balance(int(user_id), float(amount))
    await call.message.edit_caption(caption=call.message.caption + "\n\n✅ **ПАРДОХТ ТАСДИҚ ШУД!**")
    await bot.send_message(int(user_id), f"🎉 Баланси шумо бо муваффақият ба миқдори **+{amount} сомонӣ** пур карда шуд!")

# 6. Главная функция запуска
async def main():
    init_db()
    print("Бот и сервер интерфейса успешно запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())