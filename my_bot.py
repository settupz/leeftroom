import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Считываем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

# Эта функция будет отвечать на любое текстовое сообщение
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет эхо в ответ на сообщение."""
    # Выводим в лог, что мы получили сообщение
    print(f"Received message: '{update.message.text}' from user {update.effective_user.id}")
    await update.message.reply_text("Эхо: " + update.message.text)

# Функция для команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветствие."""
    print(f"Received /start command from user {update.effective_user.id}")
    await update.message.reply_text("Привет! Я - минимальный эхо-бот. Отправь мне что-нибудь.")


async def main():
    """Основная функция запуска."""
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем бота
    print("Minimal Echo Bot is starting polling...")
    await app.run_polling()
    print("Polling finished.") # Эта строка не должна появиться в нормальном режиме


if __name__ == "__main__":
    print("Script starting...")
    if TOKEN:
        print(f"Token found, ending in: ...{TOKEN[-6:]}")
        asyncio.run(main())
    else:
        print("ERROR: BOT_TOKEN not found in environment variables!")
