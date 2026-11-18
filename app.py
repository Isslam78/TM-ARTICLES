import requests
import feedparser
import random
import re
import os
from bs4 import BeautifulSoup

# كيجيبهم من GitHub Secrets، ماشي كتكتبهم فالكود
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TOPICS = [
    "https://medium.com/feed/tag/atheism",
    "https://medium.com/feed/tag/math",
    "https://medium.com/feed/tag/physics",
    "https://medium.com/feed/tag/philosophy",
    "https://medium.com/feed/tag/health",
    "https://medium.com/feed/tag/absurdity",
    "https://medium.com/feed/tag/nihilism"
]

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=20)
        print(r.text[:200])
    except Exception as e:
        print(f"Error: {e}")

def send_long_message(text):
    # تيليجرام كيقبل غير 4096 حرف فالرسالة، داكشي علاش كنقطعوه
    chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]
    for i, chunk in enumerate(chunks):
        send_telegram_msg(f"📄 Part {i+1}/{len(chunks)}\n\n{chunk}")
        # باش ميديرش سبام
        import time; time.sleep(1)

def get_full_article_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        # كنجيب غير النص ديال المقال
        paragraphs = soup.find_all('p')
        text = "\n\n".join([p.get_text() for p in paragraphs if len(p.get_text()) > 40])
        # كنحيدو الاعلانات والزايد
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text[:15000]  # باش ماتجيش رسالة طويلة بزاف
    except Exception as e:
        return f"Could not fetch full text: {e}"

def get_hard_words(text):
    # كنجيب الكلمات الطوال اللي غالبا صعاب
    words = re.findall(r'\b[a-zA-Z]{9,}\b', text.lower())
    # كنحيدو الكلمات المعاودة
    unique = list(set(words))
    random.shuffle(unique)
    hard_words = unique[:5]  # 5 كلمات صعاب
    result = "\n\n📚 *Hard Words Explained:*\n"
    for w in hard_words:
        try:
            # كنجيب الشرح من قاموس مجاني
            d = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{w}", timeout=10).json()
            definition = d[0]['meanings'][0]['definitions'][0]['definition']
            result += f"\n*• {w}:* {definition}\n"
        except:
            result += f"\n*• {w}:* (no definition found)\n"
    return result

def get_summary(text):
    # خلاصة بسيطة: أول 3 جمل + آخر جملة
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) < 5:
        return text[:800]
    summary = " ".join(sentences[:3]) + "\n\n... \n\n" + sentences[-1]
    return summary

def morning_task():
    topic_url = random.choice(TOPICS)
    feed = feedparser.parse(topic_url)
    if not feed.entries:
        send_telegram_msg("Couldn't find articles today.")
        return
    article = random.choice(feed.entries)
    send_telegram_msg(f"📖 *Daily Reading*\n\n*{article.title}*\n\n[Original Link]({article.link})\n\nFetching full article...")
    
    full_text = get_full_article_text(article.link)
    send_long_message(full_text)
    
    # شرح الكلمات
    hard = get_hard_words(full_text)
    send_telegram_msg(hard)
    
    # الخلاصة
    summary = get_summary(full_text)
    send_telegram_msg(f"✨ *Summary:*\n\n{summary}")

def evening_task():
    send_telegram_msg("🌙 *Good Evening!*\n\nI hope you had a wonderful and productive day. Wishing you a peaceful night and a great day tomorrow! ✨")

# كنشوف شنو طلبنا من GitHub Actions
import sys
if len(sys.argv) > 1 and sys.argv[1] == "morning":
    morning_task()
elif len(sys.argv) > 1 and sys.argv[1] == "evening":
    evening_task()
else:
    morning_task()