"""Czech News Digest Bot.

Крок 1 — ping-бот: при старті шле одне повідомлення в Telegram, щоб перевірити,
що пайплайн repo -> Railway -> Python -> env -> Telegram працює.
Після відправки процес лишається живим (idle-sleep), щоб Railway не крутив crash-loop.
"""

import os
import sys
import time

import httpx

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram(text: str) -> None:
    """Надсилає повідомлення в Telegram через Bot API (простий httpx POST)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = httpx.post(
        url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )
    resp.raise_for_status()


def main() -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN і TELEGRAM_CHAT_ID мають бути виставлені.", flush=True)
        sys.exit(1)

    print("Надсилаю ping у Telegram...", flush=True)
    send_telegram("✅ Czech News Bot живий")
    print("Ping надіслано. Процес лишається активним.", flush=True)

    # Тримаємо процес живим, щоб Railway бачив воркер як 'running' і не перезапускав.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
