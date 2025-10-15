import logging
import re
import os
from flask import Flask, request
from telegram import Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from collections import defaultdict
from functools import wraps
from datetime import datetime

# إعدادات اللوغينغ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- استبدل هذا بالتوكن الخاص بك ---
TOKEN = "8220416436:AAGBEFxbmxmjAF82KmrrlFnNmqV6wtJZvUE"

# Flask app
app = Flask(__name__)

# قاموس لتخزين بيانات المستخدمين وعدد الكويزات التي أنشأوها
user_quiz_counts = defaultdict(int)

def log_user_info(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_info = (
                f"\n================= تفاعل جديد مع البوت =================\n"
                f"🗓️ التاريخ والوقت: {current_time}\n"
                f"👤 الاسم: {user.full_name}\n"
                f"🆔 المعرّف: @{user.username if user.username else 'لا يوجد'}\n"
                f"🔢 الرقم التعريفي: {user.id}\n"
                f"====================================================\n"
            )
            print(user_info)
        return await func(update, context, *args, **kwargs)
    return wrapper

def print_quiz_stats(user: User, quizzes_created_this_time: int):
    user_quiz_counts[user.id] += quizzes_created_this_time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats_info = (
        f"\n================ إحصائيات إنشاء كويز ================\n"
        f"🗓️ التاريخ والوقت: {current_time}\n"
        f"👤 المستخدم: {user.full_name} (@{user.username if user.username else 'لا يوجد'})\n"
        f"🆕 عدد الكويزات هذه المرة: {quizzes_created_this_time}\n"
        f"📊 إجمالي الكويزات للمستخدم: {user_quiz_counts[user.id]}\n"
        f"==================================================\n"
    )
    print(stats_info)

@log_user_info
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "🎯 مرحباً بك في بوت الكويزات!\n\n"
        "هذا البوت يحول النصوص إلى كويزات تفاعلية.\n\n"
        "📝 طريقة الاستخدام:\n"
        "أرسل رسالة بالشكل التالي:\n\n"
        "السؤال: (تلميح اختياري)\n"
        "الخيار الأول\n"
        "الخيار الثاني\n"
        "الخيار الصحيح*\n\n"
        "✨ ميزة جديدة: يمكنك إرسال عدة أسئلة في رسالة واحدة بفصلها بعلامة #\n\n"
        "تم انشاء البوت بواسطة @ammarajaj09\n"
        "استخدم /help لمزيد من المعلومات."
    )
    await update.message.reply_text(welcome_message)

@log_user_info
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = (
        "📚 تعليمات استخدام البوت:\n\n"
        "1️⃣ اكتب السؤال متبوعاً بنقطتين (:)\n"
        "2️⃣ اكتب التلميح بين قوسين (اختياري)\n"
        "3️⃣ اكتب كل خيار في سطر منفصل\n"
        "4️⃣ ضع علامة * بجانب الإجابة الصحيحة\n\n"
        "📋 مثال لسؤال واحد:\n"
        "ما عاصمة سوريا: (المدينة الرئيسية)\n"
        "دمشق*\n"
        "حلب\n"
        "حمص\n\n"
        "--- ( إنشاء عدة كويزات ) ---\n\n"
        "✨ لإرسال عدة أسئلة دفعة واحدة، افصل بين كل سؤال بعلامة #\n\n"
        "📋 مثال لسؤالين:\n"
        "السؤال الأول:\n"
        "خيار 1*\n"
        "خيار 2\n"
        "#\n"
        "السؤال الثاني: (تلميح)\n"
        "خيار أ\n"
        "خيار ب*\n\n"
        "⚠️ ملاحظات مهمة:\n"
        "- يجب أن يكون هناك خيار واحد فقط صحيح لكل سؤال (*)\n"
        "- يمكن إضافة حتى 10 خيارات لكل سؤال."
    )
    await update.message.reply_text(help_message)

@log_user_info
async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
        
    full_text = update.message.text
    quiz_texts = [q.strip() for q in full_text.split('#') if q.strip()]

    if not quiz_texts:
        await update.message.reply_text("لم يتم العثور على أي سؤال. يرجى التحقق من النص المرسل.")
        return

    quizzes_created_count = 0
    for text in quiz_texts:
        lines = text.strip().split('\n')

        if len(lines) < 3:
            await update.message.reply_text(
                f"❌ تنسيق خاطئ في السؤال:\n`{lines[0]}`\n\n"
                "يرجاء التأكد من وجود سؤال وخيارين على الأقل.",
                parse_mode='Markdown'
            )
            continue

        question_line = lines[0].strip()
        user_hint = None

        match = re.match(r"^(.*?):?\s*\((.*?)\)$", question_line)
        if match:
            question_text = match.group(1).strip()
            user_hint = match.group(2).strip()
        else:
            question_text = question_line.strip().removesuffix(':').strip()

        options = []
        correct_option_id = -1

        for line in lines[1:]:
            line = line.strip()
            if not line: continue
            if line.endswith('*'):
                if correct_option_id != -1:
                    await update.message.reply_text(f"خطأ في السؤال '{question_text}': تم تحديد أكثر من إجابة صحيحة. يرجى استخدام * مرة واحدة فقط.")
                    correct_option_id = -2
                    break
                options.append(line[:-1].strip())
                correct_option_id = len(options) - 1
            else:
                options.append(line)
        
        if correct_option_id == -2: continue

        if correct_option_id == -1:
            await update.message.reply_text(f"خطأ في السؤال '{question_text}': يرجى تحديد الإجابة الصحيحة بعلامة *.")
            continue

        if len(options) > 10:
            await update.message.reply_text(f"خطأ في السؤال '{question_text}': لا يمكن إضافة أكثر من 10 خيارات.")
            continue

        credit_line = "تم إنشاء هذا الكويز بواسطة بوت الكويزات"
        final_explanation = f"{user_hint}\n\n{credit_line}" if user_hint else credit_line

        try:
            await update.message.reply_poll(
                question=question_text,
                options=options,
                type="quiz",
                correct_option_id=correct_option_id,
                is_anonymous=True,
                explanation=final_explanation
            )
            quizzes_created_count += 1
        except Exception as e:
            logger.error(f"Error creating quiz for question '{question_text}': {e}")
            await update.message.reply_text(f"حدث خطأ أثناء إنشاء الكويز للسؤال '{question_text}'.")

    if quizzes_created_count > 0:
        user = update.effective_user
        if user:
            print_quiz_stats(user, quizzes_created_count)
        await update.message.reply_text(f"✅ تم إنشاء {quizzes_created_count} كويز بنجاح!")

# إنشاء البوت التلجرام
application = Application.builder().token(TOKEN).build()

# إضافة handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, create_quiz))

# Routes for Render
@app.route('/')
def home():
    return "بوت الكويزات يعمل بنجاح! ✅"

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook route for Telegram"""
    update = Update.de_json(await request.get_json(), application.bot)
    await application.process_update(update)
    return 'OK'

@app.route('/set_webhook')
async def set_webhook():
    """Set webhook for Telegram"""
    webhook_url = f"https://{request.host}/webhook"
    await application.bot.set_webhook(webhook_url)
    return f"Webhook set to: {webhook_url}"

def main() -> None:
    """Start the bot with webhook for production, polling for development"""
    if os.environ.get('RENDER'):  # إذا كنا على Render
        print("🚀 Starting bot in WEBHOOK mode...")
        # سيتم تشغيل Flask app
    else:  # للتطوير المحلي
        print("🔧 Starting bot in POLLING mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
