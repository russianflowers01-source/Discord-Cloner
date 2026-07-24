/**
 * ui.js — UI Utilities & Interactions v9.0 ULTRA
 * ======================================================
 * Централизованный модуль для улучшения пользовательского опыта:
 * • Toast-уведомления (Success, Error, Warning, Info)
 * • Scroll Reveal (появление элементов при прокрутке)
 * • Умное копирование в буфер обмена с обратной связью
 * • Продвинутый аппендер логов с авто-скроллом и временем
 * • Защита форм от двойного клика (Debounce)
 */

(function () {
  'use strict';

  class UIHelper {
    constructor() {
      this.toastContainer = null;
      this._initToastContainer();
      this._initScrollReveal();
    }

    // ─── 1. Toast Уведомления (Всплывающие сообщения) ───────
    _initToastContainer() {
      if (!document.querySelector('.toast-container')) {
        this.toastContainer = document.createElement('div');
        this.toastContainer.className = 'toast-container fixed top-20 right-4 z-[100] flex flex-col gap-3 pointer-events-none';
        document.body.appendChild(this.toastContainer);
      } else {
        this.toastContainer = document.querySelector('.toast-container');
      }
    }

    /**
     * Показывает всплывающее уведомление
     * @param {string} message - Текст сообщения
     * @param {string} type - 'success' | 'error' | 'warning' | 'info'
     * @param {number} duration - Время показа в мс (по умолчанию 4000)
     */
    toast(message, type = 'info', duration = 4000) {
      const toast = document.createElement('div');
      
      // Цветовые схемы в стиле ULTRA
      const styles = {
        success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
        error:   'border-rose-500/30 bg-rose-500/10 text-rose-400',
        warning: 'border-amber-500/30 bg-amber-500/10 text-amber-400',
        info:    'border-cyan-500/30 bg-cyan-500/10 text-cyan-400'
      };

      const icons = {
        success: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
        error:   '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
        warning: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>',
        info:    '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
      };

      toast.className = `toast-item pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-2xl transform transition-all duration-300 translate-x-full opacity-0 ${styles[type]}`;
      toast.innerHTML = `
        <div class="shrink-0">${icons[type]}</div>
        <span class="text-sm font-medium text-gray-200">${message}</span>
      `;

      this.toastContainer.appendChild(toast);

      // Анимация появления
      requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full', 'opacity-0');
      });

      // Авто-удаление
      setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => {
          if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300); // Ждем окончания CSS transition
      }, duration);
    }

    // ─── 2. Scroll Reveal (Появление при скролле) ───────────
    _initScrollReveal() {
      const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
      };

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target); // Анимируем только один раз
          }
        });
      }, observerOptions);

      // Находим все элементы с классом .reveal и применяем наблюдатель
      document.querySelectorAll('.reveal').forEach(el => {
        el.classList.add('opacity-0', 'translate-y-8', 'transition-all', 'duration-700', 'ease-out');
        observer.observe(el);
      });
    }

    /**
     * Принудительно добавить элемент под наблюдение (для динамического контента)
     */
    observeElement(element) {
      if (element && !element.classList.contains('is-visible')) {
        element.classList.add('opacity-0', 'translate-y-8', 'transition-all', 'duration-700', 'ease-out');
        // Создаем новый observer для этого конкретного элемента, если нужно, 
        // или просто добавляем класс is-visible напрямую для мгновенного эффекта
        requestAnimationFrame(() => {
          element.classList.remove('opacity-0', 'translate-y-8');
          element.classList.add('is-visible');
        });
      }
    }

    // ─── 3. Умное копирование в буфер обмена ────────────────
    /**
     * Копирует текст и показывает уведомление
     */
    async copyToClipboard(text, successMsg = 'Скопировано в буфер обмена!') {
      try {
        await navigator.clipboard.writeText(text);
        this.toast(successMsg, 'success', 2500);
        return true;
      } catch (err) {
        console.error('Failed to copy: ', err);
        this.toast('Ошибка копирования', 'error', 3000);
        return false;
      }
    }

    // ─── 4. Продвинутый аппендер логов (Специально для Cloner) ─
    /**
     * Добавляет сообщение в консоль логов с временем и авто-скроллом
     * @param {string} containerId - ID элемента логов (например, 'logContent')
     * @param {string} message - Текст сообщения
     * @param {string} level - 'info' | 'success' | 'warn' | 'error'
     */
    appendLog(containerId, message, level = 'info') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const now = new Date();
      const timeStr = now.toLocaleTimeString('ru-RU', { hour12: false });
      
      const colors = {
        info: 'text-gray-400',
        success: 'text-emerald-400 font-semibold',
        warn: 'text-amber-400',
        error: 'text-rose-400 font-semibold'
      };

      const icons = {
        info: 'ℹ',
        success: '✅',
        warn: '⚠️',
        error: '❌'
      };

      const logEntry = document.createElement('div');
      logEntry.className = `log-line flex gap-2 font-mono text-xs leading-relaxed fade-in ${colors[level]}`;
      logEntry.innerHTML = `
        <span class="text-gray-600 shrink-0">[${timeStr}]</span>
        <span class="shrink-0">${icons[level]}</span>
        <span>${this._escapeHtml(message)}</span>
      `;

      container.appendChild(logEntry);
      
      // ULTRA: Плавный авто-скролл вниз
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
      });

      // Ограничение количества строк в логе (защита от утечки памяти)
      if (container.children.length > 200) {
        container.removeChild(container.firstChild);
      }
    }

    _escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // ─── 5. Защита от двойного клика (Debounce для кнопок) ──
    /**
     * Обертывает функцию, предотвращая ее частый вызов
     */
    debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    }
  }

  // ─── Инициализация и экспорт в глобальную область ─────────
  const ui = new UIHelper();
  window.ui = ui;

  // Автоматическое применение Scroll Reveal при загрузке DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.ui._initScrollReveal());
  } else {
    window.ui._initScrollReveal();
  }

})();