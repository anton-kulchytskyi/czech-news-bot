"""Czech News Digest Bot.

Збирає заголовки з чеських RSS-джерел, генерує стислий україномовний дайджест
через Anthropic API і шле його в Telegram (з розбиттям під ліміт 4096).
Розклад: двічі на день о 07:30 і 20:00 за київським часом (APScheduler).
SEND_ON_START=true шле дайджест одразу при запуску (для тесту).
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import httpx
from apscheduler.schedulers.blocking import BlockingScheduler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
SEND_ON_START = os.environ.get("SEND_ON_START", "").lower() == "true"

CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500
TIMEZONE = ZoneInfo("Europe/Kyiv")
TELEGRAM_LIMIT = 4096

# iDnes і Hospodářské noviny (servis.idnes.cz) поки віддають порожньо навіть з браузерним
# User-Agent — тимчасово прибрані. За потреби повернемо й розберемось окремо.
RSS_FEEDS = [
    {"name": "ČT24", "url": "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"},
    {"name": "Novinky.cz", "url": "https://www.novinky.cz/rss"},
    {"name": "Seznam Zprávy", "url": "https://www.seznamzpravy.cz/rss"},
    {"name": "E15", "url": "https://www.e15.cz/rss"},
]

# Скільки заголовків брати з кожного джерела (Claude сам обере 7–10 найважливіших).
ITEMS_PER_FEED = 8

# Деякі чеські сайти блокують дефолтний User-Agent feedparser, тому качаємо фід
# через httpx з браузерним UA, а потім парсимо байти.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def send_telegram(text: str) -> None:
    """Надсилає повідомлення в Telegram через Bot API (простий httpx POST)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = httpx.post(
        url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )
    if resp.status_code != 200:
        # Показуємо точну причину від Telegram (напр. "Bad Request: chat not found").
        print(f"Telegram API {resp.status_code}: {resp.text}", flush=True)
    resp.raise_for_status()


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Розбиває довге повідомлення на частини під ліміт Telegram, по рядках."""
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        # Окремий рядок довший за ліміт — ріжемо його жорстко.
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts


def fetch_news() -> list[dict]:
    """Тягне заголовки з усіх RSS-джерел. Битий/недоступний фід пропускаємо."""
    news = []
    for feed in RSS_FEEDS:
        try:
            resp = httpx.get(
                feed["url"],
                headers={"User-Agent": USER_AGENT},
                timeout=30,
                follow_redirects=True,
            )
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            entries = parsed.entries[:ITEMS_PER_FEED]
            print(f"{feed['name']}: {len(entries)} заголовків", flush=True)
            for entry in entries:
                title = entry.get("title", "").strip()
                if title:
                    news.append({"source": feed["name"], "title": title})
        except Exception as exc:  # noqa: BLE001 — фід може тимчасово не відповідати
            print(f"Пропускаю {feed['name']}: {exc}", flush=True)
    return news


def generate_digest(news: list[dict]) -> str:
    """Генерує україномовний дайджест із чеських заголовків через Anthropic API."""
    now = datetime.now(TIMEZONE)
    date_str = now.strftime("%d.%m.%Y, %H:%M")
    headlines = "\n".join(f"- [{item['source']}] {item['title']}" for item in news)

    prompt = (
        "Ти — досвідчений редактор новин. Нижче наведено заголовки з чеських "
        "новинних сайтів (чеською мовою). Зроби стислий дайджест ЖИВОЮ "
        "УКРАЇНСЬКОЮ мовою за такою структурою:\n\n"
        f"🇨🇿 Дайджест чеських новин\n🗓 {date_str} (Київ)\n\n"
        "🗞 Головне\n🏛 Політика\n💰 Економіка\n\n"
        "Правила:\n"
        "- усього 7–10 новин, розподілених за темами де це доречно;\n"
        "- кожна новина — 1–2 речення українською, передавай суть, а не дослівний переклад;\n"
        "- якщо для якоїсь теми немає новин — пропусти цю секцію;\n"
        "- НЕ використовуй markdown-розмітку (жодних зірочок, решіток, підкреслень) — "
        "лише звичайний текст з емодзі-заголовками;\n"
        "- без вступів, пояснень і коментарів — лише сам дайджест.\n\n"
        f"Заголовки:\n{headlines}"
    )

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"Anthropic API {resp.status_code}: {resp.text}", flush=True)
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"].strip()


def send_digest() -> None:
    """Повний цикл: RSS -> дайджест через Claude -> відправка в Telegram частинами."""
    print("Тягну новини з RSS...", flush=True)
    news = fetch_news()
    if not news:
        send_telegram("⚠️ Жодного заголовка не вдалося отримати.")
        print("Новин немає, дайджест не генерую.", flush=True)
        return
    print(f"Усього заголовків: {len(news)}. Генерую дайджест через Claude...", flush=True)
    digest = generate_digest(news)
    print("Дайджест готовий. Надсилаю в Telegram...", flush=True)
    for part in split_message(digest):
        send_telegram(part)
    print("Надіслано.", flush=True)


def main() -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not ANTHROPIC_API_KEY:
        print(
            "ERROR: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID і ANTHROPIC_API_KEY мають бути виставлені.",
            flush=True,
        )
        sys.exit(1)

    if SEND_ON_START:
        print("SEND_ON_START=true — надсилаю дайджест одразу.", flush=True)
        send_digest()

    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_digest, "cron", hour=7, minute=30, id="morning")
    scheduler.add_job(send_digest, "cron", hour=20, minute=0, id="evening")
    print("Планувальник запущено: дайджест о 07:30 і 20:00 (Київ).", flush=True)
    scheduler.start()


if __name__ == "__main__":
    main()
