# -*- coding: utf-8 -*-
"""
app.py — Flask + SocketIO сервер для Discord Cloner v9.0 ULTRA (2026)
=====================================================================
Production Edition — ИСПРАВЛЕНО: logging.handlers import
"""

import os
import sys
import json
import logging
import logging.handlers  # ← ИСПРАВЛЕНО: явный импорт подмодуля handlers
import time
import threading
import uuid
import secrets
import signal
from typing import Dict, List, Optional, Any
from functools import wraps
from datetime import datetime

from flask import Flask, request, jsonify, render_template, g
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Импорты из проекта
from config import (
    VERSION, HOST, PORT, DEBUG,
    DISCORD_CDN as CDN, DISCORD_API,
    TASK_TTL, TASK_CLEANUP_INTERVAL,
    SECRET_KEY, CORS_ALLOWED_ORIGINS,
    LOG_LEVEL, LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT,
    LOG_MAX_BYTES, LOG_BACKUP_COUNT,
)
from brain import SmartBrain
from cloner import run_clone, ALL_STEPS
from utils import (
    is_valid_snowflake, is_valid_token, safe_name,
    human_delay, clean_proxy_list,
)

# ═══════════════════════════════════════════════════════════════
#  LOGGING SETUP
# ═══════════════════════════════════════════════════════════════

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("cloner.app")

# ═══════════════════════════════════════════════════════════════
#  FLASK APP INITIALIZATION
# ═══════════════════════════════════════════════════════════════

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

app.config["SECRET_KEY"] = SECRET_KEY
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600
app.config["JSON_AS_ASCII"] = False

# CORS
CORS(app, resources={
    r"/api/*": {"origins": CORS_ALLOWED_ORIGINS},
    r"/socket.io/*": {"origins": "*"},
})

# SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    ping_timeout=180,
    ping_interval=30,
    max_http_buffer_size=25 * 1024 * 1024,
    logger=False,
    engineio_logger=False,
)

# ═══════════════════════════════════════════════════════════════
#  TASK MANAGEMENT
# ═══════════════════════════════════════════════════════════════

_tasks: Dict[str, Dict] = {}
_tasks_lock = threading.Lock()
_cancel_flags: Dict[str, threading.Event] = {}
_clone_history: List[Dict] = []
_history_lock = threading.Lock()
MAX_HISTORY = 100


def _cleanup_tasks_loop():
    """Фоновый поток для очистки старых задач."""
    while True:
        time.sleep(TASK_CLEANUP_INTERVAL)
        now = time.time()
        with _tasks_lock:
            to_delete = [
                tid for tid, t in _tasks.items()
                if t.get("status") in ("completed", "failed", "crashed", "cancelled")
                and (now - t.get("ended_at", 0)) > TASK_TTL
            ]
            for tid in to_delete:
                del _tasks[tid]
                _cancel_flags.pop(tid, None)
            if to_delete:
                logger.info(f"Очищено {len(to_delete)} старых задач из памяти.")


cleanup_thread = threading.Thread(target=_cleanup_tasks_loop, daemon=True)
cleanup_thread.start()


def _create_task(sid: str, src_id: str, dst_id: str, tokens_count: int) -> str:
    """Создает новую задачу."""
    task_id = str(uuid.uuid4())[:8]
    cancel_event = threading.Event()
    
    with _tasks_lock:
        _tasks[task_id] = {
            "task_id": task_id,
            "sid": sid,
            "status": "pending",
            "started_at": time.time(),
            "ended_at": None,
            "source_id": src_id,
            "target_id": dst_id,
            "tokens_count": tokens_count,
            "progress": 0.0,
            "current_step": "",
            "error": None,
            "stats": None,
        }
        _cancel_flags[task_id] = cancel_event
    
    return task_id


def _update_task(task_id: str, **kwargs):
    """Обновляет состояние задачи."""
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id].update(kwargs)


def _get_cancel_flag(task_id: str) -> Optional[threading.Event]:
    """Возвращает флаг отмены."""
    return _cancel_flags.get(task_id)


def _add_to_history(task_data: Dict):
    """Добавляет задачу в историю."""
    with _history_lock:
        _clone_history.insert(0, {
            "task_id": task_data.get("task_id"),
            "status": task_data.get("status"),
            "source_id": task_data.get("source_id"),
            "target_id": task_data.get("target_id"),
            "started_at": task_data.get("started_at"),
            "ended_at": task_data.get("ended_at"),
            "error": task_data.get("error"),
            "stats": task_data.get("stats"),
        })
        if len(_clone_history) > MAX_HISTORY:
            _clone_history.pop()


# ═══════════════════════════════════════════════════════════════
#  DECORATORS & MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

def require_json(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.is_json:
            return jsonify({"error": "Expected JSON content-type"}), 400
        return f(*args, **kwargs)
    return decorated


@app.before_request
def before_request():
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()


@app.after_request
def after_request(response):
    elapsed = time.time() - g.start_time
    logger.info(
        f"[{g.request_id}] {request.method} {request.path} "
        f"→ {response.status_code} ({elapsed:.3f}s)"
    )
    response.headers["X-Request-ID"] = g.request_id
    response.headers["X-Cloner-Version"] = VERSION
    return response


# ═══════════════════════════════════════════════════════════════
#  SOCKETIO HELPERS
# ═══════════════════════════════════════════════════════════════

def _log(sid: str, msg: str, level: str = "info"):
    socketio.emit("log", {
        "message": msg,
        "level": level,
        "timestamp": datetime.now().isoformat(),
    }, room=sid)


def _prog(sid: str, step: str, cur: int, tot: int, key: str = ""):
    progress = cur / tot if tot > 0 else 0
    socketio.emit("progress", {
        "step": step,
        "key": key,
        "current": cur,
        "total": tot,
        "progress": round(progress * 100, 1),
    }, room=sid)


def _done(sid: str, **kwargs):
    socketio.emit("clone_done", kwargs, room=sid)


# ═══════════════════════════════════════════════════════════════
#  SMART MEMBER FETCHER
# ═══════════════════════════════════════════════════════════════

def _fetch_members_smart(brain: SmartBrain, guild_id: str,
                          log_fn=None, cancel_flag: threading.Event = None) -> Dict[str, dict]:
    """Умный сбор участников с пагинацией."""
    members: Dict[str, dict] = {}
    after = "0"
    limit = 1000
    
    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("  → Запуск умного сбора участников (REST Pagination)...")
    
    while True:
        if cancel_flag and cancel_flag.is_set():
            _log("🛑 Сбор участников прерван")
            break
        
        url = f"/guilds/{guild_id}/members?limit={limit}&after={after}"
        r = brain.get(url, use_cache=False)
        
        if not r or r.status_code != 200:
            _log(f"  ⚠️ Ошибка при сборе: {brain.diagnose(r)}")
            break
        
        batch = r.json()
        if not batch:
            break
        
        for m in batch:
            uid = m["user"]["id"]
            if not m["user"].get("bot") and uid not in members:
                members[uid] = {"user": m["user"], "roles": m.get("roles", [])}
        
        if len(batch) < limit:
            break
        
        after = batch[-1]["user"]["id"]
        human_delay(2.0, 3.0, "пагинация участников")

    _log(f"  ✓ Собрано уникальных участников: {len(members)}")
    return members


# ═══════════════════════════════════════════════════════════════
#  WEB ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/guides")
def guides():
    return render_template("guides.html")

@app.route("/how-to-clone")
def how_to_clone():
    return render_template("how_to_clone.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/security")
def security():
    return render_template("security.html")


# ═══════════════════════════════════════════════════════════════
#  SOCKETIO EVENTS
# ═══════════════════════════════════════════════════════════════

@socketio.on("connect")
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit("connected", {
        "status": "ok",
        "version": VERSION,
        "server_time": datetime.now().isoformat(),
    })


@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")
    with _tasks_lock:
        for task_id, task in list(_tasks.items()):
            if task.get("sid") == request.sid and task.get("status") in ("running", "pending"):
                cancel_flag = _cancel_flags.get(task_id)
                if cancel_flag:
                    cancel_flag.set()
                task["status"] = "cancelled"
                task["ended_at"] = time.time()
                logger.info(f"Task {task_id} cancelled due to client disconnect")


@socketio.on("start_clone")
def handle_start_clone(data):
    """Запуск клонирования сервера."""
    sid = request.sid
    logger.info(f"Start clone request from {sid}")

    tokens_raw = data.get("token") or data.get("tokens") or []
    tokens = [tokens_raw.strip()] if isinstance(tokens_raw, str) else [t.strip() for t in tokens_raw if t.strip()]
    src_id = str(data.get("source_id", "")).strip()
    dst_id = str(data.get("target_id", "")).strip()
    options = data.get("options", {})
    proxies_raw = data.get("proxies", [])
    max_retries = int(data.get("max_retries", 10))

    if not tokens:
        _log(sid, "❌ Не указан токен", "error")
        _done(sid, success=False, error="Токен не указан")
        return

    invalid_tokens = [t for t in tokens if not is_valid_token(t)]
    if invalid_tokens:
        _log(sid, "❌ Неверный формат токена", "error")
        _done(sid, success=False, error="Неверный формат токена")
        return

    if not is_valid_snowflake(src_id) or not is_valid_snowflake(dst_id):
        _log(sid, "❌ Неверный ID сервера", "error")
        _done(sid, success=False, error="Неверный ID сервера")
        return

    if src_id == dst_id:
        _log(sid, "❌ Исходник и цель совпадают!", "error")
        _done(sid, success=False, error="src == dst")
        return

    proxies = clean_proxy_list(proxies_raw) if proxies_raw else []

    _log(sid, "🔍 Проверка токена...", "info")
    test_brain = SmartBrain(tokens[0], proxies=proxies[:1] if proxies else None)
    test_resp = test_brain.get("/users/@me")
    
    if not test_resp or test_resp.status_code != 200:
        err = test_brain.diagnose(test_resp, "token")
        _log(sid, f"❌ Токен недействителен: {err}", "error")
        _done(sid, success=False, error=f"Токен невалиден: {err}")
        return

    user_info = test_resp.json()
    _log(sid, f"✅ Токен валиден: {user_info.get('global_name') or user_info.get('username')}", "success")

    _log(sid, "🔍 Проверка прав на целевом сервере...", "info")
    dst_resp = test_brain.get(f"/guilds/{dst_id}")
    
    if not dst_resp or dst_resp.status_code != 200:
        _log(sid, f"❌ Целевой сервер: {test_brain.diagnose(dst_resp)}", "error")
        _done(sid, success=False, error="Нет доступа к целевому серверу")
        return

    dst_info = dst_resp.json()
    me_member = test_brain.get(f"/guilds/{dst_id}/members/@me")
    has_admin = dst_info.get("owner_id") == user_info["id"]
    
    if not has_admin and me_member and me_member.status_code == 200:
        member_roles = me_member.json().get("roles", [])
        roles_resp = test_brain.get(f"/guilds/{dst_id}/roles")
        if roles_resp and roles_resp.status_code == 200:
            roles_map = {r["id"]: r for r in roles_resp.json()}
            for rid in member_roles:
                if int(roles_map.get(rid, {}).get("permissions", 0)) & 0x8:
                    has_admin = True
                    break

    if not has_admin:
        _log(sid, f"❌ Нет прав Администратора на '{dst_info.get('name')}'", "error")
        _done(sid, success=False, error="Нет прав Администратора")
        return

    _log(sid, f"✅ Права подтверждены на '{dst_info.get('name')}'", "success")

    task_id = _create_task(sid, src_id, dst_id, len(tokens))
    cancel_flag = _get_cancel_flag(task_id)

    _log(sid, f"✅ Задача {task_id} поставлена в очередь", "info")
    emit("task_started", {"task_id": task_id}, room=sid)

    def wrapper():
        brain = SmartBrain(
            tokens=tokens,
            proxies=proxies,
            max_retries=max_retries,
            cache_ttl=20,
        )
        
        def log(msg, level="info"):
            _log(sid, msg, level)
        
        def prog(step, cur, tot, key=""):
            _prog(sid, step, cur, tot, key)
            _update_task(task_id, status="running", current_step=step,
                        progress=cur / tot if tot > 0 else 0)
        
        def done_cb(success, **kwargs):
            _done(sid, success=success, **kwargs)
            status = "completed" if success else "failed"
            _update_task(task_id, status=status, ended_at=time.time(),
                        error=kwargs.get("error"), stats=kwargs.get("stats"))
            with _tasks_lock:
                if task_id in _tasks:
                    _add_to_history(_tasks[task_id])

        try:
            _update_task(task_id, status="running")
            run_clone(
                token=None,
                src_id=src_id,
                dst_id=dst_id,
                options=options,
                log=log,
                prog=prog,
                done_cb=done_cb,
                brain=brain,
                cancel_flag=cancel_flag,
            )
        except Exception as e:
            logger.exception(f"Task {task_id} crashed")
            _log(sid, f"❌ Критическая ошибка: {e}", "error")
            _done(sid, success=False, error=str(e))
            _update_task(task_id, status="crashed", error=str(e), ended_at=time.time())
        finally:
            brain.shutdown()

    socketio.start_background_task(wrapper)


@socketio.on("cancel_clone")
def handle_cancel(data):
    task_id = data.get("task_id")
    if not task_id:
        return
    cancel_flag = _get_cancel_flag(task_id)
    if cancel_flag:
        cancel_flag.set()
        _update_task(task_id, status="cancelling")
        _log(request.sid, f"🛑 Отмена задачи {task_id} запрошена", "warn")
    else:
        _log(request.sid, f"⚠️ Задача {task_id} не найдена", "warn")


@socketio.on("validate_token")
def handle_validate_token(data):
    token = (data.get("token") or "").strip()
    if not token:
        emit("token_valid", {"valid": False, "error": "Токен не указан"})
        return
    if not is_valid_token(token):
        emit("token_valid", {"valid": False, "error": "Неверный формат токена"})
        return
    
    brain = SmartBrain([token])
    r = brain.get("/users/@me")
    if r and r.status_code == 200:
        u = r.json()
        emit("token_valid", {
            "valid": True,
            "username": u.get("global_name") or u.get("username", "?"),
            "id": u["id"],
            "avatar": f"{CDN}/avatars/{u['id']}/{u['avatar']}.png?size=64" if u.get("avatar") else None,
            "bot": u.get("bot", False),
        })
    else:
        emit("token_valid", {"valid": False, "error": brain.diagnose(r, "token")})
    brain.shutdown()


@socketio.on("get_guilds")
def handle_get_guilds(data):
    token = (data.get("token") or "").strip()
    if not token:
        emit("guilds_list", {"guilds": [], "error": "Нет токена"})
        return
    
    brain = SmartBrain([token])
    r = brain.get("/users/@me/guilds?with_counts=true")
    if r and r.status_code == 200:
        guilds = [{
            "id": g["id"],
            "name": g["name"],
            "admin": bool(int(g.get("permissions", 0)) & 0x8),
            "owner": g.get("owner", False),
            "icon": f"{CDN}/icons/{g['id']}/{g['icon']}.png?size=64" if g.get("icon") else None,
            "member_count": g.get("approximate_member_count", 0),
            "boost_level": g.get("premium_tier", 0),
        } for g in r.json()]
        guilds.sort(key=lambda x: (not x["admin"], x["name"].lower()))
        emit("guilds_list", {"guilds": guilds, "total": len(guilds)})
    else:
        emit("guilds_list", {"guilds": [], "error": brain.diagnose(r)})
    brain.shutdown()


@socketio.on("get_guild_roles")
def handle_get_guild_roles(data):
    token = (data.get("token") or "").strip()
    guild_id = (data.get("guild_id") or "").strip()
    if not token or not guild_id:
        emit("guild_roles", {"roles": [], "error": "Нет данных"})
        return
    
    brain = SmartBrain([token])
    r = brain.get(f"/guilds/{guild_id}/roles")
    if r and r.status_code == 200:
        roles = [{
            "id": rl["id"],
            "name": rl["name"],
            "color": rl.get("color", 0),
            "permissions": str(rl.get("permissions", "0")),
            "position": rl.get("position", 0),
            "managed": rl.get("managed", False),
            "hoist": rl.get("hoist", False),
        } for rl in r.json()]
        roles.sort(key=lambda x: x["position"], reverse=True)
        emit("guild_roles", {"roles": roles, "total": len(roles)})
    else:
        emit("guild_roles", {"roles": [], "error": brain.diagnose(r)})
    brain.shutdown()


@socketio.on("get_guild_channels")
def handle_get_guild_channels(data):
    token = (data.get("token") or "").strip()
    guild_id = (data.get("guild_id") or "").strip()
    if not token or not guild_id:
        emit("guild_channels", {"channels": [], "error": "Нет данных"})
        return
    
    brain = SmartBrain([token])
    r = brain.get(f"/guilds/{guild_id}/channels")
    if r and r.status_code == 200:
        channels = [{
            "id": ch["id"],
            "name": ch.get("name", ""),
            "type": ch.get("type", 0),
            "position": ch.get("position", 0),
            "parent_id": ch.get("parent_id"),
        } for ch in r.json()]
        channels.sort(key=lambda x: (x["type"] != 4, x["position"]))
        emit("guild_channels", {"channels": channels, "total": len(channels)})
    else:
        emit("guild_channels", {"channels": [], "error": brain.diagnose(r)})
    brain.shutdown()


@socketio.on("assign_role_to_all")
def handle_assign_role_to_all(data):
    sid = request.sid
    token = (data.get("token") or "").strip()
    guild_id = (data.get("guild_id") or "").strip()
    role_id = (data.get("role_id") or "").strip()
    
    if not all([token, guild_id, role_id]):
        _log(sid, "❌ Не указаны все данные", "error")
        emit("assign_done", {"success": False, "error": "Неполные данные"}, room=sid)
        return

    def do_assign():
        brain = SmartBrain([token])
        cancel_flag = threading.Event()

        def log(msg, level="info"):
            socketio.emit("assign_log", {"message": msg, "level": level}, room=sid)
        
        def prog(step, cur, tot, key=""):
            socketio.emit("assign_progress", {
                "step": step, "key": key,
                "current": cur, "total": tot,
            }, room=sid)
        
        def done(success, **kwargs):
            socketio.emit("assign_done", {"success": success, **kwargs}, room=sid)

        me = brain.get("/users/@me")
        if not me or me.status_code != 200:
            log(f"❌ Токен: {brain.diagnose(me)}", "error")
            done(success=False, error=brain.diagnose(me))
            return
        log(f"✅ Авторизован: {me.json().get('global_name') or me.json().get('username')}", "success")

        roles_resp = brain.get(f"/guilds/{guild_id}/roles")
        target_role = None
        if roles_resp and roles_resp.status_code == 200:
            target_role = next((rl for rl in roles_resp.json() if rl["id"] == role_id), None)
        
        if not target_role:
            log("❌ Роль не найдена на сервере", "error")
            done(success=False, error="Роль не найдена")
            return
        log(f"🎭 Целевая роль: {target_role['name']}", "info")

        log("🔍 Получаю список участников…", "info")
        members = _fetch_members_smart(brain, guild_id, log_fn=log, cancel_flag=cancel_flag)

        if not members:
            log("⚠️ Не удалось получить участников.", "warn")
            done(success=True, assigned=0)
            return

        log(f"👥 Участников: {len(members)}", "info")
        ok, skipped, errors = 0, 0, 0
        total = len(members)
        
        for i, (uid, mdata) in enumerate(members.items()):
            if cancel_flag.is_set():
                log("🛑 Прервано", "warn")
                break
            current_roles = mdata.get("roles", [])
            if role_id in current_roles:
                skipped += 1
                continue
            new_roles = current_roles + [role_id]
            r = brain.patch(f"/guilds/{guild_id}/members/{uid}", json={"roles": new_roles})
            if r and r.status_code in (200, 201, 204):
                ok += 1
            elif r and r.status_code == 429:
                retry_after = float(r.headers.get('Retry-After', 5))
                log(f"⏳ Rate limit, ждем {retry_after:.1f}с", "warn")
                time.sleep(retry_after + 1)
                errors += 1
            else:
                errors += 1
            if (i + 1) % 50 == 0 or i + 1 == total:
                prog("Выдача роли", i + 1, total, "assign_role")
            human_delay(2.0, 4.0, "между участниками")

        log(f"✅ Готово! Выдано: {ok}, уже имели: {skipped}, ошибки: {errors}", "success")
        done(success=True, assigned=ok, already=skipped, errors=errors)
        brain.shutdown()

    socketio.start_background_task(do_assign)


# ═══════════════════════════════════════════════════════════════
#  REST API
# ═══════════════════════════════════════════════════════════════

@app.route("/api/health")
def health():
    with _tasks_lock:
        active = sum(1 for t in _tasks.values() if t.get("status") in ("running", "pending"))
    return jsonify({
        "status": "ok",
        "version": VERSION,
        "active_tasks": active,
        "server_time": datetime.now().isoformat(),
    })


@app.route("/api/task-status/<task_id>")
def api_task_status(task_id):
    with _tasks_lock:
        if task_id in _tasks:
            task = _tasks[task_id].copy()
            task.pop("sid", None)
            return jsonify(task)
    return jsonify({"error": "Задача не найдена"}), 404


@app.route("/api/cancel/<task_id>", methods=["POST"])
def api_cancel(task_id):
    cancel_flag = _get_cancel_flag(task_id)
    if cancel_flag:
        cancel_flag.set()
        _update_task(task_id, status="cancelling")
        return jsonify({"status": "cancelling", "task_id": task_id})
    return jsonify({"error": "Задача не найдена"}), 404


@app.route("/api/tasks")
def api_tasks():
    with _tasks_lock:
        tasks = [t.copy() for t in _tasks.values()]
        for t in tasks:
            t.pop("sid", None)
    tasks.sort(key=lambda x: x.get("started_at", 0), reverse=True)
    return jsonify({"tasks": tasks, "total": len(tasks)})


@app.route("/api/history")
def api_history():
    with _history_lock:
        return jsonify({"history": _clone_history, "total": len(_clone_history)})


@app.route("/api/steps")
def api_steps():
    return jsonify({
        "steps": [{"key": k, "name": n} for k, n in ALL_STEPS],
        "total": len(ALL_STEPS),
    })


# ═══════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template("index.html"), 404


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal server error")
    return jsonify({"error": "Internal server error"}), 500


# ═══════════════════════════════════════════════════════════════
#  GRACEFUL SHUTDOWN
# ═══════════════════════════════════════════════════════════════

def graceful_shutdown(signum, frame):
    logger.info("Получен сигнал завершения. Остановка сервера...")
    with _tasks_lock:
        for task_id, task in _tasks.items():
            if task.get("status") in ("running", "pending"):
                cancel_flag = _cancel_flags.get(task_id)
                if cancel_flag:
                    cancel_flag.set()
                task["status"] = "cancelled"
    logger.info("Все задачи отменены. Сервер остановлен.")
    sys.exit(0)


signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)


# ═══════════════════════════════════════════════════════════════
#  STARTUP
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.config["START_TIME"] = time.time()
    
    print("=" * 70)
    print(f"  Discord Server Cloner v{VERSION} — ULTRA сервер")
    print(f"  • Batch Role Assignment (Обход лимитов)")
    print(f"  • Smart Member Pagination (Надежный сбор)")
    print(f"  • Cancellation Support (Отмена задач)")
    print(f"  • Smart Delays 2-5s (Защита от банов)")
    print(f"  • Адрес: http://{HOST}:{PORT}")
    print("=" * 70)

    if not os.path.exists("templates") or not os.path.exists("templates/index.html"):
        print("\n[WARNING] Папка 'templates' или файл 'index.html' не найдены!")
        print("Создайте папку 'templates' и поместите в неё HTML файлы.\n")

    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=DEBUG,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )