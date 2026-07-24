# -*- coding: utf-8 -*-
"""
config.py — Discord Cloner v9.0 ULTRA (2026) — Production Edition
=================================================================
Центральный конфигурационный файл с продвинутыми настройками обхода API,
анти-детекта, адаптивного поведения и защиты от банов.

Ключевые особенности:
  • Smart Delay System: Все задержки 2-5 секунд (минимум) для имитации человека.
  • API Bypass Engine: TLS spoofing, header rotation, payload minification.
  • Channel Cloning Config: Настройки для Forum, Stage, Voice, Media каналов.
  • Rate Limit Defense: Превентивный троттлинг, Circuit Breaker, backoff.
  • Strict Validation: Блокировка запуска при опасных настройках.

Поддержка загрузки из .env файла.
"""

import os
import sys
import random
from pathlib import Path
from typing import Any, List, Dict, Optional, Tuple

# ═══════════════════════════════════════════════════════════════
#  ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (.env)
# ═══════════════════════════════════════════════════════════════

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass  # python-dotenv не установлен — работаем только с os.environ


def _env(key: str, default: Any = None, cast: type = str) -> Any:
    """
    Безопасное получение и кастинг значения из переменных окружения.
    Поддерживает: str, int, float, bool.
    """
    val = os.environ.get(key, default)
    if val is None:
        return default
    if cast is bool:
        return str(val).lower() in ("true", "1", "yes", "on")
    try:
        return cast(val)
    except (ValueError, TypeError):
        return default


def _env_list(key: str, default: List[str] = None, separator: str = ",") -> List[str]:
    """Получает список значений из переменной окружения."""
    if default is None:
        default = []
    val = os.environ.get(key)
    if not val:
        return default
    return [item.strip() for item in val.split(separator) if item.strip()]


# ═══════════════════════════════════════════════════════════════
#  1. МЕТА-ДАННЫЕ И БАЗОВЫЕ URL
# ═══════════════════════════════════════════════════════════════

VERSION = "9.0.0-ULTRA-PRODUCTION"
VERSION_CODE = 90000
BUILD_DATE = "2026-07-25"

# Discord API Endpoints
DISCORD_API = _env("DISCORD_API", "https://discord.com/api/v10")
DISCORD_API_V9 = _env("DISCORD_API_V9", "https://discord.com/api/v9")
DISCORD_CDN = _env("CDN", "https://cdn.discordapp.com")
DISCORD_MEDIA = _env("MEDIA", "https://media.discordapp.net")
DISCORD_GATEWAY = _env("GATEWAY", "wss://gateway.discord.gg/?v=10&encoding=json")

# Task Management
TASK_TTL = _env("TASK_TTL", 3600, int)  # Время жизни задачи в памяти (сек)
TASK_CLEANUP_INTERVAL = _env("TASK_CLEANUP_INTERVAL", 300, int)  # Интервал очистки (сек)


# ═══════════════════════════════════════════════════════════════
#  2. API BYPASS ENGINE (Анти-Детект и Обход WAF)
# ═══════════════════════════════════════════════════════════════

# Главный переключатель стелс-режима
STEALTH_MODE = _env("STEALTH_MODE", True, bool)

# TLS Fingerprint Spoofing (требует curl_cffi)
# Подменяет JA3/JA4 отпечаток под реальный Chrome/Firefox
TLS_SPOOFING_ENABLED = _env("TLS_SPOOFING_ENABLED", True, bool)
TLS_IMPERSONATE_PROFILE = _env("TLS_IMPERSONATE_PROFILE", "chrome120")

# Ротация User-Agent между запросами
ROTATE_USER_AGENTS = _env("ROTATE_USER_AGENTS", True, bool)

# Минификация JSON payload (удаление null, пустых строк/списков)
# Снижает размер запроса и уменьшает шанс триггера WAF
MINIFY_PAYLOADS = _env("MINIFY_PAYLOADS", True, bool)

# Рандомизация порядка создания объектов
# False рекомендуется для стабильной синхронизации иерархии
RANDOMIZE_CREATION_ORDER = _env("RANDOMIZE_CREATION_ORDER", False, bool)

# Генерация X-Context-Properties (имитация состояния клиента)
GENERATE_CONTEXT_PROPERTIES = _env("GENERATE_CONTEXT_PROPERTIES", True, bool)

# Генерация X-Super-Properties (имитация браузерного клиента)
GENERATE_SUPER_PROPERTIES = _env("GENERATE_SUPER_PROPERTIES", True, bool)

# Прецизионность Rate Limit заголовков
RATELIMIT_PRECISION = _env("RATELIMIT_PRECISION", "millisecond")


# ═══════════════════════════════════════════════════════════════
#  3. RATE LIMIT DEFENSE (Защита от 429 и Банов)
# ═══════════════════════════════════════════════════════════════

# Максимальное количество попыток при сетевых ошибках (5xx)
BRAIN_MAX_RETRIES = _env("BRAIN_MAX_RETRIES", 10, int)

# Таймауты запросов (секунды)
BRAIN_TIMEOUT_DEFAULT = _env("BRAIN_TIMEOUT_DEFAULT", 30, int)
BRAIN_TIMEOUT_UPLOAD = _env("BRAIN_TIMEOUT_UPLOAD", 90, int)
BRAIN_TIMEOUT_DOWNLOAD = _env("BRAIN_TIMEOUT_DOWNLOAD", 60, int)

# Circuit Breaker: Порог срабатывания (количество 429 подряд)
# ВАЖНО: Установлено на 2 для раннего обнаружения лимитов
CIRCUIT_BREAKER_THRESHOLD = _env("CIRCUIT_BREAKER_THRESHOLD", 2, int)

# Circuit Breaker: Время заморозки токена (секунды)
# 45 секунд достаточно для полного сброса bucket Discord
CIRCUIT_BREAKER_PENALTY = _env("CIRCUIT_BREAKER_PENALTY", 45.0, float)

# Превентивный троттлинг: читать X-RateLimit-Remaining и спать ДО 429
PREEMPTIVE_THROTTLE_ENABLED = _env("PREEMPTIVE_THROTTLE_ENABLED", True, bool)

# Превентивный троттлинг: порог remaining запросов для активации
PREEMPTIVE_THROTTLE_THRESHOLD = _env("PREEMPTIVE_THROTTLE_THRESHOLD", 1, int)

# Экспоненциальный backoff при повторных попытках
BACKOFF_BASE = _env("BACKOFF_BASE", 2.0, float)
BACKOFF_MAX = _env("BACKOFF_MAX", 60.0, float)
BACKOFF_JITTER = _env("BACKOFF_JITTER", 0.5, float)

# Динамический Jitter (случайная добавка к задержкам)
BRAIN_JITTER_MIN = _env("BRAIN_JITTER_MIN", 0.1, float)
BRAIN_JITTER_MAX = _env("BRAIN_JITTER_MAX", 0.5, float)


# ═══════════════════════════════════════════════════════════════
#  4. SMART DELAY SYSTEM (Задержки 2-5 секунд)
# ═══════════════════════════════════════════════════════════════
#  ВАЖНО: Все задержки установлены в диапазоне 2-5 секунд (минимум).
#  Это предотвращает накопление штрафов Discord и зависания на 700+ сек.
#  НЕ МЕНЯЙТЕ эти значения на < 2.0, если используете 1 токен!
# ═══════════════════════════════════════════════════════════════

# --- Роли ---
DELAY_ROLE_MIN = _env("DELAY_ROLE_MIN", 2.0, float)
DELAY_ROLE_MAX = _env("DELAY_ROLE_MAX", 5.0, float)

# --- Каналы ---
DELAY_CHANNEL_MIN = _env("DELAY_CHANNEL_MIN", 2.0, float)
DELAY_CHANNEL_MAX = _env("DELAY_CHANNEL_MAX", 5.0, float)

# --- Эмодзи ---
DELAY_EMOJI_MIN = _env("DELAY_EMOJI_MIN", 2.5, float)
DELAY_EMOJI_MAX = _env("DELAY_EMOJI_MAX", 5.0, float)

# --- Стикеры ---
DELAY_STICKER_MIN = _env("DELAY_STICKER_MIN", 3.0, float)
DELAY_STICKER_MAX = _env("DELAY_STICKER_MAX", 6.0, float)

# --- Вебхуки ---
DELAY_WEBHOOK_MIN = _env("DELAY_WEBHOOK_MIN", 2.0, float)
DELAY_WEBHOOK_MAX = _env("DELAY_WEBHOOK_MAX", 4.0, float)

# --- Удаление (Purge) ---
DELAY_DELETE_MIN = _env("DELAY_DELETE_MIN", 1.0, float)
DELAY_DELETE_MAX = _env("DELAY_DELETE_MAX", 2.5, float)

# --- Выдача ролей участникам ---
DELAY_MEMBER_ROLE_MIN = _env("DELAY_MEMBER_ROLE_MIN", 1.5, float)
DELAY_MEMBER_ROLE_MAX = _env("DELAY_MEMBER_ROLE_MAX", 3.5, float)

# --- AutoMod правила ---
DELAY_AUTOMOD_MIN = _env("DELAY_AUTOMOD_MIN", 2.0, float)
DELAY_AUTOMOD_MAX = _env("DELAY_AUTOMOD_MAX", 4.0, float)

# --- Инвайты ---
DELAY_INVITE_MIN = _env("DELAY_INVITE_MIN", 1.5, float)
DELAY_INVITE_MAX = _env("DELAY_INVITE_MAX", 3.0, float)

# --- Настройки сервера ---
DELAY_SETTINGS_MIN = _env("DELAY_SETTINGS_MIN", 1.0, float)
DELAY_SETTINGS_MAX = _env("DELAY_SETTINGS_MAX", 2.0, float)

# --- Синхронизация прав ---
DELAY_RESYNC_MIN = _env("DELAY_RESYNC_MIN", 0.5, float)
DELAY_RESYNC_MAX = _env("DELAY_RESYNC_MAX", 1.5, float)


# ═══════════════════════════════════════════════════════════════
#  5. BATCH PROCESSING (Пакетная обработка с паузами)
# ═══════════════════════════════════════════════════════════════
#  После каждых N операций делается длинная пауза для сброса лимитов.
#  Это критически важно для предотвращения 429 ошибок.
# ═══════════════════════════════════════════════════════════════

# Роли: каждые 3 роли → пауза 12 секунд
ROLE_BATCH_SIZE = _env("ROLE_BATCH_SIZE", 3, int)
ROLE_BATCH_PAUSE = _env("ROLE_BATCH_PAUSE", 12.0, float)

# Каналы: каждые 8 каналов → пауза 10 секунд
CHANNEL_BATCH_SIZE = _env("CHANNEL_BATCH_SIZE", 8, int)
CHANNEL_BATCH_PAUSE = _env("CHANNEL_BATCH_PAUSE", 10.0, float)

# Эмодзи: каждые 5 эмодзи → пауза 8 секунд
EMOJI_BATCH_SIZE = _env("EMOJI_BATCH_SIZE", 5, int)
EMOJI_BATCH_PAUSE = _env("EMOJI_BATCH_PAUSE", 8.0, float)

# Стикеры: каждые 3 стикера → пауза 10 секунд
STICKER_BATCH_SIZE = _env("STICKER_BATCH_SIZE", 3, int)
STICKER_BATCH_PAUSE = _env("STICKER_BATCH_PAUSE", 10.0, float)

# Участники: каждые 10 участников → пауза 5 секунд
MEMBER_BATCH_SIZE = _env("MEMBER_BATCH_SIZE", 10, int)
MEMBER_BATCH_PAUSE = _env("MEMBER_BATCH_PAUSE", 5.0, float)


# ═══════════════════════════════════════════════════════════════
#  6. CHANNEL CLONING ENGINE (Настройки клонирования каналов)
# ═══════════════════════════════════════════════════════════════

# Типы каналов Discord API
CH_TEXT = 0
CH_VOICE = 2
CH_CATEGORY = 4
CH_NEWS = 5
CH_STAGE = 13
CH_FORUM = 15
CH_DIRECTORY = 16
CH_MEDIA = 17

# Типы каналов для пропуска (не клонируются)
CH_SKIP_TYPES = {CH_DIRECTORY, 6, 7, 8, 9, 14}

# Ремаппинг неподдерживаемых типов в текстовый
CH_REMAP_TYPES = {
    CH_NEWS: CH_TEXT,
    5: CH_TEXT,
    16: CH_TEXT,
}

# Иконки для логирования
CH_ICONS = {
    CH_TEXT: "💬",
    CH_VOICE: "🔊",
    CH_CATEGORY: "📂",
    CH_NEWS: "📢",
    CH_STAGE: "🎭",
    CH_FORUM: "🗂️",
    CH_MEDIA: "🎬",
    CH_DIRECTORY: "📁",
}

# Лимиты тем каналов (символы)
MAX_TOPIC_TEXT = 1024
MAX_TOPIC_STAGE = 120
MAX_TOPIC_FORUM = 4096

# Настройки голосовых каналов
DEFAULT_BITRATE = 64000
MAX_BITRATE_FREE = 96000
MAX_BITRATE_BOOST_1 = 128000
MAX_BITRATE_BOOST_2 = 256000
MAX_BITRATE_BOOST_3 = 384000

# Настройки Forum каналов
CLONE_FORUM_TAGS = _env("CLONE_FORUM_TAGS", True, bool)
MAX_FORUM_TAGS = 20
MAX_FORUM_TAG_NAME_LENGTH = 20

# Настройки Stage каналов
CLONE_STAGE_TOPICS = _env("CLONE_STAGE_TOPICS", True, bool)

# Настройки текстовых каналов
CLONE_NSFW = _env("CLONE_NSFW", True, bool)
CLONE_SLOWMODE = _env("CLONE_SLOWMODE", True, bool)
MAX_SLOWMODE = 21600  # 6 часов в секундах

# Настройки категорий
CLONE_CATEGORY_POSITIONS = _env("CLONE_CATEGORY_POSITIONS", True, bool)


# ═══════════════════════════════════════════════════════════════
#  7. ROLE CLONING ENGINE (Настройки клонирования ролей)
# ═══════════════════════════════════════════════════════════════

# Клонирование иконок ролей (CDN)
CLONE_ROLE_ICONS = _env("CLONE_ROLE_ICONS", True, bool)

# Клонирование unicode эмодзи ролей
CLONE_ROLE_EMOJIS = _env("CLONE_ROLE_EMOJIS", True, bool)

# Синхронизация иерархии ролей (позиций)
SYNC_ROLE_HIERARCHY = _env("SYNC_ROLE_HIERARCHY", True, bool)

# Максимальная длина имени роли
MAX_ROLE_NAME_LENGTH = 100

# Пропускать managed роли (боты, интеграции)
SKIP_MANAGED_ROLES = _env("SKIP_MANAGED_ROLES", True, bool)

# Бесплатные Unicode-эмодзи для ролей (Fallback при отсутствии иконки)
FREE_ROLE_EMOJIS = [
    "⭐", "🌟", "✨", "💫", "🎯", "🔥", "❄️", "⚡", "🌈", "🎮",
    "🎲", "🏆", "🎖️", "🥇", "🥈", "🥉", "💎", "👑", "🛡️", "⚔️",
    "🗡️", "🏹", "🔮", "🌙", "☀️", "🌊", "🍀", "🌺", "🦋", "🦁",
    "🐉", "🦊", "🤖", "👾", "🎪", "🎨", "🎭", "🎬", "🎸", "🎵",
    "🔑", "🗝️", "💡", "🔭", "⚗️", "🧬", "🧪", "🔬", "🧠", "💻",
    "🚀", "🛸", "🌍", "🌎", "🌏", "🪐", "☄️", "🌠", "🌌", "🔭",
    "🎯", "🎪", "🎨", "🎭", "🎬", "🎤", "🎧", "🎼", "🎹", "🥁",
    "🦄", "🐲", "🦅", "🦈", "🐺", "🦉", "🦇", "🕷️", "🦋", "🐝",
]


# ═══════════════════════════════════════════════════════════════
#  8. ЛИМИТЫ DISCORD API (Жесткие ограничения)
# ═══════════════════════════════════════════════════════════════

MAX_CHANNELS = _env("MAX_CHANNELS", 500, int)
MAX_ROLES = _env("MAX_ROLES", 250, int)
MAX_EMOJIS_FREE = _env("MAX_EMOJIS_FREE", 50, int)
MAX_EMOJIS_BOOST = _env("MAX_EMOJIS_BOOST", 250, int)
MAX_STICKERS_FREE = _env("MAX_STICKERS_FREE", 5, int)
MAX_STICKERS_BOOST = _env("MAX_STICKERS_BOOST", 60, int)
MAX_WEBHOOKS_PER_CHANNEL = 15
MAX_INVITES_PER_GUILD = 1000
MAX_AUTOMOD_RULES = 100

# Лимиты размеров файлов (байты)
MAX_ICON_SIZE = 256 * 1024          # 256 KB для иконок
MAX_BANNER_SIZE = 10 * 1024 * 1024  # 10 MB для баннеров
MAX_SPLASH_SIZE = 10 * 1024 * 1024  # 10 MB для сплэшей
MAX_EMOJI_SIZE = 256 * 1024         # 256 KB для эмодзи
MAX_STICKER_SIZE = 512 * 1024       # 512 KB для стикеров
MAX_ROLE_ICON_SIZE = 256 * 1024     # 256 KB для иконок ролей


# ═══════════════════════════════════════════════════════════════
#  9. КОДЫ ОШИБОК DISCORD API
# ═══════════════════════════════════════════════════════════════

DC_NO_ADMIN = 50013
DC_NO_ACCESS = 50001
DC_LIMIT_ROLES = 30005
DC_LIMIT_EMOJIS = 30007
DC_LIMIT_CHANNELS = 30016
DC_LIMIT_STICKERS = 30039
DC_LIMIT_WEBHOOKS = 30029
DC_NEEDS_BOOST = 50101
DC_INVALID_FORM = 50035
DC_TOO_MANY_REQUESTS = 429
DC_UNAUTHORIZED = 401
DC_FORBIDDEN = 403
DC_NOT_FOUND = 404
DC_METHOD_NOT_ALLOWED = 405
DC_SERVER_ERROR = 500
DC_BAD_GATEWAY = 502
DC_SERVICE_UNAVAILABLE = 503
DC_GATEWAY_TIMEOUT = 504

ERROR_MESSAGES = {
    DC_NO_ADMIN: "Требуется роль Администратор",
    DC_NO_ACCESS: "Нет доступа к ресурсу",
    DC_LIMIT_ROLES: "Достигнут лимит ролей (250)",
    DC_LIMIT_EMOJIS: "Достигнут лимит эмодзи",
    DC_LIMIT_CHANNELS: "Достигнут лимит каналов (500)",
    DC_LIMIT_STICKERS: "Достигнут лимит стикеров",
    DC_LIMIT_WEBHOOKS: "Достигнут лимит вебхуков на канал",
    DC_NEEDS_BOOST: "Требуется буст сервера (Level 2+)",
    DC_INVALID_FORM: "Неверный формат данных",
    DC_TOO_MANY_REQUESTS: "Rate-Limit (429). Активирован Circuit Breaker.",
    DC_UNAUTHORIZED: "Недействительный токен",
    DC_FORBIDDEN: "Нет прав для выполнения действия",
    DC_NOT_FOUND: "Ресурс не найден",
    DC_SERVER_ERROR: "Внутренняя ошибка сервера Discord",
}

# Стратегии повторных попыток для кодов ошибок
# retry: повторять запрос, skip: пропустить элемент, abort: остановить клонирование
ERROR_RETRY_STRATEGY = {
    DC_TOO_MANY_REQUESTS: "retry",
    DC_SERVER_ERROR: "retry",
    DC_BAD_GATEWAY: "retry",
    DC_SERVICE_UNAVAILABLE: "retry",
    DC_GATEWAY_TIMEOUT: "retry",
    DC_NO_ADMIN: "abort",
    DC_NO_ACCESS: "skip",
    DC_LIMIT_ROLES: "skip",
    DC_LIMIT_EMOJIS: "skip",
    DC_LIMIT_CHANNELS: "skip",
    DC_LIMIT_STICKERS: "skip",
    DC_NEEDS_BOOST: "skip",
    DC_INVALID_FORM: "skip",
    DC_UNAUTHORIZED: "abort",
    DC_FORBIDDEN: "skip",
    DC_NOT_FOUND: "skip",
}


# ═══════════════════════════════════════════════════════════════
#  10. ПРОКСИ И РОТАЦИЯ ТОКЕНОВ
# ═══════════════════════════════════════════════════════════════

TOKEN_ROTATION_STRATEGY = _env("TOKEN_ROTATION_STRATEGY", "least_used")
# Стратегии: least_used, round_robin, random, sticky

PROXY_ROTATION_ENABLED = _env("PROXY_ROTATION_ENABLED", True, bool)
PROXY_ROTATION_MODE = _env("PROXY_ROTATION_MODE", "per_request")
# Режимы: per_request, per_session, sticky

PROXY_TIMEOUT = _env("PROXY_TIMEOUT", 10, int)
PROXY_MAX_FAILURES = _env("PROXY_MAX_FAILURES", 3, int)


# ═══════════════════════════════════════════════════════════════
#  11. ВЕБ-СЕРВЕР (Flask + SocketIO) И БЕЗОПАСНОСТЬ
# ═══════════════════════════════════════════════════════════════

HOST = _env("HOST", "127.0.0.1")
PORT = _env("PORT", 5500, int)
DEBUG = _env("DEBUG", False, bool)

SECRET_KEY = _env("SECRET_KEY", "ultra-secure-discord-cloner-2026-change-this-key")
SESSION_LIFETIME = _env("SESSION_LIFETIME", 3600, int)

CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:5500", "http://127.0.0.1:5500"]
)

# Security Headers
SECURITY_HEADERS_ENABLED = _env("SECURITY_HEADERS_ENABLED", True, bool)
CONTENT_SECURITY_POLICY = _env(
    "CONTENT_SECURITY_POLICY",
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
)


# ═══════════════════════════════════════════════════════════════
#  12. ЛОГИРОВАНИЕ И МОНИТОРИНГ
# ═══════════════════════════════════════════════════════════════

LOG_LEVEL = _env("LOG_LEVEL", "INFO")
LOG_FORMAT = _env("LOG_FORMAT", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
LOG_DATE_FORMAT = _env("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
LOG_FILE = _env("LOG_FILE", "logs/cloner_ultra.log")
LOG_MAX_BYTES = _env("LOG_MAX_BYTES", 15 * 1024 * 1024, int)
LOG_BACKUP_COUNT = _env("LOG_BACKUP_COUNT", 5, int)
LOG_ENABLE_JSON = _env("LOG_ENABLE_JSON", False, bool)

# Мониторинг производительности
ENABLE_PERFORMANCE_METRICS = _env("ENABLE_PERFORMANCE_METRICS", True, bool)
METRICS_INTERVAL = _env("METRICS_INTERVAL", 60, int)


# ═══════════════════════════════════════════════════════════════
#  13. СТРАТЕГИЯ КЛОНИРОВАНИЯ (Переключатели)
# ═══════════════════════════════════════════════════════════════

# Основные шаги клонирования
CLONE_PURGE_TARGET = _env("CLONE_PURGE_TARGET", True, bool)
CLONE_ROLES = _env("CLONE_ROLES", True, bool)
CLONE_CHANNELS = _env("CLONE_CHANNELS", True, bool)
CLONE_EMOJIS = _env("CLONE_EMOJIS", True, bool)
CLONE_STICKERS = _env("CLONE_STICKERS", True, bool)
CLONE_SETTINGS = _env("CLONE_SETTINGS", True, bool)
CLONE_AUTOMOD = _env("CLONE_AUTOMOD", True, bool)
CLONE_WEBHOOKS = _env("CLONE_WEBHOOKS", True, bool)
CLONE_INVITES = _env("CLONE_INVITES", True, bool)
CLONE_MEMBER_ROLES = _env("CLONE_MEMBER_ROLES", True, bool)
CLONE_RESYNC_PERMISSIONS = _env("CLONE_RESYNC_PERMISSIONS", True, bool)

# Фильтры
CLONE_SKIP_BOTS = _env("CLONE_SKIP_BOTS", True, bool)
CLONE_ONLY_NON_ADMIN_ROLES = _env("CLONE_ONLY_NON_ADMIN_ROLES", True, bool)
CLONE_SKIP_MANAGED_ROLES = _env("CLONE_SKIP_MANAGED_ROLES", True, bool)

# Обработка ошибок
CLONE_RETRY_ON_ERROR = _env("CLONE_RETRY_ON_ERROR", True, bool)
CLONE_STOP_ON_CRITICAL = _env("CLONE_STOP_ON_CRITICAL", True, bool)
CLONE_SKIP_ON_LIMIT = _env("CLONE_SKIP_ON_LIMIT", True, bool)


# ═══════════════════════════════════════════════════════════════
#  14. HELPER FUNCTIONS (Вспомогательные функции)
# ═══════════════════════════════════════════════════════════════

def get_delay(operation: str) -> float:
    """
    Возвращает случайную задержку для указанной операции.
    Все задержки находятся в безопасном диапазоне 2-5 секунд.
    
    Args:
        operation: Тип операции (role, channel, emoji, sticker, etc.)
    
    Returns:
        float: Задержка в секундах с джиттером.
    """
    delay_map = {
        "role": (DELAY_ROLE_MIN, DELAY_ROLE_MAX),
        "channel": (DELAY_CHANNEL_MIN, DELAY_CHANNEL_MAX),
        "emoji": (DELAY_EMOJI_MIN, DELAY_EMOJI_MAX),
        "sticker": (DELAY_STICKER_MIN, DELAY_STICKER_MAX),
        "webhook": (DELAY_WEBHOOK_MIN, DELAY_WEBHOOK_MAX),
        "delete": (DELAY_DELETE_MIN, DELAY_DELETE_MAX),
        "member_role": (DELAY_MEMBER_ROLE_MIN, DELAY_MEMBER_ROLE_MAX),
        "automod": (DELAY_AUTOMOD_MIN, DELAY_AUTOMOD_MAX),
        "invite": (DELAY_INVITE_MIN, DELAY_INVITE_MAX),
        "settings": (DELAY_SETTINGS_MIN, DELAY_SETTINGS_MAX),
        "resync": (DELAY_RESYNC_MIN, DELAY_RESYNC_MAX),
    }
    
    min_d, max_d = delay_map.get(operation, (2.0, 5.0))
    base_delay = random.uniform(min_d, max_d)
    jitter = random.uniform(BRAIN_JITTER_MIN, BRAIN_JITTER_MAX)
    return base_delay + jitter


def get_batch_config(operation: str) -> Tuple[int, float]:
    """
    Возвращает конфигурацию batch для указанной операции.
    
    Args:
        operation: Тип операции (role, channel, emoji, sticker, member)
    
    Returns:
        Tuple[int, float]: (размер батча, пауза в секундах)
    """
    batch_map = {
        "role": (ROLE_BATCH_SIZE, ROLE_BATCH_PAUSE),
        "channel": (CHANNEL_BATCH_SIZE, CHANNEL_BATCH_PAUSE),
        "emoji": (EMOJI_BATCH_SIZE, EMOJI_BATCH_PAUSE),
        "sticker": (STICKER_BATCH_SIZE, STICKER_BATCH_PAUSE),
        "member": (MEMBER_BATCH_SIZE, MEMBER_BATCH_PAUSE),
    }
    return batch_map.get(operation, (5, 10.0))


def is_feature_enabled(feature: str) -> bool:
    """Проверяет, включена ли указанная функция клонирования."""
    feature_map = {
        "purge": CLONE_PURGE_TARGET,
        "roles": CLONE_ROLES,
        "channels": CLONE_CHANNELS,
        "emojis": CLONE_EMOJIS,
        "stickers": CLONE_STICKERS,
        "settings": CLONE_SETTINGS,
        "automod": CLONE_AUTOMOD,
        "webhooks": CLONE_WEBHOOKS,
        "invites": CLONE_INVITES,
        "member_roles": CLONE_MEMBER_ROLES,
        "resync": CLONE_RESYNC_PERMISSIONS,
    }
    return feature_map.get(feature, False)


def get_error_strategy(error_code: int) -> str:
    """Возвращает стратегию обработки для кода ошибки."""
    return ERROR_RETRY_STRATEGY.get(error_code, "skip")


def get_max_bitrate(boost_level: int) -> int:
    """Возвращает максимальный битрейт для уровня буста."""
    bitrate_map = {
        0: MAX_BITRATE_FREE,
        1: MAX_BITRATE_BOOST_1,
        2: MAX_BITRATE_BOOST_2,
        3: MAX_BITRATE_BOOST_3,
    }
    return bitrate_map.get(boost_level, MAX_BITRATE_FREE)


def get_api_url(endpoint: str, version: int = 10) -> str:
    """Конструирует полный URL для Discord API."""
    base = DISCORD_API if version == 10 else DISCORD_API_V9
    return f"{base}{endpoint}"


# ═══════════════════════════════════════════════════════════════
#  15. ВАЛИДАЦИЯ КОНФИГУРАЦИИ (Строгая)
# ═══════════════════════════════════════════════════════════════

def validate_config() -> List[str]:
    """
    Проверяет критические настройки на адекватность.
    Возвращает список ошибок. Если список не пуст — запуск блокируется.
    """
    errors = []
    warnings = []
    
    # Проверка базовых параметров
    if BRAIN_MAX_RETRIES < 1:
        errors.append("BRAIN_MAX_RETRIES должно быть >= 1")
    
    if BRAIN_TIMEOUT_DEFAULT < 5:
        errors.append("BRAIN_TIMEOUT_DEFAULT слишком мал (< 5 сек)")
    
    if PORT < 1 or PORT > 65535:
        errors.append(f"PORT ({PORT}) вне допустимого диапазона (1-65535)")
    
    # Проверка лимитов Discord
    if MAX_CHANNELS > 500:
        errors.append("MAX_CHANNELS не может превышать 500 (жесткий лимит Discord)")
    
    if MAX_ROLES > 250:
        errors.append("MAX_ROLES не может превышать 250 (жесткий лимит Discord)")
    
    # КРИТИЧНО: Проверка задержек (защита от банов)
    if DELAY_ROLE_MIN < 2.0:
        errors.append(
            f"DELAY_ROLE_MIN ({DELAY_ROLE_MIN}) слишком мал! "
            f"Минимум 2.0 сек для предотвращения 429 ошибок."
        )
    
    if DELAY_CHANNEL_MIN < 2.0:
        errors.append(
            f"DELAY_CHANNEL_MIN ({DELAY_CHANNEL_MIN}) слишком мал! "
            f"Минимум 2.0 сек для предотвращения 429 ошибок."
        )
    
    if DELAY_EMOJI_MIN < 2.0:
        warnings.append(
            f"DELAY_EMOJI_MIN ({DELAY_EMOJI_MIN}) рекомендуется >= 2.0 сек."
        )
    
    # Проверка batch настроек
    if ROLE_BATCH_SIZE > 5:
        warnings.append(
            f"ROLE_BATCH_SIZE ({ROLE_BATCH_SIZE}) > 5. "
            f"Рекомендуется 3-4 для стабильности."
        )
    
    if ROLE_BATCH_PAUSE < 5.0:
        errors.append(
            f"ROLE_BATCH_PAUSE ({ROLE_BATCH_PAUSE}) слишком мал! "
            f"Минимум 5.0 сек для сброса лимитов Discord."
        )
    
    if CHANNEL_BATCH_PAUSE < 5.0:
        errors.append(
            f"CHANNEL_BATCH_PAUSE ({CHANNEL_BATCH_PAUSE}) слишком мал! "
            f"Минимум 5.0 сек для сброса лимитов Discord."
        )
    
    # Проверка Circuit Breaker
    if CIRCUIT_BREAKER_THRESHOLD > 3:
        warnings.append(
            f"CIRCUIT_BREAKER_THRESHOLD ({CIRCUIT_BREAKER_THRESHOLD}) > 3. "
            f"Рекомендуется 2 для раннего обнаружения лимитов."
        )
    
    if CIRCUIT_BREAKER_PENALTY < 30.0:
        warnings.append(
            f"CIRCUIT_BREAKER_PENALTY ({CIRCUIT_BREAKER_PENALTY}) < 30 сек. "
            f"Рекомендуется 45+ сек для полного сброса bucket."
        )
    
    # Вывод предупреждений
    if warnings:
        print("\n" + "=" * 60)
        print(" [WARNING] Предупреждения в конфигурации:")
        for warn in warnings:
            print(f"   ⚠️  {warn}")
        print("=" * 60 + "\n")
    
    return errors


# Автоматическая валидация при импорте
if _env("CONFIG_VALIDATE", True, bool):
    _errors = validate_config()
    if _errors:
        print("\n" + "=" * 60)
        print(" [CRITICAL] Ошибки в конфигурации config.py / .env:")
        for err in _errors:
            print(f"   ❌ {err}")
        print("=" * 60)
        print("\n [INFO] Запуск отменен во избежание блокировки аккаунта.")
        print(" [INFO] Исправьте указанные ошибки и перезапустите.\n")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════
#  ЭКСПОРТ
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # Metadata
    "VERSION", "VERSION_CODE", "BUILD_DATE",
    # URLs
    "DISCORD_API", "DISCORD_API_V9", "DISCORD_CDN", "DISCORD_MEDIA", "DISCORD_GATEWAY",
    # Task Management
    "TASK_TTL", "TASK_CLEANUP_INTERVAL",
    # API Bypass
    "STEALTH_MODE", "TLS_SPOOFING_ENABLED", "TLS_IMPERSONATE_PROFILE",
    "ROTATE_USER_AGENTS", "MINIFY_PAYLOADS", "RANDOMIZE_CREATION_ORDER",
    "GENERATE_CONTEXT_PROPERTIES", "GENERATE_SUPER_PROPERTIES", "RATELIMIT_PRECISION",
    # Rate Limit
    "BRAIN_MAX_RETRIES", "BRAIN_TIMEOUT_DEFAULT", "BRAIN_TIMEOUT_UPLOAD",
    "BRAIN_TIMEOUT_DOWNLOAD", "CIRCUIT_BREAKER_THRESHOLD", "CIRCUIT_BREAKER_PENALTY",
    "PREEMPTIVE_THROTTLE_ENABLED", "PREEMPTIVE_THROTTLE_THRESHOLD",
    "BACKOFF_BASE", "BACKOFF_MAX", "BACKOFF_JITTER",
    "BRAIN_JITTER_MIN", "BRAIN_JITTER_MAX",
    # Delays
    "DELAY_ROLE_MIN", "DELAY_ROLE_MAX", "DELAY_CHANNEL_MIN", "DELAY_CHANNEL_MAX",
    "DELAY_EMOJI_MIN", "DELAY_EMOJI_MAX", "DELAY_STICKER_MIN", "DELAY_STICKER_MAX",
    "DELAY_WEBHOOK_MIN", "DELAY_WEBHOOK_MAX", "DELAY_DELETE_MIN", "DELAY_DELETE_MAX",
    "DELAY_MEMBER_ROLE_MIN", "DELAY_MEMBER_ROLE_MAX", "DELAY_AUTOMOD_MIN", "DELAY_AUTOMOD_MAX",
    "DELAY_INVITE_MIN", "DELAY_INVITE_MAX", "DELAY_SETTINGS_MIN", "DELAY_SETTINGS_MAX",
    "DELAY_RESYNC_MIN", "DELAY_RESYNC_MAX",
    # Batch
    "ROLE_BATCH_SIZE", "ROLE_BATCH_PAUSE", "CHANNEL_BATCH_SIZE", "CHANNEL_BATCH_PAUSE",
    "EMOJI_BATCH_SIZE", "EMOJI_BATCH_PAUSE", "STICKER_BATCH_SIZE", "STICKER_BATCH_PAUSE",
    "MEMBER_BATCH_SIZE", "MEMBER_BATCH_PAUSE",
    # Channel Types
    "CH_TEXT", "CH_VOICE", "CH_CATEGORY", "CH_NEWS", "CH_STAGE", "CH_FORUM",
    "CH_DIRECTORY", "CH_MEDIA", "CH_SKIP_TYPES", "CH_REMAP_TYPES", "CH_ICONS",
    # Channel Settings
    "MAX_TOPIC_TEXT", "MAX_TOPIC_STAGE", "MAX_TOPIC_FORUM",
    "DEFAULT_BITRATE", "MAX_BITRATE_FREE", "MAX_BITRATE_BOOST_1",
    "MAX_BITRATE_BOOST_2", "MAX_BITRATE_BOOST_3",
    "CLONE_FORUM_TAGS", "MAX_FORUM_TAGS", "MAX_FORUM_TAG_NAME_LENGTH",
    "CLONE_STAGE_TOPICS", "CLONE_NSFW", "CLONE_SLOWMODE", "MAX_SLOWMODE",
    "CLONE_CATEGORY_POSITIONS",
    # Role Settings
    "CLONE_ROLE_ICONS", "CLONE_ROLE_EMOJIS", "SYNC_ROLE_HIERARCHY",
    "MAX_ROLE_NAME_LENGTH", "SKIP_MANAGED_ROLES", "FREE_ROLE_EMOJIS",
    # Limits
    "MAX_CHANNELS", "MAX_ROLES", "MAX_EMOJIS_FREE", "MAX_EMOJIS_BOOST",
    "MAX_STICKERS_FREE", "MAX_STICKERS_BOOST", "MAX_WEBHOOKS_PER_CHANNEL",
    "MAX_INVITES_PER_GUILD", "MAX_AUTOMOD_RULES",
    "MAX_ICON_SIZE", "MAX_BANNER_SIZE", "MAX_SPLASH_SIZE",
    "MAX_EMOJI_SIZE", "MAX_STICKER_SIZE", "MAX_ROLE_ICON_SIZE",
    # Error Codes
    "DC_NO_ADMIN", "DC_NO_ACCESS", "DC_LIMIT_ROLES", "DC_LIMIT_EMOJIS",
    "DC_LIMIT_CHANNELS", "DC_LIMIT_STICKERS", "DC_LIMIT_WEBHOOKS",
    "DC_NEEDS_BOOST", "DC_INVALID_FORM", "DC_TOO_MANY_REQUESTS",
    "DC_UNAUTHORIZED", "DC_FORBIDDEN", "DC_NOT_FOUND", "DC_SERVER_ERROR",
    "ERROR_MESSAGES", "ERROR_RETRY_STRATEGY",
    # Proxy & Tokens
    "TOKEN_ROTATION_STRATEGY", "PROXY_ROTATION_ENABLED", "PROXY_ROTATION_MODE",
    "PROXY_TIMEOUT", "PROXY_MAX_FAILURES",
    # Web Server
    "HOST", "PORT", "DEBUG", "SECRET_KEY", "SESSION_LIFETIME",
    "CORS_ALLOWED_ORIGINS", "SECURITY_HEADERS_ENABLED", "CONTENT_SECURITY_POLICY",
    # Logging
    "LOG_LEVEL", "LOG_FORMAT", "LOG_DATE_FORMAT", "LOG_FILE",
    "LOG_MAX_BYTES", "LOG_BACKUP_COUNT", "LOG_ENABLE_JSON",
    "ENABLE_PERFORMANCE_METRICS", "METRICS_INTERVAL",
    # Cloning Strategy
    "CLONE_PURGE_TARGET", "CLONE_ROLES", "CLONE_CHANNELS", "CLONE_EMOJIS",
    "CLONE_STICKERS", "CLONE_SETTINGS", "CLONE_AUTOMOD", "CLONE_WEBHOOKS",
    "CLONE_INVITES", "CLONE_MEMBER_ROLES", "CLONE_RESYNC_PERMISSIONS",
    "CLONE_SKIP_BOTS", "CLONE_ONLY_NON_ADMIN_ROLES", "CLONE_SKIP_MANAGED_ROLES",
    "CLONE_RETRY_ON_ERROR", "CLONE_STOP_ON_CRITICAL", "CLONE_SKIP_ON_LIMIT",
    # Helper Functions
    "get_delay", "get_batch_config", "is_feature_enabled",
    "get_error_strategy", "get_max_bitrate", "get_api_url",
    "validate_config",
]