@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Discord Server Cloner v8.0 ULTRA — Windows Launch Script
:: ============================================================

:: Включаем поддержку ANSI-цветов для Windows 10/11
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1
chcp 65001 >nul 2>&1

:: Цвета
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "WHITE=[97m"
set "RESET=[0m"

title Discord Cloner v8.0 ULTRA

:: Переходим в папку скрипта (критично при запуске из Проводника или ярлыка)
cd /d "%~dp0"

echo %CYAN%============================================================%RESET%
echo %WHITE%   Discord Server Cloner v8.0 ULTRA%RESET%
echo %CYAN%============================================================%RESET%
echo %BLUE%   Рабочая директория: %WHITE%%CD%%RESET%
echo %CYAN%============================================================%RESET%
echo.

:: ─────────────────────────────────────────────────────────────
:: 1. Проверка Python (приоритет: py launcher, затем python)
:: ─────────────────────────────────────────────────────────────
echo %BLUE%[*] Проверка окружения Python...%RESET%

set "PYTHON_CMD="
where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=python"
)

if "%PYTHON_CMD%"=="" (
    echo %RED%[ERROR] Python не найден!%RESET%
    echo %WHITE%  Установите Python 3.8+ и обязательно отметьте "Add Python to PATH".%RESET%
    echo %WHITE%  Скачать: https://www.python.org/downloads/%RESET%
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo %GREEN%[OK] %WHITE%Найден Python %PY_VER%%RESET%

:: Проверка минимальной версии (3.8)
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if %PY_MAJOR% LSS 3 (
    echo %RED%[ERROR] Требуется Python 3.8 или выше. У вас: %PY_VER%%RESET%
    pause & exit /b 1
)
if %PY_MAJOR%==3 if %PY_MINOR% LSS 8 (
    echo %RED%[ERROR] Требуется Python 3.8 или выше. У вас: %PY_VER%%RESET%
    pause & exit /b 1
)

:: ─────────────────────────────────────────────────────────────
:: 2. Виртуальное окружение (venv)
:: ─────────────────────────────────────────────────────────────
set "VENV_PY=%~dp0venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo %BLUE%[*] Создание виртуального окружения (venv)...%RESET%
    %PYTHON_CMD% -m venv "%~dp0venv"
    if errorlevel 1 (
        echo %RED%[ERROR] Не удалось создать venv. Проверьте права администратора или антивирус.%RESET%
        pause & exit /b 1
    )
    echo %GREEN%[OK] Виртуальное окружение создано.%RESET%
) else (
    echo %GREEN%[OK] Виртуальное окружение найдено.%RESET%
)

:: ─────────────────────────────────────────────────────────────
:: 3. Обновление pip и установка зависимостей
:: ─────────────────────────────────────────────────────────────
echo %BLUE%[*] Обновление pip и установка зависимостей...%RESET%
"%VENV_PY%" -m pip install --upgrade pip --quiet --no-warn-script-location

if exist "%~dp0requirements.txt" (
    :: Пытаемся установить. Если есть C-зависимости, вывод может быть полезен, поэтому убираем полный quiet при ошибке
    "%VENV_PY%" -m pip install -r "%~dp0requirements.txt" --no-warn-script-location
    if errorlevel 1 (
        echo.
        echo %RED%[ERROR] Ошибка установки зависимостей!%RESET%
        echo %YELLOW%Возможные причины:%RESET%
        echo  %WHITE%1. Нет доступа к интернету.%RESET%
        echo  %WHITE%2. Отсутствуют Visual Studio Build Tools (нужны для cryptography/aiohttp).%RESET%
        echo  %WHITE%3. Запустите этот файл от имени Администратора.%RESET%
        echo.
        pause
        exit /b 1
    )
    echo %GREEN%[OK] Зависимости успешно установлены.%RESET%
) else (
    echo %YELLOW%[WARN] Файл requirements.txt не найден. Пропуск.%RESET%
)

:: ─────────────────────────────────────────────────────────────
:: 4. Настройка .env и проверка порта
:: ─────────────────────────────────────────────────────────────
if not exist "%~dp0.env" (
    echo %BLUE%[*] Создание файла конфигурации .env...%RESET%
    (
        echo DISCORD_API=https://discord.com/api/v10
        echo HOST=127.0.0.1
        echo PORT=5500
        echo DEBUG=true
        echo LOG_LEVEL=INFO
    ) > "%~dp0.env"
    echo %GREEN%[OK] Файл .env создан со значениями по умолчанию.%RESET%
) else (
    echo %GREEN%[OK] Файл .env найден.%RESET%
)

:: Читаем порт из .env (ищем строку, начинающуюся с PORT=)
set "PORT=5500"
for /f "tokens=2 delims==" %%a in ('findstr /I /B "PORT=" "%~dp0.env" 2^>nul') do set "PORT=%%a"
:: Убираем возможные пробелы или кавычки
set "PORT=%PORT: =%"
set "PORT=%PORT:"=%"

:: Проверка занятости порта через netstat
netstat -ano | findstr /R /C:"LISTENING.*:%PORT%" >nul 2>&1
if %errorlevel%==0 (
    echo %YELLOW%[WARN] ВНИМАНИЕ: Порт %PORT% уже используется другим процессом!%RESET%
    echo %YELLOW%       Если сервер не запустится, измените PORT в файле .env%RESET%
)

:: ─────────────────────────────────────────────────────────────
:: 5. Проверка основных файлов и запуск
:: ─────────────────────────────────────────────────────────────
if not exist "%~dp0app.py" (
    echo %RED%[ERROR] Файл app.py не найден в директории %~dp0%RESET%
    pause & exit /b 1
)

echo.
echo %GREEN%============================================================%RESET%
echo %GREEN%  [OK] Всё готово к работе!%RESET%
echo %GREEN%============================================================%RESET%
echo %WHITE%  🌐 Откройте браузер: %CYAN%http://localhost:%PORT%%RESET%
echo %WHITE%  💡 Для остановки нажмите: %RED%Ctrl+C%RESET%
echo %GREEN%============================================================%RESET%
echo.

:: Запуск приложения
"%VENV_PY%" "%~dp0app.py"

:: ─────────────────────────────────────────────────────────────
:: 6. Завершение работы
:: ─────────────────────────────────────────────────────────────
echo.
if errorlevel 1 (
    echo %RED%[ERROR] Сервер завершил работу с ошибкой.%RESET%
    echo %WHITE%  Проверьте логи выше или запустите вручную для отладки:%RESET%
    echo %WHITE%  cd /d "%~dp0" ^&^& venv\Scripts\python.exe app.py%RESET%
) else (
    echo %GREEN%[DONE] Сервер корректно остановлен.%RESET%
)

echo.
pause
exit /b 0