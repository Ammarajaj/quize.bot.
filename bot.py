import os
import logging
import re
from flask import Flask, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from collections import defaultdict
from datetime import datetime

# إعدادات اللوغينغ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# التوكن
TOKEN = "8220416136:AAGBEFxbmxmjAF82KmrrlFnNmqV6wtJZvUE"

# تطبيق Flask
app = Flask(__name__)

# قاموس لتخزين بيانات المستخدمين
user_quiz_counts = defaultdict(int)

def log_user_info(func):
    def wrapper(update, context, *args, **kwargs):
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
        return func(update, context, *args, **kwargs)
    return wrapper

def print_quiz_stats(user, quizzes_created_this_time):
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
def start(update: Update, context: CallbackContext) -> None:
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
    update.message.reply_text(welcome_message)

@log_user_info
def help_command(update: Update, context: CallbackContext) -> None:
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
        "⚠️ ملاحظات مهمة:\n"
        "- يجب أن يكون هناك خيار واحد فقط صحيح لكل سؤال (*)\n"
        "- يمكن إضافة حتى 10 خيارات لكل سؤال."
    )
    update.message.reply_text(help_message)

@log_user_info
def create_quiz(update: Update, context: CallbackContext) -> None:
    if not update.message or not update.message.text:
        return
        
    full_text = update.message.text
    quiz_texts = [q.strip() for q in full_text.split('#') if q.strip()]

    if not quiz_texts:
        update.message.reply_text("لم يتم العثور على أي سؤال. يرجى التحقق من النص المرسل.")
        return

    quizzes_created_count = 0
    for text in quiz_texts:
        lines = text.strip().split('\n')

        if len(lines) < 3:
            update.message.reply_text(
                f"❌ تنسيق خاطئ في السؤال:\n`{lines[0]}`\n\n"
                "يرجى التأكد من وجود سؤال وخيارين على الأقل."
            )
            continue

        question_line = lines[0].strip()
        user_hint = None

        match = re.match(r"^(.*?):?\s*\((.*?)\)$", question_line)
        if match:
            question_text = match.group(1).strip()
            user_hint = match.group(2).strip()
        else:
            question_text = question_line.rstrip(':').strip()

        options = []
        correct_option_id = -1

        for line in lines[1:]:
            line = line.strip()
            if not line: 
                continue
            if line.endswith('*'):
                if correct_option_id != -1:
                    update.message.reply_text(f"خطأ في السؤال '{question_text}': تم تحديد أكثر من إجابة صحيحة.")
                    correct_option_id = -2
                    break
                options.append(line[:-1].strip())
                correct_option_id = len(options) - 1
            else:
                options.append(line)
        
        if correct_option_id == -2: 
            continue

        if correct_option_id == -1:
            update.message.reply_text(f"خطأ في السؤال '{question_text}': يرجى تحديد الإجابة الصحيحة بعلامة *.")
            continue

        if len(options) > 10:
            update.message.reply_text(f"خطأ في السؤال '{question_text}': لا يمكن إضافة أكثر من 10 خيارات.")
            continue

        credit_line = "تم إنشاء هذا الكويز بواسطة بوت الكويزات"
        final_explanation = f"{user_hint}\n\n{credit_line}" if user_hint else credit_line

        try:
            update.message.reply_poll(
                question=question_text,
                options=options,
                type="quiz",
                correct_option_id=correct_option_id,
                is_anonymous=True,
                explanation=final_explanation
            )
            quizzes_created_count += 1
        except Exception as e:
            logger.error(f"Error creating quiz: {e}")
            update.message.reply_text(f"حدث خطأ أثناء إنشاء الكويز.")

    if quizzes_created_count > 0:
        user = update.effective_user
        if user:
            print_quiz_stats(user, quizzes_created_count)
        update.message.reply_text(f"✅ تم إنشاء {quizzes_created_count} كويز بنجاح!")

# إنشاء البوت
updater = Updater(TOKEN)
dp = updater.dispatcher

# إضافة handlers
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, create_quiz))

# Routes for Render
@app.route('/')
def home():
    return "بوت الكويزات يعمل بنجاح! ✅"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), updater.bot)
    dp.process_update(update)
    return 'OK'

@app.route('/set_webhook')
def set_webhook():
    webhook_url = f"https://{request.host}/webhook"
    updater.bot.set_webhook(webhook_url)
    return f"Webhook set to: {webhook_url}"

if __name__ == '__main__':
    # على Render استخدم webhook
    if 'RENDER' in os.environ:
        print("🚀 Starting in WEBHOOK mode...")
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    else:
        # للتطوير المحلي استخدم polling
        print("🔧 Starting in POLLING mode...")
        updater.start_polling()
        updater.idle()
