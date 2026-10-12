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
