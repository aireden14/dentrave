#!/usr/bin/env python3
"""Проверка целостности сайта поддержки DenTrave. Запуск: python3 check.py (из папки сайта).
Красный = нельзя выкладывать. Ловит подмену ссылок, внешние ресурсы, inline-скрипты, секреты и длинное тире."""
import re, sys, pathlib
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
SITE_URL = "https://aireden14.github.io/dentrave/"

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
