(function () {
    const themes = ['gaming', 'darkpro', 'professional', 'warm', 'minimal'];
    const theme = themes.includes(localStorage.getItem('cb-theme')) ? localStorage.getItem('cb-theme') : 'gaming';
    const body = document.body;
    if (!body) return;
    themes.forEach((t) => body.classList.remove('theme-' + t));
    body.classList.add('theme-' + theme);
    body.classList.toggle('light', theme === 'professional' || theme === 'warm' || theme === 'minimal');
    body.dataset.cbTheme = theme;
})();
