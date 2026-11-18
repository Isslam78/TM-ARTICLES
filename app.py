import requests
import feedparser
import random
import re
import os
import time
import sys

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ===== 1. كل موضوع من الموقع ديالو =====
# كل وحدة فيها 2 مواقع: إلا الأول ماخدمش، كيدوز للثاني

SOURCES = {
    "AI": [
        {"type": "dev", "tag": "ai"},
        {"type": "rss", "url": "https://hackernoon.com/tagged/artificial-intelligence/feed"},
        {"type": "rss", "url": "https://www.technologyreview.com/feed/"},
    ],
    "Chess": [
        {"type": "rss", "url": "https://www.chess.com/blog/rss"},
        {"type": "rss", "url": "https://lichess.org/blog.atom"},
        {"type": "rss", "url": "https://en.chessbase.com/rss.xml"},
    ],
    "Math": [
        {"type": "rss", "url": "https://www.quantamagazine.org/mathematics/feed/"},
        {"type": "dev", "tag": "mathematics"},
        {"type": "rss", "url": "https://www.quantamagazine.org/feed/"},
    ],
    "Physics": [
        {"type": "rss", "url": "https://www.quantamagazine.org/physics/feed/"},
        {"type": "rss", "url": "https://phys.org/rss-feed/"},
        {"type": "dev", "tag": "physics"},
    ],
    "Philosophy": [
        {"type": "rss", "url": "https://aeon.co/feed.rss"},
        {"type": "rss", "url": "https://www.lesswrong.com/feed.xml"},
        {"type": "dev", "tag": "philosophy"},
    ],
    "Health": [
        {"type": "rss", "url": "https://theconversation.com/us/health/articles.atom"},
        {"type": "rss", "url": "https://www.medicalnewstoday.com/rss"},
    ],
    "Atheism": [
        {"type": "rss", "url": "https://aeon.co/feed.rss"},
        {"type": "rss", "url": "https://www.lesswrong.com/feed.xml"},
    ],
    "Nihilism": [
        {"type": "rss", "url": "https://aeon.co/feed.rss"},
        {"type": "rss", "url": "https://www.lesswrong.com/feed.xml"},
    ],
    "Absurdity": [
        {"type": "rss", "url": "https://aeon.co/feed.rss"},
        {"type": "rss", "url": "https://www.lesswrong.com/feed.xml"},
    ],
}

# ===== 2. التنظيف 0% تخربيق =====
def clean_text(text):
    if not text:
        return ""
    # حيد HTML
    text = re.sub(r'<[^>]+>', ' ', text)
    # حيد KaTeX كامل - هادا هو اللي كان مشوه ليك
    text = re.sub(r'\{%.*?katex.*?\}', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\{%.*?%\}', ' ', text)
    # حيد رموز الرياضيات
    text = text.replace(r'\land', ' and ').replace(r'\to', ' -> ').replace(r'\neg', ' not ')
    text = re.sub(r'\\bar\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', ' ', text)
    text = re.sub(r'[{}]', ' ', text)
    # حيد الجداول ديال Markdown | --- | --- |
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('|') and line.endswith('|'): continue
        if set(line) <= set('|:- '): continue
        if 'Press enter or click to view image' in line: continue
        if line.startswith('![Image'): continue
        if 'miro.medium.com' in line: continue
        if 'wikimedia.org' in line and len(line) < 200: continue
        # حيد الروابط وبقا النص: [NASA](link) -> NASA
        line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        line = re.sub(r'!\[.*?\]\(.*?\)', '', line)
        # حيد ### و ## و **
        line = line.replace('###', '').replace('##', '').replace('**', '').replace('__', '')
        # حيد الروابط الطوال
        line = re.sub(r'https?://\S+', '', line)
        if len(line) < 3: continue
        lines.append(line)
    text = '\n\n'.join(lines)
    # حيد الفراغات الزايدة
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # بلا parse_mode باش مايتخربقش
    payload = {"chat_id": CHAT_ID, "text": text[:4000]}
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"Error: {e}")

def send_long_message(text):
    clean = clean_text(text)
    if len(clean) < 500:
        return False
    chunks = [clean[i:i+3500] for i in range(0, len(clean), 3500)]
    for i, chunk in enumerate(chunks):
        send_telegram_msg(f"📄 Part {i+1}/{len(chunks)}\n\n{chunk}")
        time.sleep(1.2)
    return True

def get_from_dev(tag):
    try:
        url = f"https://dev.to/api/articles?tag={tag}&top=7&per_page=10"
        r = requests.get(url, timeout=15).json()
        if not r: return None
        art = random.choice(r)
        # DEV API كيعطي النص كامل ونقي
        full = art.get('body_markdown', '') or art.get('description', '')
        return {"title": art['title'], "link": art['url'], "text": full}
    except Exception as e:
        print(f"DEV {tag} failed: {e}")
        return None

def get_from_rss(feed_url):
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries: return None
        # جرب 5 مقالات حتى تلقى واحد نقي وطويل
        random.shuffle(feed.entries)
        for entry in feed.entries[:5]:
            content = ""
            if hasattr(entry, 'content'):
                content = entry.content[0].value
            elif hasattr(entry, 'summary'):
                content = entry.summary
            content = clean_text(content)
            if len(content) > 800:
                return {"title": entry.title, "link": entry.link, "text": content}
        return None
    except Exception as e:
        print(f"RSS {feed_url} failed: {e}")
        return None

def get_hard_words(text):
    words = re.findall(r'\b[a-zA-Z]{8,}\b', text.lower())
    stop = {"understanding","different","something","everything","because","through","between","however","therefore","although"}
    words = [w for w in words if w not in stop]
    unique = list(set(words))
    random.shuffle(unique)
    result = "📚 Hard Words Explained:\n"
    for w in unique[:5]:
        try:
            d = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{w}", timeout=10).json()
            definition = d[0]['meanings'][0]['definitions'][0]['definition']
            result += f"\n- {w}: {definition}\n"
        except: continue
    return result

def get_summary(text):
    sentences = re.split(r'(?<=[.!?]) +', clean_text(text))
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
    if len(sentences) < 5: return text[:1000]
    return " ".join(sentences[:3]) + "\n\n... \n\n" + sentences[-1]

def morning_task():
    # نختار موضوع عشوائي
    topic = random.choice(list(SOURCES.keys()))
    print(f"Trying topic: {topic}")
    
    article = None
    # كنجربو المواقع ديال هاد الموضوع واحد بواحد
    for src in SOURCES[topic]:
        if src["type"] == "dev":
            article = get_from_dev(src["tag"])
        else:
            article = get_from_rss(src["url"])
        if article and len(clean_text(article["text"])) > 800:
            break
        article = None
    
    if not article:
        send_telegram_msg(f"⚠️ No clean article found for {topic} today, trying another topic...")
        return

    send_telegram_msg(f"📖 Daily Reading - {topic}\n\n{article['title']}\n\nLink: {article['link']}\n\nFetching clean article...")
    
    ok = send_long_message(article["text"])
    if not ok:
        send_telegram_msg("Article was too short, open the link above.")
        return

    send_telegram_msg(get_hard_words(article["text"]))
    send_telegram_msg(f"✨ Summary:\n\n{get_summary(article['text'])}")

def evening_task():
    send_telegram_msg("🌙 Good Evening!\n\nI hope you had a wonderful and productive day. Wishing you a peaceful night and a great day tomorrow!")

if len(sys.argv) > 1 and sys.argv[1] == "morning":
    morning_task()
elif len(sys.argv) > 1 and sys.argv[1] == "evening":
    evening_task()
else:
    morning_task()
