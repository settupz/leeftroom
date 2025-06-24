from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ChatAction
from geopy.geocoders import Nominatim
import os
import random
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 959818938
geolocator = Nominatim(user_agent="leeftroom_bot")

REGISTER, AGE, CITY, BIO, PHOTO, MENU, EDIT_MENU, EDIT_NAME, EDIT_AGE, EDIT_BIO, EDIT_PHOTO, EDIT_CITY = range(12)
users = {}
likes = {}
disliked = {}
hidden_users = set()

LOG_FILE = "bot_activity.log"

def log_action(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def get_main_keyboard(user_id):
    buttons = [
        ["🧍‍♂️ Мой профиль", "✏️ Изменить анкету"],
        ["🔍 Просмотр анкет", "ℹ️ О проекте"]
    ]
    if user_id == ADMIN_ID:
        buttons.append(["📁 Все анкеты", "/stats"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def send_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        if os.path.exists(LOG_FILE):
            await update.message.reply_document(document=InputFile(LOG_FILE))
        else:
            await update.message.reply_text("Лог-файл пока пуст.")
    else:
        await update.message.reply_text("У тебя нет доступа к логам.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {}
    await update.message.reply_text("Привет! Введи своё имя:")
    return REGISTER

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["name"] = update.message.text
    await update.message.reply_text("Сколько тебе лет? (только цифры)")
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Пожалуйста, введи возраст цифрами.")
        return AGE
    users[update.effective_user.id]["age"] = update.message.text
    button = KeyboardButton("Отправить геолокацию", request_location=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    await update.message.reply_text("Отправь свою геолокацию или напиши город вручную:", reply_markup=markup)
    return CITY

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.location:
        location = update.message.location
        location_data = geolocator.reverse((location.latitude, location.longitude), language='en')
        city = location_data.raw.get("address", {}).get("city", "Неизвестно")
        users[user_id]["city"] = city
        await update.message.reply_text(f"Определён город: {city}")
    elif update.message.text:
        location_data = geolocator.geocode(update.message.text)
        if location_data:
            users[user_id]["city"] = update.message.text
            await update.message.reply_text(f"Город сохранён: {update.message.text}")
        else:
            await update.message.reply_text("Пожалуйста, введи настоящий город.")
            return CITY
    else:
        await update.message.reply_text("Пожалуйста, отправь геолокацию или напиши свой город:")
        return CITY

    markup = ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True)
    await update.message.reply_text("Напиши немного о себе:", reply_markup=markup)
    return BIO

async def bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Пропустить":
        users[update.effective_user.id]["bio"] = ""
    else:
        users[update.effective_user.id]["bio"] = update.message.text
    await update.message.reply_text("Теперь отправь фото:", reply_markup=ReplyKeyboardRemove())
    return PHOTO

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправь фото.")
        return PHOTO
    photo_file = update.message.photo[-1]
    users[update.effective_user.id]["photo_id"] = photo_file.file_id
    await update.message.reply_text("Регистрация завершена!", reply_markup=get_main_keyboard(update.effective_user.id))
    return MENU

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in users or not users[user_id].get("photo_id"):
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйся. /start")
        return MENU

    if text == "🧍‍♂️ Мой профиль":
        user = users[user_id]
        caption = (
            f"Имя: {user.get('name', '')}\n"
            f"Возраст: {user.get('age', '')}\n"
            f"Город: {user.get('city', '')}\n"
            f"О себе: {user.get('bio', '')}"
        )
        await update.message.reply_photo(photo=user.get("photo_id"), caption=caption)

    elif text == "✏️ Изменить анкету":
        keyboard = [
            [InlineKeyboardButton("Имя", callback_data="edit_name")],
            [InlineKeyboardButton("Возраст", callback_data="edit_age")],
            [InlineKeyboardButton("Город", callback_data="edit_city")],
            [InlineKeyboardButton("О себе", callback_data="edit_bio")],
            [InlineKeyboardButton("Фото", callback_data="edit_photo")]
        ]
        await update.message.reply_text("Выбери, что изменить:", reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_MENU

    elif text == "ℹ️ О проекте":
        await update.message.reply_text(
            "👋 Всем привет! 😊\n\nСоздатель бота очень старается, и только-только познаёт мир программирования 🧠\nПоловина кода была написана с помощью ChatGPT 🤖\n\nЕсли хотите — можете поддержать проект для будущих улучшений 🙏",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💖 Поддержать", url="https://www.donationalerts.com/r/haunithay")]
            ])
        )

    elif text == "📁 Все анкеты" and user_id == ADMIN_ID:
        for uid, user in users.items():
            caption = (
                f"Имя: {user.get('name', '')}\n"
                f"Возраст: {user.get('age', '')}\n"
                f"Город: {user.get('city', '')}\n"
                f"О себе: {user.get('bio', '')}"
            )
            await update.message.reply_photo(photo=user.get("photo_id"), caption=caption)

async def send_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        if os.path.exists(LOG_FILE):
            await update.message.reply_document(document=InputFile(LOG_FILE))
        else:
            await update.message.reply_text("Лог-файл пока пуст.")

        log_action(f"Админ запросил лог-файл")
    else:
        await update.message.reply_text("У тебя нет доступа к логам.")

        log_action(f"Пользователь {user_id} попытался получить лог-файл")

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            CITY: [
                MessageHandler(filters.LOCATION, city),
                MessageHandler(filters.TEXT & ~filters.COMMAND, city)
            ],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            EDIT_MENU: [CallbackQueryHandler(lambda update, context: None)]  # заглушка для edit меню
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("logs", send_log))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
