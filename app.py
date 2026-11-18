import requests
import feedparser
import random
import re
import os
import time
import sys
import json
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# زدت ليك هنا الشطرنج و AI
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
    "https://medium.com/feed/tag/technology"
]

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=20)
        print(r.text[:300])
    except Exception as e:
        print(f"Error: {e}")

def send_long_message(text):
    clean = text.replace("*", "").replace("_", "").replace("`", "")
    chunks = [clean[i:i+3500] for i in range(0, len(clean), 3500)]
    for i, chunk in enumerate(chunks):
        send_telegram_msg(f"📄 Part {i+1}/{len(chunks)}\n\n{chunk}")
        time.sleep(1.5)

def clean_text(text):
    # حيد الروابط والزبل
    lines = []
    for l in text.split("\n"):
        l = l.strip()
        if len(l) < 25: continue
        if l.startswith("http"): continue
        if "Continue reading" in l: continue
        if "Published in" in l: continue
        if "Follow" in l and len(l) < 60: continue
        lines.append(l)
    return "\n\n".join(lines)

def try_freedium(url):
    try:
        # Freedium هو اللي كيفتح Medium
        f_url = f"https://freedium.cfd/{url}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(f_url, headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Freedium كيحط النص فـ p
        paras = soup.find_all('p')
        text = "\n\n".join([p.get_text() for p in paras if len(p.get_text()) > 40])
        text = clean_text(text)
        print(f"Freedium: {len(text)} chars")
        return text if len(text) > 800 else None
    except Exception as e:
        print(f"Freedium failed: {e}")
        return None

def try_jina(url):
    try:
        r = requests.get(f"https://r.jina.ai/{url}", headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        text = clean_text(r.text)
        print(f"Jina: {len(text)} chars")
        return text if len(text) > 800 else None
    except Exception as e:
        print(f"Jina failed: {e}")
        return None

def try_direct(url):
    try:
        # ?format=json كتعطي Medium النص خام
        r = requests.get(url + "?format=json", headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        txt = r.text.replace("])}while(1);</x>", "").strip()
        data = json.loads(txt)
        paras = data["payload"]["value"]["content"]["bodyModel"]["paragraphs"]
        text = "\n\n".join([p.get("text","") for p in paras if len(p.get("text","")) > 20])
        text = clean_text(text)
        print(f"Direct: {len(text)} chars")
        return text if len(text) > 800 else None
    except Exception as e:
        print(f"Direct failed: {e}")
        return None

def get_full_article_text(url):
    for func in [try_freedium, try_jina, try_direct]:
        t = func(url)
        if t:
            return t[:18000]
    return None

def get_hard_words(text):
    words = re.findall(r'\b[a-zA-Z]{8,}\b', text.lower())
    stop = {"understanding","different","something","everything","because","through","between","however","therefore","although","continue","reading","philosophy"}
    words = [w for w in words if w not in stop]
    unique = list(set(words))
    random.shuffle(unique)
    hard = unique[:5]
    if not hard:
        return "No hard words found today."
    result = "📚 Hard Words Explained:\n"
    for w in hard:
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
    # كنجربو 5 ديال المواضيع حتى نلقاو مقال خدام
    topics_shuffled = TOPICS[:]
    random.shuffle(topics_shuffled)
    
    for topic_url in topics_shuffled[:5]:
        feed = feedparser.parse(topic_url)
        if not feed.entries: continue
        entries = feed.entries[:]
        random.shuffle(entries)
        for article in entries[:4]:
            print(f"Trying: {article.title} - {article.link}")
            full_text = get_full_article_text(article.link)
            if full_text:
                send_telegram_msg(f"📖 Daily Reading\n\n{article.title}\n\nLink: {article.link}\n\nFetching full article...")
                send_long_message(full_text)
                send_telegram_msg(get_hard_words(full_text))
                send_telegram_msg(f"✨ Summary:\n\n{get_summary(full_text)}")
                return
    send_telegram_msg("⚠️ Could not fetch any full article today, try again tomorrow. Check Medium links manually.")

def evening_task():
    send_telegram_msg("🌙 Good Evening!\n\nI hope you had a wonderful and productive day. Wishing you a peaceful night and a great day tomorrow!")

if len(sys.argv) > 1 and sys.argv[1] == "morning":
    morning_task()
elif len(sys.argv) > 1 and sys.argv[1] == "evening":
    evening_task()
else:
    morning_task()
