(function () {
    'use strict';

    const THEME_EMOJIS = {
        gaming: '🕹️',
        darkpro: '💻',
        professional: '💼',
        warm: '🌅',
        minimal: '➖'
    };

    function getTheme() {
        try { return document.body.dataset.cbTheme || localStorage.getItem('cb-theme') || 'gaming'; }
        catch (e) { return 'gaming'; }
    }

    function initCursor() {
        const cur = document.getElementById('cursor');
        const ring = document.getElementById('cursor-ring');
        if (!cur || !ring) return;

        // Emoji element
        let em = cur.querySelector('.cb-cursor-emoji');
        if (!em) { em = document.createElement('span'); em.className = 'cb-cursor-emoji'; cur.appendChild(em); }

        function applyThemeEmoji() {
            const theme = getTheme();
            em.textContent = THEME_EMOJIS[theme] || '🕹️';
        }

        // Ensure elements are visible and non-interactive; helpful if page CSS hides them
        try {
            cur.style.display = 'block';
            cur.style.pointerEvents = 'none';
            cur.style.opacity = '1';
            ring.style.display = 'block';
            ring.style.pointerEvents = 'none';
            ring.style.opacity = '0.6';
        } catch (e) { /* silent */ }

        applyThemeEmoji();
        console.debug && console.debug('cursor.js: initialized, theme=', getTheme());
        // Update on theme changes
        const ob = new MutationObserver(() => applyThemeEmoji());
        ob.observe(document.body, { attributes: true, attributeFilter: ['class', 'data-cb-theme'] });

        // rAF-driven smooth cursor
        let tx = window.innerWidth / 2, ty = window.innerHeight / 2;
        let cx = tx, cy = ty, rx = tx, ry = ty;
        let visible = false;
        let lastTrail = 0;

        function onMove(e) {
            tx = e.clientX; ty = e.clientY;
            if (!visible) { visible = true; cur.style.opacity = '1'; ring.style.opacity = '0.6'; }
            const now = performance.now();
            if (now - lastTrail > 60) { lastTrail = now; spawnTrail(tx, ty); }
        }

        function onLeave() { cur.style.opacity = '0'; ring.style.opacity = '0'; visible = false; }
        function onEnter(e) { tx = e.clientX; ty = e.clientY; cur.style.left = tx + 'px'; cur.style.top = ty + 'px'; cur.style.opacity = '1'; ring.style.opacity = '0.6'; visible = true; }

        window.addEventListener('mousemove', onMove, { passive: true });
        window.addEventListener('mouseleave', onLeave);
        window.addEventListener('mouseenter', onEnter);
        window.addEventListener('mousedown', () => { cur.style.transform = 'translate3d(-50%, -50%, 0) scale(0.78)'; });
        window.addEventListener('mouseup', () => { cur.style.transform = 'translate3d(-50%, -50%, 0) scale(1)'; });

        function spawnTrail(x, y) {
            const d = document.createElement('div'); d.className = 'trail-dot'; d.style.left = x + 'px'; d.style.top = y + 'px'; document.body.appendChild(d);
            setTimeout(() => d.remove(), 650);
        }

        function lerp(a, b, t) { return a + (b - a) * t }

        function loop() {
            cx = lerp(cx, tx, 0.28); cy = lerp(cy, ty, 0.28);
            rx = lerp(rx, tx, 0.12); ry = lerp(ry, ty, 0.12);
            cur.style.left = cx + 'px'; cur.style.top = cy + 'px';
            ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
            requestAnimationFrame(loop);
        }

        requestAnimationFrame(loop);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initCursor, { once: true });
    else initCursor();
})();
