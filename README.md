# Discord Server Cloner v7.0 AUTHOR ANGELS — Python Edition

Мощный инструмент полного клонирования Discord-серверов.  
**SmartBrain v7** — умный движок с bucket-aware rate-limit, автоматическим retry и диагностикой.

---

## ✅ Что клонируется

| Объект | Поддержка | Детали |
|---|---|---|
| 📁 Категории | ✅ | Иерархия, позиции, права |
| 💬 Текстовые каналы | ✅ | Топик, slow-mode, авто-архивирование |
| 🔊 Голосовые каналы | ✅ | Битрейт, лимит, регион, видео-качество |
| 📢 Каналы объявлений | ✅ | Конвертируются в текстовые |
| 🗂️ Форумы | ✅ | Топик, slow-mode, layout, сортировка |
| 🎭 Stage каналы | ✅ | Топик |
| 🎭 Роли | ✅ | Цвет, права, hoist, mentionable |
| 🖼 Иконки ролей | ✅ FREE | CDN → оригинальный emoji → FREE emoji пул (48 иконок) |
| 🔒 Права на каналы | ✅ | allow/deny для каждой роли/пользователя |
| 😀 Эмодзи | ✅ | Статические и анимированные, lossless |
| 🎯 Стикеры | ✅ | PNG, APNG, GIF — с именем, описанием, тегами |
| 🖼️ Иконка сервера | ✅ | PNG и GIF, до 1024px |
| 🖼️ Баннер сервера | ✅ | PNG и GIF, до 2048px |
| 🖼️ Splash (фон инвайта) | ✅ | PNG |
| ⚙️ Настройки сервера | ✅ | Локаль, верификация, уведомления, фильтр |
| 📌 Системные каналы | ✅ | AFK, rules, updates, safety, system |
| 🪝 Вебхуки | ✅ | С аватарами, привязка к каналам |
| 🔒 Пересинхронизация прав | ✅ | Повторный проход — гарантирует полное соответствие |
| 👥 Роли участникам | ✅ | Выдача дефолтной роли всем участникам |
| 💬 Сообщения | ❌ | Discord API не поддерживает |
| 👥 Перенос участников | ❌ | Должны зайти сами по инвайту |

---

## 🧠 SmartBrain v7 — что умеет

- **Bucket-aware rate-limit** — правильный routing по major parameters (guild/channel/webhook)
- **Anti-loop защита** — при повторных 429 подряд не зависает, возвращает ответ и идёт дальше
- **Global RL** — глобальный rate-limit обрабатывается отдельно от bucket
- **Pre-emptive throttle** — видит `X-RateLimit-Remaining=0` и ждёт заранее
- **Exponential backoff** — для 5xx и сетевых ошибок
- **Connection pool** — один Session с 12 соединениями, не создаёт новые на каждый запрос
- **Stream download** — медиа скачивает чанками, 5 попыток
- **MIME по magic bytes** — определяет формат изображения по содержимому, не по URL

---

## 🖼️ Иконки ролей без буста (FREE)

Если целевой сервер без буста уровня 2+ — иконки ролей назначаются так:

1. **CDN иконка** — скачивается и загружается напрямую (если сервер-источник с бустом)
2. **Оригинальный Unicode emoji** — если у роли был emoji вместо картинки
3. **FREE emoji пул** — 48 встроенных unicode-иконок (⭐ 🔥 💎 👑 🎮 и т.д.)
4. **Без иконки** — если пул кончился

Роли с «невидимыми» именами (Hangul Filler, Zero-Width Space) — **сохраняются как есть**.

---

## 🚀 Быстрый старт

### Windows
```bat
run.bat
```

### Linux / macOS
```bash
chmod +x run.sh
./run.sh
```

### Вручную
```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Открой браузер: **http://localhost:5000**

---

## 📋 Как пользоваться

1. **Запусти** `run.bat` (Windows) или `run.sh` (Linux/macOS)
2. **Открой** `http://localhost:5000`
3. **Получи токен**: `discord.com/app` → F12 → Network → заголовок `Authorization`
4. **Скопируй ID серверов**: правый клик на сервере → «Копировать ID» (нужен Режим разработчика)
5. **Заполни форму** — токен, ID источника, ID цели
6. **Выбери** что клонировать (все галки включены по умолчанию)
7. **Нажми «Клонировать»** — следи за прогрессом в реальном времени

---

## 🗂️ Структура проекта

```
discord-cloner-python/
├── app.py          # Flask + SocketIO — только роуты и WebSocket
├── brain.py        # SmartBrain v7 — HTTP-клиент для Discord API
├── cloner.py       # Вся логика клонирования (9 шагов)
├── config.py       # Все константы и настройки
├── utils.py        # Утилиты (safe_name, b64, overwrites, валидация)
├── requirements.txt
├── run.bat         # Запуск Windows
├── run.sh          # Запуск Linux/macOS
├── templates/
│   ├── base.html         # Layout (nav, footer)
│   ├── index.html        # Главная — форма клонирования
│   ├── guides.html       # Руководства
│   ├── how_to_clone.html # Пошаговая инструкция
│   ├── faq.html          # FAQ
│   └── security.html     # Безопасность
└── static/
    ├── css/main.css    # Dark Discord тема + шаговый трекер
    └── js/
        ├── bg.js       # Анимированный canvas фон
        └── nav.js      # Мобильная навигация
```

---

## 🔌 API Endpoints

| Метод | URL | Описание |
|---|---|---|
| GET | `/` | Главная страница |
| GET | `/guides` | Руководства |
| GET | `/how-to-clone` | Пошаговая инструкция |
| GET | `/faq` | FAQ |
| GET | `/security` | Безопасность |
| GET | `/health` | Health check — `{"status":"ok","version":"7.0"}` |
| POST | `/api/validate-token` | Проверка Discord токена |
| POST | `/api/guild-info` | Информация о сервере |

---

## 📡 WebSocket Events

| Событие | Кто шлёт | Данные | Описание |
|---|---|---|---|
| `start_clone` | Клиент | `{token, source_id, target_id, options}` | Запуск |
| `validate_token` | Клиент | `{token}` | Валидация токена |
| `get_guilds` | Клиент | `{token}` | Список серверов |
| `get_guild_info` | Клиент | `{token, guild_id}` | Инфо о сервере |
| `log` | Сервер | `{message, level}` | Строка лога |
| `progress` | Сервер | `{step, key, current, total}` | Прогресс (key = машинный ID шага) |
| `clone_done` | Сервер | `{success, source?, target?, error?}` | Завершение |
| `token_valid` | Сервер | `{valid, username?, error?}` | Результат валидации |
| `guilds_list` | Сервер | `{guilds: [...]}` | Список серверов |
| `guild_info` | Сервер | `{id, name, icon, banner, member_count, boost_level}` | Данные сервера |

---

## 🔢 9 шагов клонирования

| # | Ключ | Название | Что делает |
|---|---|---|---|
| 1 | `purge` | Очистка | Удаляет каналы, роли, эмодзи, стикеры с цели |
| 2 | `roles` | Роли | Клонирует роли с иконками (4 стратегии fallback) |
| 3 | `channels` | Каналы | Категории → каналы с правами |
| 4 | `emojis` | Эмодзи | Статические + анимированные |
| 5 | `stickers` | Стикеры | PNG/APNG/GIF |
| 6 | `settings` | Настройки | Иконка, баннер, splash, системные каналы |
| 7 | `webhooks` | Вебхуки | С аватарами, привязка к каналам |
| 8 | `resync` | Пересинхронизация | Повторное обновление прав каналов |
| 9 | `assign_role` | Роли участникам | Дефолтная роль всем участникам |

---

## 🛡 Безопасность

- Токен **не отправляется** никуда кроме `discord.com/api`
- Работает **только локально** на твоём компьютере
- После использования **смени пароль Discord** для инвалидации токена
- Используй **только на своих серверах** с правами администратора

---

## 🔧 Зависимости

| Пакет | Версия |
|---|---|
| flask | 3.0.3 |
| flask-socketio | 5.3.6 |
| requests | 2.32.3 |

Python 3.10+

---

© 2026 Discord Server Cloner v7.0 AUTHOR ANGELS
