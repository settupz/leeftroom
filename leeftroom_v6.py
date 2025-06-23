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

main_keyboard = ReplyKeyboardMarkup(
    [["🧍‍♂️ Мой профиль", "✏️ Изменить анкету"],
     ["🔍 Просмотр анкет", "ℹ️ О проекте"],
     ["📁 Все анкеты"]], resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {}
    await update.message.reply_text("Привет! Введи своё имя:", reply_markup=ReplyKeyboardRemove())
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
        try:
            location_data = geolocator.geocode(update.message.text)
            if location_data:
                users[user_id]["city"] = update.message.text
                await update.message.reply_text(f"Город сохранён: {update.message.text}")
            else:
                await update.message.reply_text("Пожалуйста, введи реальное название города.")
                return CITY
        except:
            await update.message.reply_text("Ошибка при определении города. Повтори ввод.")
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
    photo_file = update.message.photo[-1]
    users[update.effective_user.id]["photo_id"] = photo_file.file_id
    await update.message.reply_text("Регистрация завершена!", reply_markup=main_keyboard)
    return MENU

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users.get(user_id)
    text = update.message.text

    if text == "🧍‍♂️ Мой профиль":
        if user:
            profile = (
                f"👤 <b>Имя:</b> {user.get('name', '')}\n"
                f"🎂 <b>Возраст:</b> {user.get('age', '')}\n"
                f"📍 <b>Город:</b> {user.get('city', '')}\n"
                f"💬 <b>О себе:</b> {user.get('bio', '')}"
            )
            await update.message.reply_photo(photo=user.get("photo_id"), caption=profile, parse_mode="HTML")
        else:
            await update.message.reply_text("Анкета не найдена.")

    elif text == "📁 Все анкеты" and user_id == ADMIN_ID:
        if not users:
            await update.message.reply_text("Нет анкет в базе данных.")
        for uid, udata in users.items():
            profile = (
                f"👤 <b>Имя:</b> {udata.get('name', '')}\n"
                f"🎂 <b>Возраст:</b> {udata.get('age', '')}\n"
                f"📍 <b>Город:</b> {udata.get('city', '')}\n"
                f"💬 <b>О себе:</b> {udata.get('bio', '')}"
            )
            try:
                await update.message.reply_photo(photo=udata.get("photo_id"), caption=profile, parse_mode="HTML")
            except:
                await update.message.reply_text(profile, parse_mode="HTML")

    elif text == "✏️ Изменить анкету":
        keyboard = [["Имя", "Возраст"], ["Город", "О себе"], ["Фото"]]
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

    elif text == "🔍 Просмотр анкет":
        if not user:
            await update.message.reply_text("Сначала пройди регистрацию командой /start.")
            return MENU
        candidates = [uid for uid in users if uid != user_id and uid not in likes.get(user_id, set()) and uid not in disliked.get(user_id, set())]
        if not candidates:
            await update.message.reply_text("Нет новых анкет для просмотра 🔄")
            return MENU
        target_id = random.choice(candidates)
        context.user_data['viewing'] = target_id
        target = users[target_id]
        profile = (
            f"👤 <b>Имя:</b> {target.get('name', '')}\n"
            f"🎂 <b>Возраст:</b> {target.get('age', '')}\n"
            f"📍 <b>Город:</b> {target.get('city', '')}\n"
            f"💬 <b>О себе:</b> {target.get('bio', '')}"
        )
        await update.message.reply_photo(photo=target.get("photo_id"), caption=profile, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❤️", callback_data="like"), InlineKeyboardButton("👎", callback_data="dislike")]
        ]))

    return MENU

# остальные функции оставить как есть, включая main()
