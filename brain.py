# -*- coding: utf-8 -*-
"""
brain.py — SmartBrain v10 ULTRA (2026) — Production Edition
============================================================
ИСПРАВЛЕНО: curl_cffi ошибка "Recv failure: Connection was reset"
  • Автоматический fallback на стандартный requests
  • Smart Delay Manager (2-5 секунд)
  • Preemptive Rate Limit (читает заголовки ДО запроса)
  • Channel & Role Payload Builders
  • Token Rotation & Circuit Breaker
  • Download & Media Helpers
"""

import time
import threading
import random
import logging
import base64
import json
import os
from typing import Optional, List, Dict, Any, Union
from collections import OrderedDict

# ─────────────────────────────────────────────────────────────
#  HTTP CLIENT: Безопасная инициализация
#  ПРИОРИТЕТ: стандартный requests (стабильность > TLS spoofing)
# ─────────────────────────────────────────────────────────────
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout, RequestException

# curl_cffi — опционально, только если явно включено И работает
HAS_CURL_CFFI = False
curl_requests = None
try:
    from curl_cffi import requests as _curl_requests
    # Проверяем, что curl_cffi реально работает
    _test_sess = _curl_requests.Session(impersonate="chrome120")
    _test_resp = _test_sess.get("https://httpbin.org/get", timeout=5)
    if _test_resp.status_code == 200:
        HAS_CURL_CFFI = True
        curl_requests = _curl_requests
    _test_sess.close()
except Exception:
    HAS_CURL_CFFI = False
    curl_requests = None

# ─────────────────────────────────────────────────────────────
#  CONFIG IMPORTS
# ─────────────────────────────────────────────────────────────
try:
    from config import (
        DISCORD_API, DISCORD_CDN as CDN, DISCORD_MEDIA as MEDIA,
        BRAIN_MAX_RETRIES, BRAIN_TIMEOUT_DEFAULT, BRAIN_TIMEOUT_UPLOAD,
        BRAIN_TIMEOUT_DOWNLOAD, BRAIN_JITTER_MIN, BRAIN_JITTER_MAX,
        CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_PENALTY,
        PREEMPTIVE_THROTTLE_ENABLED, PREEMPTIVE_THROTTLE_THRESHOLD,
        BACKOFF_BASE, BACKOFF_MAX, BACKOFF_JITTER,
        STEALTH_MODE, TLS_SPOOFING_ENABLED, TLS_IMPERSONATE_PROFILE,
        ROTATE_USER_AGENTS, MINIFY_PAYLOADS,
        GENERATE_CONTEXT_PROPERTIES, GENERATE_SUPER_PROPERTIES,
        RATELIMIT_PRECISION,
        DC_NO_ADMIN, DC_NO_ACCESS, DC_LIMIT_ROLES, DC_LIMIT_EMOJIS,
        DC_LIMIT_CHANNELS, DC_LIMIT_STICKERS, DC_NEEDS_BOOST,
        DC_BOTS_ONLY, DC_USERS_ONLY, DC_INVALID_FORM, DC_TOO_MANY_REQUESTS,
        CH_TEXT, CH_VOICE, CH_CATEGORY, CH_STAGE, CH_FORUM, CH_MEDIA,
        MAX_TOPIC_TEXT, MAX_TOPIC_STAGE, MAX_TOPIC_FORUM,
        MAX_BITRATE_FREE, MAX_FORUM_TAGS, MAX_FORUM_TAG_NAME_LENGTH,
        MAX_ROLE_NAME_LENGTH,
    )
except ImportError:
    DISCORD_API = "https://discord.com/api/v10"
    CDN = "https://cdn.discordapp.com"
    MEDIA = "https://media.discordapp.net"
    BRAIN_MAX_RETRIES = 10
    BRAIN_TIMEOUT_DEFAULT = 30
    BRAIN_TIMEOUT_UPLOAD = 90
    BRAIN_TIMEOUT_DOWNLOAD = 60
    BRAIN_JITTER_MIN = 0.1
    BRAIN_JITTER_MAX = 0.5
    CIRCUIT_BREAKER_THRESHOLD = 2
    CIRCUIT_BREAKER_PENALTY = 45.0
    PREEMPTIVE_THROTTLE_ENABLED = True
    PREEMPTIVE_THROTTLE_THRESHOLD = 1
    BACKOFF_BASE = 2.0
    BACKOFF_MAX = 60.0
    BACKOFF_JITTER = 0.5
    STEALTH_MODE = True
    TLS_SPOOFING_ENABLED = False
    TLS_IMPERSONATE_PROFILE = "chrome120"
    ROTATE_USER_AGENTS = True
    MINIFY_PAYLOADS = True
    GENERATE_CONTEXT_PROPERTIES = True
    GENERATE_SUPER_PROPERTIES = True
    RATELIMIT_PRECISION = "millisecond"
    DC_NO_ADMIN, DC_NO_ACCESS, DC_LIMIT_ROLES, DC_LIMIT_EMOJIS = 50013, 50001, 30005, 30007
    DC_LIMIT_CHANNELS, DC_LIMIT_STICKERS = 30016, 30039
    DC_NEEDS_BOOST, DC_BOTS_ONLY, DC_USERS_ONLY = 50101, 20001, 20002
    DC_INVALID_FORM, DC_TOO_MANY_REQUESTS = 50035, 429
    CH_TEXT, CH_VOICE, CH_CATEGORY = 0, 2, 4
    CH_STAGE, CH_FORUM, CH_MEDIA = 13, 15, 17
    MAX_TOPIC_TEXT, MAX_TOPIC_STAGE, MAX_TOPIC_FORUM = 1024, 120, 4096
    MAX_BITRATE_FREE = 96000
    MAX_FORUM_TAGS, MAX_FORUM_TAG_NAME_LENGTH = 20, 20
    MAX_ROLE_NAME_LENGTH = 100

from utils import bytes_to_b64, sanitize_channel_name, sanitize_role_name, minify_payload

logger = logging.getLogger("cloner.brain")

# ─────────────────────────────────────────────────────────────
#  USER AGENTS & FINGERPRINTS
# ─────────────────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

_SEC_CH_UA = [
    '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    '"Chromium";v="123", "Google Chrome";v="123", "Not:A-Brand";v="8"',
]

_ENDPOINT_COOLDOWN: Dict[str, float] = {
    "roles": 2.5, "emojis": 3.0, "channels": 2.0,
    "stickers": 3.5, "webhooks": 2.0, "members": 1.5,
    "delete": 1.0, "invites": 1.5, "automod": 2.0,
    "events": 2.0, "soundboard": 3.0, "settings": 1.5,
    "default": 2.0,
}

# ─────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def _jitter(lo: float = BRAIN_JITTER_MIN, hi: float = BRAIN_JITTER_MAX) -> float:
    return random.uniform(lo, hi) if STEALTH_MODE else 0.0


def _backoff(attempt: int, base: float = BACKOFF_BASE, cap: float = BACKOFF_MAX) -> float:
    delay = min(base ** attempt, cap)
    return delay + random.uniform(0, BACKOFF_JITTER * delay)


def _retry_after(resp) -> float:
    try:
        v = resp.json().get("retry_after")
        if v is not None:
            return float(v)
    except Exception:
        pass
    try:
        return float(resp.headers.get("Retry-After", 2.0))
    except Exception:
        return 2.0


def _is_retryable(code: int) -> bool:
    return code in (500, 502, 503, 504, 520, 521, 522)


def _endpoint_type(method: str, path: str) -> str:
    p = path.lower()
    if method == "DELETE": return "delete"
    if "/roles" in p and method in ("POST", "PATCH"): return "roles"
    if "/emojis" in p and method == "POST": return "emojis"
    if "/channels" in p and method == "POST" and "/guilds/" in p: return "channels"
    if "/stickers" in p and method == "POST": return "stickers"
    if "/webhooks" in p and method == "POST": return "webhooks"
    if "/members/" in p: return "members"
    if "/invites" in p and method == "POST": return "invites"
    if "/auto-moderation" in p: return "automod"
    if "/scheduled-events" in p: return "events"
    if "/soundboard" in p: return "soundboard"
    return "default"


def _generate_super_properties() -> str:
    if not GENERATE_SUPER_PROPERTIES:
        return ""
    props = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "ru-RU",
        "browser_user_agent": random.choice(_USER_AGENTS),
        "browser_version": "124.0.0.0",
        "os_version": "10",
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": random.randint(310000, 320000),
        "client_event_source": None,
    }
    return base64.b64encode(json.dumps(props, separators=(',', ':')).encode()).decode()


def _generate_context_properties(guild_id: str = "0", channel_id: str = "0") -> str:
    if not GENERATE_CONTEXT_PROPERTIES:
        return ""
    ctx = {
        "location": "Guild Settings",
        "location_guild_id": guild_id,
        "location_channel_id": channel_id,
        "location_channel_type": 0,
    }
    return base64.b64encode(json.dumps(ctx, separators=(',', ':')).encode()).decode()


def _minify(payload: dict) -> dict:
    if not MINIFY_PAYLOADS:
        return payload
    return minify_payload(payload)


def smart_delay(min_sec: float = 2.0, max_sec: float = 5.0, context: str = "") -> float:
    """Умная задержка 2-5 секунд."""
    delay = random.uniform(min_sec, max_sec) + random.uniform(0.05, 0.35)
    if delay > 3.0:
        logger.debug(f"Smart delay: {delay:.2f}s {context}")
    time.sleep(delay)
    return delay


def batch_pause(items_processed: int, batch_size: int, pause_sec: float = 12.0,
                log_fn=None) -> bool:
    """Batch пауза после N элементов."""
    if items_processed > 0 and items_processed % batch_size == 0:
        actual = pause_sec + random.uniform(0.5, 2.0)
        if log_fn:
            log_fn(f"🔄 Batch пауза {actual:.1f}с после {items_processed} элементов", "info")
        time.sleep(actual)
        return True
    return False


# ─────────────────────────────────────────────────────────────
#  RATE LIMIT BUCKET
# ─────────────────────────────────────────────────────────────

class RateLimitBucket:
    def __init__(self):
        self.remaining: int = 9999
        self.limit: int = 9999
        self.reset_after: float = 0.0
        self.bucket_id: str = ""

    def update(self, headers: dict):
        try:
            if 'X-RateLimit-Remaining' in headers:
                self.remaining = int(headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Limit' in headers:
                self.limit = int(headers['X-RateLimit-Limit'])
            if 'X-RateLimit-Reset-After' in headers:
                self.reset_after = float(headers['X-RateLimit-Reset-After'])
            if 'X-RateLimit-Bucket' in headers:
                self.bucket_id = headers['X-RateLimit-Bucket']
        except (ValueError, TypeError):
            pass

    def should_wait(self) -> bool:
        return self.remaining <= PREEMPTIVE_THROTTLE_THRESHOLD and self.reset_after > 0

    def get_wait(self) -> float:
        if not self.should_wait():
            return 0.0
        return self.reset_after + random.uniform(0.5, 1.5)


# ═══════════════════════════════════════════════════════════════
#  SMART BRAIN CLASS
# ═══════════════════════════════════════════════════════════════

class SmartBrain:
    def __init__(
        self,
        tokens: Union[str, List[str]],
        proxies: Optional[List[str]] = None,
        max_retries: int = BRAIN_MAX_RETRIES,
        timeout: int = BRAIN_TIMEOUT_DEFAULT,
        upload_timeout: int = BRAIN_TIMEOUT_UPLOAD,
        download_timeout: int = BRAIN_TIMEOUT_DOWNLOAD,
        cache_ttl: int = 30,
        max_concurrent: int = 6,
        use_tls_spoofing: bool = False,
    ):
        self.tokens = [t.strip() for t in (tokens if isinstance(tokens, list) else [tokens]) if t.strip()]
        if not self.tokens:
            raise ValueError("Нет токенов")

        self.proxies = proxies or []
        self.max_retries = max_retries
        self.timeout = timeout
        self.upload_timeout = upload_timeout
        self.download_timeout = download_timeout
        self.cache_ttl = cache_ttl

        # TLS spoofing: только если явно включено И curl_cffi работает
        self.use_tls_spoofing = use_tls_spoofing and HAS_CURL_CFFI and TLS_SPOOFING_ENABLED

        # Token management
        self._token_idx = 0
        self._token_lock = threading.Lock()
        self._token_health: Dict[str, int] = {t: 0 for t in self.tokens}
        self._token_blacklist_until: Dict[str, float] = {t: 0.0 for t in self.tokens}

        # Rate limiting
        self._global_reset = 0.0
        self._global_lock = threading.Lock()
        self._buckets: Dict[str, RateLimitBucket] = {}
        self._bucket_lock = threading.Lock()
        self._last_call: Dict[str, float] = {}
        self._last_call_lock = threading.Lock()
        self._rl_hits: Dict[str, int] = {}
        self._rl_hits_lock = threading.Lock()

        # Concurrency & caching
        self._sem = threading.Semaphore(max_concurrent)
        self._cache: OrderedDict = OrderedDict()
        self._cache_lock = threading.Lock()
        self._sessions: Dict[str, Any] = {}
        self._session_lock = threading.Lock()
        self._shutdown = False

        # Proxy
        self._proxy_usage: Dict[str, int] = {p: 0 for p in self.proxies}
        self._proxy_lock = threading.Lock()

        logger.info(
            f"SmartBrain v10 ULTRA init: tokens={len(self.tokens)}, "
            f"proxies={len(self.proxies)}, TLS_Spoof={self.use_tls_spoofing}"
        )

    # ─── TOKEN MANAGEMENT ─────────────────────────────────────

    def _get_healthy_token(self) -> str:
        with self._token_lock:
            for _ in range(len(self.tokens)):
                idx = self._token_idx
                self._token_idx = (idx + 1) % len(self.tokens)
                token = self.tokens[idx]
                if time.time() > self._token_blacklist_until.get(token, 0.0):
                    self._token_health[token] = 0
                    return token
            return self.tokens[0]

    def _mark_token_unhealthy(self, token: str):
        with self._token_lock:
            self._token_health[token] = self._token_health.get(token, 0) + 1
            if self._token_health[token] >= CIRCUIT_BREAKER_THRESHOLD:
                self._token_blacklist_until[token] = time.time() + CIRCUIT_BREAKER_PENALTY
                logger.warning(f"[Brain] ⚠️ Circuit Breaker: токен заморожен на {CIRCUIT_BREAKER_PENALTY}с")

    # ─── SESSION MANAGEMENT ───────────────────────────────────

    def _get_session(self, token: str, proxy: Optional[str] = None) -> Any:
        """
        ИСПРАВЛЕНО: Всегда использует стандартный requests.
        curl_cffi вызывает 'Connection was reset' на Windows.
        """
        key = f"{token[:20]}:{proxy or 'no_proxy'}"
        with self._session_lock:
            if key not in self._sessions:
                # ВСЕГДА используем стандартный requests (стабильность)
                sess = requests.Session()
                adapter = HTTPAdapter(
                    pool_connections=16,
                    pool_maxsize=32,
                    max_retries=0
                )
                sess.mount("https://", adapter)
                sess.mount("http://", adapter)

                if proxy:
                    sess.proxies = {"http": proxy, "https": proxy}

                self._sessions[key] = sess
            return self._sessions[key]

    def _get_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        with self._proxy_lock:
            sorted_p = sorted(self._proxy_usage.items(), key=lambda x: x[1])
            best = sorted_p[0][0]
            self._proxy_usage[best] += 1
            return best

    # ─── HEADERS ──────────────────────────────────────────────

    def _build_headers(self, token: str, multipart: bool = False,
                       guild_id: str = "0", channel_id: str = "0") -> dict:
        ua = random.choice(_USER_AGENTS) if ROTATE_USER_AGENTS else _USER_AGENTS[0]
        headers = {
            "Authorization": token,
            "User-Agent": ua,
            "X-Super-Properties": _generate_super_properties(),
            "X-Context-Properties": _generate_context_properties(guild_id, channel_id),
            "X-Discord-Locale": "ru-RU",
            "X-Discord-Timezone": "Europe/Moscow",
            "X-Debug-Options": "bugReporterEnabled",
            "X-RateLimit-Precision": RATELIMIT_PRECISION,
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": random.choice(_SEC_CH_UA),
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }
        if not multipart:
            headers["Content-Type"] = "application/json"
        return headers

    # ─── RATE LIMIT DEFENSE ───────────────────────────────────

    def _wait_global(self):
        with self._global_lock:
            diff = self._global_reset - time.time()
        if diff > 0:
            logger.warning(f"[Brain] 🌍 Global RL: {diff:.1f}с")
            time.sleep(diff + _jitter(0.5, 1.5))

    def _set_global(self, retry_after: float):
        with self._global_lock:
            self._global_reset = time.time() + retry_after

    def _bucket_key(self, method: str, path: str) -> str:
        parts = path.split("/")
        for i, p in enumerate(parts):
            if p in ("guilds", "channels", "webhooks", "users") and i + 1 < len(parts):
                major = parts[i + 1].split("?")[0]
                resource = parts[i + 2] if i + 2 < len(parts) else ""
                return f"{method}:{p}:{major}:{resource.split('?')[0]}"
        return f"{method}:{path.split('?')[0][:60]}"

    def _wait_bucket(self, key: str):
        with self._bucket_lock:
            bucket = self._buckets.get(key)
            if bucket and bucket.should_wait():
                wait = bucket.get_wait()
                logger.debug(f"[Brain] Bucket '{key}' спит {wait:.1f}с")
                time.sleep(wait)

    def _update_bucket(self, key: str, headers: dict):
        with self._bucket_lock:
            if key not in self._buckets:
                self._buckets[key] = RateLimitBucket()
            self._buckets[key].update(headers)

    def _preemptive_throttle(self, key: str, resp):
        if not PREEMPTIVE_THROTTLE_ENABLED:
            return
        try:
            remaining = int(resp.headers.get("X-RateLimit-Remaining", 9999))
            reset_after = float(resp.headers.get("X-RateLimit-Reset-After", 0))
            if remaining <= PREEMPTIVE_THROTTLE_THRESHOLD and reset_after > 0:
                wait = reset_after + _jitter(0.5, 1.5)
                logger.warning(f"[Brain] 🛡️ Превентивная пауза {wait:.1f}с (осталось {remaining})")
                time.sleep(wait)
        except (ValueError, TypeError):
            pass

    def _adaptive_cooldown(self, method: str, path: str):
        ep_type = _endpoint_type(method, path)
        min_gap = _ENDPOINT_COOLDOWN.get(ep_type, _ENDPOINT_COOLDOWN["default"])
        rl_hits = self._rl_hits.get(ep_type, 0)
        if rl_hits > 0:
            min_gap *= (1.3 ** min(rl_hits, 4))
        with self._last_call_lock:
            last = self._last_call.get(ep_type, 0.0)
            elapsed = time.time() - last
            if elapsed < min_gap:
                wait = min_gap - elapsed + _jitter(0.1, 0.4)
                self._last_call[ep_type] = time.time() + wait
                time.sleep(wait)
            self._last_call[ep_type] = time.time()

    # ─── CACHING ──────────────────────────────────────────────

    def _cache_get(self, key: str) -> Optional[Any]:
        with self._cache_lock:
            if key in self._cache:
                data, ts = self._cache[key]
                if time.time() - ts <= self.cache_ttl:
                    return data
                del self._cache[key]
        return None

    def _cache_set(self, key: str, data: Any):
        with self._cache_lock:
            if len(self._cache) >= 1024:
                self._cache.popitem(last=False)
            self._cache[key] = (data, time.time())

    # ─── MAIN REQUEST ─────────────────────────────────────────

    def request(self, method: str, path: str, timeout: Optional[int] = None,
                use_cache: bool = True, guild_id: str = "0",
                channel_id: str = "0", **kwargs) -> Optional[Any]:
        if self._shutdown:
            return None

        url = f"{DISCORD_API}{path}"
        is_get = method.upper() == "GET"
        is_upload = "files" in kwargs or "data" in kwargs
        t_out = timeout or (self.upload_timeout if is_upload else self.timeout)
        multipart = "files" in kwargs

        cache_key = f"{method}:{path}" if is_get else None
        if is_get and use_cache and cache_key:
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached

        bkey = self._bucket_key(method, path)
        errors = 0

        with self._sem:
            token = self._get_healthy_token()
            proxy = self._get_proxy()
            session = self._get_session(token, proxy)

            while True:
                self._wait_global()
                self._wait_bucket(bkey)
                self._adaptive_cooldown(method, path)

                try:
                    resp = session.request(
                        method, url,
                        headers=self._build_headers(token, multipart, guild_id, channel_id),
                        timeout=t_out,
                        **kwargs,
                    )
                except (ConnectionError, Timeout) as e:
                    errors += 1
                    if errors >= self.max_retries:
                        logger.error(f"[Brain] Net max-retries {path}")
                        return None
                    wait = _backoff(errors)
                    logger.warning(f"[Brain] Net error {path}: {e}, retry {errors} in {wait:.1f}s")
                    time.sleep(wait)
                    continue
                except RequestException as e:
                    errors += 1
                    if errors >= self.max_retries:
                        logger.error(f"[Brain] Request max-retries {path}: {e}")
                        return None
                    wait = _backoff(errors)
                    time.sleep(wait)
                    continue
                except Exception as e:
                    logger.error(f"[Brain] Unexpected {path}: {e}")
                    return None

                # Update bucket
                self._update_bucket(bkey, dict(resp.headers))

                # 429 Rate Limit
                if resp.status_code == 429:
                    is_global = resp.headers.get("X-RateLimit-Global", "").lower() == "true"
                    retry_after = _retry_after(resp)
                    ep_type = _endpoint_type(method, path)

                    with self._rl_hits_lock:
                        self._rl_hits[ep_type] = self._rl_hits.get(ep_type, 0) + 1

                    self._mark_token_unhealthy(token)

                    buffer = max(retry_after * 0.15, 0.8)
                    wait = retry_after + buffer + _jitter(0.5, 1.5)
                    logger.warning(f"[Brain] ⚠️ 429 {'GLOBAL' if is_global else 'bucket'} path={path} wait={wait:.1f}s")

                    if is_global:
                        self._set_global(retry_after + buffer)
                    else:
                        with self._bucket_lock:
                            if bkey not in self._buckets:
                                self._buckets[bkey] = RateLimitBucket()
                            self._buckets[bkey].reset_after = wait

                    # Token rotation
                    if len(self.tokens) > 1:
                        old = token
                        token = self._get_healthy_token()
                        if token != old:
                            session = self._get_session(token, proxy)
                            logger.info("[Brain] 🔄 Переключение токена после 429")
                            continue

                    time.sleep(wait)
                    continue

                # 5xx
                if _is_retryable(resp.status_code):
                    errors += 1
                    if errors >= self.max_retries:
                        logger.error(f"[Brain] Max retries {resp.status_code} {path}")
                        return resp
                    wait = _backoff(errors, base=3.0)
                    logger.warning(f"[Brain] {resp.status_code} {path}, retry {errors} in {wait:.1f}s")
                    time.sleep(wait)
                    continue

                # Success
                self._preemptive_throttle(bkey, resp)
                with self._token_lock:
                    self._token_health[token] = 0

                if is_get and use_cache and cache_key and resp.status_code == 200:
                    if "application/json" in resp.headers.get("Content-Type", ""):
                        self._cache_set(cache_key, resp)

                return resp

    # ─── HTTP SHORTCUTS ───────────────────────────────────────

    def get(self, path: str, **kw):    return self.request("GET", path, **kw)
    def post(self, path: str, **kw):   return self.request("POST", path, **kw)
    def patch(self, path: str, **kw):  return self.request("PATCH", path, **kw)
    def put(self, path: str, **kw):    return self.request("PUT", path, **kw)
    def delete(self, path: str, **kw): return self.request("DELETE", path, **kw)

    # ─── SMART DELAY ──────────────────────────────────────────

    def delay(self, operation: str = "default", context: str = "") -> float:
        base = _ENDPOINT_COOLDOWN.get(operation, _ENDPOINT_COOLDOWN["default"])
        return smart_delay(max(2.0, base), max(5.0, base + 2.0), context)

    def batch_delay(self, items_processed: int, batch_size: int,
                    pause_sec: float = 12.0, log_fn=None) -> bool:
        return batch_pause(items_processed, batch_size, pause_sec, log_fn)

    # ─── CHANNEL BUILDERS ─────────────────────────────────────

    def build_text_channel_payload(self, src: dict, role_map: dict,
                                    parent_id: Optional[str] = None) -> dict:
        from utils import build_overwrites
        payload = {
            "name": sanitize_channel_name(src.get("name", "channel")),
            "type": CH_TEXT,
            "position": src.get("position", 0),
            "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
            "nsfw": src.get("nsfw", False),
        }
        if src.get("topic"):
            payload["topic"] = src["topic"][:MAX_TOPIC_TEXT]
        if src.get("rate_limit_per_user"):
            payload["rate_limit_per_user"] = src["rate_limit_per_user"]
        if parent_id:
            payload["parent_id"] = parent_id
        return _minify(payload)

    def build_voice_channel_payload(self, src: dict, role_map: dict,
                                     parent_id: Optional[str] = None,
                                     boost_level: int = 0) -> dict:
        from utils import build_overwrites
        max_br = MAX_BITRATE_FREE
        payload = {
            "name": sanitize_channel_name(src.get("name", "voice")),
            "type": CH_VOICE,
            "position": src.get("position", 0),
            "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
            "bitrate": min(src.get("bitrate", 64000), max_br),
        }
        if src.get("user_limit"):
            payload["user_limit"] = src["user_limit"]
        if src.get("rtc_region"):
            payload["rtc_region"] = src["rtc_region"]
        if parent_id:
            payload["parent_id"] = parent_id
        return _minify(payload)

    def build_category_payload(self, src: dict, role_map: dict) -> dict:
        from utils import build_overwrites
        return _minify({
            "name": src.get("name", "Category")[:100],
            "type": CH_CATEGORY,
            "position": src.get("position", 0),
            "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
        })

    def build_forum_channel_payload(self, src: dict, role_map: dict,
                                     parent_id: Optional[str] = None) -> dict:
        from utils import build_overwrites
        payload = {
            "name": sanitize_channel_name(src.get("name", "forum")),
            "type": CH_FORUM,
            "position": src.get("position", 0),
            "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
            "nsfw": src.get("nsfw", False),
        }
        if src.get("topic"):
            payload["topic"] = src["topic"][:MAX_TOPIC_FORUM]
        if src.get("rate_limit_per_user"):
            payload["rate_limit_per_user"] = src["rate_limit_per_user"]
        if src.get("available_tags"):
            tags = []
            for tag in src["available_tags"][:MAX_FORUM_TAGS]:
                tp = {"name": tag.get("name", "tag")[:MAX_FORUM_TAG_NAME_LENGTH]}
                if tag.get("emoji_id"): tp["emoji_id"] = tag["emoji_id"]
                elif tag.get("emoji_name"): tp["emoji_name"] = tag["emoji_name"]
                tags.append(tp)
            if tags: payload["available_tags"] = tags
        if src.get("default_forum_layout"):
            payload["default_forum_layout"] = src["default_forum_layout"]
        if src.get("default_sort_order"):
            payload["default_sort_order"] = src["default_sort_order"]
        if parent_id:
            payload["parent_id"] = parent_id
        return _minify(payload)

    def build_stage_channel_payload(self, src: dict, role_map: dict,
                                     parent_id: Optional[str] = None) -> dict:
        from utils import build_overwrites
        payload = {
            "name": sanitize_channel_name(src.get("name", "stage")),
            "type": CH_STAGE,
            "position": src.get("position", 0),
            "permission_overwrites": build_overwrites(src.get("permission_overwrites", []), role_map),
        }
        if src.get("topic"):
            payload["topic"] = src["topic"][:MAX_TOPIC_STAGE]
        if parent_id:
            payload["parent_id"] = parent_id
        return _minify(payload)

    # ─── ROLE BUILDER ─────────────────────────────────────────

    def build_role_payload(self, src: dict, icon_b64: Optional[str] = None,
                           unicode_emoji: Optional[str] = None) -> dict:
        payload = {
            "name": sanitize_role_name(src.get("name", "role"), MAX_ROLE_NAME_LENGTH),
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
        return _minify(payload)

    # ─── DIAGNOSTICS ──────────────────────────────────────────

    def diagnose(self, resp: Optional[Any], ctx: str = "") -> str:
        if resp is None:
            return "Нет ответа (таймаут / сеть)"
        code = resp.status_code
        try:
            body = resp.json()
        except Exception:
            body = {}
        dc = body.get("code", 0)
        msg = body.get("message", str(resp.text)[:200])

        FORBIDDEN = {
            DC_NO_ADMIN: "Нет прав Администратора",
            DC_NO_ACCESS: "Нет доступа к ресурсу",
            DC_LIMIT_ROLES: "Лимит ролей (250)",
            DC_LIMIT_EMOJIS: "Лимит эмодзи",
            DC_LIMIT_CHANNELS: "Лимит каналов (500)",
            DC_LIMIT_STICKERS: "Лимит стикеров",
            DC_NEEDS_BOOST: "Нужен буст сервера",
            DC_BOTS_ONLY: "Только для ботов",
            DC_USERS_ONLY: "Только для пользователей",
        }
        if code == 401: return "401 Недействительный токен"
        if code == 403: return f"403 {FORBIDDEN.get(dc, msg)} (code={dc})"
        if code == 404: return f"404 Не найдено: {ctx or msg}"
        if code == 400:
            def parse_errors(err_dict, prefix=""):
                details = []
                for k, v in err_dict.items():
                    if isinstance(v, dict) and "_errors" in v:
                        for e in v["_errors"]:
                            details.append(f"{prefix}{k}: {e.get('message', '')}")
                    elif isinstance(v, dict):
                        details.extend(parse_errors(v, f"{prefix}{k}."))
                return details
            details = parse_errors(body.get("errors", {}))
            return f"400 {'; '.join(details) if details else msg}"
        if code == 429: return f"429 Rate-limit (retry={_retry_after(resp):.1f}s)"
        if code >= 500: return f"{code} Ошибка сервера Discord"
        return f"HTTP {code}: {msg}"

    def is_rate_limited(self, resp) -> bool:
        return resp is not None and resp.status_code == 429

    # ─── DOWNLOAD & MEDIA ─────────────────────────────────────

    def download(self, url: str, timeout: Optional[int] = None) -> Optional[bytes]:
        t = timeout or self.download_timeout
        for attempt in range(6):
            if self._shutdown:
                return None
            try:
                sess = self._get_session(self._get_healthy_token(), None)
                hdrs = {
                    "User-Agent": random.choice(_USER_AGENTS),
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Referer": "https://discord.com/",
                }
                r = sess.get(url, headers=hdrs, timeout=t, stream=True)
                if r.status_code == 200:
                    return b"".join(r.iter_content(chunk_size=131072))
                if r.status_code in (403, 404, 401):
                    return None
                if r.status_code == 429:
                    time.sleep(_retry_after(r) + _jitter(1.0, 2.0))
                    continue
            except Exception as e:
                logger.debug(f"[Brain] DL attempt {attempt+1}: {e}")
                time.sleep(_backoff(attempt, 1.5))
        return None

    def download_multi(self, urls: List[str], timeout: Optional[int] = None) -> Optional[bytes]:
        for url in urls:
            data = self.download(url, timeout=timeout)
            if data:
                return data
        return None

    def to_b64(self, url: str, fallback_urls: Optional[List[str]] = None,
               timeout: Optional[int] = None) -> Optional[str]:
        data = self.download_multi([url] + (fallback_urls or []), timeout=timeout)
        return bytes_to_b64(data, url_hint=url) if data else None

    # ─── LIFECYCLE ────────────────────────────────────────────

    def shutdown(self):
        self._shutdown = True
        with self._session_lock:
            for s in self._sessions.values():
                try:
                    s.close()
                except Exception:
                    pass
            self._sessions.clear()
        logger.info("SmartBrain v10 ULTRA shutdown")

    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()

    def reset_rate_limits(self):
        with self._bucket_lock:
            self._buckets.clear()
        with self._global_lock:
            self._global_reset = 0.0
        with self._rl_hits_lock:
            self._rl_hits.clear()


def create_brain(tokens, proxies=None, **kwargs) -> SmartBrain:
    return SmartBrain(tokens, proxies, **kwargs)


__all__ = ["SmartBrain", "create_brain", "RateLimitBucket", "smart_delay", "batch_pause"]