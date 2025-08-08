# main.py
# بوت تيليجرام لتحليل الشارتات حسب استراتيجيتك المؤسسية + سكالبينج
# يعتمد على Gemini Vision لتحليل الصور و NewsAPI لجلب الأخبار
# مكتوب بسيط وواضح علشان ترفعه على GitHub وتشغّله بسهولة.

import time
import requests
import base64
import telebot
from datetime import datetime

# ----------------- إعدادات (ضع التوكنات هنا كما أعطيتني) -----------------
TELEGRAM_TOKEN = "8395291239:AAHO-gN9TJwF6LJ2-SBB4e1PQk1WkrWEpGU"
GEMINI_API_KEY = "AIzaSyDKtS7zLFfp-dFYrP5JvDsFL7nMlChDORM"
NEWS_API_KEY = "4d8b101b90e04e19acb77615631c9507"
# ------------------------------------------------------------------------

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)

# صغير: قاموس كلمات إيجابية/سلبية لتحليل سريع للمشاعر (مش احترافي لكن مفيد للبداية)
POS_WORDS = {"صعود","إيجابي","ارتفاع","قوي","شراء","تفاؤل","ربح","ارتفاعات","موجة"}
NEG_WORDS = {"هبوط","سلبي","انخفاض","خسارة","بيع","تشاؤم","هبوطات","ذعر"}

# ---------- دوال المساعدة ----------
def simple_sentiment(text):
    """
    تحليل بسيط للمشاعر: عد كلمات إيجابية وسلبية.
    """
    t = text.lower()
    pos = sum(t.count(w) for w in POS_WORDS)
    neg = sum(t.count(w) for w in NEG_WORDS)
    if pos > neg:
        return "إيجابية (ميل للشراء)"
    elif neg > pos:
        return "سلبية (ميل للبيع)"
    else:
        return "محايدة / غير واضحة"

def chunk_text(text, size=3000):
    """يجزأ النص لو طويل عشان تقدر تبعته في رسائل متعددة"""
    return [text[i:i+size] for i in range(0, len(text), size)]

# ---------- جلب الأخبار (NewsAPI) ----------
def get_market_news(pair_name, lang="ar"):
    try:
        q = requests.utils.quote(pair_name)
        url = f"https://newsapi.org/v2/everything?q={q}&language={lang}&sortBy=publishedAt&pageSize=6&apiKey={NEWS_API_KEY}"
        r = requests.get(url, timeout=12)
        j = r.json()
        if j.get("status") != "ok":
            return "لم أتمكن من جلب الأخبار الآن."
        articles = j.get("articles", [])[:5]
        if not articles:
            return "لا توجد أخبار حديثة مرتبطة بهذا الزوج."
        out = []
        for a in articles:
            ts = a.get("publishedAt", "")
            title = a.get("title", "")
            src = a.get("source", {}).get("name", "")
            urla = a.get("url", "")
            out.append(f"• {title} ({src})\n{urla}\n")
        return "\n".join(out)
    except Exception as e:
        return f"خطأ في جلب الأخبار: {e}"

# ---------- استدعاء Gemini Vision لتحليل الصور ----------
def analyze_image_with_gemini_base64(image_b64, pair_name):
    """
    يرسل الصورة (base64) مع برومبت مخصص للاستراتيجية.
    يعيد نص التحليل من خدمة Gemini (Generative Language API).
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json; charset=utf-8"}

    prompt_text = f"""
أنت محلل سوق محترف (مؤسسي + سكالبينج) مُطّلع على الاستراتيجية التالية:
- SMC: مناطق السيولة، Stop Hunts، مناطق تجميع المؤسسات.
- مؤشرات: RSI (زاوية الميل)، MACD، حجم التداول، EMA50/200، VWAP.
- برايس أكشن: الشموع Engulfing, Pin Bar, Doji, Marubozu.
- نماذج سعرية: Head&Shoulders, Double Top/Bottom, Triangles, Channels.
- ATR/Market Profile لتحديد التقلب ومناطق القيمة.
- ربط الأخبار وSentiment مع التحليل الفني.

الصورة المرفقة تُظهر شارت ومؤشرات لزوج: {pair_name}.
المطلوب منك:
1) قراءة الشارت: اذكر الاتجاه العام على H1/H4/Daily إن أمكن.
2) حدد مناطق الدعم والمقاومة الظاهرة، ومناطق السيولة المحتملة.
3) اقرأ الشموع الظاهرة (اذكر أي Engulfing/PinBar/Doji).
4) حدد أي نموذج سعري ظاهر واقترح نقاط دخول (مع فريم) ووقف خسارة وTPs.
5) قيم قوة الصفقة (ضعيفة/متوسطة/قوية) على حسب توافق الفلاتر.
6) اذكر أي فرضيات اعتمدتها أو بيانات ناقصة.
أعطني النتيجة كنص عربي منظم.
"""

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text},
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                ]
            }
        ],
        "temperature": 0.1,
        "maxOutputTokens": 1200
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=25)
        j = resp.json()
        # نحاول الوصول للنص بأمان
        candidates = j.get("candidates") or []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "لم أتمكن من استخراج نص من Gemini.")
        # تعليق أو خطأ
        return f"تعذر استخراج نتيجة من Gemini. الرد الخام: {j}"
    except Exception as e:
        return f"خطأ في طلب Gemini: {e}"

# ---------- التعامل مع صور التيليجرام ----------
@bot.message_handler(commands=['start','help'])
def send_welcome(m):
    txt = (
        "أهلاً! 👋\n"
        "طريقة الاستخدام البسيطة:\n"
        "1) ارسل صورة للشارت (افضل إنك ترفق اسم الزوج في الكابشن، مثل: EURUSD)\n"
        "2) سأحلل الصورة، أجلب الأخبار، وأرد عليك بتقرير كامل مبني على استراتيجيتنا.\n\n"
        "أوامر:\n"
        "/start - رسالة ترحيب\n"
        "/status - حالة البوت\n"
        "/example - شرح سريع للمخرجات"
    )
    bot.reply_to(m, txt)

@bot.message_handler(commands=['status'])
def status(m):
    bot.reply_to(m, f"بوت التحليل شغال الآن — الوقت: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

@bot.message_handler(commands=['example'])
def example(m):
    ex = (
        "مثال للنتيجة التي ستستلمها:\n"
        "• اتجاه H1: صاعد\n"
        "• مناطق دعم: 1.0750 — مقاومة: 1.0820\n"
        "• اقتراح دخول شراء عند 1.0760 (SL 1.0720) TP1=1.0800 TP2=1.0850\n"
        "• قوة الصفقة: متوسطة (SMC + Engulfing + Volume surge)\n"
    )
    bot.reply_to(m, ex)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # اسم الزوج من الكابشن أو استخدم EURUSD كمجرد مثال
        pair = (message.caption or "").strip()
        if not pair:
            pair = "EURUSD"

        # جلب ملف الصورة من تيليجرام
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        # تحويل للصيغة base64
        image_b64 = base64.b64encode(downloaded).decode('utf-8')

        bot.reply_to(message, f"استلمت الصورة للزوج {pair} — جاري التحليل الآن...")

        # 1) تحليل الصورة عبر Gemini Vision
        analysis_text = analyze_image_with_gemini_base64(image_b64, pair)

        # 2) جلب الأخبار
        news_text = get_market_news(pair)

        # 3) تحليل مشاعر بسيط من عناوين الأخبار
        sentiment = simple_sentiment(" ".join([news_text or ""]))

        # 4) بناء التقرير
        report = f"📊 تحليل: {pair}\n\n"
        report += f"🔎 ناتج تحليل الشارت:\n{analysis_text}\n\n"
        report += f"📰 آخر الأخبار:\n{news_text}\n\n"
        report += f"🧭 تحليـل المشاعر (سريع): {sentiment}\n\n"
        report += "⚠️ ملاحظات: اعتمدت على الصور المرسلة والأخبار المأخوذة من NewsAPI. قد تحتاج بيانات Bookmap/عمق سوق إضافية لتحليل أعمق.\n"

        # ارسال التقرير على شكل مقاطع لو طويل
        for ch in chunk_text(report, 3000):
            bot.send_message(message.chat.id, ch)
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {e}")

# ---------- تشغيل مستمر (مهم في بعض البيئات) ----------
if __name__ == "__main__":
    print("Bot started...")
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout = 60)
    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception as e:
        print("Bot crashed:", e)
        time.sleep(10)
