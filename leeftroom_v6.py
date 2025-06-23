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
ADMIN_ID = 959818938
geolocator = Nominatim(user_agent="leeftroom_bot")

REGISTER, AGE, CITY, BIO, PHOTO, MENU, EDIT_MENU, EDIT_NAME, EDIT_AGE, EDIT_BIO, EDIT_PHOTO, EDIT_CITY = range(12)
users = {}
likes = {}
disliked = {}

main_keyboard = ReplyKeyboardMarkup(
    [["🧍‍♂️ Мой профиль", "✏️ Изменить анкету"],
     ["🔍 Просмотр анкет", "ℹ️ О проекте"],
     ["📁 Все анкеты"]], resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {}
        await update.message.reply_text("Привет! Введи своё имя:")
        return REGISTER
    await update.message.reply_text("Вы уже зарегистрированы.", reply_markup=main_keyboard)
    return MENU

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["name"] = update.message.text
    await update.message.reply_text("Сколько тебе лет? (только цифры)")
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Пожалуйста, введи возраст цифрами.")
        return AGE
    users[update.effective_user.id]["age"] = update.message.text
    button = KeyboardButton("📍 Отправить геолокацию", request_location=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    await update.message.reply_text("Отправь геолокацию или введи город вручную:", reply_markup=markup)
    return CITY

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.location:
        location = update.message.location
        location_data = geolocator.reverse((location.latitude, location.longitude), language='en')
        city = location_data.raw.get("address", {}).get("city", None)
        if city:
            users[user_id]["city"] = city
            await update.message.reply_text(f"Город определён: {city}")
        else:
            await update.message.reply_text("Не удалось определить город, введите его вручную:")
            return CITY
    elif update.message.text:
        location_data = geolocator.geocode(update.message.text)
        if location_data:
            users[user_id]["city"] = update.message.text
            await update.message.reply_text(f"Город сохранён: {update.message.text}")
        else:
            await update.message.reply_text("Такой город не найден. Попробуй снова:")
            return CITY
    else:
        await update.message.reply_text("Пожалуйста, отправь геолокацию или введи город:")
        return CITY
    markup = ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True)
    await update.message.reply_text("Напиши немного о себе:", reply_markup=markup)
    return BIO

async def bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["bio"] = "" if update.message.text == "Пропустить" else update.message.text
    await update.message.reply_text("Теперь отправь фото:", reply_markup=ReplyKeyboardRemove())
    return PHOTO

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1]
    users[update.effective_user.id]["photo_id"] = photo_file.file_id
    await update.message.reply_text("Регистрация завершена!", reply_markup=main_keyboard)
    return MENU

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in users:
        await update.message.reply_text("Сначала пройди регистрацию: /start")
        return REGISTER

    if text == "🧍‍♂️ Мой профиль":
        user = users.get(user_id)
        if user:
            profile = (
                f"👤 Имя: {user.get('name', '')}\n"
                f"📅 Возраст: {user.get('age', '')}\n"
                f"🏙️ Город: {user.get('city', '')}\n"
                f"📖 О себе: {user.get('bio', '')}"
            )
            await update.message.reply_photo(photo=user.get("photo_id"), caption=profile)
        return MENU

    elif text == "✏️ Изменить анкету":
        await update.message.reply_text("Что ты хочешь изменить?", reply_markup=ReplyKeyboardMarkup(
            [["Имя", "Возраст"], ["Город", "О себе"], ["Фото"], ["⬅️ Назад"]], resize_keyboard=True))
        return EDIT_MENU

    elif text == "🔍 Просмотр анкет":
        all_users = list(users.keys())
        random.shuffle(all_users)
        for uid in all_users:
            if uid != user_id and uid not in likes.get(user_id, []) and uid not in disliked.get(user_id, []):
                target = users[uid]
                profile = (
                    f"👤 Имя: {target.get('name', '')}\n"
                    f"📅 Возраст: {target.get('age', '')}\n"
                    f"🏙️ Город: {target.get('city', '')}\n"
                    f"📖 О себе: {target.get('bio', '')}"
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❤️", callback_data=f"like_{uid}"),
                     InlineKeyboardButton("👎", callback_data=f"dislike_{uid}")]
                ])
                await update.message.reply_photo(photo=target.get("photo_id"), caption=profile, reply_markup=keyboard)
                return MENU
        await update.message.reply_text("Пока нет новых анкет.")
        return MENU

    elif text == "ℹ️ О проекте":
        await update.message.reply_text(
            "👋 Всем привет! 😊\n"
            "Создатель бота очень старается, и только-только познаёт мир программирования 🧠\n"
            "Половина кода была написана с помощью ChatGPT 🤖\n"
            "Если хотите — можете поддержать проект для будущих улучшений 🙏",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💖 Поддержать", url="https://www.donationalerts.com/r/haunithay")]
            ])
        )
        return MENU

    elif text == "📁 Все анкеты" and user_id == ADMIN_ID:
        for uid, data in users.items():
            profile = (
                f"👤 Имя: {data.get('name', '')}\n"
                f"📅 Возраст: {data.get('age', '')}\n"
                f"🏙️ Город: {data.get('city', '')}\n"
                f"📖 О себе: {data.get('bio', '')}"
            )
            await update.message.reply_photo(photo=data.get("photo_id"), caption=profile)
        return MENU

    return MENU

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("like_"):
        liked_id = int(query.data.split("_")[1])
        likes.setdefault(user_id, []).append(liked_id)
        await query.edit_message_caption(caption="❤️ Ты лайкнул анкету.")
    elif query.data.startswith("dislike_"):
        disliked_id = int(query.data.split("_")[1])
        disliked.setdefault(user_id, []).append(disliked_id)
        await query.edit_message_caption(caption="👎 Ты пропустил анкету.")

async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "Имя":
        await update.message.reply_text("Введи новое имя:")
        return EDIT_NAME
    elif text == "Возраст":
        await update.message.reply_text("Введи новый возраст:")
        return EDIT_AGE
    elif text == "Город":
        await update.message.reply_text("Введи новый город:")
        return EDIT_CITY
    elif text == "О себе":
        await update.message.reply_text("Введи новую информацию о себе:")
        return EDIT_BIO
    elif text == "Фото":
        await update.message.reply_text("Отправь новое фото:")
        return EDIT_PHOTO
    elif text == "⬅️ Назад":
        await update.message.reply_text("Главное меню.", reply_markup=main_keyboard)
        return MENU
    return EDIT_MENU

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["name"] = update.message.text
    await update.message.reply_text("Имя обновлено.")
    return EDIT_MENU

async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Пожалуйста, введи возраст цифрами.")
        return EDIT_AGE
    users[update.effective_user.id]["age"] = update.message.text
    await update.message.reply_text("Возраст обновлён.")
    return EDIT_MENU

async def edit_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["city"] = update.message.text
    await update.message.reply_text("Город обновлён.")
    return EDIT_MENU

async def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["bio"] = update.message.text
    await update.message.reply_text("Информация обновлена.")
    return EDIT_MENU

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1]
    users[update.effective_user.id]["photo_id"] = photo_file.file_id
    await update.message.reply_text("Фото обновлено.")
    return EDIT_MENU

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            CITY: [MessageHandler(filters.LOCATION | filters.TEXT & ~filters.COMMAND, city)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu)],
            EDIT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit)],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            EDIT_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_city)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_bio)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, edit_photo)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_buttons))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
