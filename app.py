import requests
import feedparser
import random
import re
import os
import time
import sys

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
    # حيدنا parse_mode باش مايبقاش يخوي الرسالة
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=20)
        print(r.text[:500])
    except Exception as e:
        print(f"Error: {e}")

def send_long_message(text):
    # كنقطعو على 3500 حرف
    clean = text.replace("*", "").replace("_", "").replace("`", "")
    chunks = [clean[i:i+3500] for i in range(0, len(clean), 3500)]
    for i, chunk in enumerate(chunks):
        send_telegram_msg(f"📄 Part {i+1}/{len(chunks)}\n\n{chunk}")
        time.sleep(1.5)

def get_full_article_text(url, rss_content=""):
    # 1. نجربو Jina Reader - هو اللي كيحل مشكل Medium
    try:
        jina_url = f"https://cc.bingj.com/cache.cgi?d=1&w=1&u=https://cc.bingj.com/cache.cgi?d=1&w=1&u=https://r.jina.ai/{url}"
        # الطريقة الصحيحة:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(jina_url, headers=headers, timeout=30)
        text = r.text
        # كنحيدو الزبل ديال Jina
        # كناخدو غير النص من بعد العنوان
        if len(text) > 1000:
            # حيد أول سطور ديال الميتا
            lines = [l for l in text.split("\n") if len(l.strip()) > 30]
            text = "\n\n".join(lines)
            return text[:18000]
    except Exception as e:
        print(f"Jina failed: {e}")
    
    # 2. إلا فشل Jina، نجيبو من RSS
    if rss_content and len(rss_content) > 500:
        # حيد HTML tags
        clean = re.sub(r'<[^>]+>', '', rss_content)
        return clean[:18000]
    
    return "Could not fetch full article. Please open the link above."

def get_hard_words(text):
    words = re.findall(r'\b[a-zA-Z]{8,}\b', text.lower())
    # حيد الكلمات العادية
    stop = {"understanding","different","something","everything","because","through","between","however","therefore","although"}
    words = [w for w in words if w not in stop]
    unique = list(set(words))
    random.shuffle(unique)
    hard_words = unique[:5]
    if not hard_words:
        return "No hard words found today."
    result = "📚 Hard Words Explained:\n"
    for w in hard_words:
        try:
            d = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{w}", timeout=10).json()
            definition = d[0]['meanings'][0]['definitions'][0]['definition']
            result += f"\n- {w}: {definition}\n"
        except:
            continue
    return result

def get_summary(text):
    sentences = re.split(r'(?<=[.!?]) +', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
    if len(sentences) < 5:
        return text[:1000]
    summary = " ".join(sentences[:3]) + "\n\n... \n\n" + sentences[-1]
    return summary

def morning_task():
    topic_url = random.choice(TOPICS)
    feed = feedparser.parse(topic_url)
    if not feed.entries:
        send_telegram_msg("Couldn't find articles today.")
        return
    article = random.choice(feed.entries)
    # جيب المحتوى ديال RSS كـ backup
    rss_content = ""
    if hasattr(article, 'content'):
        rss_content = article.content[0].value
    elif hasattr(article, 'summary'):
        rss_content = article.summary

    send_telegram_msg(f"📖 Daily Reading\n\n{article.title}\n\nLink: {article.link}\n\nFetching full article...")
    
    full_text = get_full_article_text(article.link, rss_content)
    send_long_message(full_text)
    
    hard = get_hard_words(full_text)
    send_telegram_msg(hard)
    
    summary = get_summary(full_text)
    send_telegram_msg(f"✨ Summary:\n\n{summary}")

def evening_task():
    send_telegram_msg("🌙 Good Evening!\n\nI hope you had a wonderful and productive day. Wishing you a peaceful night and a great day tomorrow!")

if len(sys.argv) > 1 and sys.argv[1] == "morning":
    morning_task()
elif len(sys.argv) > 1 and sys.argv[1] == "evening":
    evening_task()
else:
    morning_task()
