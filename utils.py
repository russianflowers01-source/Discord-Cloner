# -*- coding: utf-8 -*-
"""
utils.py — Вспомогательные функции для Discord Cloner v9.0 ULTRA
=================================================================
Полный набор утилит для стабильного клонирования, обхода API и анти-детекта.
Включает:
  • Smart Delay Manager (2-5 сек с джиттером)
  • Channel & Role Payload Builders (все типы каналов)
  • API Bypass (минификация, заголовки, обход WAF)
  • Rate Limit Tracker (парсинг заголовков Discord)
  • Строковые операции, транслитерация, парсинг эмодзи
  • Работа с медиа, MIME, конвертация цветов
  • Права Discord, валидация, Snowflake
  • JSON, расшифровка, сетевые утилиты
"""

import unicodedata
import base64
import logging
import re
import time
import json
import random
import string
import hashlib
import zlib
import math
from typing import Optional, Union, List, Dict, Any, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse, quote

logger = logging.getLogger("cloner.utils")

# ═══════════════════════════════════════════════════════════════
#  1. SMART DELAY MANAGER (Анти-Детект и Стабильность)
# ═══════════════════════════════════════════════════════════════

def human_delay(min_sec: float = 2.0, max_sec: float = 5.0, context: str = "", log_fn=None) -> float:
    """
    ULTRA: Умная задержка для имитации действий человека.
    Строго соблюдает диапазон 2-5 секунд (по умолчанию) с добавлением случайного джиттера.
    Предотвращает 429 ошибки и блокировки аккаунта.
    
    Args:
        min_sec: Минимальная задержка в секундах.
        max_sec: Максимальная задержка в секундах.
        context: Описание действия для логирования.
        log_fn: Функция логирования (опционально).
    
    Returns:
        float: Фактическое время ожидания.
    """
    # Базовая задержка в заданном диапазоне
    base_delay = random.uniform(min_sec, max_sec)
    
    # Добавляем микро-джиттер для максимальной реалистичности
    jitter = random.uniform(0.05, 0.35)
    total_delay = base_delay + jitter
    
    # Логируем только долгие паузы (> 3 сек), чтобы не спамить лог
    if total_delay > 3.0 and log_fn:
        log_fn(f"⏸ Пауза {total_delay:.1f}с {context}", "warn")
    elif total_delay > 3.0:
        logger.debug(f"Human delay: {total_delay:.2f}s {context}")
    
    time.sleep(total_delay)
    return total_delay


def fast_delay(min_sec: float = 0.3, max_sec: float = 0.8, context: str = "") -> float:
    """Быстрая задержка для операций, не требующих строгого лимита (например, чтение данных)."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay


def batch_pause(items_processed: int, batch_size: int, pause_sec: float = 12.0, log_fn=None) -> bool:
    """
    ULTRA: Делает паузу после обработки определенного количества элементов (batch).
    Возвращает True, если пауза была сделана.
    """
    if items_processed > 0 and items_processed % batch_size == 0:
        actual_pause = pause_sec + random.uniform(0.5, 2.0)
        if log_fn:
            log_fn(f"🔄 Batch пауза {actual_pause:.1f}с после {items_processed} элементов", "info")
        time.sleep(actual_pause)
        return True
    return False


# ═══════════════════════════════════════════════════════════════
#  2. СТРОКОВЫЕ ФУНКЦИИ И ЭМОДЗИ (ULTRA)
# ═══════════════════════════════════════════════════════════════

def safe_name(name: str, fallback: str = "channel", max_len: int = 100,
              allow_invisible: bool = False, allow_control: bool = False,
              force_lower: bool = False) -> str:
    """
    Очищает имя для Discord.
    force_lower=True идеально подходит для создания URL-безопасных имен каналов.
    """
    if not name or not name.strip():
        return fallback
    
    categories_to_remove = {"Cc"}
    if not allow_control:
        categories_to_remove.add("Cc")
    if not allow_invisible:
        categories_to_remove.add("Cf")
    
    clean = "".join(c for c in name if unicodedata.category(c) not in categories_to_remove)
    result = clean[:max_len].strip()
    
    if force_lower:
        result = result.lower()
        
    return result if result else fallback


def sanitize_channel_name(name: str, max_len: int = 100) -> str:
    """
    ULTRA: Специальная очистка имени канала по строгим правилам Discord.
    - Только строчные буквы, цифры, дефисы, подчеркивания.
    - Транслитерация кириллицы.
    - Удаление спецсимволов.
    """
    # Транслитерируем кириллицу
    name = transliterate_cyrillic(name)
    # Переводим в нижний регистр
    name = name.lower().strip()
    # Заменяем пробелы и недопустимые символы на дефисы
    name = re.sub(r'[^a-z0-9\-_]', '-', name)
    # Убираем множественные дефисы
    name = re.sub(r'-+', '-', name)
    # Убираем дефисы в начале и конце
    name = name.strip('-_')
    
    if not name:
        return "channel"
    return name[:max_len]


def sanitize_role_name(name: str, max_len: int = 100) -> str:
    """Очистка имени роли (более мягкие правила, чем для каналов)."""
    if not name or not name.strip():
        return "role"
    # Удаляем управляющие символы, но оставляем эмодзи и юникод
    clean = "".join(c for c in name if unicodedata.category(c) not in {"Cc", "Cf"})
    return clean[:max_len].strip() or "role"


def transliterate_cyrillic(text: str) -> str:
    """Транслитерирует кириллицу в латиницу."""
    cyrillic_to_latin = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
        'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh',
        'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
        'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts',
        'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    return "".join(cyrillic_to_latin.get(char, char) for char in text)


def strip_emoji(text: str) -> str:
    """Удаляет все стандартные эмодзи из строки."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F" "\U0001F300-\U0001F5FF" "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F" "\U0001F780-\U0001F7FF" "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF" "\U0001FA00-\U0001FA6F" "\U0001FA70-\U0001FAFF"
        "\U0001FAB0-\U0001FAB6" "\U0001FAC0-\U0001FAC5" "\U0001FAD0-\U0001FAD9"
        "\U00002600-\U000026FF" "\U00002700-\U000027BF" "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    return re.sub(r'[\uFE00-\uFE0F\u200D]', '', text).strip()


def extract_custom_emojis(text: str) -> List[Dict[str, str]]:
    """Извлекает кастомные эмодзи Discord: <:name:id> или <a:name:id>."""
    pattern = re.compile(r"<(a?):(\w+):(\d+)>")
    results = []
    for match in pattern.finditer(text):
        results.append({
            "animated": match.group(1) == "a",
            "name": match.group(2),
            "id": match.group(3)
        })
    return results


def extract_mentions(text: str) -> Dict[str, List[str]]:
    """ULTRA: Извлекает все упоминания (пользователи, роли, каналы) из текста."""
    return {
        "users": re.findall(r'<@!?(\d+)>', text),
        "roles": re.findall(r'<@&(\d+)>', text),
        "channels": re.findall(r'<#(\d+)>', text),
    }


def slugify(text: str, max_len: int = 80, transliterate: bool = True) -> str:
    """Преобразует текст в безопасный URL-слаг."""
    if transliterate:
        text = transliterate_cyrillic(text)
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:max_len]


# ═══════════════════════════════════════════════════════════════
#  3. CHANNEL CLONING ENGINE (Конструкторы Payload)
# ═══════════════════════════════════════════════════════════════

# Типы каналов Discord API
CH_TEXT = 0
CH_VOICE = 2
CH_CATEGORY = 4
CH_NEWS = 5
CH_STAGE = 13
CH_FORUM = 15
CH_MEDIA = 17

# Лимиты Discord
MAX_TOPIC_TEXT = 1024
MAX_TOPIC_STAGE = 120
MAX_TOPIC_FORUM = 4096
MAX_BITRATE_FREE = 96000
MAX_BITRATE_BOOST = 384000


def map_channel_type(src_type: int) -> int:
    """ULTRA: Маппинг неподдерживаемых типов каналов в текстовый."""
    remap = {
        CH_NEWS: CH_TEXT,
        5: CH_TEXT,
        16: CH_TEXT,  # Directory
        6: CH_TEXT,   # Store (deprecated)
        7: CH_TEXT,   # Group DM
        8: CH_TEXT,   # Unknown
        9: CH_TEXT,   # Unknown
        14: CH_TEXT,  # Unknown
    }
    return remap.get(src_type, src_type)


def sanitize_topic(topic: str, channel_type: int) -> Optional[str]:
    """Очищает и обрезает тему канала согласно лимитам Discord."""
    if not topic:
        return None
    
    topic = topic.strip()
    if channel_type == CH_STAGE:
        return topic[:MAX_TOPIC_STAGE] if topic else None
    elif channel_type in (CH_FORUM, CH_MEDIA):
        return topic[:MAX_TOPIC_FORUM] if topic else None
    else:
        return topic[:MAX_TOPIC_TEXT] if topic else None


def build_text_channel_payload(src: dict, role_map: dict, parent_id: Optional[str] = None) -> dict:
    """ULTRA: Конструктор payload для текстового канала."""
    payload = {
        "name": sanitize_channel_name(src.get("name", "channel")),
        "type": CH_TEXT,
        "position": src.get("position", 0),
        "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
        "nsfw": src.get("nsfw", False),
    }
    
    topic = sanitize_topic(src.get("topic"), CH_TEXT)
    if topic:
        payload["topic"] = topic
    
    if src.get("rate_limit_per_user"):
        payload["rate_limit_per_user"] = src["rate_limit_per_user"]
    
    if parent_id:
        payload["parent_id"] = parent_id
    
    return minify_payload(payload)


def build_voice_channel_payload(src: dict, role_map: dict, parent_id: Optional[str] = None, 
                                 boost_level: int = 0) -> dict:
    """ULTRA: Конструктор payload для голосового канала."""
    max_bitrate = MAX_BITRATE_BOOST if boost_level >= 2 else MAX_BITRATE_FREE
    
    payload = {
        "name": sanitize_channel_name(src.get("name", "voice")),
        "type": CH_VOICE,
        "position": src.get("position", 0),
        "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
        "bitrate": min(src.get("bitrate", 64000), max_bitrate),
    }
    
    if src.get("user_limit"):
        payload["user_limit"] = src["user_limit"]
    
    if src.get("rtc_region"):
        payload["rtc_region"] = src["rtc_region"]
    
    if parent_id:
        payload["parent_id"] = parent_id
    
    return minify_payload(payload)


def build_category_payload(src: dict, role_map: dict) -> dict:
    """ULTRA: Конструктор payload для категории."""
    payload = {
        "name": safe_name(src.get("name", "Category"), max_len=100),
        "type": CH_CATEGORY,
        "position": src.get("position", 0),
        "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
    }
    return minify_payload(payload)


def build_stage_channel_payload(src: dict, role_map: dict, parent_id: Optional[str] = None) -> dict:
    """ULTRA: Конструктор payload для Stage канала."""
    payload = {
        "name": sanitize_channel_name(src.get("name", "stage")),
        "type": CH_STAGE,
        "position": src.get("position", 0),
        "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
    }
    
    topic = sanitize_topic(src.get("topic"), CH_STAGE)
    if topic:
        payload["topic"] = topic
    
    if parent_id:
        payload["parent_id"] = parent_id
    
    return minify_payload(payload)


def build_forum_channel_payload(src: dict, role_map: dict, parent_id: Optional[str] = None) -> dict:
    """ULTRA: Конструктор payload для Forum/Media канала."""
    payload = {
        "name": sanitize_channel_name(src.get("name", "forum")),
        "type": CH_FORUM,
        "position": src.get("position", 0),
        "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
        "nsfw": src.get("nsfw", False),
    }
    
    topic = sanitize_topic(src.get("topic"), CH_FORUM)
    if topic:
        payload["topic"] = topic
    
    if src.get("rate_limit_per_user"):
        payload["rate_limit_per_user"] = src["rate_limit_per_user"]
    
    # Клонирование тегов форума
    if src.get("available_tags"):
        tags = []
        for tag in src["available_tags"][:20]:  # Лимит 20 тегов
            tag_payload = {"name": tag.get("name", "tag")[:20]}
            if tag.get("emoji_id"):
                tag_payload["emoji_id"] = tag["emoji_id"]
            elif tag.get("emoji_name"):
                tag_payload["emoji_name"] = tag["emoji_name"]
            tags.append(tag_payload)
        if tags:
            payload["available_tags"] = tags
    
    if src.get("default_forum_layout"):
        payload["default_forum_layout"] = src["default_forum_layout"]
    
    if src.get("default_sort_order"):
        payload["default_sort_order"] = src["default_sort_order"]
    
    if parent_id:
        payload["parent_id"] = parent_id
    
    return minify_payload(payload)


def build_channel_payload(src: dict, role_map: dict, parent_id: Optional[str] = None,
                          boost_level: int = 0) -> dict:
    """
    ULTRA: Универсальный конструктор payload для любого типа канала.
    Автоматически определяет тип и вызывает соответствующий билдер.
    """
    src_type = src.get("type", CH_TEXT)
    mapped_type = map_channel_type(src_type)
    
    if mapped_type == CH_CATEGORY:
        return build_category_payload(src, role_map)
    elif mapped_type == CH_VOICE:
        return build_voice_channel_payload(src, role_map, parent_id, boost_level)
    elif mapped_type == CH_STAGE:
        return build_stage_channel_payload(src, role_map, parent_id)
    elif mapped_type in (CH_FORUM, CH_MEDIA):
        return build_forum_channel_payload(src, role_map, parent_id)
    else:
        return build_text_channel_payload(src, role_map, parent_id)


# ═══════════════════════════════════════════════════════════════
#  4. ROLE CLONING ENGINE
# ═══════════════════════════════════════════════════════════════

def build_role_payload(src: dict, icon_b64: Optional[str] = None, 
                       unicode_emoji: Optional[str] = None) -> dict:
    """
    ULTRA: Конструктор payload для создания роли.
    Приоритет: CDN иконка > Unicode emoji > Без иконки.
    """
    payload = {
        "name": sanitize_role_name(src.get("name", "role")),
        "permissions": str(src.get("permissions", "0")),
        "color": src.get("color", 0),
        "hoist": src.get("hoist", False),
        "mentionable": src.get("mentionable", False),
    }
    
    if icon_b64:
        payload["icon"] = icon_b64
    elif unicode_emoji:
        payload["unicode_emoji"] = unicode_emoji
    elif src.get("unicode_emoji"):
        payload["unicode_emoji"] = src["unicode_emoji"]
    
    return minify_payload(payload)


def calculate_role_position(src_position: int, total_roles: int) -> int:
    """Вычисляет безопасную позицию для роли."""
    return max(1, min(src_position, total_roles - 1))


# ═══════════════════════════════════════════════════════════════
#  5. API BYPASS & PAYLOAD MINIFICATION
# ═══════════════════════════════════════════════════════════════

def minify_payload(payload: dict) -> dict:
    """
    ULTRA: Удаляет null, пустые строки и пустые списки из payload.
    Снижает размер запроса и уменьшает шанс триггера WAF Discord.
    """
    if not isinstance(payload, dict):
        return payload
    
    result = {}
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        if isinstance(v, list) and len(v) == 0:
            continue
        if isinstance(v, dict) and len(v) == 0:
            continue
        result[k] = v
    
    return result


def strip_null_values(data: Any) -> Any:
    """Рекурсивно удаляет все None значения из вложенных структур."""
    if isinstance(data, dict):
        return {k: strip_null_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [strip_null_values(item) for item in data if item is not None]
    return data


def generate_discord_headers(token: str, multipart: bool = False, 
                              extra_headers: Optional[dict] = None) -> dict:
    """
    ULTRA: Генерирует полный набор заголовков для обхода детекта Discord.
    Включает: User-Agent, X-Super-Properties, X-Context-Properties, Sec-Ch-Ua.
    """
    ua = random_user_agent()
    
    headers = {
        "Authorization": token,
        "User-Agent": ua,
        "X-Super-Properties": generate_super_properties(),
        "X-Context-Properties": generate_x_context_properties(),
        "X-Discord-Locale": "ru-RU",
        "X-Discord-Timezone": "Europe/Moscow",
        "X-Debug-Options": "bugReporterEnabled",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/channels/@me",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "X-RateLimit-Precision": "millisecond",
    }
    
    if not multipart:
        headers["Content-Type"] = "application/json"
    
    if extra_headers:
        headers.update(extra_headers)
    
    return headers


def generate_x_context_properties(guild_id: str = "0", channel_id: str = "0") -> str:
    """Генерирует X-Context-Properties для имитации состояния клиента."""
    ctx = {
        "location": "Guild Settings",
        "location_guild_id": guild_id,
        "location_channel_id": channel_id,
        "location_channel_type": 0,
    }
    json_str = json.dumps(ctx, separators=(',', ':'))
    return base64.b64encode(json_str.encode('utf-8')).decode('ascii')


def generate_client_state() -> str:
    """Генерирует случайный client_state для WebSocket handshake."""
    return hashlib.md5(random_string(32).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════
#  6. RATE LIMIT TRACKER
# ═══════════════════════════════════════════════════════════════

class RateLimitBucket:
    """ULTRA: Трекер лимитов Discord API по заголовкам ответов."""
    
    def __init__(self):
        self.remaining: int = 9999
        self.limit: int = 9999
        self.reset_at: float = 0.0
        self.reset_after: float = 0.0
        self.bucket_id: str = ""
    
    def update_from_headers(self, headers: dict) -> None:
        """Обновляет состояние из заголовков ответа Discord."""
        try:
            if 'X-RateLimit-Remaining' in headers:
                self.remaining = int(headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Limit' in headers:
                self.limit = int(headers['X-RateLimit-Limit'])
            if 'X-RateLimit-Reset' in headers:
                self.reset_at = float(headers['X-RateLimit-Reset'])
            if 'X-RateLimit-Reset-After' in headers:
                self.reset_after = float(headers['X-RateLimit-Reset-After'])
            if 'X-RateLimit-Bucket' in headers:
                self.bucket_id = headers['X-RateLimit-Bucket']
        except (ValueError, TypeError):
            pass
    
    def should_wait(self) -> bool:
        """Проверяет, нужно ли ждать перед следующим запросом."""
        return self.remaining <= 1 and self.reset_after > 0
    
    def get_wait_time(self) -> float:
        """Возвращает время ожидания с учетом джиттера."""
        if not self.should_wait():
            return 0.0
        return self.reset_after + random.uniform(0.5, 1.5)
    
    def is_exhausted(self) -> bool:
        """Проверяет, исчерпан ли лимит."""
        return self.remaining <= 0


def parse_rate_limit_headers(headers: dict) -> Dict[str, Any]:
    """Парсит все заголовки rate limit в словарь."""
    return {
        "remaining": int(headers.get('X-RateLimit-Remaining', 9999)),
        "limit": int(headers.get('X-RateLimit-Limit', 9999)),
        "reset": float(headers.get('X-RateLimit-Reset', 0)),
        "reset_after": float(headers.get('X-RateLimit-Reset-After', 0)),
        "bucket": headers.get('X-RateLimit-Bucket', ''),
        "global": headers.get('X-RateLimit-Global', 'false').lower() == 'true',
    }


def get_retry_after(headers: Dict[str, str], default: float = 1.0) -> float:
    """Парсит заголовки ответа Discord для обхода Rate-Limit (429)."""
    if 'Retry-After' in headers:
        try:
            return float(headers['Retry-After'])
        except ValueError:
            pass
    
    if 'X-RateLimit-Reset' in headers:
        try:
            reset_time = float(headers['X-RateLimit-Reset'])
            delay = reset_time - time.time()
            return max(0.0, delay)
        except ValueError:
            pass
            
    return default + random.uniform(0.1, 0.5)


# ═══════════════════════════════════════════════════════════════
#  7. МЕДИА, MIME И КОНВЕРТАЦИЯ
# ═══════════════════════════════════════════════════════════════

def bytes_to_b64(data: bytes, url_hint: str = "") -> str:
    """Конвертирует байты в data-URI base64 с автоопределением MIME."""
    mime = detect_mime(data, url_hint)
    encoded = base64.b64encode(data).decode('ascii')
    return f"data:{mime};base64,{encoded}"


def detect_mime(data: bytes, url_hint: str = "") -> str:
    """Определяет MIME-тип по magic bytes."""
    if len(data) < 12:
        if url_hint:
            ext = url_hint.split("?")[0].lower()
            if ext.endswith(".gif"): return "image/gif"
            if ext.endswith((".jpg", ".jpeg")): return "image/jpeg"
            if ext.endswith(".webp"): return "image/webp"
            if ext.endswith(".png"): return "image/png"
            if ext.endswith(".mp4"): return "video/mp4"
            if ext.endswith(".webm"): return "video/webm"
        return "application/octet-stream"

    if data[:6] in (b"GIF87a", b"GIF89a"): return "image/gif"
    if data[:8] == b"\x89PNG\r\n\x1a\n": return "image/png"
    if data[:2] == b"\xff\xd8": return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP": return "image/webp"
    if data[:4] == b"ftyp" or (len(data) > 4 and data[4:8] == b"ftyp"): return "video/mp4"
    if data[:4] == b"\x1a\x45\xdf\xa3": return "video/webm"
    if data[:4] == b"OggS": return "audio/ogg"
    if data[:4] == b"fLaC": return "audio/flac"
    if data[:3] == b"ID3" or data[:2] == b"\xff\xfb": return "audio/mpeg"
    if data[:4] == b"AVIF" or (len(data) > 4 and data[4:8] == b"ftypavif"): return "image/avif"
    
    return "application/octet-stream"


def decompress_zlib(data: bytes) -> bytes:
    """Распаковывает zlib/deflate данные."""
    try:
        return zlib.decompress(data)
    except zlib.error:
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error:
            logger.warning("Не удалось распаковать zlib данные")
            return data


def is_animated_url(url: str) -> bool:
    """Определяет, является ли URL анимированным ресурсом."""
    if not url:
        return False
    u = url.split("?")[0].lower()
    return u.endswith(".gif") or "/a_" in u or "/a/" in u or u.endswith(".webm")


def get_file_extension(mime: str) -> str:
    """Возвращает расширение файла по MIME-типу."""
    map_mime_ext = {
        "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
        "image/webp": "webp", "image/svg+xml": "svg", "image/avif": "avif",
        "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/flac": "flac",
        "video/mp4": "mp4", "video/webm": "webm", "application/json": "json",
        "text/plain": "txt", "application/octet-stream": "bin"
    }
    return map_mime_ext.get(mime, "bin")


def hex_to_discord_int(hex_color: str) -> int:
    """Конвертирует HEX цвет (#RRGGBB) в целое число Discord."""
    hex_color = hex_color.lstrip('#')
    try:
        return int(hex_color, 16)
    except ValueError:
        return 0


def discord_int_to_hex(color_int: int) -> str:
    """Конвертирует целое число Discord в HEX цвет (#RRGGBB)."""
    if not color_int or color_int == 0:
        return "#000000"
    return f"#{color_int:06x}"


def get_discord_cdn_url(base_url: str, asset_id: str, file_hash: str, 
                         ext: str = "png", size: int = 1024) -> str:
    """ULTRA: Конструирует правильный URL для Discord CDN."""
    return f"{base_url}/{asset_id}/{file_hash}.{ext}?size={size}"


def is_valid_image_data(data: bytes) -> bool:
    """Проверяет, являются ли данные валидным изображением."""
    if len(data) < 12:
        return False
    mime = detect_mime(data)
    return mime.startswith("image/")


# ═══════════════════════════════════════════════════════════════
#  8. ПРАВА DISCORD
# ═══════════════════════════════════════════════════════════════

DISCORD_PERMISSIONS = {
    "CREATE_INSTANT_INVITE": 0x0000000001, "KICK_MEMBERS": 0x0000000002,
    "BAN_MEMBERS": 0x0000000004, "ADMINISTRATOR": 0x0000000008,
    "MANAGE_CHANNELS": 0x0000000010, "MANAGE_GUILD": 0x0000000020,
    "ADD_REACTIONS": 0x0000000040, "VIEW_AUDIT_LOG": 0x0000000080,
    "PRIORITY_SPEAKER": 0x0000000100, "STREAM": 0x0000000200,
    "VIEW_CHANNEL": 0x0000000400, "SEND_MESSAGES": 0x0000000800,
    "SEND_TTS_MESSAGES": 0x0000001000, "MANAGE_MESSAGES": 0x0000002000,
    "EMBED_LINKS": 0x0000004000, "ATTACH_FILES": 0x0000008000,
    "READ_MESSAGE_HISTORY": 0x0000010000, "MENTION_EVERYONE": 0x0000020000,
    "USE_EXTERNAL_EMOJIS": 0x0000040000, "VIEW_GUILD_INSIGHTS": 0x0000080000,
    "CONNECT": 0x0000100000, "SPEAK": 0x0000200000,
    "MUTE_MEMBERS": 0x0000400000, "DEAFEN_MEMBERS": 0x0000800000,
    "MOVE_MEMBERS": 0x0001000000, "USE_VAD": 0x0002000000,
    "CHANGE_NICKNAME": 0x0004000000, "MANAGE_NICKNAMES": 0x0008000000,
    "MANAGE_ROLES": 0x0010000000, "MANAGE_WEBHOOKS": 0x0020000000,
    "MANAGE_GUILD_EXPRESSIONS": 0x0040000000, "USE_APPLICATION_COMMANDS": 0x0080000000,
    "REQUEST_TO_SPEAK": 0x0100000000, "MANAGE_EVENTS": 0x0200000000,
    "MANAGE_THREADS": 0x0400000000, "CREATE_PUBLIC_THREADS": 0x0800000000,
    "CREATE_PRIVATE_THREADS": 0x1000000000, "USE_EXTERNAL_STICKERS": 0x2000000000,
    "SEND_MESSAGES_IN_THREADS": 0x4000000000, "USE_EMBEDDED_ACTIVITIES": 0x8000000000,
    "MODERATE_MEMBERS": 0x10000000000,
}

def build_permission_mask(permissions: List[str]) -> int:
    """Собирает битовую маску прав из списка названий."""
    mask = 0
    for perm in permissions:
        perm_upper = perm.upper().strip()
        if perm_upper in DISCORD_PERMISSIONS:
            mask |= DISCORD_PERMISSIONS[perm_upper]
    return mask


def parse_permission_mask(mask: int) -> List[str]:
    """Возвращает список названий прав из битовой маски."""
    return [name for name, bit in DISCORD_PERMISSIONS.items() if mask & bit]


def has_permission(permissions: Union[int, str], bit: int) -> bool:
    """Проверяет наличие флага разрешений."""
    try:
        return bool(int(permissions) & bit)
    except (ValueError, TypeError):
        return False


def is_admin_overwrite(overwrites: list, role_id: str) -> bool:
    """ULTRA: Проверяет, дает ли конкретный overwrite права администратора."""
    for ow in overwrites:
        if str(ow.get("id")) == str(role_id):
            allow = int(ow.get("allow", 0))
            return bool(allow & DISCORD_PERMISSIONS["ADMINISTRATOR"])
    return False


def build_overwrites(raw: list, role_map: dict) -> list:
    """Преобразует permission_overwrites, заменяя ID через role_map."""
    result = []
    for ow in raw:
        new_id = role_map.get(str(ow["id"]), str(ow["id"]))
        result.append({
            "id": new_id,
            "type": ow["type"],
            "allow": str(ow.get("allow", "0")),
            "deny": str(ow.get("deny", "0")),
        })
    return result


# ═══════════════════════════════════════════════════════════════
#  9. ВАЛИДАЦИЯ И SNOWFLAKE
# ═══════════════════════════════════════════════════════════════

DISCORD_EPOCH = 1420070400000

def snowflake_to_datetime(snowflake: Union[int, str]) -> Optional[datetime]:
    """Извлекает дату создания объекта Discord из его Snowflake ID."""
    try:
        ts = (int(snowflake) >> 22) + DISCORD_EPOCH
        return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def is_valid_snowflake(s: str) -> bool:
    """Проверяет, является ли строка допустимым Discord snowflake ID."""
    try:
        v = int(s)
        return 10**16 < v < 10**20
    except (ValueError, TypeError):
        return False


def is_valid_token(token: str) -> bool:
    """Проверка формата Discord токена (User или Bot)."""
    if not token or len(token) < 50:
        return False
    parts = token.split(".")
    if len(parts) == 3:
        b64_re = re.compile(r'^[A-Za-z0-9_-]+$')
        try:
            padded = parts[0] + '=' * (-len(parts[0]) % 4)
            base64.urlsafe_b64decode(padded)
            return all(b64_re.match(p) for p in parts)
        except Exception:
            return False
    return False


def is_valid_invite(code: str) -> bool:
    """Проверяет формат кода приглашения Discord."""
    return bool(re.match(r'^[a-zA-Z0-9_-]{2,20}$', code))


def is_valid_webhook_url(url: str) -> bool:
    """ULTRA: Проверяет формат URL вебхука Discord."""
    pattern = r'^https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+$'
    return bool(re.match(pattern, url))


def is_valid_url(url: str) -> bool:
    """Проверяет, является ли строка валидным URL."""
    pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(pattern.match(url))


def clean_proxy_list(proxies: Union[str, List[str]]) -> List[str]:
    """Очищает, валидирует и дедуплицирует список прокси."""
    if isinstance(proxies, str):
        proxies = re.split(r'[,\n]+', proxies)
    
    valid_proxies = []
    seen = set()
    
    for p in proxies:
        p = p.strip()
        if not p or p in seen:
            continue
        
        if re.match(r'^(?:http|https|socks4|socks5):\/\/[^\s@]+@[^\s:]+:\d+$|^(?:http|https|socks4|socks5):\/\/[^\s:]+:\d+$|^[^\s:]+:\d+$', p, re.IGNORECASE):
            valid_proxies.append(p)
            seen.add(p)
            
    return valid_proxies


def parse_proxy_to_dict(proxy_str: str) -> Optional[Dict[str, str]]:
    """Парсит строку прокси в словарь, готовый для requests/aiohttp."""
    if not proxy_str or " " in proxy_str:
        return None
    
    if "://" in proxy_str:
        parsed = urlparse(proxy_str)
        if parsed.hostname and parsed.port:
            scheme = parsed.scheme or "http"
            auth = f"{parsed.username}:{parsed.password}@" if parsed.username else ""
            proxy_url = f"{scheme}://{auth}{parsed.hostname}:{parsed.port}"
            return {"http": proxy_url, "https": proxy_url}
    else:
        parts = proxy_str.split(":")
        if len(parts) == 2:
            host, port = parts
            if host and port.isdigit() and 1 <= int(port) <= 65535:
                url = f"http://{host}:{port}"
                return {"http": url, "https": url}
        elif len(parts) == 4:
            host, port, user, pwd = parts
            if host and port.isdigit() and 1 <= int(port) <= 65535:
                url = f"http://{user}:{pwd}@{host}:{port}"
                return {"http": url, "https": url}
    return None


# ═══════════════════════════════════════════════════════════════
#  10. ДАТЫ, ВРЕМЯ, СЛУЧАЙНЫЕ ДАННЫЕ
# ═══════════════════════════════════════════════════════════════

def format_timestamp(ts: Optional[float], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Форматирует timestamp в строку."""
    if ts is None:
        return "N/A"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt)
    except (ValueError, OSError, OverflowError):
        return str(ts)


def time_ago(ts: float) -> str:
    """Возвращает строку вида '2h ago', '5m ago'."""
    if not ts:
        return "never"
    diff = time.time() - ts
    if diff < 0: return "in future"
    if diff < 60: return f"{int(diff)}s ago"
    if diff < 3600: return f"{int(diff//60)}m ago"
    if diff < 86400: return f"{int(diff//3600)}h ago"
    if diff < 604800: return f"{int(diff//86400)}d ago"
    return f"{int(diff//604800)}w ago"


def random_string(length: int = 8, chars: str = None) -> str:
    """Генерирует случайную строку."""
    if chars is None:
        chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def random_user_agent() -> str:
    """Возвращает случайный современный User-Agent."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    return random.choice(agents)


def generate_super_properties(browser: str = "Chrome", os: str = "Windows") -> str:
    """Генерирует base64-строку x-super-properties."""
    props = {
        "os": os,
        "browser": browser,
        "device": "",
        "system_locale": "ru-RU",
        "browser_user_agent": random_user_agent(),
        "browser_version": "124.0.0.0",
        "os_version": "10",
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": random.randint(310000, 320000),
        "client_event_source": None
    }
    json_str = json.dumps(props, separators=(',', ':'))
    return base64.b64encode(json_str.encode('utf-8')).decode('ascii')


# ═══════════════════════════════════════════════════════════════
#  11. JSON, РАСШИФРОВКА, СЕТЬ
# ═══════════════════════════════════════════════════════════════

def extract_json_from_text(text: str) -> List[Dict[Any, Any]]:
    """Stack-based извлечение JSON-объектов из обфусцированного текста."""
    results = []
    i = 0
    n = len(text)
    
    while i < n:
        if text[i] == '{':
            start = i
            bracket_count = 1
            in_string = False
            escape_next = False
            i += 1
            
            while i < n and bracket_count > 0:
                char = text[i]
                if escape_next:
                    escape_next = False
                elif char == '\\':
                    escape_next = True
                elif char == '"' and not escape_next:
                    in_string = not in_string
                elif not in_string:
                    if char == '{': bracket_count += 1
                    elif char == '}': bracket_count -= 1
                i += 1
                
            if bracket_count == 0:
                candidate = text[start:i]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        results.append(obj)
                except json.JSONDecodeError:
                    pass
        else:
            i += 1
            
    return results


def safe_json_loads(text: str, default=None):
    """Безопасно парсит JSON."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def safe_json_dumps(data, indent: int = 2, fallback: str = "{}") -> str:
    """Безопасно сериализует в JSON."""
    try:
        return json.dumps(data, indent=indent, ensure_ascii=False)
    except (TypeError, ValueError):
        return fallback


def flatten_json(data: dict, prefix: str = "") -> Dict[str, Any]:
    """ULTRA: Преобразует вложенный JSON в плоский словарь для логирования."""
    result = {}
    for k, v in data.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten_json(v, key))
        elif isinstance(v, list):
            result[key] = f"[list:{len(v)} items]"
        else:
            result[key] = v
    return result


def b64_urlsafe_encode(data: Union[str, bytes]) -> str:
    """Кодирует в URL-safe base64."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def b64_urlsafe_decode(data: str) -> bytes:
    """Декодирует URL-safe base64."""
    padded = data + '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def fmt_size(n: int) -> str:
    """Форматирует размер файла в читаемый вид."""
    if n < 1024: return f"{n} B"
    if n < 1024 ** 2: return f"{n / 1024:.1f} KB"
    if n < 1024 ** 3: return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024 ** 3:.2f} GB"


def chunk_list(lst: list, chunk_size: int) -> List[List]:
    """Разбивает список на части."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_get(data: dict, path: str, default=None, separator: str = "."):
    """Безопасно получает значение по пути."""
    keys = path.split(separator)
    for key in keys:
        try:
            if isinstance(data, list) and key.isdigit():
                data = data[int(key)]
            else:
                data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data


def merge_dicts(*dicts) -> dict:
    """Рекурсивно объединяет словари."""
    result = {}
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, dict) and k in result and isinstance(result[k], dict):
                result[k] = merge_dicts(result[k], v)
            else:
                result[k] = v
    return result


def parse_discord_error(resp_json: dict) -> str:
    """ULTRA: Извлекает детальное сообщение об ошибке из ответа Discord API."""
    if not resp_json:
        return "Unknown error"
    
    # Простое сообщение
    if "message" in resp_json:
        msg = resp_json["message"]
        # Проверяем вложенные ошибки
        if "errors" in resp_json:
            details = []
            for field, err in resp_json["errors"].items():
                if isinstance(err, dict) and "_errors" in err:
                    for e in err["_errors"]:
                        details.append(f"{field}: {e.get('message', '')}")
            if details:
                return f"{msg} ({'; '.join(details)})"
        return msg
    
    return str(resp_json)[:200]


# ═══════════════════════════════════════════════════════════════
#  ЭКСПОРТ
# ═══════════════════════════════════════════════════════════════
__all__ = [
    # Delay Manager
    'human_delay', 'fast_delay', 'batch_pause',
    # Strings & Emojis
    'safe_name', 'sanitize_channel_name', 'sanitize_role_name', 'transliterate_cyrillic',
    'strip_emoji', 'extract_custom_emojis', 'extract_mentions', 'slugify',
    # Channel Cloning
    'CH_TEXT', 'CH_VOICE', 'CH_CATEGORY', 'CH_NEWS', 'CH_STAGE', 'CH_FORUM', 'CH_MEDIA',
    'map_channel_type', 'sanitize_topic', 'build_text_channel_payload',
    'build_voice_channel_payload', 'build_category_payload', 'build_stage_channel_payload',
    'build_forum_channel_payload', 'build_channel_payload',
    # Role Cloning
    'build_role_payload', 'calculate_role_position',
    # API Bypass
    'minify_payload', 'strip_null_values', 'generate_discord_headers',
    'generate_x_context_properties', 'generate_client_state',
    # Rate Limit
    'RateLimitBucket', 'parse_rate_limit_headers', 'get_retry_after',
    # Media & MIME
    'bytes_to_b64', 'detect_mime', 'decompress_zlib', 'is_animated_url',
    'get_file_extension', 'hex_to_discord_int', 'discord_int_to_hex',
    'get_discord_cdn_url', 'is_valid_image_data',
    # Permissions
    'DISCORD_PERMISSIONS', 'build_permission_mask', 'parse_permission_mask',
    'has_permission', 'is_admin_overwrite', 'build_overwrites',
    # Validation
    'snowflake_to_datetime', 'is_valid_snowflake', 'is_valid_token',
    'is_valid_invite', 'is_valid_webhook_url', 'is_valid_url',
    'clean_proxy_list', 'parse_proxy_to_dict',
    # Dates & Random
    'format_timestamp', 'time_ago', 'random_string', 'random_user_agent',
    'generate_super_properties',
    # JSON & Network
    'extract_json_from_text', 'safe_json_loads', 'safe_json_dumps', 'flatten_json',
    'b64_urlsafe_encode', 'b64_urlsafe_decode', 'fmt_size', 'chunk_list',
    'safe_get', 'merge_dicts', 'parse_discord_error',
]