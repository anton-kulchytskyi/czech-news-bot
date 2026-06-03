# Czech News Digest Bot

## Що це
Telegram-бот, який двічі на день збирає новини з чеських сайтів і надсилає дайджест **українською мовою** через Claude AI.

## Стек
- Python 3.12
- `feedparser` — парсинг RSS
- `httpx` — запити до Anthropic API і до Telegram Bot API (відправка простим POST, без python-telegram-bot)
- `APScheduler` — розклад (07:30 і 20:00, таймзона Europe/Kyiv)
- Деплой: Railway (фоновий worker, без HTTP-порту)

## Джерела новин (RSS)
Фіди качаються через httpx з браузерним User-Agent (деякі сайти блокують дефолтний UA feedparser).

| Сайт | URL |
|---|---|
| ČT24 | https://ct24.ceskatelevize.cz/rss/hlavni-zpravy |
| Novinky.cz | https://www.novinky.cz/rss |
| Seznam Zprávy | https://www.seznamzpravy.cz/rss |
| E15 (економіка) | https://www.e15.cz/rss |

> iDnes (`...?c=zpravodajstvi`) і Hospodářské noviny (`...?c=hn`) з servis.idnes.cz тимчасово
> вимкнені — віддають порожньо навіть з браузерним User-Agent. Повернути після окремого розбору.

## Теми дайджесту
Загальні новини, Політика, Економіка

## Структура дайджесту (що генерує Claude)
- Заголовок з датою і часом
- 🗞 Головне
- 🏛 Політика
- 💰 Економіка
- 7–10 новин, кожна — 1–2 речення, живою українською

## Змінні середовища (обов'язкові)
```
TELEGRAM_TOKEN      # токен від @BotFather
TELEGRAM_CHAT_ID    # числовий id чату / каналу / групи
ANTHROPIC_API_KEY   # ключ з console.anthropic.com
SEND_ON_START       # true = надіслати дайджест одразу при запуску (для тесту)
```

## Запуск
```bash
# Встановити залежності
pip install -r requirements.txt

# Запустити бота
python bot.py
```

Деплой на Railway: репо підключене до сервісу, `Procfile` (`worker: python bot.py`) тримає
фоновий процес. Змінні середовища — у Railway → Variables. Пуш у `main` тригерить авто-деплой.

## Типові задачі

### Додати нове RSS-джерело
У `bot.py` знайди список `RSS_FEEDS` і додай словник:
```python
{"name": "Назва сайту", "url": "https://..."},
```

### Змінити час відправки
У `bot.py` в функції `main()` знайди рядки з `scheduler.add_job` — там параметри `hour`/`minute`.
Час вказується за Europe/Kyiv (не UTC). Зараз два джоби: 07:30 (`morning`) і 20:00 (`evening`).

### Змінити стиль або теми дайджесту
У `bot.py` знайди функцію `generate_digest()` — там є промпт для Claude. Редагуй текст промпту.

### Надсилати в канал або групу
Додай бота як адміністратора. `TELEGRAM_CHAT_ID` для каналу має вигляд `-100xxxxxxxxxx`.

### Протестувати без чекання розкладу
Вистав `SEND_ON_START=true` (локально або у Railway → Variables) — бот надішле дайджест
одразу при запуску, а потім стане на розклад. Прибери змінну, щоб шати лише за розкладом.

## Відомі нюанси
- Деякі чеські RSS можуть тимчасово не відповідати — це нормально, бот пропускає і йде далі
- Telegram має ліміт 4096 символів на повідомлення — `split_message()` розбиває автоматично
- Claude модель: `claude-sonnet-4-20250514`, `max_tokens: 1500`
