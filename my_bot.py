import os
import json
import random
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from geopy.geocoders import Nominatim

# --- НАСТРОЙКИ И ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 959818938))
geolocator = Nominatim(user_agent="leeftroom_bot")

(REGISTER, AGE, CITY, BIO, PHOTO, MENU, EDIT_MENU,
 EDIT_NAME, EDIT_AGE, EDIT_BIO, EDIT_PHOTO, EDIT_CITY) = range(12)

LOG_FILE = "bot_activity.log"
USERS_FILE = "users.json"
LIKES_FILE = "likes.json"
DISLIKED_FILE = "disliked.json"

users = {}
likes = {}
disliked = {}
viewing_profiles = {}

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ И ЛОГАМИ ---

def log_action(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- КЛАВИАТУРЫ ---

def get_main_keyboard(user_id):
    buttons = [
        ["🧍‍♂️ Мой профиль", "✏️ Изменить анкету"],
        ["🔍 Просмотр анкет", "ℹ️ О проекте"]
    ]
    if user_id == ADMIN_ID:
        buttons.append(["📁 Все анкеты", "📊 Статистика"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_edit_keyboard():
    buttons = [
        ["Имя", "Возраст"],
        ["Город", "О себе"],
        ["Фото", "⬅️ Назад в меню"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    log_action(f"User {user_id} started interaction.")
    if user_id in users and users.get(user_id, {}).get('photo_id'):
        await update.message.reply_text(
            "Вы уже зарегистрированы!",
            reply_markup=get_main_keyboard(user_id)
        )
        return MENU

    users[user_id] = {}
    await update.message.reply_text("Привет! Давай создадим твою анкету. Введи своё имя:")
    return REGISTER

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "Действие отменено. Вы в главном меню.",
        reply_markup=get_main_keyboard(user_id)
    )
    return MENU

# --- ЛОГИКА РЕГИСТРАЦИИ ---

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["name"] = update.message.text
    await update.message.reply_text("Отлично! Сколько тебе лет? (только цифры)")
    return AGE

async def register_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit() or not 14 < int(update.message.text) < 100:
        await update.message.reply_text("Пожалуйста, введи реальный возраст цифрами.")
        return AGE
    users[update.effective_user.id]["age"] = int(update.message.text)
    button = KeyboardButton("📍 Отправить геолокацию", request_location=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Теперь отправь свою геолокацию или напиши город вручную:", reply_markup=markup)
    return CITY

async def register_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    city_name = ""
    try:
        if update.message.location:
            location = update.message.location
            location_data = geolocator.reverse((location.latitude, location.longitude), language='ru')
            city_name = location_data.raw.get("address", {}).get("city", "Неизвестно")
        elif update.message.text:
            location_data = geolocator.geocode(update.message.text, language='ru')
            if location_data:
                city_name = update.message.text
            else:
                await update.message.reply_text("Не могу найти такой город. Попробуй ещё раз.")
                return CITY

        users[user_id]["city"] = city_name
        await update.message.reply_text(f"Твой город: {city_name}. Теперь напиши немного о себе:", reply_markup=ReplyKeyboardRemove())
        return BIO
    except Exception as e:
        log_action(f"Geopy error: {e}")
        await update.message.reply_text("Произошла ошибка с определением города. Попробуй ввести его вручную.")
        return CITY

async def register_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["bio"] = update.message.text
    await update.message.reply_text("Супер! И последнее — отправь своё лучшее фото.")
    return PHOTO

async def register_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        await update.message.reply_text("Это не фото. Пожалуйста, отправь фото.")
        return PHOTO

    users[user_id]["photo_id"] = update.message.photo[-1].file_id
    save_data(users, USERS_FILE)
    log_action(f"New user registered: {user_id}, name: {users[user_id]['name']}")

    await update.message.reply_text(
        "Отлично! Твоя анкета готова. Добро пожаловать!",
        reply_markup=get_main_keyboard(user_id)
    )
    return MENU

# --- ГЛАВНОЕ МЕНЮ И ПРОСМОТР АНКЕТ ---

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in users or not users[user_id].get("photo_id"):
        await update.message.reply_text("Похоже, твоя регистрация не завершена. Давай начнём заново. /start")
        return await start(update, context)

    if text == "🧍‍♂️ Мой профиль":
        await show_my_profile(update, context)
    elif text == "🔍 Просмотр анкет":
        await show_next_profile(update.message, context)
    elif text == "✏️ Изменить анкету":
        await update.message.reply_text("Что именно ты хочешь изменить?", reply_markup=get_edit_keyboard())
        return EDIT_MENU
    elif text == "ℹ️ О проекте":
        await about_project(update, context)
    elif text == "📁 Все анкеты" and user_id == ADMIN_ID:
        await show_all_profiles(update, context)
    elif text == "📊 Статистика" and user_id == ADMIN_ID:
        await show_stats(update, context)

    return MENU

def get_profile_caption(user_data):
    return (
        f"<b>{user_data.get('name', '')}, {user_data.get('age', '')}</b>\n"
        f"📍 {user_data.get('city', '')}\n\n"
        f"{user_data.get('bio', '')}"
    )

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = users.get(user_id)
    if user_data and user_data.get("photo_id"):
        caption = get_profile_caption(user_data)
        await update.message.reply_photo(
            photo=user_data["photo_id"],
            caption=caption,
            parse_mode='HTML'
        )

def liked_or_disliked_set(user_id):
    user_likes = set(likes.get(user_id, []))
    user_dislikes = set(disliked.get(user_id, []))
    return user_likes | user_dislikes

async def show_next_profile(message, context: ContextTypes.DEFAULT_TYPE):
    user_id = message.from_user.id
    viewed_ids = liked_or_disliked_set(user_id)
    candidates = [uid for uid in users if uid != user_id and uid not in viewed_ids and users[uid].get('photo_id')]

    if not candidates:
        await message.reply_text("На сегодня анкеты закончились! Загляни позже.")
        return

    target_id = random.choice(candidates)
    viewing_profiles[user_id] = target_id
    target_data = users[target_id]

    caption = get_profile_caption(target_data)
    buttons = [
        [
            InlineKeyboardButton("👍", callback_data=f"like_{target_id}"),
            InlineKeyboardButton("👎", callback_data=f"dislike_{target_id}")
        ]
    ]

    await message.reply_photo(
        photo=target_data["photo_id"],
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )

async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    action, target_id_str = query.data.split("_")
    target_id = int(target_id_str)

    await query.edit_message_reply_markup(reply_markup=None)

    if action == "like":
        likes.setdefault(user_id, []).append(target_id)
        save_data(likes, LIKES_FILE)
        log_action(f"User {user_id} liked user {target_id}")
        await context.bot.send_message(user_id, f"Вы лайкнули анкету пользователя {users[target_id]['name']}!")

        if target_id in likes and user_id in likes.get(target_id, []):
            log_action(f"Mutual like between {user_id} and {target_id}")
            match_message = "🎉 У вас взаимная симпатия!"
            try:
                target_chat = await context.bot.get_chat(target_id)
                user_chat = await context.bot.get_chat(user_id)
                await context.bot.send_message(user_id, f"{match_message} Вот профиль: @{target_chat.username}")
                await context.bot.send_message(target_id, f"{match_message} Вот профиль: @{user_chat.username}")
            except Exception as e:
                log_action(f"Error sending match notification: {e}")

    elif action == "dislike":
        disliked.setdefault(user_id, []).append(target_id)
        save_data(disliked, DISLIKED_FILE)
        log_action(f"User {user_id} disliked user {target_id}")
        await context.bot.send_message(user_id, "Анкета пропущена.")

    await show_next_profile(query.message, context)

# --- РЕДАКТИРОВАНИЕ АНКЕТЫ ---

async def handle_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    actions = {
        "Имя": (EDIT_NAME, "Введи новое имя:"),
        "Возраст": (EDIT_AGE, "Введи новый возраст:"),
        "Город": (EDIT_CITY, "Введи новый город:"),
        "О себе": (EDIT_BIO, "Напиши новый текст о себе:"),
        "Фото": (EDIT_PHOTO, "Отправь новое фото:"),
    }
    if text in actions:
        next_state, reply_text = actions[text]
        await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
        return next_state
    elif text == "⬅️ Назад в меню":
        return await cancel(update, context)
    return EDIT_MENU

async def edit_generic_text(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, state: int):
    user_id = update.effective_user.id
    new_value = update.message.text
    if field == "age" and (not new_value.isdigit() or not 14 < int(new_value) < 100):
        await update.message.reply_text("Пожалуйста, введи реальный возраст цифрами.")
        return state
    users[user_id][field] = int(new_value) if field == "age" else new_value
    save_data(users, USERS_FILE)
    log_action(f"User {user_id} edited field {field}.")
    await update.message.reply_text(f"Поле обновлено!", reply_markup=get_main_keyboard(user_id))
    return MENU

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_generic_text(update, context, 'name', EDIT_NAME)
async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_generic_text(update, context, 'age', EDIT_AGE)
async def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_generic_text(update, context, 'bio', EDIT_BIO)
async def edit_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_generic_text(update, context, 'city', EDIT_CITY)
async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        await update.message.reply_text("Это не фото. Пожалуйста, отправь фото.")
        return EDIT_PHOTO
    users[user_id]["photo_id"] = update.message.photo[-1].file_id
    save_data(users, USERS_FILE)
    log_action(f"User {user_id} edited photo.")
    await update.message.reply_text("Фото обновлено!", reply_markup=get_main_keyboard(user_id))
    return MENU

# --- ПРОЧИЕ И АДМИНСКИЕ ФУНКЦИИ ---

async def about_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\nЭто учебный проект, созданный для изучения разработки ботов.\n"
        "Автор в телеграме: @haunithay",
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        total_users = len(users)
        total_likes = sum(len(v) for v in likes.values())
        await update.message.reply_text(
            f"<b>Статистика бота:</b>\n\n"
            f"🙋‍♂️ Всего анкет: {total_users}\n"
            f"👍 Всего лайков поставлено: {total_likes}",
            parse_mode='HTML'
        )

async def send_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        if os.path.exists(LOG_FILE):
            await update.message.reply_document(document=InputFile(LOG_FILE))

async def show_all_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        if not users:
            await update.message.reply_text("Анкет пока нет.")
            return
        await update.message.reply_text(f"Отправляю {len(users)} анкет...")
        for uid, udata in users.items():
            if udata.get("photo_id"):
                caption = get_profile_caption(udata) + f"\n\nID: <code>{uid}</code>"
                await update.message.reply_photo(photo=udata["photo_id"], caption=caption, parse_mode='HTML')

# --- СБОРКА БОТА И ВЕБ-СЕРВЕР ДЛЯ РАБОТЫ 24/7 ---

def run_bot():
    global users, likes, disliked
    users = load_data(USERS_FILE)
    likes = load_data(LIKES_FILE)
    disliked = load_data(DISLIKED_FILE)

    log_action("Bot starting...")
    app = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_age)],
            CITY: [MessageHandler(filters.LOCATION | (filters.TEXT & ~filters.COMMAND), register_city)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_bio)],
            PHOTO: [MessageHandler(filters.PHOTO, register_photo)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            EDIT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_menu)],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            EDIT_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_city)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_bio)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, edit_photo)],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_button_press, pattern=r"^(like|dislike)_"))
    app.add_handler(CommandHandler("logs", send_logs))
    print("Bot is running...")
    app.run_polling()

flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "I'm alive!"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port)