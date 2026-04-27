import asyncio
import random
import threading
import os
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ (ПРОПИСАНЫ НАПРЯМУЮ) ---
TOKEN = "8718665017:AAEZsiGeEmTeaIkayV6IIw7DiLCSKdv8H7E"
ADMIN_ID = 7137923579
CHANNEL_ID = -1003639433974 
PORT = int(os.environ.get("PORT", 10000))

# ID Премиум Эмодзи
EMOJI_START = "5424818078833715060"
EMOJI_JOIN = "5206607081334906820"
EMOJI_PRIVATE = "5447644880824181073"
EMOJI_WAIT = "5436113877181941026"
EMOJI_WIN = "5461151367559141950"

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Данные в оперативной памяти
participants = []
active_lottery_prize = "Не указана"
chat_ids = set()

# --- WEB СЕРВЕР ДЛЯ RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # Render передает порт в переменной окружения PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА БОТА ---
def get_emoji(emoji_id):
    return f'<tg-emoji id="{emoji_id}">🔘</tg-emoji>'

async def check_subscribe(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

@dp.message(Command("lottery"))
async def cmd_lottery(message: types.Message, command: CommandObject):
    if message.chat.type == "private":
        return await message.answer(f"{get_emoji(EMOJI_PRIVATE)}Я работаю только в группах!")
    
    if not command.args:
        return await message.answer("Ошибка! Напишите награду: /lottery 1000 рублей")

    global participants, active_lottery_prize
    participants = []
    active_lottery_prize = command.args
    chat_ids.add(message.chat.id)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Участвовать", callback_data="join_lottery"))

    await message.answer(
        f"{get_emoji(EMOJI_START)} Лотерея запущена!\n"
        f"Победитель получит: <b>{active_lottery_prize}</b>\n\n"
        f"Для участия нажмите {get_emoji(EMOJI_JOIN)}Участвовать ниже 👇",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "join_lottery")
async def join_callback(callback: types.CallbackQuery):
    is_sub = await check_subscribe(callback.from_user.id)
    
    if not is_sub:
        return await callback.answer("❌ Сначала подпишись на канал!", show_alert=True)

    if any(p.id == callback.from_user.id for p in participants):
        return await callback.answer("✅ Ты уже в списке!", show_alert=True)
    
    participants.append(callback.from_user)
    
    try:
        log_text = (
            f"📥 <b>Новый участник!</b>\n"
            f"Имя: {callback.from_user.full_name}\n"
            f"ID: <code>{callback.from_user.id}</code>\n"
            f"User: @{callback.from_user.username or '—'}\n"
            f"Чат: {callback.message.chat.title}"
        )
        await bot.send_message(ADMIN_ID, log_text)
    except:
        pass

    await callback.answer("Успешно! Ты участвуешь.")

@dp.message(Command("lt"))
async def cmd_stop(message: types.Message):
    global participants
    if message.from_user.id != ADMIN_ID: return

    if not participants:
        return await message.answer("Участников нет.")

    msg = await message.answer(f"{get_emoji(EMOJI_WAIT)}Подвожу итоги.")
    await asyncio.sleep(8)
    await msg.delete()

    winner = random.choice(participants)
    winner_link = f'<a href="tg://user?id={winner.id}">{winner.full_name}</a>'
    
    await message.answer(
        f"{get_emoji(EMOJI_WIN)}Победитель лотереи: {winner_link}\n"
        f"Приз: <b>{active_lottery_prize}</b>"
    )
    participants = [] 

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID or not command.args: return
    
    sent_count = 0
    for c_id in list(chat_ids):
        try: 
            await bot.send_message(c_id, command.args)
            sent_count += 1
        except: continue
    await message.answer(f"📢 Рассылка завершена ({sent_count} чатов).")

@dp.message(F.chat.type == "private")
async def private_msg(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Бот онлайн. Команды: /admin [текст]")
    else:
        await message.answer(f"{get_emoji(EMOJI_PRIVATE)}Я работаю только в группах!")

@dp.my_chat_member()
async def on_my_chat_member(update: types.ChatMemberUpdated):
    if update.new_chat_member.status in ["member", "administrator"]:
        chat_ids.add(update.chat.id)

async def main():
    # Запуск Flask в потоке
    threading.Thread(target=run_flask, daemon=True).start()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
