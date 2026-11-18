import requests
import feedparser
import random
import re
import os
import time
import sys
import json

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
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=20)
        print(r.text[:500])
    except Exception as e:
        print(f"Error: {e}")

def send_long_message(text):
    clean = text.replace("*", "").replace("_", "").replace("`", "")
    if len(clean) < 50:
        send_telegram_msg("⚠️ Could not fetch full text, open the link above.")
        return
    chunks = [clean[i:i+3500] for i in range(0, len(clean), 3500)]
    for i, chunk in enumerate(chunks):
        send_telegram_msg(f"📄 Part {i+1}/{len(chunks)}\n\n{chunk}")
        time.sleep(1.5)

def get_from_medium_api(url):
    # كنجبدو ID ديال المقال من اللينك: مثلا ...-bc1bdbd72a9b
    try:
        m = re.search(r'-([a-f0-9]{10,})', url)
        if not m:
            return None
        article_id = m.group(1)
        print(f"Article ID: {article_id}")
        api_url = f"https://medium.com/_/api/articles/{article_id}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        r = requests.get(api_url, headers=headers, timeout=20)
        text = r.text
        # Medium كيزيد هاد السطر فاللول: ]) }while(1);
        text = text.replace("])}while(1);</x>", "").strip()
        data = json.loads(text)
        paragraphs = data["payload"]["value"]["content"]["bodyModel"]["paragraphs"]
        full = []
        for p in paragraphs:
            t = p.get("text", "").strip()
            if len(t) > 20:
                full.append(t)
        result = "\n\n".join(full)
        print(f"Medium API got {len(result)} chars")
        return result if len(result) > 500 else None
    except Exception as e:
        print(f"Medium API failed: {e}")
        return None

def get_from_jina(url):
    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"User-Agent": "Mozilla/5.0", "X-Return-Format": "text"}
        r = requests.get(jina_url, headers=headers, timeout=30)
        text = r.text
        # إلا كان فيه "Continue reading" غير بوحدو، راه فشل
        if len(text) < 1000 or "Continue reading on Medium" in text[:2000] and len(text) < 2000:
            return None
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 30]
        # حيد السطور ديال المينيو والروابط
        lines = [l for l in lines if not l.startswith("http") and "Published in" not in l]
        return "\n\n".join(lines)[:18000]
    except Exception as e:
        print(f"Jina failed: {e}")
        return None

def get_full_article_text(url):
    # 1. جرب Medium API هو اللول - هو الأفضل
    t = get_from_medium_api(url)
    if t:
        return t[:18000]
    # 2. جرب Jina
    t = get_from_jina(url)
    if t:
        return t
    return "Could not fetch full article. Please open the link above."

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
    summary = " ".join(sentences[:3]) + "\n\n... \n\n" + sentences[-1]
    return summary

def morning_task():
    topic_url = random.choice(TOPICS)
    feed = feedparser.parse(topic_url)
    if not feed.entries:
        send_telegram_msg("Couldn't find articles today.")
        return
    article = random.choice(feed.entries)
    send_telegram_msg(f"📖 Daily Reading\n\n{article.title}\n\nLink: {article.link}\n\nFetching full article...")
    
    full_text = get_full_article_text(article.link)
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
