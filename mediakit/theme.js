// Переключатель «день / ночь»: по умолчанию как в системе, выбор запоминается.
(function () {
  var root = document.documentElement, key = 'dentrave-theme';
  var saved = null;
  try { saved = localStorage.getItem(key); } catch (e) {}
  if (saved) root.dataset.theme = saved;
  var btn = document.getElementById('theme');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark';
    try { localStorage.setItem(key, root.dataset.theme); } catch (e) {}
  });
})();
