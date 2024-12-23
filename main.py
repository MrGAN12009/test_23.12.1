import time
import requests
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types.bot_command import BotCommand
from aiogram.client.session.aiohttp import AiohttpSession
import threading


BOT_TOKEN = "7366620789:AAHVh92T3-jp1EXkE4bRWEaxNzBWAFoKERM"
bot = Bot(token=BOT_TOKEN, session=AiohttpSession())
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


API_URL = "https://api.binance.com/api/v3/ticker/price"
crypto_prices = {}


def get_crypto_prices():
    global crypto_prices
    print(1)
    while True:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            top_20 = {item['symbol'][:-4]: float(item['price']) for item in data if item['symbol'].endswith('USDT')}
            crypto_prices = dict(list(top_20.items())[:20])
        else:
            continue
        time.sleep(600)


# global courses
user_selected_coin = {}


@dp.message(Command(commands=["start", "help"]))
async def send_welcome(message: Message):
    await message.answer("Привет! Я помогу узнать стоимость ТОП-20 криптомонет. Напишите /buy, чтобы начать покупку.")


@dp.message(Command(commands=["buy"]))
async def choose_coin(message: Message):
    global crypto_prices

    buttons = [
        InlineKeyboardButton(text=coin, callback_data=f"coin_{coin}")
        for coin in crypto_prices.keys()
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            buttons[i:i + 5] for i in range(0, len(buttons), 5)
        ]
    )

    await message.answer("Выберите монету, которую хотите купить:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("coin_"))
async def coin_selected(callback_query: CallbackQuery):
    global user_selected_coin
    coin = callback_query.data.split("_")[1]
    user_selected_coin[callback_query.from_user.id] = coin
    await bot.send_message(callback_query.from_user.id, f"Сколько {coin} вы хотите купить?")

    @dp.message()
    async def get_amount(message: Message):
        try:
            user_id = message.from_user.id
            if user_id not in user_selected_coin:
                await message.answer("Пожалуйста, сначала выберите монету через /buy.")
                return

            coin = user_selected_coin[user_id]
            amount = float(message.text)
            price = crypto_prices.get(coin, 0)
            total_cost = amount * price
            button = InlineKeyboardButton(text="Кнопка 1", callback_data="pay")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [button],  # Одна кнопка в строке
                ]
            )
            await message.answer(
                f"{amount} {coin} будет стоить {total_cost:.2f} USDT. Для оплаты нажмите кнопку ниже.",
                reply_markup=keyboard
            )
        except ValueError as ex:
            print(ex)
            await message.answer("Пожалуйста, введите числовое значение.")


@dp.callback_query(lambda c: c.data == "pay")
async def process_payment(callback_query: CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Оплата пока не настроена. Это тестовая кнопка.")


async def main():
    # Установка команд для бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Получить помощь"),
        BotCommand(command="buy", description="Купить криптовалюту"),
    ])

    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    thread = threading.Thread(target=get_crypto_prices)
    thread.start()
    asyncio.run(main())

