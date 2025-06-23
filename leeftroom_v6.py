from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ChatAction
from geopy.geocoders import Nominatim
import os
import random

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 959818938  # ЗАМЕНИ на свой Telegram ID
geolocator = Nominatim(user_agent="leeftroom_bot")

REGISTER, AGE, CITY, BIO, PHOTO, MENU, EDIT_MENU, EDIT_NAME, EDIT_AGE, EDIT_BIO, EDIT_PHOTO, EDIT_CITY = range(12)
users = {}
likes = {}
disliked = {}


def get_main_keyboard(user_id):
    buttons = [
        ["🧍‍♂️ Мой профиль", "✏️ Изменить анкету"],
        ["🔍 Просмотр анкет", "ℹ️ О проекте"]
    ]
    if user_id == ADMIN_ID:
        buttons.append(["📁 Все анкеты"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


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
        location = geolocator.geocode(update.message.text)
        if location:
            users[user_id]["city"] = update.message.text
            await update.message.reply_text(f"Город сохранён: {update.message.text}")
        else:
            await update.message.reply_text("Пожалуйста, введи корректное название города.")
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


async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user = users.get(user_id)

    if not user or "name" not in user:
        await update.message.reply_text("Сначала пройди регистрацию. Напиши /start")
        return REGISTER

    if text == "🧍‍♂️ Мой профиль":
        profile = (
            f"Имя: {user.get('name', '')}\n"
            f"Возраст: {user.get('age', '')}\n"
            f"Город: {user.get('city', '')}\n"
            f"О себе: {user.get('bio', '')}"
        )
        await context.bot.send_photo(chat_id=user_id, photo=user.get("photo_id"), caption=profile)

    elif text == "✏️ Изменить анкету":
        keyboard = [
            ["🖼 Сменить фото"],
            ["📛 Сменить имя", "🔢 Сменить возраст"],
            ["🏙 Сменить город", "💬 Сменить о себе"],
            ["🔙 Назад"]
        ]
        await update.message.reply_text("Что хочешь изменить?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return EDIT_MENU

    elif text == "ℹ️ О проекте":
        await update.message.reply_text(
            "👋 Всем привет! 😊\n\n"
            "Создатель бота очень старается, и только-только познаёт мир программирования 🧠\n"
            "Половина кода была написана с помощью ChatGPT 🤖\n\n"
            "Если хотите — можете поддержать проект для будущих улучшений 🙏",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💖 Поддержать", url="https://www.donationalerts.com/r/haunithay")]
            ])
        )

    elif text == "📁 Все анкеты" and user_id == ADMIN_ID:
        if users:
            for uid, info in users.items():
                profile = (
                    f"Имя: {info.get('name', '')}\n"
                    f"Возраст: {info.get('age', '')}\n"
                    f"Город: {info.get('city', '')}\n"
                    f"О себе: {info.get('bio', '')}"
                )
                await context.bot.send_photo(chat_id=user_id, photo=info.get("photo_id"), caption=profile)
        else:
            await update.message.reply_text("Нет анкет.")

    return MENU


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
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu)],
            EDIT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
