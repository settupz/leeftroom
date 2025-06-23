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
ADMIN_ID = 959818938  # Заменить на свой Telegram ID
geolocator = Nominatim(user_agent="leeftroom_bot")

REGISTER, AGE, CITY, BIO, PHOTO, MENU, EDIT_MENU, EDIT_NAME, EDIT_AGE, EDIT_BIO, EDIT_PHOTO, EDIT_CITY = range(12)
users = {}
likes = {}
disliked = {}

main_keyboard = ReplyKeyboardMarkup(
    [["🣍️ Мой профиль", "✏️ Изменить анкету"],
     ["🔍 Просмотр анкет", "ℹ️ О проекте"]], resize_keyboard=True
)

def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {}
        update.message.reply_text("Привет! Введи своё имя:")
        return REGISTER
    else:
        update.message.reply_text("Ты уже зарегистрирован!", reply_markup=main_keyboard)
        return MENU

def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["name"] = update.message.text
    update.message.reply_text("Сколько тебе лет? (только цифры)")
    return AGE

def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        update.message.reply_text("Пожалуйста, введи возраст цифрами.")
        return AGE
    users[update.effective_user.id]["age"] = update.message.text
    button = KeyboardButton("Отправить геолокацию", request_location=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    update.message.reply_text("Отправь свою геолокацию или напиши город вручную:", reply_markup=markup)
    return CITY

def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.location:
        location = update.message.location
        location_data = geolocator.reverse((location.latitude, location.longitude), language='en')
        city = location_data.raw.get("address", {}).get("city", "Неизвестно")
        users[user_id]["city"] = city
        update.message.reply_text(f"Определён город: {city}")
    elif update.message.text:
        city_name = update.message.text.strip()
        try:
            location = geolocator.geocode(city_name)
            if location:
                users[user_id]["city"] = city_name
                update.message.reply_text(f"Город сохранён: {city_name}")
            else:
                update.message.reply_text("Город не найден. Попробуйте снова:")
                return CITY
        except:
            update.message.reply_text("Ошибка при определении города. Попробуйте снова:")
            return CITY
    markup = ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True)
    update.message.reply_text("Напиши немного о себе:", reply_markup=markup)
    return BIO

def bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["bio"] = "" if update.message.text == "Пропустить" else update.message.text
    update.message.reply_text("Теперь отправь фото:", reply_markup=ReplyKeyboardRemove())
    return PHOTO

def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return PHOTO
    photo_file = update.message.photo[-1]
    users[update.effective_user.id]["photo_id"] = photo_file.file_id
    update.message.reply_text("Регистрация завершена!", reply_markup=main_keyboard)
    return MENU

def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user = users.get(user_id)

    if text == "🣝️ Мой профиль" and user:
        caption = (
            f"Имя: {user.get('name', '')}\n"
            f"Возраст: {user.get('age', '')}\n"
            f"Город: {user.get('city', '')}\n"
            f"О себе: {user.get('bio', '')}"
        )
        update.message.reply_photo(photo=user.get("photo_id"), caption=caption)

    elif text == "✏️ Изменить анкету":
        markup = ReplyKeyboardMarkup([
            ["Имя", "Возраст"],
            ["Город", "О себе"],
            ["Фото", "Назад"]
        ], resize_keyboard=True)
        update.message.reply_text("Что хочешь изменить?", reply_markup=markup)
        return EDIT_MENU

    elif text == "ℹ️ О проекте":
        update.message.reply_text(
            "👋 Всем привет! 😊\n\n"
            "Создатель бота очень старается, и только-только познаёт мир программирования 🧠\n"
            "Половина кода была написана с помощью ChatGPT 🤖\n\n"
            "Если хотите — можете поддержать проект для будущих улучшений 🙏",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💖 Поддержать", url="https://www.donationalerts.com/r/haunithay")]
            ])
        )

    elif text == "🔍 Просмотр анкет":
        other_users = [uid for uid in users if uid != user_id and uid not in likes.get(user_id, [])]
        if not other_users:
            update.message.reply_text("Нет анкет для просмотра.")
            return MENU
        viewed_id = random.choice(other_users)
        viewed = users[viewed_id]
        caption = (
            f"Имя: {viewed.get('name', '')}\n"
            f"Возраст: {viewed.get('age', '')}\n"
            f"Город: {viewed.get('city', '')}\n"
            f"О себе: {viewed.get('bio', '')}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❤️", callback_data=f"like:{viewed_id}"),
             InlineKeyboardButton("❌", callback_data=f"dislike:{viewed_id}")]
        ])
        context.bot.send_photo(chat_id=user_id, photo=viewed.get("photo_id"), caption=caption, reply_markup=keyboard)

    elif text == "📁 Все анкеты" and user_id == ADMIN_ID:
        for uid, u in users.items():
            caption = (
                f"ID: {uid}\n"
                f"Имя: {u.get('name', '')}\n"
                f"Возраст: {u.get('age', '')}\n"
                f"Город: {u.get('city', '')}\n"
                f"О себе: {u.get('bio', '')}"
            )
            try:
                update.message.reply_photo(photo=u.get("photo_id"), caption=caption)
            except:
                update.message.reply_text(caption)

    return MENU

def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data.startswith("like"):
        liked_id = int(data.split(":")[1])
        likes.setdefault(user_id, []).append(liked_id)
        query.answer("Вы лайкнули пользователя.")
    elif data.startswith("dislike"):
        disliked_id = int(data.split(":")[1])
        disliked.setdefault(user_id, []).append(disliked_id)
        query.answer("Вы пропустили пользователя.")

    query.message.delete()
    handle_text_menu(update, context)

def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "Имя":
        update.message.reply_text("Введи новое имя:")
        return EDIT_NAME
    elif text == "Возраст":
        update.message.reply_text("Введи новый возраст:")
        return EDIT_AGE
    elif text == "Город":
        update.message.reply_text("Введи новый город:")
        return EDIT_CITY
    elif text == "О себе":
        update.message.reply_text("Напиши о себе:")
        return EDIT_BIO
    elif text == "Фото":
        update.message.reply_text("Отправь новую фотографию:")
        return EDIT_PHOTO
    elif text == "Назад":
        update.message.reply_text("Главное меню:", reply_markup=main_keyboard)
        return MENU

    return EDIT_MENU

def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["name"] = update.message.text
    update.message.reply_text("Имя обновлено.", reply_markup=main_keyboard)
    return MENU

def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        update.message.reply_text("Пожалуйста, введи возраст цифрами.")
        return EDIT_AGE
    users[update.effective_user.id]["age"] = update.message.text
    update.message.reply_text("Возраст обновлён.", reply_markup=main_keyboard)
    return MENU

def edit_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["city"] = update.message.text
    update.message.reply_text("Город обновлён.", reply_markup=main_keyboard)
    return MENU

def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["bio"] = update.message.text
    update.message.reply_text("О себе обновлено.", reply_markup=main_keyboard)
    return MENU

def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return EDIT_PHOTO
    users[update.effective_user.id]["photo_id"] = update.message.photo[-1].file_id
    update.message.reply_text("Фото обновлено.", reply_markup=main_keyboard)
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
            EDIT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field)],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            EDIT_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_city)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_bio)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, edit_photo)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_buttons))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
