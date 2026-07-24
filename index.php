{% extends "base.html" %}

{% block title %}dc://cloner — Discord Server Cloner v9.0 ULTRA{% endblock %}

{% block content %}
<!-- Глобальные стили для ULTRA эффектов -->
<style>
  .glass-panel {
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(75, 85, 99, 0.4);
  }
  .input-ultra {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(75, 85, 99, 0.5);
    transition: all 0.2s ease;
  }
  .input-ultra:focus {
    border-color: #10b981; /* emerald-500 */
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    outline: none;
  }
  /* Кастомный чекбокс (Toggle) */
  .toggle-checkbox:checked {
    right: 0;
    border-color: #10b981;
  }
  .toggle-checkbox:checked + .toggle-label {
    background-color: #10b981;
  }
  /* Анимация пульсации для онлайн статуса */
  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
    50% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  }
  .pulse-glow { animation: pulse-glow 2s infinite; }
  
  /* Цвета логов */
  .log-info { color: #9ca3af; }
  .log-success { color: #34d399; font-weight: 600; }
  .log-warn { color: #fbbf24; }
  .log-error { color: #f87171; font-weight: 600; }
</style>

<!-- Hero Section -->
<section class="pt-20 pb-10 px-4 relative overflow-hidden">
  <!-- Декоративный фон -->
  <div class="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-4xl bg-gradient-to-b from-emerald-500/10 to-transparent pointer-events-none blur-3xl"></div>
  
  <div class="max-w-4xl mx-auto text-center relative z-10">
    <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-800/50 border border-gray-700 mb-6 text-[11px] text-emerald-400 font-medium tracking-wider uppercase">
      <span class="w-2 h-2 rounded-full bg-emerald-500 pulse-glow"></span>
      System Online • v9.0 ULTRA
    </div>
    <h1 class="text-3xl md:text-5xl font-bold text-white leading-tight mb-4 tracking-tight">
      Discord Server <span class="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">Cloner</span>
    </h1>
    <p class="text-gray-400 text-sm md:text-base max-w-xl mx-auto mb-8 leading-relaxed">
      Полное копирование серверов: каналы, роли, эмодзи, настройки и права. 
      Максимальная скорость, обход лимитов и защита аккаунта.
    </p>
    
    <!-- Блок Техподдержки -->
    <a href="https://t.me/Angels_Squads" target="_blank" class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#229ED9]/10 border border-[#229ED9]/30 text-[#229ED9] hover:bg-[#229ED9]/20 hover:border-[#229ED9]/50 transition-all duration-300 text-sm font-medium group">
      <svg class="w-5 h-5 group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
      Нужна помощь? Напишите в техподдержку @Angels_Squads
      <svg class="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
    </a>
  </div>
</section>

<!-- Main Grid -->
<section class="px-4 pb-20" id="cloner">
  <div class="max-w-6xl mx-auto grid lg:grid-cols-2 gap-6">

    <!-- ==================== CLONER PANEL ==================== -->
    <div class="glass-panel rounded-2xl p-6 shadow-2xl shadow-black/20">
      <div class="flex items-center gap-3 mb-6 pb-4 border-b border-gray-700/50">
        <div class="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
        </div>
        <div>
          <h2 class="text-white font-semibold text-lg">Клонирование сервера</h2>
          <p class="text-gray-500 text-xs">Настройте параметры и запустите процесс</p>
        </div>
      </div>

      <form id="cloneForm" class="space-y-4">
        <!-- Token & Validate -->
        <div>
          <label class="block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wide">User Token</label>
          <div class="flex gap-2">
            <input type="password" id="token" required class="input-ultra w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-gray-600" placeholder="Вставьте ваш Discord токен">
            <button type="button" id="validateBtn" class="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 transition-colors text-xs font-medium whitespace-nowrap">
              Проверить
            </button>
          </div>
          <p id="tokenStatus" class="text-xs mt-1.5 h-4"></p>
        </div>

        <!-- IDs -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wide">ID Источника</label>
            <input type="text" id="guildId" required class="input-ultra w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-gray-600" placeholder="1234567890">
          </div>
          <div>
            <label class="block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wide">ID Цели</label>
            <input type="text" id="targetId" required class="input-ultra w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-gray-600" placeholder="0987654321">
          </div>
        </div>

        <!-- Proxies -->
        <div>
          <label class="block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wide">Прокси (опционально)</label>
          <input type="text" id="proxies" class="input-ultra w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-gray-600" placeholder="http://user:pass@ip:port, socks5://...">
        </div>

        <div class="h-px bg-gray-700/50 my-2"></div>

        <!-- Options Toggles -->
        <div>
          <label class="block text-gray-400 text-xs font-medium mb-3 uppercase tracking-wide">Параметры клонирования</label>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <!-- Toggle Item -->
            <label class="flex items-center justify-between p-3 rounded-lg bg-gray-800/30 border border-gray-700/50 cursor-pointer hover:border-emerald-500/50 transition-colors">
              <span class="text-sm text-gray-300">Каналы</span>
              <div class="relative inline-block w-10 mr-2 align-middle select-none">
                <input type="checkbox" id="cloneChannels" checked class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-gray-700 appearance-none cursor-pointer transition-all duration-300" style="top: 2px; left: 2px;"/>
                <label class="toggle-label block overflow-hidden h-6 rounded-full bg-gray-700 cursor-pointer transition-colors duration-300"></label>
              </div>
            </label>
            <!-- Toggle Item -->
            <label class="flex items-center justify-between p-3 rounded-lg bg-gray-800/30 border border-gray-700/50 cursor-pointer hover:border-emerald-500/50 transition-colors">
              <span class="text-sm text-gray-300">Роли</span>
              <div class="relative inline-block w-10 mr-2 align-middle select-none">
                <input type="checkbox" id="cloneRoles" checked class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-gray-700 appearance-none cursor-pointer transition-all duration-300" style="top: 2px; left: 2px;"/>
                <label class="toggle-label block overflow-hidden h-6 rounded-full bg-gray-700 cursor-pointer transition-colors duration-300"></label>
              </div>
            </label>
            <!-- Toggle Item -->
            <label class="flex items-center justify-between p-3 rounded-lg bg-gray-800/30 border border-gray-700/50 cursor-pointer hover:border-emerald-500/50 transition-colors">
              <span class="text-sm text-gray-300">Эмодзи и Стикеры</span>
              <div class="relative inline-block w-10 mr-2 align-middle select-none">
                <input type="checkbox" id="cloneEmojis" checked class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-gray-700 appearance-none cursor-pointer transition-all duration-300" style="top: 2px; left: 2px;"/>
                <label class="toggle-label block overflow-hidden h-6 rounded-full bg-gray-700 cursor-pointer transition-colors duration-300"></label>
              </div>
            </label>
            <!-- Toggle Item -->
            <label class="flex items-center justify-between p-3 rounded-lg bg-gray-800/30 border border-gray-700/50 cursor-pointer hover:border-emerald-500/50 transition-colors">
              <span class="text-sm text-gray-300">Очистить цель (Purge)</span>
              <div class="relative inline-block w-10 mr-2 align-middle select-none">
                <input type="checkbox" id="purgeTarget" checked class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 border-gray-700 appearance-none cursor-pointer transition-all duration-300" style="top: 2px; left: 2px;"/>
                <label class="toggle-label block overflow-hidden h-6 rounded-full bg-gray-700 cursor-pointer transition-colors duration-300"></label>
              </div>
            </label>
          </div>
        </div>

        <button type="submit" id="cloneBtn" class="w-full py-3 rounded-lg bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-semibold text-sm shadow-lg shadow-emerald-500/20 transition-all duration-300 flex items-center justify-center gap-2 mt-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Запустить клонирование
        </button>
      </form>

      <!-- Progress & Log -->
      <div id="progress" class="hidden mt-6 space-y-3 fade-in">
        <div class="flex justify-between items-end mb-1">
          <span id="progressText" class="text-xs text-emerald-400 font-medium">Инициализация...</span>
          <span id="progressPercent" class="text-xs text-gray-500">0%</span>
        </div>
        <div class="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div id="progressBar" class="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-500 ease-out" style="width:0%"></div>
        </div>
        
        <div id="log" class="hidden">
          <div class="flex items-center gap-2 mb-2">
            <svg class="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
            <span class="text-xs text-gray-500 uppercase tracking-wider font-semibold">Console Log</span>
          </div>
          <div id="logContent" class="bg-black/40 border border-gray-800 rounded-lg p-3 max-h-56 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-1"></div>
        </div>
      </div>
    </div>

    <!-- ==================== ROLE MANAGER PANEL ==================== -->
    <div class="glass-panel rounded-2xl p-6 shadow-2xl shadow-black/20">
      <div class="flex items-center gap-3 mb-6 pb-4 border-b border-gray-700/50">
        <div class="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
        </div>
        <div>
          <h2 class="text-white font-semibold text-lg">Массовая выдача ролей</h2>
          <p class="text-gray-500 text-xs">Быстрое назначение роли всем участникам</p>
        </div>
      </div>

      <form id="roleForm" class="space-y-4">
        <div>
          <label class="block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wide">User Token</label>
          <input type="password" id="roleToken" required class="input-ultra w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-gray-600" placeholder="Токен с правами администратора">
        </div>

        <div>
          <label class="block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wide">ID Сервера</label>
          <input type="text" id="roleGuildId" required class="input-ultra w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-gray-600" placeholder="ID сервера для выдачи">
        </div>

        <button type="button" id="loadRolesBtn" class="w-full py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 transition-all duration-300 flex items-center justify-center gap-2 text-sm font-medium">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          Загрузить список ролей
        </button>

        <div id="roleSelectBlock" class="hidden space-y-4 fade-in">
          <div>
            <label class="block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wide">Выберите роль</label>
            <select id="roleSelect" class="input-ultra w-full px-3 py-2.5 rounded-lg text-sm text-white bg-gray-900 cursor-pointer">
              <option value="" disabled selected>Загрузка...</option>
            </select>
          </div>

          <button type="submit" id="assignRoleBtn" class="w-full py-3 rounded-lg bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm shadow-lg shadow-indigo-500/20 transition-all duration-300 flex items-center justify-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            Выдать роль всем участникам
          </button>
        </div>
      </form>

      <!-- Role Progress & Log -->
      <div id="roleProgress" class="hidden mt-6 space-y-3 fade-in">
        <div class="flex justify-between items-end mb-1">
          <span id="roleProgressText" class="text-xs text-indigo-400 font-medium">Подготовка...</span>
          <span id="roleProgressPercent" class="text-xs text-gray-500">0%</span>
        </div>
        <div class="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div id="roleProgressBar" class="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out" style="width:0%"></div>
        </div>
        
        <div id="roleLog" class="hidden">
          <div class="flex items-center gap-2 mb-2">
            <svg class="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
            <span class="text-xs text-gray-500 uppercase tracking-wider font-semibold">Console Log</span>
          </div>
          <div id="roleLogContent" class="bg-black/40 border border-gray-800 rounded-lg p-3 max-h-56 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-1"></div>
        </div>
      </div>
    </div>

  </div>
</section>
{% endblock %}

{% block scripts %}
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
  const socket = io();

  // --- Утилиты ---
  function formatLogMessage(msg) {
    // Простой парсер для раскраски логов
    let className = 'log-info';
    if (msg.includes('✅') || msg.includes('done') || msg.includes('success') || msg.includes('Успех')) className = 'log-success';
    else if (msg.includes('⚠️') || msg.includes('warn') || msg.includes('Пауза')) className = 'log-warn';
    else if (msg.includes('❌') || msg.includes('error') || msg.includes('Ошибка') || msg.includes('429')) className = 'log-error';
    
    const div = document.createElement('div');
    div.className = className;
    div.textContent = `> ${msg}`;
    return div;
  }

  // --- Cloner Logic ---
  const cloneForm = document.getElementById('cloneForm');
  const cloneBtn = document.getElementById('cloneBtn');
  const progress = document.getElementById('progress');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const progressPercent = document.getElementById('progressPercent');
  const log = document.getElementById('log');
  const logContent = document.getElementById('logContent');
  const tokenStatus = document.getElementById('tokenStatus');

  // Валидация токена
  document.getElementById('validateBtn').addEventListener('click', () => {
    const token = document.getElementById('token').value.trim();
    if (!token) return;
    
    tokenStatus.textContent = 'Проверка...';
    tokenStatus.className = 'text-xs mt-1.5 h-4 text-gray-400';
    
    socket.emit('validate_token', { token: token });
  });

  socket.on('token_valid', (d) => {
    if (d.valid) {
      tokenStatus.textContent = `✓ Успешно: ${d.username} (ID: ${d.id})`;
      tokenStatus.className = 'text-xs mt-1.5 h-4 text-emerald-400 font-medium';
    } else {
      tokenStatus.textContent = `✗ Ошибка: ${d.error}`;
      tokenStatus.className = 'text-xs mt-1.5 h-4 text-red-400 font-medium';
    }
  });

  socket.on('log', (d) => { 
    if (d.message) {
      log.classList.remove('hidden');
      logContent.appendChild(formatLogMessage(d.message));
      logContent.scrollTop = logContent.scrollHeight;
    }
  });

  socket.on('progress', (d) => {
    progress.classList.remove('hidden');
    if (d.total > 0) {
      const p = Math.round((d.current / d.total) * 100);
      progressBar.style.width = p + '%';
      progressPercent.textContent = p + '%';
      progressText.textContent = d.step;
    }
  });

  socket.on('clone_done', (d) => {
    cloneBtn.disabled = false;
    cloneBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Запустить клонирование`;
    
    if (d.success) {
      progressBar.className = 'h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-500 ease-out';
      progressBar.style.width = '100%';
      progressPercent.textContent = '100%';
      progressText.textContent = 'Клонирование успешно завершено!';
      logContent.appendChild(formatLogMessage('✅ Процесс успешно завершен.'));
    } else {
      progressBar.className = 'h-full bg-red-500 rounded-full transition-all duration-500 ease-out';
      progressText.textContent = 'Процесс остановлен с ошибкой';
      logContent.appendChild(formatLogMessage(`❌ Ошибка: ${d.error || 'Неизвестная ошибка'}`));
    }
    logContent.scrollTop = logContent.scrollHeight;
  });

  cloneForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const s = document.getElementById('guildId').value.trim();
    const t = document.getElementById('targetId').value.trim();
    const token = document.getElementById('token').value.trim();
    
    if (!s || !t || !token) { 
      alert('Пожалуйста, заполните токен и оба ID сервера'); 
      return; 
    }

    cloneBtn.disabled = true;
    cloneBtn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Обработка...`;
    
    progress.classList.remove('hidden');
    log.classList.remove('hidden');
    logContent.innerHTML = '';
    progressBar.style.width = '0%';
    progressBar.className = 'h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-500 ease-out';
    progressPercent.textContent = '0%';
    progressText.textContent = 'Инициализация...';

    // Парсинг прокси
    const proxyRaw = document.getElementById('proxies').value.trim();
    const proxies = proxyRaw ? proxyRaw.split(',').map(p => p.trim()).filter(p => p) : [];

    socket.emit('start_clone', {
      token: token,
      source_id: s, 
      target_id: t,
      proxies: proxies,
      options: {
        channels: document.getElementById('cloneChannels').checked,
        roles: document.getElementById('cloneRoles').checked,
        emojis: document.getElementById('cloneEmojis').checked,
        purge: document.getElementById('purgeTarget').checked
      }
    });
  });

  // --- Role Manager Logic ---
  const roleForm = document.getElementById('roleForm');
  const loadBtn = document.getElementById('loadRolesBtn');
  const selBlock = document.getElementById('roleSelectBlock');
  const sel = document.getElementById('roleSelect');
  const assignBtn = document.getElementById('assignRoleBtn');
  const rp = document.getElementById('roleProgress');
  const rpb = document.getElementById('roleProgressBar');
  const rpt = document.getElementById('roleProgressText');
  const rpPercent = document.getElementById('roleProgressPercent');
  const rl = document.getElementById('roleLog');
  const rlc = document.getElementById('roleLogContent');

  socket.on('assign_log', (d) => { 
    if (d.message) {
      rl.classList.remove('hidden');
      rlc.appendChild(formatLogMessage(d.message));
      rlc.scrollTop = rlc.scrollHeight;
    }
  });

  socket.on('assign_progress', (d) => {
    rp.classList.remove('hidden');
    if (d.total > 0) {
      const p = Math.round((d.current / d.total) * 100);
      rpb.style.width = p + '%';
      rpPercent.textContent = p + '%';
      rpt.textContent = d.step;
    }
  });

  socket.on('guild_roles', (d) => {
    loadBtn.disabled = false;
    loadBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg> Загрузить список ролей`;
    
    if (d.error) { 
      rlc.appendChild(formatLogMessage(`✗ Ошибка загрузки: ${d.error}`)); 
      rl.classList.remove('hidden');
      return; 
    }
    
    const roles = d.roles || [];
    if (!roles.length) { 
      rlc.appendChild(formatLogMessage('⚠ На сервере не найдено пользовательских ролей')); 
      rl.classList.remove('hidden');
      return; 
    }
    
    sel.innerHTML = '<option value="" disabled selected>Выберите роль для выдачи</option>';
    roles.forEach((r) => {
      if (r.name === '@everyone' || r.managed) return;
      const o = document.createElement('option');
      o.value = r.id;
      const c = r.color ? `#${r.color.toString(16).padStart(6, '0')}` : '#9ca3af';
      o.textContent = `${r.name} (ID: ${r.id})`;
      o.style.color = c;
      sel.appendChild(o);
    });
    
    selBlock.classList.remove('hidden');
    assignBtn.disabled = false;
    rlc.appendChild(formatLogMessage(`✓ Успешно загружено ${sel.options.length - 1} ролей`));
    rl.classList.remove('hidden');
  });

  socket.on('assign_done', (d) => {
    assignBtn.disabled = false;
    assignBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Выдать роль всем участникам`;
    
    if (d.success) {
      rpb.className = 'h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-500 ease-out';
      rpb.style.width = '100%';
      rpPercent.textContent = '100%';
      rpt.textContent = 'Выдача завершена';
      rlc.appendChild(formatLogMessage(`✅ Готово! Выдано: ${d.assigned||0} | Уже имели: ${d.already||0} | Ошибки: ${d.errors||0}`));
    } else {
      rpb.className = 'h-full bg-red-500 rounded-full transition-all duration-500 ease-out';
      rpt.textContent = 'Процесс остановлен';
      rlc.appendChild(formatLogMessage(`❌ Ошибка: ${d.error || 'Неизвестная ошибка'}`));
    }
    rlc.scrollTop = rlc.scrollHeight;
  });

  loadBtn.addEventListener('click', () => {
    const tk = document.getElementById('roleToken').value.trim();
    const gid = document.getElementById('roleGuildId').value.trim();
    if (!tk || !gid) { alert('Укажите токен и ID сервера'); return; }
    
    loadBtn.disabled = true;
    loadBtn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Загрузка...`;
    selBlock.classList.add('hidden');
    assignBtn.disabled = true;
    rlc.innerHTML = '';
    rp.classList.add('hidden');
    rl.classList.add('hidden');
    
    socket.emit('get_guild_roles', { token: tk, guild_id: gid });
  });

  roleForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const tk = document.getElementById('roleToken').value.trim();
    const gid = document.getElementById('roleGuildId').value.trim();
    const rid = sel.value;
    
    if (!tk || !gid || !rid) { alert('Загрузите роли и выберите одну из списка'); return; }
    
    const roleName = sel.options[sel.selectedIndex].text;
    if (!confirm(`Вы уверены, что хотите выдать роль "${roleName}" всем участникам сервера? Это действие может занять время.`)) return;

    assignBtn.disabled = true;
    assignBtn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Выдача ролей...`;
    
    rlc.innerHTML = '';
    rpb.style.width = '0%';
    rpb.className = 'h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out';
    rpPercent.textContent = '0%';
    rpt.textContent = 'Инициализация...';
    rp.classList.remove('hidden');
    rl.classList.remove('hidden');

    socket.emit('assign_role_to_all', { token: tk, guild_id: gid, role_id: rid });
  });
});
</script>
{% endblock %}
