import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

# ══════════════════════════════════════════
# НАСТРОЙКИ
# ══════════════════════════════════════════
TOKEN       = "8637969737:AAEEgbeCABVYymkX435S38TEyTiioYJsNHo"
ADMIN_ID    = 143516369
ADMIN_USER  = "@albega1"

FILES = {
    "opdir_a1": "leads/opdir/checklist-opdir.pdf",
    "opdir_b1": "leads/opdir/tracking-rnp.xlsx",
    "opdir_c1": "leads/opdir/uzkoe-gorlyshko.pdf",
    "strat_ch": "leads/stratsessiya/checklist-stratsessiya.pdf",
    "strat_b1": "leads/stratsessiya/stratsessiya-ili-spektakl.pdf",
    "strat_a2": "leads/stratsessiya/test-komandnoy-sinkhronizatsii.pdf",
    "strat_b2": "leads/stratsessiya/dorozhnaya-karta.xlsx",
    "strat_c1": "leads/stratsessiya/kak-ne-dat-strategii-umeret.pdf",
}

NAMES = {
    "opdir_a1": "Готов ли бизнес к операционному директору",
    "opdir_b1": "Трекинг-отчёт РНП",
    "opdir_c1": "7 признаков узкого горлышка",
    "strat_ch": "Чеклист подготовки к стратсессии",
    "strat_b1": "Стратсессия или спектакль?",
    "strat_a2": "Тест командной синхронизации",
    "strat_b2": "Дорожная карта стратсессии",
    "strat_c1": "Как не дать стратегии умереть",
    "consult":  "заявка на диагностику",
}

ASK_NAME, ASK_REVENUE, ASK_PHONE = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════
# HEALTH-CHECK СЕРВЕР (для Render.com)
# ══════════════════════════════════════════
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *args):
        pass  # тишина в логах

def run_health_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthHandler)
    server.serve_forever()


# ══════════════════════════════════════════
# ГЛАВНОЕ МЕНЮ
# ══════════════════════════════════════════
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("── Операционный директор ──", callback_data="noop")],
        [InlineKeyboardButton("📋 Готов ли бизнес к опердиру (PDF)",     callback_data="opdir_a1")],
        [InlineKeyboardButton("📊 Трекинг-отчёт РНП (Excel)",            callback_data="opdir_b1")],
        [InlineKeyboardButton("🔴 7 признаков узкого горлышка (PDF)",    callback_data="opdir_c1")],
        [InlineKeyboardButton("── Стратегическая сессия ──",             callback_data="noop")],
        [InlineKeyboardButton("✅ Чеклист подготовки к стратсессии (PDF)", callback_data="strat_ch")],
        [InlineKeyboardButton("🎭 Стратсессия или спектакль? (PDF)",     callback_data="strat_b1")],
        [InlineKeyboardButton("🧪 Тест командной синхронизации (PDF)",   callback_data="strat_a2")],
        [InlineKeyboardButton("🗺 Дорожная карта стратсессии (Excel)",   callback_data="strat_b2")],
        [InlineKeyboardButton("📄 Как не дать стратегии умереть (PDF)",  callback_data="strat_c1")],
        [InlineKeyboardButton("──────────────────",                       callback_data="noop")],
        [InlineKeyboardButton("💬 Оставить заявку на диагностику",       callback_data="consult")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Точка входа — показываем меню."""
    context.user_data.clear()  # сбрасываем любое старое состояние
    text = (
        "👋 Привет! Я бот Nexops.\n\n"
        "Выберите что хотите получить 👇"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=get_main_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())


# ══════════════════════════════════════════
# КНОПКА ВЫБРАНА — спрашиваем имя
# ══════════════════════════════════════════
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data
    context.user_data["file_key"]  = key
    context.user_data["file_name"] = NAMES.get(key, "материал")

    await query.message.reply_text(
        f"Отлично! Пришлю *{NAMES.get(key, 'материал')}* прямо сейчас.\n\n"
        "Сначала пара вопросов — 30 секунд.\n\n"
        "Как вас зовут?",
        parse_mode="Markdown"
    )
    return ASK_NAME


# ══════════════════════════════════════════
# ШАГ 1 — ИМЯ
# ══════════════════════════════════════════
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text

    keyboard = ReplyKeyboardMarkup(
        [["До 30 млн ₽", "30–100 млн ₽"], ["100–500 млн ₽", "Больше 500 млн ₽"]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(
        f"Приятно познакомиться, {update.message.text}! 👋\n\n"
        "Какая примерно годовая выручка вашего бизнеса?",
        reply_markup=keyboard
    )
    return ASK_REVENUE


# ══════════════════════════════════════════
# ШАГ 2 — ВЫРУЧКА
# ══════════════════════════════════════════
async def ask_revenue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["revenue"] = update.message.text

    await update.message.reply_text(
        "Хорошо! Последний вопрос.\n\n"
        "Укажите ваш телефон или Telegram-username — Денис свяжется лично:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_PHONE


# ══════════════════════════════════════════
# ШАГ 3 — ТЕЛЕФОН → отправляем файл
# ══════════════════════════════════════════
async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text

    name     = context.user_data.get("name", "—")
    revenue  = context.user_data.get("revenue", "—")
    phone    = update.message.text
    file_key = context.user_data.get("file_key", "")
    file_name = context.user_data.get("file_name", "материал")

    # Уведомление Денису
    await update.get_bot().send_message(
        chat_id=ADMIN_ID,
        text=(
            f"🔔 Новый лид из бота!\n\n"
            f"👤 Имя: {name}\n"
            f"💰 Выручка: {revenue}\n"
            f"📞 Контакт: {phone}\n"
            f"📎 Запросил: {file_name}\n"
            f"🆔 Telegram ID: {update.effective_user.id}"
        )
    )

    # Отправка файла пользователю
    await update.message.reply_text(f"Отправляю {file_name} прямо сейчас 👇")

    if file_key in FILES:
        try:
            with open(FILES[file_key], "rb") as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"📎 {file_name}\n\nПо вопросам: {ADMIN_USER}"
                )
        except FileNotFoundError:
            logger.error(f"Файл не найден: {FILES[file_key]}")
            await update.message.reply_text(
                f"Файл пришлём в ближайшее время. Напишите напрямую: {ADMIN_USER}"
            )
    elif file_key == "consult":
        await update.message.reply_text(
            f"✅ Заявка принята! Денис свяжется в течение нескольких часов.\n\n"
            f"Пока почитайте материалы: https://media.nexops.ru"
        )

    # Финальные кнопки
    await update.message.reply_text(
        "Если есть вопросы — всегда на связи:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Сайт Nexops", url="https://nexops.ru")],
            [InlineKeyboardButton("📚 Медиа — статьи", url="https://media.nexops.ru")],
            [InlineKeyboardButton("🔄 Получить другой материал", callback_data="restart")],
        ])
    )
    return ConversationHandler.END


# ══════════════════════════════════════════
# РЕСТАРТ
# ══════════════════════════════════════════
async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await start(update, context)


async def noop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Разделители — просто сбрасываем callback."""
    await update.callback_query.answer()


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "До встречи! Напишите /start когда понадоблюсь.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ══════════════════════════════════════════
# ЗАПУСК
# ══════════════════════════════════════════
def main():
    # Запускаем health-check сервер в фоне (нужен для Render.com)
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    app = Application.builder().token(TOKEN).build()

    # ConversationHandler с allow_reentry=True — ключевой фикс!
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler, pattern="^(?!restart$|noop$).*")
        ],
        states={
            ASK_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_REVENUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_revenue)],
            ASK_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            # Если в середине диалога нажали другую кнопку — перезапускаем
            CallbackQueryHandler(button_handler, pattern="^(?!restart$|noop$).*"),
        ],
        allow_reentry=True,  # ФИКС: разрешаем повторный вход в диалог
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(restart_handler, pattern="^restart$"))
    app.add_handler(CallbackQueryHandler(noop_handler, pattern="^noop$"))
    app.add_handler(conv)

    print("✅ Бот запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
