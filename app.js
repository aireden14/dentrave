// Единственный скрипт сайта: кнопка «Отправить ссылку другу». Без сети, без аналитики, без внешних адресов.
(function () {
  var btn = document.getElementById('share');
  if (!btn) return;
  var url = location.href.split('#')[0];
  if (navigator.share) {
    btn.hidden = false;
    btn.addEventListener('click', function () {
      navigator.share({ title: 'Поддержать DenTrave', url: url }).catch(function () {});
    });
  } else if (navigator.clipboard && navigator.clipboard.writeText) {
    btn.hidden = false;
    btn.textContent = 'Скопировать ссылку на страницу';
    btn.addEventListener('click', function () {
      navigator.clipboard.writeText(url).then(function () {
        btn.textContent = 'Ссылка скопирована';
        setTimeout(function () { btn.textContent = 'Скопировать ссылку на страницу'; }, 2200);
      }).catch(function () {});
    });
  }
})();

// Кнопки «Копировать» у крипто-адресов: адрес берётся из data-copy, наружу ничего не уходит.
(function () {
  var buttons = document.querySelectorAll('[data-copy]');
  if (!buttons.length) return;
  function legacyCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.top = '0';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, text.length);
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }
  function mark(btn, label, done) {
    if (!btn.getAttribute('data-label')) btn.setAttribute('data-label', btn.textContent);
    btn.textContent = label;
    btn.classList.toggle('done', done);
    clearTimeout(btn._t);
    btn._t = setTimeout(function () {
      btn.textContent = btn.getAttribute('data-label');
      btn.classList.remove('done');
    }, 2200);
  }
  Array.prototype.forEach.call(buttons, function (btn) {
    btn.setAttribute('aria-live', 'polite');
    btn.addEventListener('click', function () {
      var text = btn.getAttribute('data-copy');
      var good = function () { mark(btn, 'Скопировано', true); };
      var bad = function () { mark(btn, 'Не вышло, выделите адрес', false); };
      var fallback = function () { if (legacyCopy(text)) good(); else bad(); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(good, fallback);
      } else {
        fallback();
      }
    });
  });
})();
