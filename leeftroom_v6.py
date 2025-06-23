from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ChatAction
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
import os

TOKEN = os.getenv("BOT_TOKEN")
geolocator = Nominatim(user_agent="leeftroom_bot")

REGISTER, AGE, CITY, BIO, PHOTO, MENU = range(6)
users = {}

main_keyboard = ReplyKeyboardMarkup(
    [["\U0001F9CD\u200D\u2642\uFE0F Мой профиль", "\u270F\uFE0F Изменить анкету"],
     ["\U0001F50D Просмотр анкет", "\u2139\uFE0F О проекте"]], resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {}
    await update.message.reply_text("Привет! Введи свой ник:", reply_markup=ReplyKeyboardRemove())
    return REGISTER

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["nickname"] = update.message.text
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
        try:
            location_data = geolocator.reverse((location.latitude, location.longitude), language='en')
            city_name = location_data.raw.get("address", {}).get("city") or \
                        location_data.raw.get("address", {}).get("town") or \
                        location_data.raw.get("address", {}).get("village")
            if city_name:
                users[user_id]["city"] = city_name
                await update.message.reply_text(f"Определён город: {city_name}")
            else:
                await update.message.reply_text("Не удалось определить город по геолокации.")
                return CITY
        except (GeocoderUnavailable, GeocoderTimedOut):
            await update.message.reply_text("Ошибка при определении города. Попробуй ещё раз позже.")
            return CITY

    elif update.message.text:
        city_input = update.message.text.strip()
        try:
            location_data = geolocator.geocode(city_input)
            if location_data and ("city" in location_data.raw.get("address", {}) or
                                  "town" in location_data.raw.get("address", {}) or
                                  "village" in location_data.raw.get("address", {})):
                users[user_id]["city"] = city_input
                await update.message.reply_text(f"Город сохранён: {city_input}")
            else:
                await update.message.reply_text("Пожалуйста, введи настоящий город.")
                return CITY
        except (GeocoderUnavailable, GeocoderTimedOut):
            await update.message.reply_text("Не удалось проверить город. Попробуй позже.")
            return CITY

    else:
        await update.message.reply_text("Пожалуйста, отправь геолокацию или введи город вручную:")
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
    photo_file = update.message.photo[-1]
    users[update.effective_user.id]["photo_id"] = photo_file.file_id
    await update.message.reply_text("Регистрация завершена!")
    return await show_menu(update, context)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Меню:", reply_markup=main_keyboard)
    return MENU

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users.get(user_id)
    text = update.message.text

    if text == "\U0001F9CD\u200D\u2642\uFE0F Мой профиль":
        if user:
            profile = (
                f"Ник: {user.get('nickname', '')}\n"
                f"Возраст: {user.get('age', '')}\n"
                f"Город: {user.get('city', '')}\n"
                f"О себе: {user.get('bio', '')}"
            )
            await update.message.reply_photo(photo=user.get("photo_id"), caption=profile)
        else:
            await update.message.reply_text("Анкета не найдена.")

    elif text == "\u270F\uFE0F Изменить анкету":
        await update.message.reply_text("Что хочешь изменить? Введи заново:", reply_markup=ReplyKeyboardRemove())
        return REGISTER

    elif text == "\u2139\uFE0F О проекте":
        await update.message.reply_text(
            "\U0001F44B Всем привет! \U0001F60A\n\n"
            "Создатель бота очень старается, и только-только познаёт мир программирования \U0001F9E0\n"
            "Половина кода была написана с помощью ChatGPT \U0001F916\n\n"
            "Если хотите — можете поддержать проект для будущих улучшений \U0001F64F",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001F496 Поддержать", url="https://www.donationalerts.com/r/haunithay")]
            ])
        )

    elif text == "\U0001F50D Просмотр анкет":
        await update.message.reply_text("Функция просмотра анкет пока в разработке \U0001F6E0")

    return MENU

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пока!")
    return ConversationHandler.END

async def delete_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in users:
        del users[user_id]
        print(f"User {user_id} data deleted.")

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
        },
        fallbacks=[CommandHandler("stop", stop)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_data))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
