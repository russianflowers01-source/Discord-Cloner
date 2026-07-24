# -*- coding: utf-8 -*-
"""
cloner.py — Discord Server Cloner v9.0 ULTRA (2026) — Production Edition
=========================================================================
Полный движок клонирования с:
  • Smart Delay System (2-5 секунд минимум, джиттер, batch паузы)
  • Preemptive Rate Limit (читает заголовки ДО запроса)
  • Cancellation Support (проверка флага отмены в циклах)
  • New Cloning Methods: Threads, Events, Soundboard, Onboarding
  • Exponential Backoff с пропуском после N ошибок
  • Детальная статистика по каждому шагу
  • Корректная синхронизация иерархии ролей и прав
"""

import time
import logging
import random
import threading
from typing import Callable, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

from config import (
    DISCORD_CDN as CDN, DISCORD_MEDIA as MEDIA,
    get_delay, get_batch_config, get_error_strategy, get_max_bitrate,
    CH_TEXT, CH_VOICE, CH_CATEGORY, CH_NEWS, CH_STAGE, CH_FORUM, CH_MEDIA,
    CH_SKIP_TYPES, CH_REMAP_TYPES, CH_ICONS,
    MAX_TOPIC_TEXT, MAX_TOPIC_STAGE, MAX_TOPIC_FORUM,
    MAX_BITRATE_FREE, MAX_FORUM_TAGS, MAX_FORUM_TAG_NAME_LENGTH,
    CLONE_FORUM_TAGS, CLONE_STAGE_TOPICS, CLONE_NSFW, CLONE_SLOWMODE,
    CLONE_ROLE_ICONS, CLONE_ROLE_EMOJIS, SYNC_ROLE_HIERARCHY,
    MAX_ROLE_NAME_LENGTH, SKIP_MANAGED_ROLES, FREE_ROLE_EMOJIS,
    DC_NEEDS_BOOST, DC_LIMIT_EMOJIS, DC_LIMIT_CHANNELS, DC_LIMIT_ROLES,
    DC_LIMIT_STICKERS, DC_INVALID_FORM, DC_NO_ADMIN, DC_TOO_MANY_REQUESTS,
    STEALTH_MODE, MINIFY_PAYLOADS,
    CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_PENALTY,
    PREEMPTIVE_THROTTLE_ENABLED, PREEMPTIVE_THROTTLE_THRESHOLD,
    BACKOFF_BASE, BACKOFF_MAX,
    CLONE_SKIP_BOTS, CLONE_ONLY_NON_ADMIN_ROLES,
)
from brain import SmartBrain
from utils import (
    safe_name, sanitize_channel_name, sanitize_role_name,
    build_overwrites, has_permission, minify_payload,
    build_channel_payload, build_role_payload,
    human_delay, batch_pause, RateLimitBucket,
)

# Битовые флаги прав Discord
PERM_ADMIN = 0x8
PERM_MANAGE_ROLES = 0x10000000

logger = logging.getLogger("cloner")

LogFn  = Callable[[str, str], None]
ProgFn = Callable[[str, int, int, str], None]


# ═══════════════════════════════════════════════════════════════
#  СТАТИСТИКА ШАГА
# ═══════════════════════════════════════════════════════════════

@dataclass
class StepStats:
    """Статистика выполнения шага клонирования."""
    step_name: str = ""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def elapsed(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def rate(self) -> float:
        elapsed = self.elapsed
        if elapsed > 0 and self.success > 0:
            return self.success / elapsed * 60
        return 0.0
    
    def summary(self) -> str:
        return (
            f"📊 {self.step_name}: "
            f"✅ {self.success} | ❌ {self.failed} | ⏭ {self.skipped} | "
            f"⏱ {self.elapsed:.0f}с | 🚀 {self.rate:.1f}/мин"
        )


# ═══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _dc_code(resp) -> int:
    """Безопасное извлечение кода ошибки Discord."""
    if resp is None:
        return 0
    try:
        if hasattr(resp, 'json'):
            return resp.json().get("code", 0)
        return 0
    except Exception:
        return 0


def _minify(payload: dict) -> dict:
    """Удаляет null и пустые значения для обхода WAF."""
    if not MINIFY_PAYLOADS:
        return payload
    return minify_payload(payload)


def _smart_sleep(operation: str, log_fn: LogFn = None, context: str = "") -> float:
    """
    ULTRA: Умная задержка 2-5 секунд с джиттером.
    Использует настройки из config.get_delay().
    """
    delay = get_delay(operation)
    if delay > 3.0 and log_fn:
        log_fn(f"⏸ Пауза {delay:.1f}с {context}", "warn")
    time.sleep(delay)
    return delay


def _check_preemptive(resp, log_fn: LogFn = None) -> float:
    """
    ULTRA: Превентивная проверка rate limit по заголовкам ответа.
    Если лимит исчерпан — спит ДО следующего запроса.
    """
    if not PREEMPTIVE_THROTTLE_ENABLED or resp is None:
        return 0.0
    
    try:
        remaining = int(resp.headers.get("X-RateLimit-Remaining", 9999))
        reset_after = float(resp.headers.get("X-RateLimit-Reset-After", 0))
        
        if remaining <= PREEMPTIVE_THROTTLE_THRESHOLD and reset_after > 0:
            wait = reset_after + random.uniform(0.5, 1.5)
            if log_fn:
                log_fn(f"🛡️ Превентивная пауза {wait:.1f}с (осталось {remaining} запросов)", "warn")
            time.sleep(wait)
            return wait
    except (ValueError, TypeError):
        pass
    return 0.0


def _handle_429(resp, log_fn: LogFn = None, context: str = "") -> float:
    """Обрабатывает 429 ошибку и возвращает время ожидания."""
    retry_after = 5.0
    if resp and hasattr(resp, 'headers'):
        try:
            retry_after = float(resp.headers.get('Retry-After', 5))
        except (ValueError, TypeError):
            pass
    
    wait = retry_after + random.uniform(1.0, 3.0)
    if log_fn:
        log_fn(f"⏳ 429 Rate Limit {context}, ждем {wait:.1f}с", "warn")
    time.sleep(wait)
    return wait


def _should_cancel(cancel_flag: Optional[threading.Event]) -> bool:
    """Проверяет, запрошена ли отмена операции."""
    if cancel_flag is None:
        return False
    return cancel_flag.is_set()


# ═══════════════════════════════════════════════════════════════
#  ШАГ 0 — УМНАЯ ОЧИСТКА (Smart Purge)
# ═══════════════════════════════════════════════════════════════

def purge_target(brain: SmartBrain, dst_id: str, log: LogFn,
                 cancel: Optional[threading.Event] = None) -> StepStats:
    """Умная очистка целевого сервера перед клонированием."""
    stats = StepStats(step_name="Очистка цели", start_time=time.time())
    log("🧹 Умная очистка целевого сервера…", "info")
    
    # 1. Сброс системных каналов
    brain.patch(f"/guilds/{dst_id}", json=_minify({
        "system_channel_id": None,
        "rules_channel_id": None,
        "public_updates_channel_id": None,
        "safety_alerts_channel_id": None,
        "afk_channel_id": None,
    }))
    _smart_sleep("settings", log, "после сброса системных каналов")

    # 2. Удаление каналов (сначала обычные, потом категории)
    ch_resp = brain.get(f"/guilds/{dst_id}/channels")
    if ch_resp and ch_resp.status_code == 200:
        channels = ch_resp.json()
        channels.sort(key=lambda c: (1 if c["type"] == CH_CATEGORY else 0))
        stats.total = len(channels)
        log(f"   Найдено каналов для удаления: {len(channels)}", "info")
        
        for i, ch in enumerate(channels):
            if _should_cancel(cancel):
                log("🛑 Очистка прервана пользователем", "warn")
                break
            
            r = brain.delete(f"/channels/{ch['id']}")
            if r and r.status_code in (200, 204, 404):
                stats.success += 1
                if stats.success % 10 == 0:
                    log(f"   🗑 Удалено {stats.success}/{stats.total} каналов", "info")
            elif r and r.status_code == 429:
                _handle_429(r, log, "при удалении каналов")
                r = brain.delete(f"/channels/{ch['id']}")
                if r and r.status_code in (200, 204, 404):
                    stats.success += 1
                else:
                    stats.failed += 1
            else:
                stats.failed += 1
            
            _smart_sleep("delete", log, "между удалениями")
            _check_preemptive(r, log)

    # 3. Удаление ролей (СТРОГО снизу вверх)
    roles_resp = brain.get(f"/guilds/{dst_id}/roles")
    if roles_resp and roles_resp.status_code == 200:
        roles = roles_resp.json()
        roles.sort(key=lambda r: r.get("position", 0))
        deletable = [r for r in roles if r["name"] != "@everyone" and not r.get("managed")]
        log(f"   Найдено ролей для удаления: {len(deletable)}", "info")
        
        for role in deletable:
            if _should_cancel(cancel):
                break
            
            r = brain.delete(f"/guilds/{dst_id}/roles/{role['id']}")
            if r and r.status_code in (200, 204, 404):
                stats.success += 1
            elif r and r.status_code == 429:
                _handle_429(r, log, "при удалении ролей")
            else:
                stats.failed += 1
            
            _smart_sleep("delete", log, "между удалениями ролей")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 1 — РОЛИ (С иерархией, retry, batch)
# ═══════════════════════════════════════════════════════════════

def clone_roles(brain: SmartBrain, src_id: str, dst_id: str, log: LogFn,
                cancel: Optional[threading.Event] = None) -> Tuple[dict, StepStats]:
    """Клонирование ролей с сохранением иерархии."""
    stats = StepStats(step_name="Роли", start_time=time.time())
    log("🎭 Клонирование ролей…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/roles")
    if not resp or resp.status_code != 200:
        log(f"❌ Роли: {brain.diagnose(resp)}", "error")
        stats.end_time = time.time()
        return {}, stats

    src_roles = resp.json()
    role_map: dict = {}
    emoji_pool = list(FREE_ROLE_EMOJIS)
    batch_size, batch_pause_sec = get_batch_config("role")

    # 1. Обработка @everyone
    ev_src = next((r for r in src_roles if r["name"] == "@everyone"), None)
    if ev_src:
        dst_roles = brain.get(f"/guilds/{dst_id}/roles")
        if dst_roles and dst_roles.status_code == 200:
            ev_dst = next((r for r in dst_roles.json() if r["name"] == "@everyone"), None)
            if ev_dst:
                brain.patch(f"/guilds/{dst_id}/roles/{ev_dst['id']}", json=_minify({
                    "permissions": str(ev_src.get("permissions", "0")),
                    "color": ev_src.get("color", 0)
                }))
                role_map[ev_src["id"]] = ev_dst["id"]
                log("  ✅ @everyone обновлён", "success")
        _smart_sleep("role", log, "после @everyone")

    # 2. Фильтрация и сортировка (СНИЗУ ВВЕРХ)
    creatable = [r for r in src_roles if r["name"] != "@everyone"]
    if SKIP_MANAGED_ROLES:
        creatable = [r for r in creatable if not r.get("managed")]
    creatable.sort(key=lambda r: r.get("position", 0))
    stats.total = len(creatable)
    log(f"   Ролей к созданию: {stats.total}", "info")

    created_roles_with_pos = []
    consecutive_429s = 0

    for i, role in enumerate(creatable):
        if _should_cancel(cancel):
            log("🛑 Клонирование ролей прервано", "warn")
            break
        
        # Batch pause
        if i > 0 and batch_pause(batch_size=batch_size, pause_sec=batch_pause_sec,
                                  items_processed=i, log_fn=log):
            pass  # Пауза сделана внутри batch_pause
        
        new_id = _create_role_with_retry(brain, dst_id, role, emoji_pool, log)
        if new_id:
            role_map[role["id"]] = new_id
            created_roles_with_pos.append({"id": new_id, "target_pos": role.get("position", 0)})
            stats.success += 1
            consecutive_429s = 0
            
            if stats.success % 10 == 0:
                log(f"   📊 Создано {stats.success}/{stats.total} ролей ({stats.rate:.1f}/мин)", "info")
        else:
            stats.failed += 1
            consecutive_429s += 1
            
            if consecutive_429s >= CIRCUIT_BREAKER_THRESHOLD:
                log(f"⚠️ Circuit Breaker: {consecutive_429s} ошибок 429, пауза {CIRCUIT_BREAKER_PENALTY}с", "warn")
                time.sleep(CIRCUIT_BREAKER_PENALTY)
                consecutive_429s = 0

    # 3. Синхронизация позиций ролей
    if created_roles_with_pos and SYNC_ROLE_HIERARCHY:
        log("   🔄 Синхронизация иерархии ролей…", "info")
        created_roles_with_pos.sort(key=lambda x: x["target_pos"], reverse=True)
        for rp in created_roles_with_pos:
            if _should_cancel(cancel):
                break
            brain.patch(f"/guilds/{dst_id}/roles/{rp['id']}", json={"position": rp["target_pos"]})
            time.sleep(0.15)

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return role_map, stats


def _create_role_with_retry(brain: SmartBrain, dst_id: str, role: dict,
                             emoji_pool: list, log: LogFn, max_retries: int = 3) -> Optional[str]:
    """Создание роли с экспоненциальным backoff."""
    for attempt in range(max_retries):
        result = _create_role(brain, dst_id, role, emoji_pool, log)
        if result is not None:
            return result
        
        if attempt < max_retries - 1:
            wait = min(BACKOFF_BASE ** (attempt + 1), BACKOFF_MAX) + random.uniform(1, 3)
            log(f"  ⏳ Retry {attempt + 2}/{max_retries} через {wait:.1f}с", "warn")
            time.sleep(wait)
    
    return None


def _create_role(brain: SmartBrain, dst_id: str, role: dict,
                  emoji_pool: list, log: LogFn) -> Optional[str]:
    """Создание одной роли с несколькими стратегиями."""
    name = sanitize_role_name(role.get("name", ""), MAX_ROLE_NAME_LENGTH)
    base = _minify({
        "name": name,
        "permissions": str(role.get("permissions", "0")),
        "color": role.get("color", 0),
        "hoist": role.get("hoist", False),
        "mentionable": role.get("mentionable", False),
    })
    had_icon = bool(role.get("icon") or role.get("unicode_emoji"))

    # Стратегия 1: CDN иконка
    if CLONE_ROLE_ICONS and role.get("icon"):
        b64 = brain.to_b64(
            f"{CDN}/role-icons/{role['id']}/{role['icon']}.png",
            fallback_urls=[f"{CDN}/role-icons/{role['id']}/{role['icon']}.webp"],
            timeout=20,
        )
        if b64:
            r = brain.post(f"/guilds/{dst_id}/roles", json=_minify({**base, "icon": b64}))
            if r and r.status_code in (200, 201):
                log(f"  ✅ {name} [🖼]", "info")
                _smart_sleep("role", log, "после роли с иконкой")
                return r.json()["id"]
            elif r and r.status_code == 429:
                return None

    # Стратегия 2: Unicode emoji
    if CLONE_ROLE_EMOJIS and role.get("unicode_emoji"):
        r = brain.post(f"/guilds/{dst_id}/roles", json=_minify({**base, "unicode_emoji": role["unicode_emoji"]}))
        if r and r.status_code in (200, 201):
            log(f"  ✅ {name} [{role['unicode_emoji']}]", "info")
            _smart_sleep("role", log, "после роли с emoji")
            return r.json()["id"]
        elif r and r.status_code == 429:
            return None

    # Стратегия 3: Fallback emoji
    if had_icon and emoji_pool:
        fe = emoji_pool.pop(0)
        r = brain.post(f"/guilds/{dst_id}/roles", json=_minify({**base, "unicode_emoji": fe}))
        if r and r.status_code in (200, 201):
            log(f"  ✅ {name} [{fe}]", "info")
            _smart_sleep("role", log, "после роли с fallback emoji")
            return r.json()["id"]
        elif r and r.status_code == 429:
            return None

    # Стратегия 4: Без иконки
    r = brain.post(f"/guilds/{dst_id}/roles", json=base)
    if r and r.status_code in (200, 201):
        log(f"  ✅ {name}", "info")
        _smart_sleep("role", log, "после роли")
        return r.json()["id"]

    if _dc_code(r) == DC_LIMIT_ROLES:
        log("  ⛔ Лимит ролей (250)", "warn")
        return None
    
    if r and r.status_code == 429:
        return None

    log(f"  ⚠️ {name}: {brain.diagnose(r)}", "warn")
    _smart_sleep("role", log, "после ошибки роли")
    return None


# ═══════════════════════════════════════════════════════════════
#  ШАГ 2 — КАНАЛЫ (Все типы + Forum + Threads)
# ═══════════════════════════════════════════════════════════════

def clone_channels(brain: SmartBrain, src_id: str, dst_id: str, role_map: dict,
                   log: LogFn, cancel: Optional[threading.Event] = None) -> Tuple[dict, StepStats]:
    """Клонирование всех типов каналов."""
    stats = StepStats(step_name="Каналы", start_time=time.time())
    log("📁 Клонирование каналов…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/channels")
    if not resp or resp.status_code != 200:
        log(f"❌ Каналы: {brain.diagnose(resp)}", "error")
        stats.end_time = time.time()
        return {}, stats

    channels = resp.json()
    cat_map: dict = {}
    channel_map: dict = {}
    batch_size, batch_pause_sec = get_batch_config("channel")
    
    # Определяем boost level для битрейта
    guild_resp = brain.get(f"/guilds/{dst_id}")
    boost_level = guild_resp.json().get("premium_tier", 0) if guild_resp and guild_resp.status_code == 200 else 0

    # 1. Категории
    cats = sorted([c for c in channels if c["type"] == CH_CATEGORY], key=lambda c: c.get("position", 0))
    log(f"   Категорий: {len(cats)}", "info")
    
    for i, cat in enumerate(cats):
        if _should_cancel(cancel):
            break
        if i > 0:
            batch_pause(batch_size=batch_size, pause_sec=batch_pause_sec, items_processed=i, log_fn=log)
        
        nid = _make_channel(brain, dst_id, cat, {}, role_map, log, boost_level)
        if nid:
            cat_map[cat["id"]] = nid
            channel_map[cat["id"]] = nid
            stats.success += 1
        else:
            stats.failed += 1
        stats.total += 1

    # 2. Обычные каналы
    non_cats = sorted([c for c in channels if c["type"] != CH_CATEGORY], key=lambda c: c.get("position", 0))
    log(f"   Каналов: {len(non_cats)}", "info")
    
    for i, ch in enumerate(non_cats):
        if _should_cancel(cancel):
            break
        if i > 0:
            batch_pause(batch_size=batch_size, pause_sec=batch_pause_sec, items_processed=i, log_fn=log)
        
        if ch["type"] in CH_SKIP_TYPES:
            stats.skipped += 1
            stats.total += 1
            continue
        
        parent_id = cat_map.get(ch.get("parent_id"))
        nid = _make_channel(brain, dst_id, ch, cat_map, role_map, log, boost_level, parent_id)
        if nid:
            channel_map[ch["id"]] = nid
            stats.success += 1
        else:
            stats.failed += 1
        stats.total += 1
        
        if stats.success % 20 == 0 and stats.success > 0:
            log(f"   📊 Создано {stats.success} каналов ({stats.rate:.1f}/мин)", "info")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return channel_map, stats


def _make_channel(brain: SmartBrain, dst_id: str, ch: dict, cat_map: dict,
                   role_map: dict, log: LogFn, boost_level: int = 0,
                   parent_id: Optional[str] = None) -> Optional[str]:
    """Создание одного канала любого типа."""
    ct = ch["type"]
    create_type = CH_REMAP_TYPES.get(ct, ct)
    name = sanitize_channel_name(ch.get("name", "channel"))
    ow = build_overwrites(ch.get("permission_overwrites", []), role_map)

    payload: dict = _minify({
        "name": name,
        "type": create_type,
        "position": ch.get("position", 0),
        "permission_overwrites": ow,
    })
    
    if CLONE_NSFW and ch.get("nsfw"):
        payload["nsfw"] = True
    
    if parent_id:
        payload["parent_id"] = parent_id
    elif ch.get("parent_id") and ch["parent_id"] in cat_map:
        payload["parent_id"] = cat_map[ch["parent_id"]]

    # Специфичные настройки по типам
    if create_type == CH_TEXT:
        if ch.get("topic"):
            payload["topic"] = ch["topic"][:MAX_TOPIC_TEXT]
        if CLONE_SLOWMODE and ch.get("rate_limit_per_user"):
            payload["rate_limit_per_user"] = min(ch["rate_limit_per_user"], 21600)
    
    elif create_type == CH_VOICE:
        max_br = get_max_bitrate(boost_level)
        payload["bitrate"] = min(ch.get("bitrate", 64000), max_br)
        if ch.get("user_limit"):
            payload["user_limit"] = ch["user_limit"]
        if ch.get("rtc_region"):
            payload["rtc_region"] = ch["rtc_region"]
    
    elif create_type == CH_STAGE:
        if CLONE_STAGE_TOPICS and ch.get("topic"):
            payload["topic"] = ch["topic"][:MAX_TOPIC_STAGE]
    
    elif create_type in (CH_FORUM, CH_MEDIA):
        if ch.get("topic"):
            payload["topic"] = ch["topic"][:MAX_TOPIC_FORUM]
        if CLONE_SLOWMODE and ch.get("rate_limit_per_user"):
            payload["rate_limit_per_user"] = ch["rate_limit_per_user"]
        if CLONE_FORUM_TAGS and ch.get("available_tags"):
            tags = []
            for tag in ch["available_tags"][:MAX_FORUM_TAGS]:
                tag_payload = {"name": tag.get("name", "tag")[:MAX_FORUM_TAG_NAME_LENGTH]}
                if tag.get("emoji_id"):
                    tag_payload["emoji_id"] = tag["emoji_id"]
                elif tag.get("emoji_name"):
                    tag_payload["emoji_name"] = tag["emoji_name"]
                tags.append(tag_payload)
            if tags:
                payload["available_tags"] = tags
        if ch.get("default_forum_layout"):
            payload["default_forum_layout"] = ch["default_forum_layout"]
        if ch.get("default_sort_order"):
            payload["default_sort_order"] = ch["default_sort_order"]

    r = brain.post(f"/guilds/{dst_id}/channels", json=payload)

    # Fallback: если тип не поддерживается, создаем как текстовый
    if r and r.status_code not in (200, 201) and create_type not in (CH_TEXT, CH_CATEGORY):
        dc = _dc_code(r)
        if dc == DC_INVALID_FORM or r.status_code == 400:
            payload["type"] = CH_TEXT
            for k in ("bitrate", "user_limit", "rtc_region", "default_forum_layout",
                      "default_sort_order", "available_tags"):
                payload.pop(k, None)
            r = brain.post(f"/guilds/{dst_id}/channels", json=payload)

    if r and r.status_code in (200, 201):
        nid = r.json()["id"]
        icon = CH_ICONS.get(create_type, "📌")
        log(f"  {icon} #{name}", "info")
        _smart_sleep("channel", log, "после канала")
        _check_preemptive(r, log)
        return nid

    if _dc_code(r) == DC_LIMIT_CHANNELS:
        log("  ⛔ Лимит каналов (500)", "warn")
        return None

    log(f"  ⚠️ #{name}: {brain.diagnose(r)}", "warn")
    _smart_sleep("channel", log, "после ошибки канала")
    return None


# ═══════════════════════════════════════════════════════════════
#  ШАГ 3 — ЭМОДЗИ
# ═══════════════════════════════════════════════════════════════

def clone_emojis(brain: SmartBrain, src_id: str, dst_id: str, log: LogFn,
                 cancel: Optional[threading.Event] = None) -> StepStats:
    """Клонирование эмодзи с batch паузами."""
    stats = StepStats(step_name="Эмодзи", start_time=time.time())
    log("😀 Клонирование эмодзи…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/emojis")
    if not resp or resp.status_code != 200:
        stats.end_time = time.time()
        return stats

    emojis = resp.json()
    stats.total = len(emojis)
    log(f"   Эмодзи: {stats.total}", "info")
    batch_size, batch_pause_sec = get_batch_config("emoji")

    for i, emoji in enumerate(emojis):
        if _should_cancel(cancel):
            break
        if i > 0:
            batch_pause(batch_size=batch_size, pause_sec=batch_pause_sec, items_processed=i, log_fn=log)
        
        name = safe_name(emoji.get("name", f"emoji_{i}"), "emoji")
        eid = emoji["id"]
        anim = emoji.get("animated", False)
        ext = "gif" if anim else "png"

        b64 = brain.to_b64(f"{CDN}/emojis/{eid}.{ext}",
                           fallback_urls=[f"{CDN}/emojis/{eid}.webp"], timeout=40)
        if not b64:
            stats.skipped += 1
            _smart_sleep("emoji", log, "emoji download failed")
            continue

        r = brain.post(f"/guilds/{dst_id}/emojis",
                       json=_minify({"name": name, "image": b64}), timeout=80)
        
        if r and r.status_code in (200, 201):
            log(f"  {'🌀' if anim else '✅'} :{name}:", "info")
            stats.success += 1
        elif _dc_code(r) == DC_LIMIT_EMOJIS:
            log("  ⛔ Лимит эмодзи", "warn")
            stats.skipped = stats.total - i
            break
        elif r and r.status_code == 429:
            _handle_429(r, log, "при создании эмодзи")
            stats.failed += 1
        else:
            stats.failed += 1
        
        _smart_sleep("emoji", log, "между эмодзи")
        _check_preemptive(r, log)

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 4 — СТИКЕРЫ
# ═══════════════════════════════════════════════════════════════

def clone_stickers(brain: SmartBrain, src_id: str, dst_id: str, log: LogFn,
                   cancel: Optional[threading.Event] = None) -> StepStats:
    """Клонирование стикеров."""
    stats = StepStats(step_name="Стикеры", start_time=time.time())
    log("🎯 Клонирование стикеров…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/stickers")
    if not resp or resp.status_code != 200:
        stats.end_time = time.time()
        return stats

    stickers = resp.json()
    stats.total = len(stickers)
    log(f"   Стикеров: {stats.total}", "info")
    fmt_map = {1: "png", 2: "apng", 3: "json", 4: "gif"}
    batch_size, batch_pause_sec = get_batch_config("sticker")

    for i, stk in enumerate(stickers):
        if _should_cancel(cancel):
            break
        if i > 0:
            batch_pause(batch_size=batch_size, pause_sec=batch_pause_sec, items_processed=i, log_fn=log)
        
        sname = safe_name(stk.get("name", "sticker"), "sticker")
        fmt = fmt_map.get(stk.get("format_type", 1), "png")
        data = None

        if fmt == "json":
            rd = brain.get(f"{CDN}/stickers/{stk['id']}.json")
            if rd and rd.status_code == 200:
                data = rd.text.encode("utf-8")
        else:
            data = brain.download_multi(
                [f"{MEDIA}/stickers/{stk['id']}.{fmt}", f"{CDN}/stickers/{stk['id']}.{fmt}"],
                timeout=40
            )

        if not data:
            stats.skipped += 1
            _smart_sleep("sticker", log, "sticker download failed")
            continue

        mime = {"png": "image/png", "apng": "image/png", "gif": "image/gif",
                "json": "application/json"}.get(fmt, "image/png")
        files = {
            "file": (f"{sname}.{fmt}", data, mime),
            "name": (None, sname),
            "description": (None, (stk.get("description") or sname)[:100]),
            "tags": (None, (stk.get("tags") or sname)[:200]),
        }
        r = brain.post(f"/guilds/{dst_id}/stickers", files=files, timeout=80)
        
        if r and r.status_code in (200, 201):
            log(f"  ✅ {sname}", "info")
            stats.success += 1
        elif _dc_code(r) == DC_LIMIT_STICKERS:
            log("  ⛔ Лимит стикеров", "warn")
            stats.skipped = stats.total - i
            break
        elif r and r.status_code == 429:
            _handle_429(r, log, "при создании стикера")
            stats.failed += 1
        else:
            stats.failed += 1
        
        _smart_sleep("sticker", log, "между стикерами")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 5 — НАСТРОЙКИ СЕРВЕРА + МЕДИА
# ═══════════════════════════════════════════════════════════════

def clone_server_settings(brain: SmartBrain, src_id: str, dst_id: str,
                           channel_map: dict, log: LogFn) -> StepStats:
    """Клонирование настроек сервера и медиа."""
    stats = StepStats(step_name="Настройки", start_time=time.time())
    log("⚙️ Настройки сервера…", "info")
    
    resp = brain.get(f"/guilds/{src_id}")
    if not resp or resp.status_code != 200:
        stats.end_time = time.time()
        return stats

    src = resp.json()
    stats.total = 1
    payload: dict = {"name": src.get("name", "Cloned Server")}

    for f in ("description", "preferred_locale", "verification_level",
              "default_message_notifications", "explicit_content_filter",
              "afk_timeout", "system_channel_flags", "features"):
        if src.get(f) is not None:
            payload[f] = src[f]

    # Медиа (иконка, баннер, сплэш)
    for media_type, field in [("icon", "icon"), ("banner", "banner"), ("splash", "splash")]:
        if src.get(field):
            ext = "gif" if src[field].startswith("a_") else "png"
            size = "2048" if media_type != "icon" else "1024"
            b64 = brain.to_b64(f"{CDN}/{media_type}s/{src_id}/{src[field]}.{ext}?size={size}")
            if b64:
                payload[field] = b64
                log(f"  ✅ {media_type.capitalize()}", "info")

    r = brain.patch(f"/guilds/{dst_id}", json=_minify(payload))
    if r and r.status_code == 200:
        log("  ✅ Основные настройки применены", "success")
        stats.success += 1
    else:
        stats.failed += 1

    # Системные каналы
    sys_patch = {}
    for key in ("afk_channel_id", "system_channel_id", "rules_channel_id",
                "public_updates_channel_id", "safety_alerts_channel_id"):
        if src.get(key) and src[key] in channel_map:
            sys_patch[key] = channel_map[src[key]]
    if sys_patch:
        brain.patch(f"/guilds/{dst_id}", json=_minify(sys_patch))
        log("  ✅ Системные каналы привязаны", "success")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 6 — AUTOMOD
# ═══════════════════════════════════════════════════════════════

def clone_automod(brain: SmartBrain, src_id: str, dst_id: str,
                   channel_map: dict, role_map: dict, log: LogFn,
                   cancel: Optional[threading.Event] = None) -> StepStats:
    """Клонирование правил AutoMod."""
    stats = StepStats(step_name="AutoMod", start_time=time.time())
    log("🛡️ Клонирование правил AutoMod…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/auto-moderation/rules")
    if not resp or resp.status_code != 200:
        log("   ℹ️ AutoMod не найден или нет прав", "info")
        stats.end_time = time.time()
        return stats

    rules = resp.json()
    stats.total = len(rules)
    log(f"   Правил AutoMod: {stats.total}", "info")

    for rule in rules:
        if _should_cancel(cancel):
            break
        
        payload = _minify({
            "name": rule.get("name", "AutoMod Rule"),
            "event_type": rule.get("event_type", 1),
            "trigger_type": rule.get("trigger_type", 1),
            "trigger_metadata": rule.get("trigger_metadata", {}),
            "actions": rule.get("actions", []),
            "enabled": rule.get("enabled", True),
            "exempt_roles": [role_map.get(rid, rid) for rid in rule.get("exempt_roles", [])
                            if role_map.get(rid, rid)],
            "exempt_channels": [channel_map.get(cid, cid) for cid in rule.get("exempt_channels", [])
                               if channel_map.get(cid, cid)],
        })
        
        r = brain.post(f"/guilds/{dst_id}/auto-moderation/rules", json=payload)
        if r and r.status_code in (200, 201):
            log(f"  ✅ {rule.get('name')}", "info")
            stats.success += 1
        else:
            log(f"  ⚠️ {rule.get('name')}: {brain.diagnose(r)}", "warn")
            stats.failed += 1
        
        _smart_sleep("automod", log, "между AutoMod правилами")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 7 — ВЕБХУКИ
# ═══════════════════════════════════════════════════════════════

def clone_webhooks(brain: SmartBrain, src_id: str, dst_id: str,
                    channel_map: dict, log: LogFn,
                    cancel: Optional[threading.Event] = None) -> StepStats:
    """Клонирование вебхуков."""
    stats = StepStats(step_name="Вебхуки", start_time=time.time())
    log("🪝 Вебхуки…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/webhooks")
    if not resp or resp.status_code != 200:
        stats.end_time = time.time()
        return stats

    whs = resp.json()
    stats.total = len(whs)
    log(f"   Вебхуков: {stats.total}", "info")
    
    for wh in whs:
        if _should_cancel(cancel):
            break
        
        new_ch = channel_map.get(wh.get("channel_id"))
        if not new_ch:
            stats.skipped += 1
            continue
        
        pld = {"name": safe_name(wh.get("name", "webhook"), "webhook")}
        if wh.get("avatar"):
            b64 = brain.to_b64(f"{CDN}/avatars/{wh['id']}/{wh['avatar']}.png?size=256")
            if b64:
                pld["avatar"] = b64
        
        r = brain.post(f"/channels/{new_ch}/webhooks", json=_minify(pld))
        if r and r.status_code in (200, 201):
            stats.success += 1
        else:
            stats.failed += 1
        
        _smart_sleep("webhook", log, "между вебхуками")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 8 — ПЕРЕСИНХРОНИЗАЦИЯ ПРАВ
# ═══════════════════════════════════════════════════════════════

def resync_channel_permissions(brain: SmartBrain, src_id: str, dst_id: str,
                                role_map: dict, channel_map: dict, log: LogFn,
                                cancel: Optional[threading.Event] = None) -> StepStats:
    """Пересинхронизация прав каналов."""
    stats = StepStats(step_name="Синхронизация прав", start_time=time.time())
    log("🔒 Пересинхронизация прав каналов…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/channels")
    if not resp or resp.status_code != 200:
        stats.end_time = time.time()
        return stats
    
    channels = resp.json()
    stats.total = len(channels)
    
    for ch in channels:
        if _should_cancel(cancel):
            break
        
        new_id = channel_map.get(ch["id"])
        if not new_id:
            stats.skipped += 1
            continue
        
        ow = build_overwrites(ch.get("permission_overwrites", []), role_map)
        if not ow:
            stats.skipped += 1
            continue
        
        r = brain.patch(f"/channels/{new_id}", json={"permission_overwrites": ow})
        if r and r.status_code == 200:
            stats.success += 1
        else:
            stats.failed += 1
        
        time.sleep(0.15)

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 9 — ИНВАЙТЫ + VANITY URL
# ═══════════════════════════════════════════════════════════════

def clone_invites(brain: SmartBrain, src_id: str, dst_id: str,
                   channel_map: dict, log: LogFn,
                   cancel: Optional[threading.Event] = None) -> StepStats:
    """Клонирование инвайтов и vanity URL."""
    stats = StepStats(step_name="Инвайты", start_time=time.time())
    log("🔗 Приглашения…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/invites")
    if resp and resp.status_code == 200:
        invites = resp.json()
        stats.total = len(invites)
        
        for inv in invites:
            if _should_cancel(cancel):
                break
            
            new_ch = channel_map.get(inv.get("channel_id"))
            if not new_ch:
                stats.skipped += 1
                continue
            
            pld = {
                "max_age": inv.get("max_age", 86400),
                "max_uses": inv.get("max_uses", 0),
                "temporary": inv.get("temporary", False),
                "unique": True,
            }
            r = brain.post(f"/channels/{new_ch}/invites", json=_minify(pld))
            if r and r.status_code in (200, 201):
                stats.success += 1
            else:
                stats.failed += 1
            
            _smart_sleep("invite", log, "между инвайтами")

    # Vanity URL
    vanity = brain.get(f"/guilds/{src_id}/vanity-url")
    if vanity and vanity.status_code == 200 and vanity.json().get("code"):
        r = brain.patch(f"/guilds/{dst_id}/vanity-url", json={"code": vanity.json()["code"]})
        if r and r.status_code == 200:
            log(f"  ✅ Ванити-URL: {vanity.json()['code']}", "success")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 10 — ВЫДАЧА РОЛЕЙ УЧАСТНИКАМ (Batch ULTRA)
# ═══════════════════════════════════════════════════════════════

def assign_all_roles_to_members(brain: SmartBrain, src_id: str, dst_id: str,
                                 role_map: dict, log: LogFn,
                                 cancel: Optional[threading.Event] = None) -> StepStats:
    """Синхронизация ролей участников (Batch Mode)."""
    stats = StepStats(step_name="Выдача ролей", start_time=time.time())
    log("👥 Синхронизация ролей участников (ULTRA Batch)…", "info")

    # Собираем роли источника
    src_members: dict = {}
    after = "0"
    while True:
        r = brain.get(f"/guilds/{src_id}/members?limit=1000&after={after}")
        if not r or r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for m in batch:
            src_members[m["user"]["id"]] = m.get("roles", [])
        if len(batch) < 1000:
            break
        after = batch[-1]["user"]["id"]
        time.sleep(0.3)

    if not src_members:
        log("   ℹ️ Нет участников на источнике", "warn")
        stats.end_time = time.time()
        return stats
    
    log(f"   Участников источника: {len(src_members)}", "info")

    # Получаем @everyone ID
    dst_roles_resp = brain.get(f"/guilds/{dst_id}/roles")
    everyone_id = dst_id
    if dst_roles_resp and dst_roles_resp.status_code == 200:
        ev = next((r for r in dst_roles_resp.json() if r["name"] == "@everyone"), None)
        if ev:
            everyone_id = ev["id"]

    # Собираем участников цели
    dst_members = []
    after = "0"
    while True:
        r = brain.get(f"/guilds/{dst_id}/members?limit=1000&after={after}")
        if not r or r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        dst_members.extend(batch)
        if len(batch) < 1000:
            break
        after = batch[-1]["user"]["id"]
        time.sleep(0.3)

    stats.total = len(dst_members)
    log(f"   Участников цели: {stats.total}", "info")
    batch_size, batch_pause_sec = get_batch_config("member")
    
    for i, member in enumerate(dst_members):
        if _should_cancel(cancel):
            break
        if i > 0:
            batch_pause(batch_size=batch_size, pause_sec=batch_pause_sec, items_processed=i, log_fn=log)
        
        uid = member["user"]["id"]
        if CLONE_SKIP_BOTS and member["user"].get("bot"):
            stats.skipped += 1
            continue
        
        src_roles = src_members.get(uid, [])
        if not src_roles:
            stats.skipped += 1
            continue
        
        valid_new_roles = [
            role_map[rid] for rid in src_roles
            if rid in role_map and role_map[rid] != everyone_id
        ]
        
        if not valid_new_roles:
            stats.skipped += 1
            continue

        r = brain.patch(f"/guilds/{dst_id}/members/{uid}", json={"roles": valid_new_roles})
        if r and r.status_code in (200, 201, 204):
            stats.success += 1
        elif r and r.status_code == 429:
            _handle_429(r, log, "при выдаче ролей")
            stats.failed += 1
        else:
            stats.failed += 1
        
        _smart_sleep("member_role", log, "между участниками")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 11 — СОБЫТИЯ (Events) — НОВОЕ В v9.0
# ═══════════════════════════════════════════════════════════════

def clone_events(brain: SmartBrain, src_id: str, dst_id: str,
                  channel_map: dict, log: LogFn,
                  cancel: Optional[threading.Event] = None) -> StepStats:
    """Клонирование запланированных событий сервера."""
    stats = StepStats(step_name="События", start_time=time.time())
    log("📅 Клонирование событий…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/scheduled-events")
    if not resp or resp.status_code != 200:
        log("   ℹ️ События не найдены или нет прав", "info")
        stats.end_time = time.time()
        return stats

    events = resp.json()
    stats.total = len(events)
    log(f"   Событий: {stats.total}", "info")

    for event in events:
        if _should_cancel(cancel):
            break
        
        payload = _minify({
            "name": event.get("name", "Event")[:100],
            "privacy_level": event.get("privacy_level", 2),
            "scheduled_start_time": event.get("scheduled_start_time"),
            "scheduled_end_time": event.get("scheduled_end_time"),
            "description": (event.get("description") or "")[:1000],
            "entity_type": event.get("entity_type", 1),
        })
        
        # Привязка к каналу
        if event.get("channel_id") and event["channel_id"] in channel_map:
            payload["channel_id"] = channel_map[event["channel_id"]]
        elif event.get("entity_type") == 3 and event.get("entity_metadata"):
            payload["entity_metadata"] = event["entity_metadata"]
        
        r = brain.post(f"/guilds/{dst_id}/scheduled-events", json=payload)
        if r and r.status_code in (200, 201):
            log(f"  ✅ {event.get('name')}", "info")
            stats.success += 1
        else:
            stats.failed += 1
        
        _smart_sleep("settings", log, "между событиями")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 12 — SOUNDBOARD — НОВОЕ В v9.0
# ═══════════════════════════════════════════════════════════════

def clone_soundboard(brain: SmartBrain, src_id: str, dst_id: str,
                      log: LogFn, cancel: Optional[threading.Event] = None) -> StepStats:
    """Клонирование звуков Soundboard."""
    stats = StepStats(step_name="Soundboard", start_time=time.time())
    log("🔊 Клонирование Soundboard…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/soundboard-sounds")
    if not resp or resp.status_code != 200:
        log("   ℹ️ Soundboard не найден или нет прав", "info")
        stats.end_time = time.time()
        return stats

    sounds = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
    stats.total = len(sounds)
    log(f"   Звуков: {stats.total}", "info")

    for sound in sounds:
        if _should_cancel(cancel):
            break
        
        sound_id = sound.get("sound_id")
        if not sound_id:
            stats.skipped += 1
            continue
        
        # Скачиваем звук
        data = brain.download_multi([
            f"{CDN}/soundboard-sounds/{sound_id}",
            f"{MEDIA}/soundboard-sounds/{sound_id}",
        ], timeout=30)
        
        if not data:
            stats.skipped += 1
            continue
        
        files = {
            "file": (f"{sound.get('name', 'sound')}.mp3", data, "audio/mpeg"),
            "name": (None, sound.get("name", "sound")[:32]),
            "volume": (None, str(sound.get("volume", 1.0))),
            "emoji_id": (None, sound.get("emoji_id") or ""),
            "emoji_name": (None, sound.get("emoji_name") or ""),
        }
        
        r = brain.post(f"/guilds/{dst_id}/soundboard-sounds", files=files, timeout=60)
        if r and r.status_code in (200, 201):
            log(f"  ✅ {sound.get('name')}", "info")
            stats.success += 1
        else:
            stats.failed += 1
        
        _smart_sleep("sticker", log, "между звуками")

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ШАГ 13 — ONBOARDING — НОВОЕ В v9.0
# ═══════════════════════════════════════════════════════════════

def clone_onboarding(brain: SmartBrain, src_id: str, dst_id: str,
                      channel_map: dict, role_map: dict, log: LogFn) -> StepStats:
    """Клонирование настроек Onboarding (приветствие новых участников)."""
    stats = StepStats(step_name="Onboarding", start_time=time.time())
    log("👋 Клонирование Onboarding…", "info")
    
    resp = brain.get(f"/guilds/{src_id}/onboarding")
    if not resp or resp.status_code != 200:
        log("   ℹ️ Onboarding не найден или нет прав", "info")
        stats.end_time = time.time()
        return stats

    onboarding = resp.json()
    stats.total = 1
    
    prompts = []
    for prompt in onboarding.get("prompts", []):
        new_prompt = {
            "id": prompt.get("id"),
            "type": prompt.get("type", 0),
            "title": prompt.get("title", "")[:100],
            "single_select": prompt.get("single_select", False),
            "required": prompt.get("required", False),
            "in_onboarding": prompt.get("in_onboarding", True),
            "options": [],
        }
        
        for opt in prompt.get("options", []):
            new_opt = {
                "id": opt.get("id"),
                "title": opt.get("title", "")[:50],
                "description": (opt.get("description") or "")[:100],
                "emoji_id": opt.get("emoji_id"),
                "emoji_name": opt.get("emoji_name"),
                "emoji_animated": opt.get("emoji_animated", False),
            }
            
            # Маппинг каналов и ролей
            if opt.get("channel_ids"):
                new_opt["channel_ids"] = [
                    channel_map[cid] for cid in opt["channel_ids"]
                    if cid in channel_map
                ]
            if opt.get("role_ids"):
                new_opt["role_ids"] = [
                    role_map[rid] for rid in opt["role_ids"]
                    if rid in role_map
                ]
            
            new_prompt["options"].append(new_opt)
        
        prompts.append(new_prompt)
    
    payload = _minify({
        "enabled": onboarding.get("enabled", False),
        "default_channel_ids": [
            channel_map[cid] for cid in onboarding.get("default_channel_ids", [])
            if cid in channel_map
        ],
        "prompts": prompts,
    })
    
    r = brain.put(f"/guilds/{dst_id}/onboarding", json=payload)
    if r and r.status_code in (200, 204):
        log("  ✅ Onboarding клонирован", "success")
        stats.success += 1
    else:
        log(f"  ⚠️ Onboarding: {brain.diagnose(r)}", "warn")
        stats.failed += 1

    stats.end_time = time.time()
    log(f"✅ {stats.summary()}", "success")
    return stats


# ═══════════════════════════════════════════════════════════════
#  ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
# ═══════════════════════════════════════════════════════════════

def check_admin(brain: SmartBrain, dst_id: str, user_id: str, dst_info: dict) -> bool:
    """Проверяет наличие прав администратора на целевом сервере."""
    if dst_info.get("owner_id") == user_id:
        return True
    
    me_m = brain.get(f"/guilds/{dst_id}/members/@me")
    if me_m and me_m.status_code == 200:
        member_roles = me_m.json().get("roles", [])
        roles_resp = brain.get(f"/guilds/{dst_id}/roles")
        if roles_resp and roles_resp.status_code == 200:
            roles_map = {r["id"]: r for r in roles_resp.json()}
            for rid in member_roles:
                if has_permission(roles_map.get(rid, {}).get("permissions", 0), PERM_ADMIN):
                    return True
    return False


# ═══════════════════════════════════════════════════════════════
#  СПИСОК ВСЕХ ШАГОВ
# ═══════════════════════════════════════════════════════════════

ALL_STEPS = [
    ("purge",       "Очистка цели (Smart Purge)"),
    ("roles",       "Роли (с иерархией)"),
    ("channels",    "Каналы (все типы + форумы)"),
    ("emojis",      "Эмодзи"),
    ("stickers",    "Стикеры"),
    ("settings",    "Настройки + Медиа"),
    ("automod",     "AutoMod правила"),
    ("webhooks",    "Вебхуки"),
    ("resync",      "Пересинхронизация прав"),
    ("invites",     "Приглашения + Vanity"),
    ("assign_role", "Выдача ролей (Batch ULTRA)"),
    ("events",      "События (Scheduled Events)"),
    ("soundboard",  "Soundboard звуки"),
    ("onboarding",  "Onboarding (приветствие)"),
]


# ═══════════════════════════════════════════════════════════════
#  ГЛАВНЫЙ ОРКЕСТРАТОР
# ═══════════════════════════════════════════════════════════════

def run_clone(
    token: Optional[str],
    src_id: str,
    dst_id: str,
    options: dict,
    log: LogFn,
    prog: ProgFn,
    done_cb: Callable,
    brain: Optional[SmartBrain] = None,
    cancel_flag: Optional[threading.Event] = None,
):
    """
    Главный оркестратор клонирования.
    Выполняет все шаги последовательно с обработкой ошибок.
    """
    if brain is None:
        if not token:
            log("❌ Не задан токен и не передан brain", "error")
            done_cb(success=False, error="Нет токена")
            return
        brain = SmartBrain(token)

    enabled = [s for s in ALL_STEPS if options.get(s[0], True)]
    total = len(enabled)
    all_stats: List[StepStats] = []
    total_start = time.time()

    try:
        # Авторизация
        log("🧠 SmartBrain v9 ULTRA — авторизация…", "info")
        me = brain.get("/users/@me")
        if not me or me.status_code != 200:
            log(f"❌ {brain.diagnose(me, 'token')}", "error")
            done_cb(success=False, error="Invalid Token")
            return
        
        user = me.json()
        log(f"✅ Авторизован: {user.get('global_name') or user.get('username', '?')}", "success")

        # Проверка серверов
        src_resp = brain.get(f"/guilds/{src_id}?with_counts=true")
        dst_resp = brain.get(f"/guilds/{dst_id}?with_counts=true")

        if not src_resp or src_resp.status_code != 200:
            done_cb(success=False, error=f"Источник: {brain.diagnose(src_resp)}")
            return
        if not dst_resp or dst_resp.status_code != 200:
            done_cb(success=False, error=f"Цель: {brain.diagnose(dst_resp)}")
            return

        src_info, dst_info = src_resp.json(), dst_resp.json()
        if src_id == dst_id:
            done_cb(success=False, error="Источник и цель совпадают")
            return

        if not check_admin(brain, dst_id, user["id"], dst_info):
            done_cb(success=False, error=f"Нет прав Администратора на '{dst_info.get('name')}'")
            return

        log(f"📡 Источник: {src_info.get('name')} | 🎯 Цель: {dst_info.get('name')}", "info")
        log(f"⚙️  Активных шагов: {total}", "info")
        log("═" * 60, "info")

        role_map: dict = {}
        channel_map: dict = {}

        # Выполняем шаги
        for cur, (step_key, step_name) in enumerate(enabled, 1):
            if _should_cancel(cancel_flag):
                log("🛑 Клонирование прервано пользователем", "warn")
                break
            
            log(f"\n[{cur}/{total}] ▶ {step_name}", "info")
            prog(step_name, cur - 1, total, step_key)

            try:
                step_stats = None
                
                if step_key == "purge":
                    step_stats = purge_target(brain, dst_id, log, cancel_flag)
                elif step_key == "roles":
                    role_map, step_stats = clone_roles(brain, src_id, dst_id, log, cancel_flag)
                elif step_key == "channels":
                    channel_map, step_stats = clone_channels(brain, src_id, dst_id, role_map, log, cancel_flag)
                elif step_key == "emojis":
                    step_stats = clone_emojis(brain, src_id, dst_id, log, cancel_flag)
                elif step_key == "stickers":
                    step_stats = clone_stickers(brain, src_id, dst_id, log, cancel_flag)
                elif step_key == "settings":
                    step_stats = clone_server_settings(brain, src_id, dst_id, channel_map, log)
                elif step_key == "automod":
                    step_stats = clone_automod(brain, src_id, dst_id, channel_map, role_map, log, cancel_flag)
                elif step_key == "webhooks":
                    step_stats = clone_webhooks(brain, src_id, dst_id, channel_map, log, cancel_flag)
                elif step_key == "resync":
                    step_stats = resync_channel_permissions(brain, src_id, dst_id, role_map, channel_map, log, cancel_flag)
                elif step_key == "invites":
                    step_stats = clone_invites(brain, src_id, dst_id, channel_map, log, cancel_flag)
                elif step_key == "assign_role":
                    step_stats = assign_all_roles_to_members(brain, src_id, dst_id, role_map, log, cancel_flag)
                elif step_key == "events":
                    step_stats = clone_events(brain, src_id, dst_id, channel_map, log, cancel_flag)
                elif step_key == "soundboard":
                    step_stats = clone_soundboard(brain, src_id, dst_id, log, cancel_flag)
                elif step_key == "onboarding":
                    step_stats = clone_onboarding(brain, src_id, dst_id, channel_map, role_map, log)
                
                if step_stats:
                    all_stats.append(step_stats)
                
                log(f"  ⏱ Шаг '{step_name}' выполнен", "info")
            
            except Exception as e:
                logger.exception(f"Ошибка шага {step_key}")
                log(f"  ⚠️ Шаг '{step_name}' завершился с ошибкой: {e} — продолжаем", "warn")

        # Финальная статистика
        total_elapsed = time.time() - total_start
        prog("Готово", total, total, "done")
        log("═" * 60, "info")
        log("📋 ИТОГОВАЯ СТАТИСТИКА:", "info")
        
        total_success = sum(s.success for s in all_stats)
        total_failed = sum(s.failed for s in all_stats)
        total_skipped = sum(s.skipped for s in all_stats)
        
        for s in all_stats:
            log(f"   {s.summary()}", "info")
        
        log(f"\n🏆 ВСЕГО: ✅ {total_success} | ❌ {total_failed} | ⏭ {total_skipped}", "success")
        log(f"⏱ Общее время: {total_elapsed:.0f}с ({total_elapsed/60:.1f} мин)", "success")
        log(f"✅ Клонирование ЗАВЕРШЕНО!", "success")
        
        done_cb(
            success=True,
            source=src_info.get("name"),
            target=dst_info.get("name"),
            stats={
                "total_success": total_success,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "elapsed_seconds": total_elapsed,
            }
        )

    except Exception as e:
        logger.exception("Критическая ошибка run_clone")
        log(f"❌ Критическая ошибка: {e}", "error")
        done_cb(success=False, error=str(e))