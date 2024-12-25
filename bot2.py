from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
from datetime import datetime, timedelta
import aiohttp

BOT_TOKEN = "7210002949:AAGkhUGyZ2e76bdKLLRKZRE4Wel1YCfA0hw"
API_URL = "https://api.binance.com/api/v3/ticker/price"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

crypto_history = {}
user_settings = {}

default_interval = 10  # Default interval in minutes
default_threshold = 10.0  # Default threshold in percentage


# FSM States
class SettingsStates(StatesGroup):
    waiting_for_threshold = State()
    waiting_for_interval = State()


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

            # Remove entries older than 1 hour
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
            if old_price != 0:  # Avoid division by zero
                change = ((current_price - old_price) / old_price) * 100
                changes[symbol] = change
    return changes


@dp.message(Command(commands=["start", "help"]))
async def send_welcome(message: Message):
    await message.answer("Привет! Я помогу отслеживать изменения цен на криптовалюты.\n"
                         "Напишите /set_threshold, чтобы задать порог отклонения.\n"
                         "Напишите /set_interval, чтобы задать временной промежуток.")


@dp.message(Command(commands=["set_threshold"]))
async def set_threshold(message: Message, state: FSMContext):
    await message.answer("Введите порог изменения цены в процентах (например, 10 для 10%):")
    await state.set_state(SettingsStates.waiting_for_threshold)


@dp.message(SettingsStates.waiting_for_threshold)
async def get_threshold(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"threshold": default_threshold, "interval": default_interval}

    try:
        threshold = float(message.text)
        user_settings[user_id]["threshold"] = threshold
        await message.answer(f"Порог установлен: {threshold}%.")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите числовое значение.")


@dp.message(Command(commands=["set_interval"]))
async def set_interval(message: Message, state: FSMContext):
    await message.answer("Введите временной промежуток в минутах (например, 10 для 10 минут):")
    await state.set_state(SettingsStates.waiting_for_interval)


@dp.message(SettingsStates.waiting_for_interval)
async def get_interval(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"threshold": default_threshold, "interval": default_interval}

    try:
        interval = int(message.text)
        user_settings[user_id]["interval"] = interval
        await message.answer(f"Временной промежуток установлен: {interval} минут.")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите числовое значение.")


@dp.message(Command(commands=["get_top10"]))
async def get_top_10(message: Message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {"threshold": default_threshold, "interval": default_interval})
    threshold = settings["threshold"]
    interval = settings["interval"]

    current_time = datetime.now().strftime('%H:%M')
    target_time = (datetime.now() - timedelta(minutes=interval)).strftime('%H:%M')

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

    response = f"★ Топ 10 монет с изменением, близким к {threshold}% за последние {interval} минут:\n"
    for symbol, change in top_10:
        direction = "⬆" if change > 0 else "⬇"
        response += f"{symbol}: {change:.2f}% {direction}\n"
    await message.answer(response)


async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Получить помощь"),
        BotCommand(command="set_threshold", description="Задать порог изменения цены"),
        BotCommand(command="set_interval", description="Задать временной промежуток"),
        BotCommand(command="get_top10", description="Получить ТОП-10 монет"),
    ])

    # Start recording prices
    asyncio.create_task(record_prices())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
