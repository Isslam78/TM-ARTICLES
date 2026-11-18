import requests
import feedparser
import random
import re
import os
import time
import sys
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# زدت الشطرنج و AI هنا
TOPICS = [
    "https://medium.com/feed/tag/atheism",
    "https://medium.com/feed/tag/math",
    "https://medium.com/feed/tag/physics",
    "https://medium.com/feed/tag/philosophy",
    "https://medium.com/feed/tag/health",
    "https://medium.com/feed/tag/absurdity",
    "https://medium.com/feed/tag/nihilism",
    "https://medium.com/feed/tag/chess",
    "https://medium.com/feed/tag/chess-strategy",
    "https://medium.com/feed/tag/artificial-intelligence",
    "https://medium.com/feed/tag/ai",
    "https://medium.com/feed/tag/machine-learning",
    "https://medium.com/feed/tag/deep-learning",
]

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"Error: {e}")

def clean_text(text):
    """هادي هي اللي كتنقي النص المشوه"""
    if not text:
        return ""
    # حيد روابط الصور ![...](...)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # حيد الروابط [نص](رابط) -> خلي غير النص
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # حيد ### و ## و # و *** و ___
    text = re.sub(r'#+\s*', '', text)
    text = text.replace("***", "").replace("___", "")
    # حيد الروابط الخام
    text = re.sub(r'https?://\S+', '', text)
    # حيد سطور الزبل ديال Medium
    bad_lines = ["Press enter", "click to view image", "Image:", "Published in", "Continue reading", "Source:", "URI Source", "Title:"]
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 5:
            continue
        if any(b in line for b in bad_lines):
            continue
        if line.startswith("!") or line.startswith("["):
            continue
        lines.append(line)
    text = "\n\n".join(lines)
    # حيد الفراغات الكثيرة
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()[:18000]

def try_freedium(url):
    """المصدر 1: Freedium"""
    try:
        print("Trying Freedium...")
        freedium_url = f"https://freedium.cfd/{url}"
        r = requests.get(freedium_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Freedium كيحط المقال فـ article ولا div
        article = soup.find('article') or soup.find('div', class_='main-content') or soup
        paras = article.find_all('p')
        text = "\n\n".join([p.get_text() for p in paras if len(p.get_text()) > 30])
        print(f"Freedium got {len(text)} chars")
        return text if len(text) > 800 else None
    except Exception as e:
        print(f"Freedium failed: {e}")
        return None

def try_jina(url):
    """المصدر 2: Jina"""
    try:
        print("Trying Jina...")
        r = requests.get(f"https://r.jina.ai/{url}", headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        text = r.text
        print(f"Jina got {len(text)} chars")
        return text if len(text) > 800 else None
    except Exception as e:
        print(f"Jina failed: {e}")
        return None

def try_direct(url):
    """المصدر 3: Direct"""
    try:
        print("Trying Direct...")
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        paras = soup.find_all('p')
        text = "\n\n".join([p.get_text() for p in paras if len(p.get_text()) > 30])
        return text if len(text) > 800 else None
    except:
        return None

def get_full_article_text(url, rss_content=""):
    # كنجربو واحد بواحد
    for func in [try_freedium, try_jina, try_direct]:
        raw = func(url)
        if raw:
            cleaned = clean_text(raw)
            if len(cleaned) > 800:
                return cleaned
    # إلا كاملين فشلو، نرجعو لـ RSS
    if rss_content:
        cleaned = clean_text(re.sub(r'<[^>]+>', '', rss_content))
        if len(cleaned) > 200:
            return cleaned
    return None

def send_long_message(text):
    chunks = [text[i:i+3500] for i in range(0, len(text), 3500)]
    for i, chunk in enumerate(chunks):
        send_telegram_msg(f"📄 Part {i+1}/{len(chunks)}\n\n{chunk}")
        time.sleep(1.5)

def get_hard_words(text):
    words = re.findall(r'\b[a-zA-Z]{8,}\b', text.lower())
    stop = {"understanding","different","something","everything","because","through","between","however","therefore","although","continue","reading"}
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
    return " ".join(sentences[:3]) + "\n\n... \n\n" + sentences[-1]

def morning_task():
    topic_url = random.choice(TOPICS)
    feed = feedparser.parse(topic_url)
    if not feed.entries:
        send_telegram_msg("Couldn't find articles today.")
        return
    # كنجربو حتى 5 مقالات حتى نلقاو واحد خدام
    random.shuffle(feed.entries)
    for article in feed.entries[:5]:
        rss_content = ""
        if hasattr(article, 'content'):
            rss_content = article.content[0].value
        elif hasattr(article, 'summary'):
            rss_content = article.summary

        full_text = get_full_article_text(article.link, rss_content)
        if full_text and len(full_text) > 800:
            send_telegram_msg(f"📖 Daily Reading\n\n{article.title}\n\nLink: {article.link}")
            send_long_message(full_text)
            send_telegram_msg(get_hard_words(full_text))
            send_telegram_msg(f"✨ Summary:\n\n{get_summary(full_text)}")
            return
        else:
            print(f"Skipped {article.title}, trying next...")

    send_telegram_msg("⚠️ All articles failed today, try tomorrow.")

def evening_task():
    send_telegram_msg("🌙 Good Evening!\n\nI hope you had a wonderful and productive day. Wishing you a peaceful night and a great day tomorrow!")

if len(sys.argv) > 1 and sys.argv[1] == "morning":
    morning_task()
elif len(sys.argv) > 1 and sys.argv[1] == "evening":
    evening_task()
else:
    morning_task()
