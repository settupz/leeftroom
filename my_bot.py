import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# Асинхронная функция для ответа на /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Received /start from user {update.effective_user.id}")
    await update.message.reply_text("Привет! Я - самый простой эхо-бот. Отправь мне текст.")

# Асинхронная функция для эхо-ответа
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Echoing message from user {update.effective_user.id}")
    await update.message.reply_text("Эхо: " + update.message.text)


def main() -> None:
    """Основная функция, которая запускает всё."""
    print("Script starting...")

    # Проверяем, есть ли токен
    if not TOKEN:
        print("ОШИБКА: Не найден BOT_TOKEN в переменных окружения!")
        return # Выходим, если токена нет

    print(f"Token found, ending with: ...{TOKEN[-6:]}")

    # Создаём приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем бота. Эта функция сама всё сделает, включая управление asyncio.
    # Она будет работать вечно, пока её не остановить.
    print("Starting bot polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
