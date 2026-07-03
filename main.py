import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# =====================================================================
# НАСТРОЙКИ: ТВОИ ДАННЫЕ УЖЕ ТУТ!
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@dxnk_admin"
COUNTER_FILE = "counter.txt"
# =====================================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_next_questionnaire_number():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("0")
    with open(COUNTER_FILE, "r") as f:
        try:
            current_number = int(f.read().strip())
        except ValueError:
            current_number = 0
    next_number = current_number + 1
    with open(COUNTER_FILE, "w") as f:
        f.write(str(next_number))
    return next_number


# Обновленные шаги анкеты (добавлены 2 новых шага)
class Questionnaire(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_source = State()
    waiting_for_plans = State()  # Что собирается делать (новый пункт)
    waiting_for_rules = State()  # Согласие с правилами/наказанием (новый пункт)
    waiting_for_about = State()


def get_start_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Заполнить анкету")]],
        resize_keyboard=True
    )


def get_admin_keyboard(user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
    )


@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        f"⚠️ **ВАЖНО:** Пожалуйста, пишите анкету максимально **грамотно**. "
        f"Все заявки рассматриваются строго, и неграмотные анкеты будут сразу отклоняться!\n\n"
        f"Нажми на кнопку ниже, чтобы начать заполнение.",
        reply_markup=get_start_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(F.text == "Заполнить анкету")
async def start_questionnaire(message: Message, state: FSMContext):
    await message.answer("Введи свой игровой никнейм:", reply_markup=None)
    await state.set_state(Questionnaire.waiting_for_nickname)


@dp.message(Questionnaire.waiting_for_nickname)
async def process_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await message.answer("Как вас зовут?")
    await state.set_state(Questionnaire.waiting_for_name)


@dp.message(Questionnaire.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько вам лет?")
    await state.set_state(Questionnaire.waiting_for_age)


@dp.message(Questionnaire.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Как вы узнали о нашем сервере?")
    await state.set_state(Questionnaire.waiting_for_source)


# НОВЫЙ ПУНКТ: Планы на сервере
@dp.message(Questionnaire.waiting_for_source)
async def process_source(message: Message, state: FSMContext):
    await state.update_data(source=message.text)
    await message.answer("Что ты собираешься делать на нашем сервере? Какие планы?")
    await state.set_state(Questionnaire.waiting_for_plans)


# НОВЫЙ ПУНКТ: Согласие с правилами и наказанием
@dp.message(Questionnaire.waiting_for_plans)
async def process_plans(message: Message, state: FSMContext):
    await state.update_data(plans=message.text)
    await message.answer(
        "Обязуешься ли ты соблюдать правила сервера? И в случае их нарушения, готов ли ты понести наказание?")
    await state.set_state(Questionnaire.waiting_for_rules)


# Финал: О себе
@dp.message(Questionnaire.waiting_for_rules)
async def process_rules(message: Message, state: FSMContext):
    await state.update_data(rules=message.text)
    await message.answer(
        "Расскажи немного о себе (твои увлечения, хобби).\n⚠️ **Желательно от 3 предложений и больше!**")
    await state.set_state(Questionnaire.waiting_for_about)


@dp.message(Questionnaire.waiting_for_about)
async def process_about(message: Message, state: FSMContext):
    await state.update_data(about=message.text)
    user_data = await state.get_data()

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Не указан"
    q_number = get_next_questionnaire_number()

    # Красивый пост с новыми пунктами 5 и 6
    post_text = (
        f"📝 **Новая анкета — #{q_number}**\n"
        f"🆔 **ID - игрока:** `{user_id}`\n"
        f"🌐 **Юзернейм:** {username}\n"
        f"👤 **Автор:** {message.from_user.mention_markdown()}\n\n"
        f"📋 **Анкета:**\n"
        f"🎮 **Игровой никнейм:** {user_data['nickname']}\n"
        f"1️⃣ **Имя:** {user_data['name']}\n"
        f"2️⃣ **Возраст:** {user_data['age']}\n"
        f"3️⃣ **Как узнал о сервере:** {user_data['source']}\n"
        f"4️⃣ **Планы на сервере:** {user_data['plans']}\n"
        f"5️⃣ **Соблюдение правил и ответственность:** {user_data['rules']}\n"
        f"6️⃣ **О себе:** {user_data['about']}"
    )

    try:
        await bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=post_text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard(user_id)
        )
        await message.answer("🎉 Ваша анкета отправлена на рассмотрение!",
                             reply_markup=get_start_keyboard())
    except Exception as e:
        await message.answer(
            f"❌ Ошибка отправки в канал. Проверь админку бота!\nОшибка: {e}",
            reply_markup=get_start_keyboard()
        )

    await state.clear()


# =====================================================================
# ОБРАБОТКА НАЖАТИЯ КНОПОК В КАНАЛЕ (ДЛЯ АДМИНОВ)
# =====================================================================

@dp.callback_query(F.data.startswith("accept_"))
async def handle_accept(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    admin_name = callback.from_user.first_name

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="🎉 Отличные новости! Ваша анкета была рассматрена, вы приняты! Добро пожаловать на DestrixNetwork! 🙌"
        )
        await callback.answer("Пользователь уведомлён о принятии!", show_alert=True)
    except Exception:
        await callback.answer("❌ Не удалось написать юзеру в ЛС (возможно, заблокировал бота)", show_alert=True)

    current_time = datetime.now().strftime("%H:%M:%S")
    updated_text = callback.message.text + f"\n\n🟢 **Вердикт:** Принят админом {admin_name} в {current_time}."
    await callback.message.edit_text(text=updated_text, reply_markup=None)


@dp.callback_query(F.data.startswith("reject_"))
async def handle_reject(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    admin_name = callback.from_user.first_name

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="❌ К сожалению, ваша анкета была рассмотрена, вы не приняты. С уважением команда проекта DestrixNetwork."
        )
        await callback.answer("Пользователь уведомлён об отказе!", show_alert=True)
    except Exception:
        await callback.answer("❌ Не удалось написать юзеру в ЛС", show_alert=True)

    current_time = datetime.now().strftime("%H:%M:%S")
    updated_text = callback.message.text + f"\n\n🔴 **Вердикт:** Отклонён админом {admin_name} в {current_time}."
    await callback.message.edit_text(text=updated_text, reply_markup=None)


async def main():
    print("Бот успешно запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())