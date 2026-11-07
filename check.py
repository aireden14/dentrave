#!/usr/bin/env python3
"""Проверка целостности сайта поддержки DenTrave. Запуск: python3 check.py (из папки сайта).
Красный = нельзя выкладывать. Ловит подмену ссылок, внешние ресурсы, inline-скрипты, секреты и длинное тире."""
import re, sys, pathlib
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
SITE_URL = "https://dentrave.com/"

# Ровно то, что прислал Денис (12.10.2026), без правок.
DONATE = {
    "cloudtips": "https://pay.cloudtips.ru/p/e88f9b66",
    "destream": "https://destream.net/live/DenTrave/donate",
    "boosty": "https://boosty.to/dentrave",
}
ALLOWED_EXTERNAL = set(DONATE.values()) | {
    "https://www.youtube.com/@DenTrave",
    "https://t.me/dentraveai",
    "https://www.twitch.tv/dentraveai",
}
# Адреса для приёма крипты, присланные Денисом 08.11.2026, дословно. Только получение, никаких ключей и seed-фраз.
CRYPTO = {
    "trc20": "TDuJiTeJf99t3fX841AN2d82nYBekGzvTZ",
    "evm": "0x8A94851Ca0f415101533F7eCD9D9f8a379725265",
    "solana": "FCLWTr9eG371x26NEVd2N9ucoYqgGYzqdayM4wzNDB7k",
    "btc": "bc1q7mzrccc0u37mglz9jafmezpzfsd84qvfvjjr7j",
}
ADDR_PATTERNS = [r"\b0x[0-9a-fA-F]{40}\b", r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b", r"\bbc1[ac-hj-np-z02-9]{11,71}\b",
                 r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"]
SECRET_PATTERNS = [r"gsk_[A-Za-z0-9]{10}", r"ghp_[A-Za-z0-9]{10}", r"napi_[A-Za-z0-9]{10}", r"rnd_[A-Za-z0-9]{10}",
                   r"sk-ant", r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b", r"BEGIN [A-Z ]*PRIVATE KEY", r"michelpct"]
MAX_IMG = 350 * 1024
MAX_PAGE = 1100 * 1024

errors: list[str] = []
def fail(msg): errors.append(msg)

index = ROOT / "index.html"
if not index.exists():
    fail("нет index.html"); print("\n".join(errors)); sys.exit(1)
html = index.read_text(encoding="utf-8")

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
    handle_startendtag = handle_starttag
p = P(); p.feed(html)

def is_external(u): return bool(urlparse(u).scheme) or u.startswith("//")

# 1. ссылки <a>: только белый список, у внешних rel=noopener noreferrer
seen_donate = set()
for tag, a in p.tags:
    if tag == "a":
        href = a.get("href", "")
        if href.startswith("#"): continue
        if is_external(href):
            if href not in ALLOWED_EXTERNAL: fail(f"ссылка вне белого списка: {href}")
            rel = (a.get("rel") or "").split()
            if "noopener" not in rel or "noreferrer" not in rel: fail(f"нет rel=noopener noreferrer: {href}")
            for k, v in DONATE.items():
                if href == v: seen_donate.add(k)
        else:
            if not (ROOT / href.split("?")[0].split("#")[0]).exists(): fail(f"битая внутренняя ссылка: {href}")
for k in DONATE:
    if k not in seen_donate: fail(f"в index.html нет ссылки на донат «{k}» ({DONATE[k]})")

# 1б. крипто-адреса: ровно четыре, дословно; у каждого <code> с адресом и <button type="button" data-copy>
class C(HTMLParser):
    def __init__(self):
        super().__init__(); self.in_code = False; self.codes = []; self.buttons = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "code": self.in_code = True; self.codes.append("")
        if tag == "button" and "data-copy" in a: self.buttons.append(a)
    def handle_endtag(self, tag):
        if tag == "code": self.in_code = False
    def handle_data(self, d):
        if self.in_code: self.codes[-1] += d
c = C(); c.feed(html)
codes = [x.strip() for x in c.codes]
copy_vals = [b["data-copy"] for b in c.buttons]
for k, addr in CRYPTO.items():
    if codes.count(addr) != 1: fail(f"адрес «{k}» должен стоять в <code> ровно один раз и дословно: {addr}")
    if copy_vals.count(addr) != 1: fail(f"у адреса «{k}» нет ровно одной кнопки копирования data-copy")
for b in c.buttons:
    if b.get("type") != "button": fail("кнопка копирования без type=\"button\"")
    if not b.get("aria-label"): fail("у кнопки копирования нет aria-label (какая сеть)")
    if b["data-copy"] not in CRYPTO.values(): fail(f"data-copy не из белого списка: {b['data-copy']}")
for f in (index, ROOT / "style.css", ROOT / "app.js"):
    if not f.exists(): continue
    t = f.read_text(encoding="utf-8")
    for pat in ADDR_PATTERNS:
        for m in re.findall(pat, t):
            if m not in CRYPTO.values(): fail(f"посторонний крипто-адрес в {f.name}: {m}")
pos = {s: html.find(f'class="{s}"') for s in ("ways", "crypto", "free")}
if min(pos.values()) < 0 or not (pos["ways"] < pos["crypto"] < pos["free"]):
    fail("блок крипты должен стоять после способов (CloudTips первый) и до «Нет возможности донатить»")
if 'class="crypto-warn"' not in html: fail("нет предупреждения про выбор сети (class=\"crypto-warn\")")
appjs = ROOT / "app.js"
if appjs.exists():
    t = appjs.read_text(encoding="utf-8")
    if "data-copy" not in t or "clipboard" not in t: fail("app.js не обрабатывает кнопки копирования (data-copy + clipboard)")

# 2. внешние ресурсы и опасные теги
for tag, a in p.tags:
    if tag in ("iframe", "form", "object", "embed", "frame", "base", "input", "textarea"): fail(f"запрещённый тег <{tag}>")
    for attr in a:
        if attr.startswith("on"): fail(f"inline-обработчик {attr} в <{tag}>")
    if tag == "script":
        src = a.get("src")
        if not src: fail("inline <script> (CSP его всё равно блокирует)")
        elif is_external(src): fail(f"внешний скрипт: {src}")
    if tag in ("img", "source", "script") and a.get("src") and is_external(a["src"]): fail(f"внешний ресурс {tag}: {a['src']}")
    if tag == "link" and a.get("href") and is_external(a["href"]) and a.get("rel") not in ("canonical",): fail(f"внешний <link>: {a['href']}")
    if tag == "style": fail("inline <style> (CSP его блокирует) - стили только в style.css")

# 3. CSP и мета
m = re.search(r'<meta[^>]+http-equiv="Content-Security-Policy"[^>]+content="([^"]+)"', html)
if not m: fail("нет CSP в <meta>")
else:
    csp = m.group(1)
    for need in ("default-src 'none'", "script-src 'self'", "style-src 'self'", "img-src 'self'", "base-uri 'none'", "form-action 'none'"):
        if need not in csp: fail(f"в CSP нет «{need}»")
    for bad in ("unsafe-inline", "unsafe-eval", "*", "http:"):
        if bad in csp: fail(f"в CSP запрещено «{bad}»")
for need, label in ((r'<html[^>]+lang="ru"', 'lang="ru"'), (r'name="viewport"', "viewport"), (r'name="theme-color"', "theme-color"),
                    (r'name="referrer" content="no-referrer"', "referrer no-referrer"), (r'property="og:image"', "og:image"), (r'rel="canonical"', "canonical")):
    if not re.search(need, html): fail(f"нет {label}")
if f'href="{SITE_URL}"' not in html: fail(f"canonical не равен {SITE_URL}")

# 4. тексты: нет длинного тире, нет секретов
for f in [index, ROOT / "style.css", ROOT / "app.js", ROOT / "README.md"]:
    if not f.exists():
        if f.name in ("style.css", "app.js"): fail(f"нет {f.name}")
        continue
    t = f.read_text(encoding="utf-8")
    if "—" in t or "–" in t: fail(f"длинное/среднее тире в {f.name}: только дефис «-»")
    for pat in SECRET_PATTERNS:
        if re.search(pat, t): fail(f"похоже на секрет/контакт ({pat}) в {f.name}")

# 5. внешние ссылки в css/js
for f in (ROOT / "style.css", ROOT / "app.js"):
    if f.exists() and re.search(r"https?://", f.read_text(encoding="utf-8").replace("http://www.w3.org", "")):
        fail(f"внешний адрес в {f.name}")

# 6. картинки и вес
need_imgs = ["img/hero.webp", "img/thanks.webp", "img/og.jpg", "img/favicon-32.png", "img/apple-touch-icon.png"]
total = index.stat().st_size
for f in (ROOT / "style.css", ROOT / "app.js"):
    if f.exists(): total += f.stat().st_size
for rel in need_imgs:
    f = ROOT / rel
    if not f.exists(): fail(f"нет файла {rel}"); continue
    if f.stat().st_size > MAX_IMG: fail(f"{rel} тяжелее {MAX_IMG // 1024} КБ ({f.stat().st_size // 1024} КБ)")
    if rel != "img/og.jpg": total += f.stat().st_size if rel in ("img/hero.webp", "img/thanks.webp") else 0
if total > MAX_PAGE: fail(f"страница весит {total // 1024} КБ (лимит {MAX_PAGE // 1024} КБ)")
for tag, a in p.tags:
    if tag == "img":
        if not (ROOT / a.get("src", "")).exists(): fail(f"нет файла картинки {a.get('src')}")
        if not a.get("alt") and a.get("alt") != "": fail(f"у <img src={a.get('src')}> нет alt")
        if not (a.get("width") and a.get("height")): fail(f"у <img src={a.get('src')}> нет width/height (прыжок вёрстки)")

try:
    from PIL import Image
    og = ROOT / "img/og.jpg"
    if og.exists() and Image.open(og).size != (1200, 630): fail("og.jpg должен быть 1200x630")
except ImportError:
    pass

if errors:
    print("КРАСНЫЙ:"); [print(" -", e) for e in errors]; sys.exit(1)
print(f"ЗЕЛЁНЫЙ: ссылок в белом списке {len(ALLOWED_EXTERNAL)}, вес страницы ~{total // 1024} КБ")
