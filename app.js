// Единственный скрипт сайта. Без сети, без аналитики, без внешних адресов.
// Делает четыре вещи: «Отправить ссылку», «Копировать» у крипто-адресов, вкладки сетей и плывущие имена в «Спасибо вам».
// Безопасность: никакого innerHTML/eval - элементы строятся через createElement и textContent;
// позиции задаются через CSSOM (style.setProperty), а не атрибутом style, поэтому CSP страницы их не блокирует.

// 1. Кнопка «Отправить ссылку другу».
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

// 2. Кнопки «Копировать» у крипто-адресов: адрес берётся из data-copy, наружу ничего не уходит.
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

// 3. Вкладки сетей: без скрипта видны все четыре адреса подряд, со скриптом - по одному.
(function () {
  var box = document.querySelector('.crypto');
  var wrap = box && box.querySelector('.wallets');
  if (!wrap) return;
  var wallets = Array.prototype.slice.call(wrap.querySelectorAll('.wallet'));
  if (wallets.length < 2) return;
  var bar = document.createElement('div');
  bar.className = 'tabs';
  bar.setAttribute('role', 'tablist');
  bar.setAttribute('aria-label', 'Сеть для перевода');
  var tabs = [];
  function select(i, focus) {
    wallets.forEach(function (w, k) {
      w.hidden = k !== i;
      tabs[k].setAttribute('aria-selected', k === i ? 'true' : 'false');
      tabs[k].tabIndex = k === i ? 0 : -1;
    });
    if (focus) tabs[i].focus();
  }
  wallets.forEach(function (w, i) {
    w.id = 'wallet-' + i;
    w.setAttribute('role', 'tabpanel');
    w.setAttribute('aria-labelledby', 'tab-' + i);
    var t = document.createElement('button');
    t.type = 'button';
    t.className = 'tab';
    t.id = 'tab-' + i;
    t.setAttribute('role', 'tab');
    t.setAttribute('aria-controls', 'wallet-' + i);
    t.textContent = w.getAttribute('data-net') || ('Сеть ' + (i + 1));
    t.addEventListener('click', function () { select(i, false); });
    t.addEventListener('keydown', function (e) {
      var n = null;
      if (e.key === 'ArrowRight') n = (i + 1) % wallets.length;
      else if (e.key === 'ArrowLeft') n = (i - 1 + wallets.length) % wallets.length;
      else if (e.key === 'Home') n = 0;
      else if (e.key === 'End') n = wallets.length - 1;
      if (n !== null) { e.preventDefault(); select(n, true); }
    });
    bar.appendChild(t);
    tabs.push(t);
  });
  wrap.parentNode.insertBefore(bar, wrap);
  box.classList.add('tabs-on');
  select(0, false);
})();

// 4. «Спасибо вам»: имена поддержавших плывут вверх, как огоньки. При «уменьшить движение» остаётся спокойный список.
(function () {
  var sky = document.getElementById('sky');
  var list = document.getElementById('donors');
  if (!sky || !list) return;
  var items = Array.prototype.slice.call(list.children);
  if (!items.length) return;
  var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  if (mq && mq.matches) return;

  // Свой маленький генератор с постоянным зерном: картина одинакова при каждом открытии, проверять её проще.
  var seed = 20261108;
  function rnd() {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  }

  // Имя оборачиваем в span: li едет вверх, span качается из стороны в сторону.
  items.forEach(function (li) {
    var span = document.createElement('span');
    span.textContent = li.textContent;
    while (li.firstChild) li.removeChild(li.firstChild);
    li.appendChild(span);
  });

  // Порядок появления перемешан. Все имена плывут с одной скоростью и равными промежутками по времени,
  // поэтому по вертикали они не налезают друг на друга, а по горизонтали разнесены «золотым» шагом.
  var order = items.slice();
  for (var a = order.length - 1; a > 0; a--) {
    var b = Math.floor(rnd() * (a + 1));
    var tmp = order[a]; order[a] = order[b]; order[b] = tmp;
  }
  var n = order.length;
  var cycle = Math.max(26, Math.round(n * 1.9));
  var recs = order.map(function (li, i) {
    var depth = rnd();
    var sw = 8 + rnd() * 14;
    var sd = 4.5 + rnd() * 3.5;
    li.style.setProperty('--s', (0.92 + depth * 0.4).toFixed(2));
    li.style.setProperty('--o', (0.66 + depth * 0.34).toFixed(2));
    li.style.setProperty('--sw', sw.toFixed(1));
    li.style.setProperty('--sd', sd.toFixed(2) + 's');
    li.style.setProperty('--sdl', (-rnd() * sd).toFixed(2) + 's');
    li.style.setProperty('--cycle', cycle + 's');
    li.style.setProperty('--delay', (-(i * cycle / n)).toFixed(2) + 's');
    return { el: li, sw: sw, u: (i * 0.618034 + 0.09) % 1 };
  });

  // Искры: маленькие огоньки без текста, плывут вверх с разной скоростью.
  for (var k = 0; k < 18; k++) {
    var sp = document.createElement('i');
    sp.className = 'spark';
    sp.setAttribute('aria-hidden', 'true');
    var dur = 9 + rnd() * 10;
    sp.style.setProperty('--sx', (4 + rnd() * 92).toFixed(1));
    sp.style.setProperty('--sz', (2.5 + rnd() * 4).toFixed(1) + 'px');
    sp.style.setProperty('--sdur', dur.toFixed(1) + 's');
    sp.style.setProperty('--sdel', (-rnd() * dur).toFixed(1) + 's');
    sp.style.setProperty('--dx', ((rnd() - 0.5) * 60).toFixed(0));
    sp.style.setProperty('--so', (0.45 + rnd() * 0.5).toFixed(2));
    sky.insertBefore(sp, list);
  }

  // Горизонтальные позиции считаем по реальной ширине имени, чтобы ни одно не вылезало за край.
  function layout() {
    var W = sky.clientWidth;
    sky.style.setProperty('--W', String(W));
    recs.forEach(function (r) {
      var w = r.el.offsetWidth;
      var pad = r.sw + 6;
      var room = Math.max(0, W - w - 2 * pad);
      r.el.style.setProperty('--x', (pad + r.u * room).toFixed(1));
    });
  }
  sky.classList.add('fly');
  layout();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);
  var raf = 0;
  window.addEventListener('resize', function () {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(layout);
  });

  // Вне экрана анимацию ставим на паузу, чтобы не греть телефон зря.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { sky.classList.toggle('paused', !e.isIntersecting); });
    }, { threshold: 0 }).observe(sky);
  }
  if (mq && mq.addEventListener) {
    mq.addEventListener('change', function () {
      sky.classList.toggle('fly', !mq.matches);
      if (!mq.matches) layout();
    });
  }
})();
