import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, format, *args):
        pass
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# ══════════════════════════════════════════
# НАСТРОЙКИ
# ══════════════════════════════════════════
TOKEN = "8637969737:AAEEgbeCABVYymkX435S38TEyTiioYJsNHo"
ADMIN_CHAT_ID = 143516369
ADMIN_USERNAME = "@albega1"

# Пути к файлам
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
    "strat_b1": "Стратсессия или спектакль",
    "strat_a2": "Тест командной синхронизации",
    "strat_b2": "Дорожная карта стратсессии",
    "strat_c1": "Как не дать стратегии умереть через месяц",
    "consult":  "Заявка на диагностику",
}

ASK_NAME, ASK_REVENUE, ASK_PHONE = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("── Операционный директор ──", callback_data="noop")],
        [InlineKeyboardButton("📋 Готов ли бизнес к опердиру (PDF)", callback_data="opdir_a1")],
        [InlineKeyboardButton("📊 Трекинг-отчёт РНП (Excel)", callback_data="opdir_b1")],
        [InlineKeyboardButton("🔴 7 признаков узкого горлышка (PDF)", callback_data="opdir_c1")],
        [InlineKeyboardButton("── Стратегическая сессия ──", callback_data="noop")],
        [InlineKeyboardButton("✅ Чеклист подготовки к стратсессии (PDF)", callback_data="strat_ch")],
        [InlineKeyboardButton("🎭 Стратсессия или спектакль? (PDF)", callback_data="strat_b1")],
        [InlineKeyboardButton("🧪 Тест командной синхронизации (PDF)", callback_data="strat_a2")],
        [InlineKeyboardButton("🗺 Дорожная карта стратсессии (Excel)", callback_data="strat_b2")],
        [InlineKeyboardButton("📄 Как не дать стратегии умереть (PDF)", callback_data="strat_c1")],
        [InlineKeyboardButton("── ── ──", callback_data="noop")],
        [InlineKeyboardButton("💬 Оставить заявку на диагностику", callback_data="consult")],
    ]
    text = "👋 Привет! Я бот Nexops.\n\nВыберите что хотите получить 👇"
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["file_key"] = query.data
    context.user_data["file_name"] = NAMES.get(query.data, "материал")
    await query.message.reply_text(
        "Отлично! Пришлю прямо сейчас.\n\n"
        "Сначала пара вопросов — займёт 30 секунд.\n\n"
        "Как вас зовут?"
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    keyboard = [
        ["До 30 млн ₽", "30–100 млн ₽"],
        ["100–500 млн ₽", "Больше 500 млн ₽"],
    ]
    await update.message.reply_text(
        f"Приятно познакомиться, {context.user_data['name']}! 👋\n\n"
        "Какая примерно годовая выручка вашего бизнеса?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_REVENUE


async def ask_revenue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["revenue"] = update.message.text
    await update.message.reply_text(
        "Хорошо! Последний вопрос.\n\n"
        "Оставьте номер телефона — пришлю материал и при необходимости свяжемся:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    name      = context.user_data.get("name", "—")
    revenue   = context.user_data.get("revenue", "—")
    phone     = context.user_data.get("phone", "—")
    file_key  = context.user_data.get("file_key")
    file_name = context.user_data.get("file_name", "материал")
    tg_user   = update.message.from_user
    tg_link   = f"@{tg_user.username}" if tg_user.username else f"id:{tg_user.id}"

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"🔔 Новый лид из бота!\n\n"
            f"👤 Имя: {name}\n"
            f"💰 Выручка: {revenue}\n"
            f"📞 Телефон: {phone}\n"
            f"📱 Telegram: {tg_link}\n"
            f"📦 Запросил: {file_name}"
        )
    )

    await update.message.reply_text(f"Спасибо, {name}! Отправляю прямо сейчас 👇")

    if file_key and file_key in FILES:
        try:
            with open(FILES[file_key], "rb") as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"📎 {file_name}\n\nПо вопросам: {ADMIN_USERNAME}"
                )
        except FileNotFoundError:
            await update.message.reply_text(
                f"📎 Файл пришлём в ближайшее время.\n"
                f"Напишите напрямую: {ADMIN_USERNAME}"
            )
    else:
        await update.message.reply_text(
            "✅ Заявка принята! Денис свяжется в течение нескольких часов.\n\n"
            "Пока почитайте материалы: https://media.nexops.ru"
        )

    keyboard = [
        [InlineKeyboardButton("🌐 Сайт Nexops", url="https://nexops.ru")],
        [InlineKeyboardButton("📚 Медиа — статьи и материалы", url="https://media.nexops.ru")],
        [InlineKeyboardButton("💬 Написать Денису", url="https://t.me/denismatyushin")],
        [InlineKeyboardButton("🔄 Получить другой материал", callback_data="restart")],
    ]
    await update.message.reply_text(
        "Если есть вопросы — всегда на связи:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END


async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "До встречи! Напишите /start когда понадоблюсь.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^(?!restart$|noop$).*")],
        states={
            ASK_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_REVENUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_revenue)],
            ASK_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(restart_handler, pattern="^restart$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"))
    app.add_handler(conv)
    PORT = int(__import__('os').environ.get('PORT', 10000))
    threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), Handler).serve_forever(), daemon=True).start()
    app.run_polling()

if __name__ == "__main__":
    main()
