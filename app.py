import requests
import feedparser
import random
import re
import os
import time
import sys

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- المواضيع ديالك ---
# كل موضوع عندو الكلمة ديالو فكل موقع
MY_TOPICS = ["ai", "chess", "philosophy", "physics", "math", "health", "atheism", "nihilism", "absurdity"]

# تحويل المواضيع لـ DEV.to tags
DEV_TAG_MAP = {
    "ai": "ai",
    "chess": "chess",
    "philosophy": "philosophy",
    "physics": "physics",
    "math": "mathematics",
    "health": "health",
    "atheism": "philosophy",
    "nihilism": "philosophy",
    "absurdity": "philosophy",
}

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"Send Error: {e}")

def clean_text(text):
    if not text:
        return ""
    # حيد Markdown
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # حيد الصور
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # خلي غير النص ديال اللينك
    text = re.sub(r'#{1,6}\s*', '', text)  # حيد ###
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)  # حيد الروابط
    text = text.replace("Press enter or click to view image in full size", "")
    text = text.replace("Continue reading on Medium", "")
    # حيد السطور الخاوية بزاف
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 5]
    # حيد سطور الزبل
    lines = [l for l in lines if not l.lower().startswith(("image:", "photo by", "published in", "source:"))]
    clean = "\n\n".join(lines)
    return clean.strip()

def send_long_message(text):
    clean = clean_text(text)
    if len(clean) < 500:
        return False
    chunks = [clean[i:i+3500] for i in range(0, len(clean), 3500)]
    for i, chunk in enumerate(chunks):
        send_telegram_msg(f"📄 Part {i+1}/{len(chunks)}\n\n{chunk}")
        time.sleep(1.2)
    return True

# ========== 1. DEV.TO - أفضل مصدر، API نقي 0% خطأ ==========
def try_devto(topic):
    try:
        tag = DEV_TAG_MAP.get(topic, "ai")
        url = f"https://dev.to/api/articles?tag={tag}&top=7&per_page=10"
        r = requests.get(url, timeout=15)
        articles = r.json()
        if not articles:
            return None
        random.shuffle(articles)
        for art in articles[:3]:
            # جيب المقال كامل بالـ ID
            detail = requests.get(f"https://dev.to/api/articles/{art['id']}", timeout=15).json()
            body = clean_text(detail.get("body_markdown", "") or detail.get("body_html", ""))
            # حيد HTML إلا بقا
            body = re.sub(r'<[^>]+>', '', body)
            if len(body) > 800:
                return {"title": detail.get("title"), "link": detail.get("url"), "text": body, "source": "DEV.to"}
        return None
    except Exception as e:
        print(f"DEV failed: {e}")
        return None

# ========== 2. RSS SOURCES - كيعطيو النص كامل ==========
def try_rss(feed_url, source_name):
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return None
        random.shuffle(feed.entries)
        for entry in feed.entries[:4]:
            content = ""
            if hasattr(entry, 'content'):
                content = entry.content[0].value
            elif hasattr(entry, 'summary'):
                content = entry.summary
            # حيد HTML
            content = re.sub(r'<[^>]+>', '\n', content)
            content = clean_text(content)
            if len(content) > 800:
                return {"title": entry.title, "link": entry.link, "text": content, "source": source_name}
        return None
    except Exception as e:
        print(f"{source_name} failed: {e}")
        return None

# ========== 3. MEDIUM - آخر واحد، غير إلا فشلو كاملين ==========
def try_medium(topic):
    try:
        feed_url = f"https://medium.com/feed/tag/{topic}"
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return None
        random.shuffle(feed.entries)
        for entry in feed.entries[:3]:
            # جرب Freedium
            try:
                freedium_url = f"https://freedium.cfd/{entry.link}"
                r = requests.get(freedium_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                # جيب الفقرات
                paras = re.findall(r'<p[^>]*>(.*?)</p>', r.text, re.DOTALL)
                text = "\n\n".join([re.sub(r'<[^>]+>', '', p) for p in paras])
                text = clean_text(text)
                if len(text) > 800:
                    return {"title": entry.title, "link": entry.link, "text": text, "source": "Medium via Freedium"}
            except:
                continue
            # جرب Jina
            try:
                jina = requests.get(f"https://r.jina.ai/{entry.link}", timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
                jina = clean_text(jina)
                if len(jina) > 800:
                    return {"title": entry.title, "link": entry.link, "text": jina, "source": "Medium via Jina"}
            except:
                continue
        return None
    except Exception as e:
        print(f"Medium failed: {e}")
        return None

def get_hard_words(text):
    words = re.findall(r'\b[a-zA-Z]{8,}\b', text.lower())
    stop = {"understanding","different","something","everything","because","through","between","however","therefore","although","continue","reading"}
    words = [w for w in words if w not in stop]
    unique = list(set(words))
    random.shuffle(unique)
    result = "📚 Hard Words Explained:\n"
    count = 0
    for w in unique:
        if count >= 5: break
        try:
            d = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{w}", timeout=10).json()
            definition = d[0]['meanings'][0]['definitions'][0]['definition']
            result += f"\n- {w}: {definition}\n"
            count += 1
        except:
            continue
    return result if count > 0 else "No hard words today."

def get_summary(text):
    sentences = re.split(r'(?<=[.!?]) +', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
    if len(sentences) < 5:
        return text[:1000]
    return " ".join(sentences[:3]) + "\n\n... \n\n" + sentences[-1]

def morning_task():
    topic = random.choice(MY_TOPICS)
    print(f"Topic today: {topic}")
    article = None

    # 1. جرب DEV.to هو اللول
    article = try_devto(topic)
    print(f"DEV result: {article is not None}")

    # 2. إلا فشل، جرب freeCodeCamp
    if not article:
        article = try_rss("https://www.freecodecamp.org/news/rss/", "freeCodeCamp")

    # 3. إلا فشل، جرب HackerNoon
    if not article:
        article = try_rss("https://hackernoon.com/feed", "HackerNoon")

    # 4. إلا فشل، جرب The Conversation - ممتاز للفلسفة والفيزياء
    if not article:
        article = try_rss("https://theconversation.com/articles.atom", "The Conversation")

    # 5. آخر واحد Medium
    if not article:
        article = try_medium(topic)

    if not article:
        send_telegram_msg("⚠️ All sources failed today. Trying again tomorrow.")
        return

    send_telegram_msg(f"📖 Daily Reading from {article['source']}\n\nTopic: {topic}\n\n{article['title']}\n\nLink: {article['link']}")
    
    ok = send_long_message(article['text'])
    if not ok:
        send_telegram_msg("⚠️ Text was too short, open the link above.")
        return

    send_telegram_msg(get_hard_words(article['text']))
    send_telegram_msg(f"✨ Summary:\n\n{get_summary(article['text'])}")

def evening_task():
    send_telegram_msg("🌙 Good Evening!\n\nI hope you had a wonderful and productive day. Wishing you a peaceful night and a great day tomorrow!")

if len(sys.argv) > 1 and sys.argv[1] == "morning":
    morning_task()
elif len(sys.argv) > 1 and sys.argv[1] == "evening":
    evening_task()
else:
    morning_task()
