(function () {
    'use strict';

    const THEMES = [
        { id: 'gaming', label: 'GAMING', emoji: '🕹️', desc: 'Jet black · electric cyan' },
        { id: 'darkpro', label: 'DARK PRO', emoji: '💻', desc: 'Navy dark · amber gold' },
        { id: 'professional', label: 'PROFESSIONAL', emoji: '💼', desc: 'Clean white · deep indigo' },
        { id: 'warm', label: 'WARM', emoji: '🌅', desc: 'Cream · terracotta brown' },
        { id: 'minimal', label: 'MINIMAL', emoji: '➖', desc: 'Pure white · forest green' },
    ];
    const LIGHT_THEMES = new Set(['professional', 'warm', 'minimal']);
    const DEFAULT_THEME = 'gaming';

    function getTheme(theme) {
        return THEMES.some((item) => item.id === theme) ? theme : DEFAULT_THEME;
    }

    function getCurrentTheme() {
        try {
            return getTheme(localStorage.getItem('cb-theme'));
        } catch (error) {
            return DEFAULT_THEME;
        }
    }

    function getElements() {
        return {
            wrap: document.getElementById('authThemeWrap'),
            toggle: document.getElementById('authThemeToggle'),
            menu: document.getElementById('authThemeMenu'),
            label: document.getElementById('authThemeLabel'),
            emoji: document.getElementById('authThemeEmoji'),
            items: Array.from(document.querySelectorAll('[data-auth-theme]')),
        };
    }

    function applyBodyTheme(theme) {
        const body = document.body;
        THEMES.forEach((item) => body.classList.remove('theme-' + item.id));
        body.classList.remove('light');
        body.classList.add('theme-' + theme);
        if (LIGHT_THEMES.has(theme)) {
            body.classList.add('light');
        }
        body.dataset.cbTheme = theme;
    }

    function updateThemeUI(theme) {
        const { toggle, menu, label, emoji, items } = getElements();
        const current = getTheme(theme);
        const meta = THEMES.find((item) => item.id === current) || THEMES[0];

        if (label) label.textContent = meta.label;
        if (emoji) emoji.textContent = meta.emoji;
        if (toggle) toggle.setAttribute('aria-expanded', menu && menu.classList.contains('open') ? 'true' : 'false');

        items.forEach((item) => {
            const active = item.dataset.authTheme === current;
            item.classList.toggle('active', active);
            item.setAttribute('aria-pressed', active ? 'true' : 'false');
            const check = item.querySelector('.auth-theme-check');
            if (check) check.style.opacity = active ? '1' : '0';
        });
    }

    function setTheme(theme) {
        const current = getTheme(theme);
        try {
            localStorage.setItem('cb-theme', current);
        } catch (error) {
            // Ignore storage failures; the body class still updates.
        }
        applyBodyTheme(current);
        updateThemeUI(current);
        closeMenu();
    }

    function openMenu() {
        const { menu, toggle } = getElements();
        if (!menu) return;
        menu.classList.add('open');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
    }

    function closeMenu() {
        const { menu, toggle } = getElements();
        if (!menu) return;
        menu.classList.remove('open');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }

    function toggleMenu() {
        const { menu } = getElements();
        if (!menu) return;
        if (menu.classList.contains('open')) {
            closeMenu();
        } else {
            openMenu();
        }
    }

    function init() {
        const { wrap, toggle, items } = getElements();
        if (!wrap || !toggle || !items.length) return;

        const current = getCurrentTheme();
        applyBodyTheme(current);
        updateThemeUI(current);

        toggle.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            toggleMenu();
        });

        items.forEach((item) => {
            item.addEventListener('click', () => {
                setTheme(item.dataset.authTheme);
            });
        });

        document.addEventListener('click', (event) => {
            if (!wrap.contains(event.target)) {
                closeMenu();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeMenu();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
