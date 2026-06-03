"""Czech News Digest Bot.

Крок 2 — RSS: при старті бот тягне заголовки з RSS-джерел і шле сирий
список у Telegram. Поки одне джерело (Novinky.cz), щоб перевірити, що мережа
і feedparser працюють на Railway. Далі розширимо список і додамо дайджест.
Після відправки процес лишається живим (idle-sleep), щоб Railway не крутив crash-loop.
"""

import os
import sys
import time

import feedparser
import httpx

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

RSS_FEEDS = [
    {"name": "ČT24", "url": "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"},
    {"name": "iDnes", "url": "https://servis.idnes.cz/rss.aspx?c=zpravodajstvi"},
    {"name": "Novinky.cz", "url": "https://www.novinky.cz/rss"},
    {"name": "Seznam Zprávy", "url": "https://www.seznamzpravy.cz/rss"},
    {"name": "E15", "url": "https://www.e15.cz/rss"},
    {"name": "Hospodářské noviny", "url": "https://servis.idnes.cz/rss.aspx?c=hn"},
]

# Скільки заголовків брати з кожного джерела (на кроці 2 менше, бо ще без розбиття на 4096).
ITEMS_PER_FEED = 5


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


# Деякі чеські сайти (servis.idnes.cz) блокують дефолтний User-Agent feedparser
# і віддають порожньо, тому качаємо фід через httpx з браузерним UA, а потім парсимо байти.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


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


def format_raw(news: list[dict]) -> str:
    """Форматує сирий список заголовків для крока 2 (без Claude)."""
    if not news:
        return "⚠️ Жодного заголовка не вдалося отримати."
    lines = ["📰 RSS-перевірка — сирі заголовки:\n"]
    for item in news:
        lines.append(f"• [{item['source']}] {item['title']}")
    return "\n".join(lines)


def main() -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN і TELEGRAM_CHAT_ID мають бути виставлені.", flush=True)
        sys.exit(1)

    print("Тягну новини з RSS...", flush=True)
    news = fetch_news()
    print(f"Усього заголовків: {len(news)}. Надсилаю в Telegram...", flush=True)
    send_telegram(format_raw(news))
    print("Надіслано. Процес лишається активним.", flush=True)

    # Тримаємо процес живим, щоб Railway бачив воркер як 'running' і не перезапускав.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
