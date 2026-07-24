/**
 * nav.js — Mobile Navigation v9.0 ULTRA (Discord Cloner)
 * ======================================================
 • Поддержка нескольких меню на странице
 • Плавная анимация и аппаратное ускорение (GPU)
 • Управление фокусом (Accessibility / a11y)
 • Закрытие по Escape, клику вне меню и свайпу (Swipe-to-close)
 • Динамический Backdrop (затемнение фона)
 • Блокировка прокрутки body (с фиксом для iOS Safari)
 • Автозакрытие при ресайзе окна (переход на десктоп)
 • Кастомные события для легкой интеграции
 */

(function () {
  'use strict';

  // ─── Конфигурация ──────────────────────────────────────────
  const CONFIG = {
    burgerSelector: '#burger',          // Совместимо с новым base.html
    menuSelector: '#mobile-menu',       // Совместимо с новым base.html
    linkSelector: 'a[href]',            // Любой элемент ссылки закроет меню
    openClass: 'open',
    activeClass: 'active',
    bodyLockClass: 'menu-open',
    animationDuration: 300,             // ms, должно совпадать с transition в CSS
    swipeThreshold: 50,                 // px, минимальная дистанция для свайпа
    resizeBreakpoint: 768,              // px, при какой ширине меню считается "десктопным"
    trapFocus: true,
    closeOnEsc: true,
    closeOnOutsideClick: true,
    closeOnLinkClick: true,
    enableSwipeClose: true,             // ULTRA: Закрытие свайпом влево или вниз
  };

  // ─── Хранилище экземпляров ────────────────────────────────
  const instances = new Map();

  // ─── Класс MobileNav ──────────────────────────────────────
  class MobileNav {
    constructor(burger, menu, options = {}) {
      this.burger = burger;
      this.menu = menu;
      this.options = Object.assign({}, CONFIG, options);

      this.isOpen = false;
      this.focusableElements = [];
      this.previouslyFocused = null;
      this.backdrop = null;

      // Для свайпа
      this.touchStartX = 0;
      this.touchStartY = 0;

      // Для ресайза
      this.resizeTimeout = null;

      // Инициализация
      this._createBackdrop();
      this._bindEvents();
      this._setAria();
    }

    // ─── Публичные методы ────────────────────────────────────
    open() {
      if (this.isOpen) return;
      this.isOpen = true;

      this.previouslyFocused = document.activeElement;

      this.menu.classList.add(this.options.openClass);
      this.burger.classList.add(this.options.activeClass);
      if (this.backdrop) this.backdrop.classList.add(this.options.openClass);
      
      this.burger.setAttribute('aria-expanded', 'true');
      this.menu.setAttribute('aria-hidden', 'false');

      this._lockBodyScroll();

      if (this.options.trapFocus) {
        this._updateFocusableElements();
        requestAnimationFrame(() => {
          if (this.focusableElements.length) this.focusableElements[0].focus();
        });
      }

      this._emitEvent('nav:open');
    }

    close() {
      if (!this.isOpen) return;
      this.isOpen = false;

      this.menu.classList.remove(this.options.openClass);
      this.burger.classList.remove(this.options.activeClass);
      if (this.backdrop) this.backdrop.classList.remove(this.options.openClass);

      this.burger.setAttribute('aria-expanded', 'false');
      this.menu.setAttribute('aria-hidden', 'true');

      this._unlockBodyScroll();

      if (this.options.trapFocus && this.previouslyFocused) {
        setTimeout(() => this.previouslyFocused.focus(), this.options.animationDuration);
      }

      this._emitEvent('nav:close');
    }

    toggle() {
      this.isOpen ? this.close() : this.open();
    }

    destroy() {
      this._unbindEvents();
      if (this.backdrop && this.backdrop.parentNode) {
        this.backdrop.parentNode.removeChild(this.backdrop);
      }
      this.close();
      instances.delete(this.burger);
    }

    // ─── Приватные методы ────────────────────────────────────
    _createBackdrop() {
      // Создаем затемнение, если его нет в DOM
      if (!document.querySelector('.nav-backdrop')) {
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'nav-backdrop';
        this.backdrop.style.cssText = `
          position: fixed; top: 0; left: 0; width: 100%; height: 100%;
          background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);
          z-index: 40; opacity: 0; pointer-events: none;
          transition: opacity ${this.options.animationDuration}ms ease;
        `;
        document.body.appendChild(this.backdrop);
      } else {
        this.backdrop = document.querySelector('.nav-backdrop');
      }
    }

    _lockBodyScroll() {
      document.body.classList.add(this.options.bodyLockClass);
      // ULTRA: Фикс для iOS Safari (предотвращает "пружинивание" фона)
      document.body.style.overscrollBehavior = 'none';
      document.body.style.position = 'fixed';
      document.body.style.width = '100%';
      document.body.style.top = `-${window.scrollY}px`;
    }

    _unlockBodyScroll() {
      document.body.classList.remove(this.options.bodyLockClass);
      document.body.style.overscrollBehavior = '';
      document.body.style.position = '';
      document.body.style.width = '';
      
      // ULTRA: Восстанавливаем скролл на iOS
      const scrollY = document.body.style.top;
      document.body.style.top = '';
      if (scrollY) window.scrollTo(0, parseInt(scrollY || '0', 10) * -1);
    }

    _bindEvents() {
      this.burger.addEventListener('click', this._onBurgerClick);
      
      if (this.backdrop) {
        this.backdrop.addEventListener('click', () => this.close());
      }

      if (this.options.closeOnLinkClick) {
        this.menu.addEventListener('click', this._onMenuLinkClick);
      }

      if (this.options.closeOnEsc) {
        document.addEventListener('keydown', this._onKeyDown);
      }

      if (this.options.enableSwipeClose) {
        this.menu.addEventListener('touchstart', this._onTouchStart, { passive: true });
        this.menu.addEventListener('touchend', this._onTouchEnd, { passive: true });
      }

      if (this.options.trapFocus) {
        this._observer = new MutationObserver(() => {
          if (this.isOpen) this._updateFocusableElements();
        });
        this._observer.observe(this.menu, { childList: true, subtree: true });
      }

      // ULTRA: Автозакрытие при ресайзе окна (например, поворот планшета)
      window.addEventListener('resize', this._onResize);
    }

    _unbindEvents() {
      this.burger.removeEventListener('click', this._onBurgerClick);
      if (this.backdrop) this.backdrop.removeEventListener('click', () => this.close());
      this.menu.removeEventListener('click', this._onMenuLinkClick);
      document.removeEventListener('keydown', this._onKeyDown);
      
      if (this.options.enableSwipeClose) {
        this.menu.removeEventListener('touchstart', this._onTouchStart);
        this.menu.removeEventListener('touchend', this._onTouchEnd);
      }
      
      window.removeEventListener('resize', this._onResize);
      if (this._observer) this._observer.disconnect();
    }

    _onBurgerClick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.toggle();
    };

    _onMenuLinkClick = (e) => {
      const link = e.target.closest(this.options.linkSelector);
      if (link && !link.getAttribute('href').startsWith('#')) {
        // Небольшая задержка для визуального отклика перед закрытием
        setTimeout(() => this.close(), 150);
      }
    };

    _onKeyDown = (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        e.preventDefault();
        this.close();
      }
      if (e.key === 'Tab' && this.isOpen && this.options.trapFocus) {
        this._handleTab(e);
      }
    };

    // ─── ULTRA: Swipe-to-close логика ────────────────────────
    _onTouchStart = (e) => {
      this.touchStartX = e.changedTouches[0].screenX;
      this.touchStartY = e.changedTouches[0].screenY;
    };

    _onTouchEnd = (e) => {
      const touchEndX = e.changedTouches[0].screenX;
      const touchEndY = e.changedTouches[0].screenY;
      
      const diffX = this.touchStartX - touchEndX; // Свайп влево (положительный)
      const diffY = touchEndY - this.touchStartY; // Свайп вниз (положительный)

      // Если свайпнули влево или вниз больше, чем порог, и горизонтальное движение преобладает
      if ((diffX > this.options.swipeThreshold || diffY > this.options.swipeThreshold) && Math.abs(diffX) > Math.abs(diffY) * 0.5) {
        this.close();
      }
    };

    // ─── ULTRA: Resize handler ───────────────────────────────
    _onResize = () => {
      clearTimeout(this.resizeTimeout);
      this.resizeTimeout = setTimeout(() => {
        if (window.innerWidth >= this.options.resizeBreakpoint && this.isOpen) {
          this.close();
        }
      }, 100);
    };

    _handleTab(e) {
      if (!this.focusableElements.length) return;
      const first = this.focusableElements[0];
      const last = this.focusableElements[this.focusableElements.length - 1];
      
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    _updateFocusableElements() {
      const all = this.menu.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      this.focusableElements = Array.from(all).filter(el => !el.disabled && el.offsetParent !== null);
    }

    _setAria() {
      this.burger.setAttribute('aria-expanded', 'false');
      this.burger.setAttribute('aria-controls', this.menu.id || 'mobile-menu');
      this.burger.setAttribute('aria-haspopup', 'true');
      this.menu.setAttribute('aria-hidden', 'true');
      this.menu.setAttribute('role', 'dialog');
      this.menu.setAttribute('aria-modal', 'true');
    }

    _emitEvent(name) {
      const event = new CustomEvent(name, {
        detail: { instance: this, isOpen: this.isOpen },
        bubbles: true,
      });
      this.burger.dispatchEvent(event);
    }
  }

  // ─── Инициализация ─────────────────────────────────────────
  function initNav(options = {}) {
    const burgers = document.querySelectorAll(options.burgerSelector || CONFIG.burgerSelector);
    burgers.forEach((burger) => {
      if (instances.has(burger)) return;

      const menuId = burger.getAttribute('data-target') || burger.getAttribute('aria-controls');
      let menu = menuId ? document.getElementById(menuId) : null;
      
      if (!menu) {
        menu = document.querySelector(options.menuSelector || CONFIG.menuSelector);
      }

      if (!menu) {
        console.warn('[Nav ULTRA] Меню не найдено для бургера:', burger);
        return;
      }

      const instance = new MobileNav(burger, menu, options);
      instances.set(burger, instance);
    });
  }

  // ─── Автозапуск ────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => initNav());
  } else {
    initNav();
  }

  // ─── Публичный API ─────────────────────────────────────────
  window.nav = {
    init: initNav,
    getInstance: (burger) => instances.get(burger) || null,
    closeAll: () => instances.forEach((instance) => instance.close()),
    destroyAll: () => {
      instances.forEach((instance) => instance.destroy());
      instances.clear();
    },
  };

})();