# Czech News Digest Bot

## Що це
Telegram-бот, який двічі на день збирає новини з чеських сайтів і надсилає дайджест **українською мовою** через Claude AI.

## Стек
- Python 3.12
- `feedparser` — парсинг RSS
- `httpx` — запити до Anthropic API
- `python-telegram-bot` — відправка в Telegram
- `APScheduler` — розклад (08:00 і 18:00, таймзона Europe/Prague)

## Джерела новин (RSS)
| Сайт | URL |
|---|---|
| ČT24 | https://ct24.ceskatelevize.cz/rss/hlavni-zpravy |
| iDnes | https://servis.idnes.cz/rss.aspx?c=zpravodajstvi |
| Novinky.cz | https://www.novinky.cz/rss |
| Seznam Zprávy | https://www.seznamzpravy.cz/rss |
| E15 (економіка) | https://www.e15.cz/rss |
| Hospodářské noviny | https://servis.idnes.cz/rss.aspx?c=hn |

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

# Або через Docker
docker compose up -d
docker compose logs -f
```

## Типові задачі

### Додати нове RSS-джерело
У `bot.py` знайди список `RSS_FEEDS` і додай словник:
```python
{"name": "Назва сайту", "url": "https://..."},
```

### Змінити час відправки
У `bot.py` в функції `main()` знайди рядок з `scheduler.add_job` — там параметр `hour`.
Час вказується за Europe/Prague (не UTC).

### Змінити стиль або теми дайджесту
У `bot.py` знайди функцію `generate_digest()` — там є промпт для Claude. Редагуй текст промпту.

### Надсилати в канал або групу
Додай бота як адміністратора. `TELEGRAM_CHAT_ID` для каналу має вигляд `-100xxxxxxxxxx`.

### Протестувати без чекання розкладу
```bash
SEND_ON_START=true python bot.py
# Ctrl+C одразу після отримання дайджесту
```

## Відомі нюанси
- Деякі чеські RSS можуть тимчасово не відповідати — це нормально, бот пропускає і йде далі
- Telegram має ліміт 4096 символів на повідомлення — `split_message()` розбиває автоматично
- Claude модель: `claude-sonnet-4-20250514`, `max_tokens: 1500`
