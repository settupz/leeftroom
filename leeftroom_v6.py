from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ChatAction
from geopy.geocoders import Nominatim
import os

TOKEN = os.getenv("BOT_TOKEN")
geolocator = Nominatim(user_agent="leeftroom_bot")

REGISTER, AGE, CITY, BIO, PHOTO, MENU = range(6)
users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {}
    await update.message.reply_text("Привет! Введи свой ник:")
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
        location_data = geolocator.reverse((location.latitude, location.longitude), language='en')
        city = location_data.raw.get("address", {}).get("city", "Неизвестно")
        users[user_id]["city"] = city
        await update.message.reply_text(f"Определён город: {city}")
    elif update.message.text:
        users[user_id]["city"] = update.message.text
        await update.message.reply_text(f"Город сохранён: {update.message.text}")
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
    photo_file = update.message.photo[-1]
    users[update.effective_user.id]["photo_id"] = photo_file.file_id
    await update.message.reply_text("Регистрация завершена!")
    return await show_menu(update)

async def show_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("Изменить анкету", callback_data="edit")],
        [InlineKeyboardButton("Показать анкету", callback_data="profile")],
        [InlineKeyboardButton("О проекте", callback_data="about")]
    ]
    await update.message.reply_text("Меню:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = users.get(user_id)

    if query.data == "edit":
        await context.bot.send_message(chat_id=user_id, text="Что хочешь изменить? Введи заново:")
        return REGISTER

    elif query.data == "profile":
        if user:
            profile = (
                f"Ник: {user.get('nickname', '')}
"
                f"Возраст: {user.get('age', '')}
"
                f"Город: {user.get('city', '')}
"
                f"О себе: {user.get('bio', '')}"
            )
            await context.bot.send_photo(chat_id=user_id, photo=user.get("photo_id"), caption=profile)
        else:
            await context.bot.send_message(chat_id=user_id, text="Анкета не найдена.")
        return MENU

    elif query.data == "about":
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "👋 Всем привет! 😊

"
                "Создатель бота очень старается, и только-только познаёт мир программирования 🧠
"
                "Половина кода была написана с помощью ChatGPT 🤖

"
                "Если хотите — можете поддержать проект для будущих улучшений 🙏"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💖 Поддержать", url="https://www.donationalerts.com/r/haunithay")]
            ])
        )
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
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_menu)],
        },
        fallbacks=[CommandHandler("stop", stop)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(menu_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_data))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
