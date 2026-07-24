#!/usr/bin/env bash
# ==============================================================================
#  Discord Server Cloner v9.0 ULTRA — Production Run Script
# ==============================================================================
#  Features:
#    • Smart Delay Manager (2-5s strategic pauses)
#    • Watchdog / Auto-Restart on crash
#    • Safe .env parser (handles quotes & spaces)
#    • Health Check (verifies HTTP response)
#    • Robust venv & dependency management
#    • Cross-platform support (Linux, macOS, WSL, Git Bash)
#    • Comprehensive logging to logs/run.log
# ==============================================================================

set -euo pipefail

# ─────────────────────────────────────────────────────────────
# 1. GLOBAL CONFIGURATION
# ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Versions & Requirements
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=8
APP_PORT="${PORT:-5500}"
HEALTH_CHECK_URL="http://127.0.0.1:${APP_PORT}/api/health"

# Timeouts & Delays (ULTRA: 2-5 seconds strategic pauses)
MIN_DELAY=2
MAX_DELAY=5
STARTUP_DELAY=3
RESTART_DELAY=5
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=5

# Paths
VENV_DIR="venv"
LOG_DIR="logs"
LOG_FILE="${LOG_DIR}/run.log"
ENV_FILE=".env"
PID_FILE=".cloner.pid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ─────────────────────────────────────────────────────────────
# 2. LOGGING SYSTEM
# ─────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local color="$NC"
    
    case "$level" in
        INFO)    color="$BLUE" ;;
        SUCCESS) color="$GREEN" ;;
        WARN)    color="$YELLOW" ;;
        ERROR)   color="$RED" ;;
        DEBUG)   color="$MAGENTA" ;;
    esac
    
    # Console output
    echo -e "${color}[${timestamp}] [${level}]${NC} ${message}"
    
    # File output (strip colors)
    echo "[${timestamp}] [${level}] ${message}" | sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"
}

log_info()    { log "INFO" "$@"; }
log_success() { log "SUCCESS" "$@"; }
log_warn()    { log "WARN" "$@"; }
log_error()   { log "ERROR" "$@"; }
log_debug()   { log "DEBUG" "$@"; }

# ─────────────────────────────────────────────────────────────
# 3. UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────

# ULTRA: Smart Delay (2-5 seconds) for system stabilization
smart_delay() {
    local context="${1:-system stabilization}"
    local delay
    delay=$(awk "BEGIN {srand(); print int($MIN_DELAY + rand() * ($MAX_DELAY - $MIN_DELAY + 1))}")
    log_info "⏸ Пауза ${delay}с (${context})..."
    sleep "$delay"
}

# Spinner for long operations
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep "$pid")" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Check if a command exists
check_command() {
    command -v "$1" &> /dev/null
}

# Get the correct Python command
get_python_cmd() {
    if check_command python3; then
        echo "python3"
    elif check_command python; then
        echo "python"
    else
        echo ""
    fi
}

# ─────────────────────────────────────────────────────────────
# 4. CLEANUP & SIGNAL HANDLING
# ─────────────────────────────────────────────────────────────
APP_PID=""

cleanup() {
    echo ""
    log_warn "Получен сигнал завершения. Остановка Discord Cloner..."
    
    # Kill the app process if it's running
    if [ -n "$APP_PID" ] && kill -0 "$APP_PID" 2>/dev/null; then
        log_info "Остановка процесса app.py (PID: $APP_PID)..."
        kill -TERM "$APP_PID" 2>/dev/null || true
        
        # Wait for graceful shutdown (max 10 seconds)
        local count=0
        while kill -0 "$APP_PID" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if still running
        if kill -0 "$APP_PID" 2>/dev/null; then
            log_warn "Принудительная остановка процесса..."
            kill -9 "$APP_PID" 2>/dev/null || true
        fi
    fi
    
    # Remove PID file
    rm -f "$PID_FILE"
    
    # Deactivate venv if active
    if type deactivate &> /dev/null; then
        deactivate 2>/dev/null || true
    fi
    
    log_success "✅ Discord Cloner успешно остановлен."
    exit 0
}

# Trap signals
trap cleanup SIGINT SIGTERM EXIT

# ─────────────────────────────────────────────────────────────
# 5. SYSTEM PREREQUISITES CHECK
# ─────────────────────────────────────────────────────────────
check_system() {
    log_info "🔍 Проверка системных требований..."
    
    # Check OS
    local os_name
    os_name="$(uname -s)"
    log_info "   ОС: ${os_name}"
    
    # Check Python
    local python_cmd
    python_cmd=$(get_python_cmd)
    
    if [ -z "$python_cmd" ]; then
        log_error "❌ Python не найден! Установите Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+"
        exit 1
    fi
    
    # Check Python version
    local python_version
    python_version=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    
    if [ -z "$python_version" ]; then
        log_error "❌ Не удалось определить версию Python."
        exit 1
    fi
    
    local major minor
    major=$(echo "$python_version" | cut -d. -f1)
    minor=$(echo "$python_version" | cut -d. -f2)
    
    if [ "$major" -lt "$REQUIRED_PYTHON_MAJOR" ] || { [ "$major" -eq "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -lt "$REQUIRED_PYTHON_MINOR" ]; }; then
        log_error "❌ Требуется Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+, найдено: ${python_version}"
        exit 1
    fi
    
    log_success "   Python: ${python_version} ($python_cmd)"
    
    # Check pip
    if ! $python_cmd -m pip --version &> /dev/null; then
        log_error "❌ pip не найден. Установите pip: $python_cmd -m ensurepip --upgrade"
        exit 1
    fi
    
    log_success "   pip: $($python_cmd -m pip --version | awk '{print $2}')"
    
    # Check curl for health checks
    if check_command curl; then
        log_success "   curl: найден (для health check)"
    elif check_command wget; then
        log_success "   wget: найден (для health check)"
    else
        log_warn "   ⚠️ curl/wget не найдены. Health check будет пропущен."
    fi
    
    # Check disk space (minimum 500MB)
    local available_space
    available_space=$(df -m "$SCRIPT_DIR" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 500 ]; then
        log_warn "   ⚠️ Мало места на диске: ${available_space}MB (рекомендуется 500MB+)"
    else
        log_success "   Свободное место: ${available_space}MB"
    fi
    
    log_success "✅ Системные требования выполнены."
}

# ─────────────────────────────────────────────────────────────
# 6. FILE INTEGRITY CHECK
# ─────────────────────────────────────────────────────────────
check_files() {
    log_info "📁 Проверка целостности файлов проекта..."
    
    local required_files=(
        "app.py"
        "config.py"
        "brain.py"
        "cloner.py"
        "utils.py"
        "requirements.txt"
    )
    
    local missing=0
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "   ❌ Отсутствует: $file"
            missing=1
        else
            log_debug "   ✓ $file"
        fi
    done
    
    # Check templates directory
    if [ ! -d "templates" ]; then
        log_error "   ❌ Отсутствует папка: templates/"
        missing=1
    else
        local html_count
        html_count=$(find templates -name "*.html" 2>/dev/null | wc -l)
        log_debug "   ✓ templates/ (${html_count} HTML файлов)"
    fi
    
    if [ "$missing" -eq 1 ]; then
        log_error "❌ Критические файлы отсутствуют. Запуск невозможен."
        exit 1
    fi
    
    log_success "✅ Все файлы на месте."
}

# ─────────────────────────────────────────────────────────────
# 7. VIRTUAL ENVIRONMENT MANAGEMENT
# ─────────────────────────────────────────────────────────────
setup_venv() {
    local python_cmd
    python_cmd=$(get_python_cmd)
    
    if [ ! -d "$VENV_DIR" ]; then
        log_info "📦 Создание виртуального окружения (venv)..."
        if ! $python_cmd -m venv "$VENV_DIR"; then
            log_error "❌ Не удалось создать venv."
            exit 1
        fi
        log_success "✅ Виртуальное окружение создано."
        smart_delay "инициализация venv"
    else
        log_info "   ✓ venv уже существует."
    fi
    
    # Activate venv (cross-platform)
    log_info "🔄 Активация виртуального окружения..."
    
    local activate_script=""
    if [ -f "${VENV_DIR}/bin/activate" ]; then
        activate_script="${VENV_DIR}/bin/activate"
    elif [ -f "${VENV_DIR}/Scripts/activate" ]; then
        activate_script="${VENV_DIR}/Scripts/activate"
    elif [ -f "${VENV_DIR}/Scripts/activate.bat" ]; then
        # Git Bash on Windows
        activate_script="${VENV_DIR}/Scripts/activate"
    fi
    
    if [ -z "$activate_script" ]; then
        log_error "❌ Не найден скрипт активации venv."
        exit 1
    fi
    
    # shellcheck disable=SC1090
    source "$activate_script"
    
    # Verify activation
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        log_error "❌ Не удалось активировать venv."
        exit 1
    fi
    
    log_success "✅ venv активирован: $(basename "$VIRTUAL_ENV")"
    
    # Upgrade pip quietly
    log_info "   ⬆️ Обновление pip..."
    python -m pip install --upgrade pip --quiet --disable-pip-version-check 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────
# 8. DEPENDENCY INSTALLATION (SMART)
# ─────────────────────────────────────────────────────────────
install_dependencies() {
    log_info "📥 Установка зависимостей из requirements.txt..."
    
    # Check if requirements.txt is empty
    if [ ! -s "requirements.txt" ]; then
        log_warn "   ⚠️ requirements.txt пуст. Пропускаем установку."
        return 0
    fi
    
    # Count packages
    local pkg_count
    pkg_count=$(grep -v '^\s*#' requirements.txt | grep -v '^\s*$' | wc -l)
    log_info "   Найдено пакетов: ${pkg_count}"
    
    # Try standard install
    log_info "   Установка пакетов (это может занять время)..."
    
    if pip install -r requirements.txt --quiet --disable-pip-version-check 2>>"$LOG_FILE"; then
        log_success "✅ Зависимости успешно установлены."
    else
        log_warn "   ⚠️ Стандартная установка не удалась. Пробуем альтернативные методы..."
        
        # Try with --user flag
        if pip install -r requirements.txt --user --quiet --disable-pip-version-check 2>>"$LOG_FILE"; then
            log_success "✅ Зависимости установлены в пользовательскую директорию."
        else
            # Try installing packages one by one (skip broken ones)
            log_warn "   ⚠️ Пакетная установка не удалась. Устанавливаем по одному..."
            local failed_pkgs=()
            
            while IFS= read -r pkg || [ -n "$pkg" ]; do
                # Skip comments and empty lines
                [[ "$pkg" =~ ^\s*# ]] && continue
                [[ -z "${pkg// }" ]] && continue
                
                log_debug "   Установка: $pkg"
                if ! pip install "$pkg" --quiet --disable-pip-version-check 2>>"$LOG_FILE"; then
                    log_warn "   ⚠️ Не удалось установить: $pkg"
                    failed_pkgs+=("$pkg")
                fi
            done < requirements.txt
            
            if [ ${#failed_pkgs[@]} -gt 0 ]; then
                log_warn "   ⚠️ Не установленные пакеты: ${failed_pkgs[*]}"
                log_warn "   Приложение может работать с ограничениями."
            else
                log_success "✅ Все пакеты установлены по отдельности."
            fi
        fi
    fi
    
    # Special handling for curl_cffi (known problematic package)
    if grep -q "curl_cffi" requirements.txt 2>/dev/null; then
        log_info "   🔧 Проверка curl_cffi (TLS spoofing)..."
        if python -c "import curl_cffi" 2>/dev/null; then
            log_success "   ✓ curl_cffi работает."
        else
            log_warn "   ⚠️ curl_cffi не работает. Будет использован стандартный requests."
            log_warn "   Для установки: pip install curl_cffi --upgrade"
        fi
    fi
    
    smart_delay "стабилизация после установки зависимостей"
}

# ─────────────────────────────────────────────────────────────
# 9. SAFE .ENV PARSER (ULTRA FIX)
# ─────────────────────────────────────────────────────────────
load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        log_info "   ℹ️ Файл .env не найден. Используем значения по умолчанию."
        return 0
    fi
    
    log_info "🔐 Загрузка переменных окружения из .env..."
    
    local loaded=0
    local skipped=0
    
    # Read line by line (safe parsing)
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        [[ -z "${line// }" ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Extract key and value
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)[[:space:]]*$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            
            # Remove surrounding quotes if present
            value="${value%\"}"
            value="${value#\"}"
            value="${value%\'}"
            value="${value#\'}"
            
            # Export the variable
            export "$key=$value"
            loaded=$((loaded + 1))
            log_debug "   ✓ $key"
        else
            skipped=$((skipped + 1))
            log_debug "   ⚠️ Пропущена строка: $line"
        fi
    done < "$ENV_FILE"
    
    log_success "✅ Загружено переменных: ${loaded}, пропущено: ${skipped}"
    
    # Override PORT if set in .env
    if [ -n "${PORT:-}" ]; then
        APP_PORT="$PORT"
        HEALTH_CHECK_URL="http://127.0.0.1:${APP_PORT}/api/health"
    fi
}

# ─────────────────────────────────────────────────────────────
# 10. PORT & PROCESS MANAGEMENT
# ─────────────────────────────────────────────────────────────
check_port() {
    log_info "🔌 Проверка порта ${APP_PORT}..."
    
    local port_in_use=0
    
    # Method 1: ss (Linux)
    if check_command ss; then
        if ss -tuln 2>/dev/null | grep -q ":${APP_PORT} "; then
            port_in_use=1
        fi
    # Method 2: lsof (macOS/Linux)
    elif check_command lsof; then
        if lsof -i ":${APP_PORT}" > /dev/null 2>&1; then
            port_in_use=1
        fi
    # Method 3: netstat (fallback)
    elif check_command netstat; then
        if netstat -tuln 2>/dev/null | grep -q ":${APP_PORT} "; then
            port_in_use=1
        fi
    # Method 4: Python socket check (cross-platform)
    else
        if python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = s.connect_ex(('127.0.0.1', ${APP_PORT}))
s.close()
exit(0 if result == 0 else 1)
" 2>/dev/null; then
            port_in_use=1
        fi
    fi
    
    if [ "$port_in_use" -eq 1 ]; then
        log_warn "   ⚠️ Порт ${APP_PORT} уже используется!"
        
        # Try to find the process
        local pid=""
        if check_command lsof; then
            pid=$(lsof -ti ":${APP_PORT}" 2>/dev/null | head -n1)
        elif check_command fuser; then
            pid=$(fuser "${APP_PORT}/tcp" 2>/dev/null | awk '{print $1}')
        fi
        
        if [ -n "$pid" ]; then
            log_warn "   Процесс: PID ${pid}"
            
            # Check if it's our previous instance
            if [ -f "$PID_FILE" ] && [ "$(cat "$PID_FILE" 2>/dev/null)" = "$pid" ]; then
                log_info "   Обнаружен предыдущий экземпляр. Остановка..."
                kill -TERM "$pid" 2>/dev/null || true
                sleep 2
                kill -9 "$pid" 2>/dev/null || true
                rm -f "$PID_FILE"
                log_success "   ✅ Предыдущий экземпляр остановлен."
            else
                log_warn "   ⚠️ Порт занят другим процессом. Возможны конфликты."
                log_warn "   Завершите процесс: kill ${pid}"
                log_warn "   Или измените порт в .env файле."
            fi
        fi
    else
        log_success "   ✓ Порт ${APP_PORT} свободен."
    fi
}

# ─────────────────────────────────────────────────────────────
# 11. HEALTH CHECK
# ─────────────────────────────────────────────────────────────
health_check() {
    log_info "🏥 Проверка работоспособности сервера..."
    
    local retries=$HEALTH_CHECK_RETRIES
    local attempt=1
    
    while [ $attempt -le $retries ]; do
        log_debug "   Попытка ${attempt}/${retries}..."
        
        local http_code=""
        
        if check_command curl; then
            http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_CHECK_URL" 2>/dev/null || echo "000")
        elif check_command wget; then
            if wget -q --spider --timeout=5 "$HEALTH_CHECK_URL" 2>/dev/null; then
                http_code="200"
            else
                http_code="000"
            fi
        else
            # Fallback: Python urllib
            http_code=$(python -c "
import urllib.request
try:
    r = urllib.request.urlopen('${HEALTH_CHECK_URL}', timeout=5)
    print(r.getcode())
except:
    print('000')
" 2>/dev/null || echo "000")
        fi
        
        if [ "$http_code" = "200" ]; then
            log_success "✅ Сервер работает! HTTP 200 OK"
            return 0
        fi
        
        log_debug "   HTTP код: ${http_code}. Ожидание 2с..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_warn "   ⚠️ Сервер не ответил после ${retries} попыток."
    log_warn "   Проверьте логи: ${LOG_FILE}"
    return 1
}

# ─────────────────────────────────────────────────────────────
# 12. WATCHDOG / AUTO-RESTART
# ─────────────────────────────────────────────────────────────
run_app() {
    local restart_count=0
    local max_restarts=10
    
    log_info "🚀 Запуск Discord Cloner..."
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Discord Server Cloner v9.0 ULTRA${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e " 🌐 Адрес: ${CYAN}http://localhost:${APP_PORT}${NC}"
    echo -e " 📋 Логи:  ${CYAN}${LOG_FILE}${NC}"
    echo -e " 🛑 Стоп:  ${RED}Ctrl+C${NC}"
    echo ""
    
    # ULTRA: Strategic pause before first launch
    smart_delay "подготовка к запуску"
    
    while true; do
        # Run app.py and capture PID
        python app.py &
        APP_PID=$!
        echo "$APP_PID" > "$PID_FILE"
        
        log_info "   ▶ app.py запущен (PID: ${APP_PID})"
        
        # Wait for the process to exit
        wait "$APP_PID"
        local exit_code=$?
        
        # Check if we should restart
        if [ $exit_code -eq 0 ]; then
            log_info "   ℹ️ app.py завершился нормально (код 0)."
            break
        fi
        
        restart_count=$((restart_count + 1))
        
        if [ $restart_count -ge $max_restarts ]; then
            log_error "❌ Достигнут лимит перезапусков (${max_restarts}). Остановка."
            break
        fi
        
        log_warn "   ⚠️ app.py завершился с ошибкой (код: ${exit_code})."
        log_warn "   🔄 Перезапуск через ${RESTART_DELAY}с... (попытка ${restart_count}/${max_restarts})"
        
        sleep "$RESTART_DELAY"
    done
    
    rm -f "$PID_FILE"
}

# ─────────────────────────────────────────────────────────────
# 13. MAIN EXECUTION FLOW
# ─────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║   Discord Server Cloner v9.0 ULTRA (2026)   ║${NC}"
    echo -e "${CYAN}${BOLD}║   Production Run Script                     ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Step 1: System checks
    check_system
    echo ""
    
    # Step 2: File integrity
    check_files
    echo ""
    
    # Step 3: Virtual environment
    setup_venv
    echo ""
    
    # Step 4: Dependencies
    install_dependencies
    echo ""
    
    # Step 5: Environment variables
    load_env
    echo ""
    
    # Step 6: Port check
    check_port
    echo ""
    
    # Step 7: Run with watchdog
    run_app
    
    # Final cleanup
    cleanup
}

# ─────────────────────────────────────────────────────────────
# 14. ENTRY POINT
# ─────────────────────────────────────────────────────────────
main "$@"