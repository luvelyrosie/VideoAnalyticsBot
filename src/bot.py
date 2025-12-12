import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from nl_to_sql import ask_question


load_dotenv()


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Add TELEGRAM_BOT_TOKEN to .env!")


bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я — бот для аналитики видео-статистики.\n"
        "Просто задавай любой вопрос на русском — отвечу одним числом.\n\n"
        "**Примеры вопросов:**\n\n"
        
        "**Основные вопросы из теста:**\n"
        "• Сколько всего видео есть в системе?\n"
        "• Сколько видео у креатора с id aca1061a9d324ecf8c3fa2bb32d7be63 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?\n"
        "• Сколько видео набрало больше 100000 просмотров за всё время?\n"
        "• На сколько просмотров в сумме выросли все видео 28 ноября 2025?\n"
        "• Сколько разных видео получали новые просмотры 27 ноября 2025?\n\n"
        
        "**Дополнительные примеры:**\n"
        "• Сколько видео набрало больше 1000 просмотров?\n"
        "• Сколько видео у креатора с id example123?\n"
        "• На сколько просмотров выросли все видео 26 ноября 2025?\n"
        "• Сколько различных видео получали новые просмотры 28 ноября 2025?\n"
        "• Сколько видео получило лайки?\n\n"
        
        "**Как задавать вопросы:**\n"
        "• Можно менять даты (1-5 ноября, 26-28 ноября и т.д.)\n"
        "• Можно менять ID креаторов\n"
        "• Можно менять числа просмотров (1000, 10000, 100000)\n"
        "• Всегда получаешь один числовой ответ!"
    )


@dp.message()
async def handle_question(message: types.Message):
    question = message.text.strip()
    try:
        answer = ask_question(question)
        await message.answer(str(answer))
    except Exception as e:
        print(f"Error in bot: {e}")
        await message.answer("0")


async def main():
    print("Bot is running and waiting for messages...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())