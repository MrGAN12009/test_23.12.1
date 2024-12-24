import asyncio
from datetime import datetime, timedelta
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types.bot_command import BotCommand

BOT_TOKEN = ""
API_URL = "https://api.binance.com/api/v3/ticker/price"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

crypto_history = {}
user_threshold = {}

async def fetch_crypto_prices():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as response:
            if response.status == 200:
                data = await response.json()
                return {item['symbol'][:-3]: float(item['price']) for item in data if item['symbol'].endswith('USD')}
            return {}

async def record_prices():
    global crypto_history
    while True:
        try:
            current_prices = await fetch_crypto_prices()
            current_time = datetime.now().strftime('%H:%M')
            crypto_history[current_time] = current_prices

            #Удаление записай старше 1 часа
            one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%H:%M')
            if one_hour_ago in crypto_history:
                del crypto_history[one_hour_ago]

        except Exception as e:
            print(f"Error fetching prices: {e}")

        await asyncio.sleep(60)

async def calculate_changes(target_time, current_prices):
    old_prices = crypto_history.get(target_time, {})
    changes = {}
    for symbol, current_price in current_prices.items():
        if symbol in old_prices:
            old_price = old_prices[symbol]
            if old_price != 0:  # избегаем деления на 0
                change = ((current_price - old_price) / old_price) * 100
                changes[symbol] = change
    return changes

@dp.message(Command(commands=["start", "help"]))
async def send_welcome(message: Message):
    await message.answer("Привет! Я помогу отслеживать изменения цен на криптовалюты. Напишите /set_threshold, чтобы задать порог отклонения.")

@dp.message(Command(commands=["set_threshold"]))
async def set_threshold(message: Message):
    await message.answer("Введите порог изменения цены в процентах (например, 10 для 10%):")

    @dp.message()
    async def get_threshold(message: Message):
        try:
            threshold = float(message.text)
            user_threshold[message.from_user.id] = threshold
            await message.answer(f"Порог установлен: {threshold}%.")
        except ValueError:
            await message.answer("Пожалуйста, введите числовое значение.")

@dp.message(Command(commands=["get_top10"]))
async def get_top_10(message: Message):
    user_id = message.from_user.id
    threshold = user_threshold.get(user_id, 10)  # Значение по умолчанию: 10%

    current_time = datetime.now().strftime('%H:%M')
    target_time = (datetime.now() - timedelta(minutes=10)).strftime('%H:%M')

    if target_time not in crypto_history:
        await message.answer("Данные за указанное время недоступны. Подождите немного, пока накопятся данные.")
        return

    current_prices = crypto_history.get(current_time, {})
    changes = await calculate_changes(target_time, current_prices)

    sorted_coins = sorted(changes.items(), key=lambda x: abs(x[1] - threshold))
    top_10 = sorted_coins[:10]

    if not top_10:
        await message.answer("Нет монет, близких к заданному порогу отклонения.")
        return

    response = f"★ Топ 10 монет с изменением, близким к {threshold}% за последние 10 минут:\n"
    for symbol, change in top_10:
        direction = "⬆" if change > 0 else "⬇"
        response += f"{symbol}: {change:.2f}% {direction}\n"
    await message.answer(response)

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Получить помощь"),
        BotCommand(command="set_threshold", description="Задать порог изменения цены"),
        BotCommand(command="get_top10", description="Получить ТОП-10 монет"),
    ])

    #Запуск записи цен
    asyncio.create_task(record_prices())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())