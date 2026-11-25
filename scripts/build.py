#!/usr/bin/env python3
"""Convierte la exportación del diseño (Main.dc.html + React + support.js) en un
sitio estático listo para Cloudflare Pages, en dist/.

Uso:  python3 scripts/build.py [--site-url https://cnitp.pages.dev]
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC_HTML = ROOT / "Main.dc.html"
SRC_ASSETS = ROOT / "assets"
SRC_JS = ROOT / "src" / "main.js"
DIST = ROOT / "dist"

HERO_BG = "abb1e37251fa1a3d6ba89e5932c9d1a8.webp"
RAIZ_BG = "627b3abce66552f8adde43c2e896c062.jpg"
POSTER = "89cade6fbd0b59a37db0cc812016d80f.webp"
LOGO_SVG = "7f86735244cae55097d7c75deb1d039d.svg"
ICON_SVG = "4bb7a58d0bb2f66d540e433b20cc497e.svg"
FORM_URL = "https://forms.gle/zPLDPsFgSgiYJZvq9"

# Fotos que reciben srcset (ancho de origen >= 700 px). Valor = atributo sizes.
DEFAULT_SIZES = "(max-width: 960px) 100vw, 50vw"
SIZES = {
    "a36752f04f8ffb54b51afc4cc3640719.webp": "(max-width: 600px) 100vw, 380px",  # portada revista
    POSTER: "(max-width: 700px) 100vw, 360px",                                     # cartel Los 100
    "7cf35ee2cea7f8f3bd8d3bdc55e386c2.jpg": "230px",                              # miniatura video
    "2951dc82e7ef2956a9efd224416723c4.jpg": "(max-width: 700px) 100vw, 480px",    # gala
}
WIDTHS = [480, 800, 1200, 1440]
PHOTO_Q = 78
LOGO_Q = 82

TITLE = "CNITP · Consejo Nacional de Investigaciones Tanatológicas y Psicológicas"
DESCRIPTION = ("Investigamos, formamos y certificamos en Tanatología y Psicología. "
               "17 años de trayectoria y más de 9,000 personas graduadas. "
               "Postula a Los 100 hasta el 5 de diciembre.")


def log(*a):
    print(*a, file=sys.stderr)


def save_webp(im, path, q):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=q, method=6)
    return path.stat().st_size


def process_photo(name):
    """Genera variantes WebP. Devuelve (src, srcset, w, h)."""
    im = Image.open(SRC_ASSETS / name)
    im.load()
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    w0, h0 = im.size
    stem = Path(name).stem
    widths = sorted({w for w in WIDTHS if w < w0} | {min(w0, WIDTHS[-1])})
    parts = []
    for w in widths:
        h = round(h0 * w / w0)
        out = f"{stem}-{w}.webp"
        save_webp(im.resize((w, h), Image.LANCZOS) if w != w0 else im, DIST / "assets" / out, PHOTO_Q)
        parts.append((out, w))
    src = parts[-1][0]
    srcset = ", ".join(f"./assets/{f} {w}w" for f, w in parts)
    return src, srcset, w0, h0


def process_small(name, max_w=None):
    """Recomprime una imagen pequeña (logos). Conserva el nombre si no hay ahorro."""
    src = SRC_ASSETS / name
    im = Image.open(src)
    im.load()
    if max_w and im.size[0] > max_w:
        im = im.resize((max_w, round(im.size[1] * max_w / im.size[0])), Image.LANCZOS)
    stem = Path(name).stem
    out = DIST / "assets" / f"{stem}.webp"
    size = save_webp(im, out, LOGO_Q)
    if size >= src.stat().st_size and src.suffix == ".webp":
        shutil.copy2(src, out)  # el original ya era más ligero
        return out.name, Image.open(src).size
    return out.name, im.size


def make_og(path):
    bg = Image.open(SRC_ASSETS / HERO_BG).convert("RGB")
    bw, bh = bg.size
    scale = max(1200 / bw, 630 / bh)
    bg = bg.resize((round(bw * scale), round(bh * scale)), Image.LANCZOS)
    left = (bg.size[0] - 1200) // 2
    top = (bg.size[1] - 630) // 2
    bg = bg.crop((left, top, left + 1200, top + 630))
    poster = Image.open(SRC_ASSETS / POSTER).convert("RGB")
    ph = 590
    pw = round(poster.size[0] * ph / poster.size[1])
    poster = poster.resize((pw, ph), Image.LANCZOS)
    bg.paste(poster, ((1200 - pw) // 2, 20))
    path.parent.mkdir(parents=True, exist_ok=True)
    bg.save(path, "JPEG", quality=84, optimize=True, progressive=True)


def build(site_url):
    site_url = site_url.rstrip("/")
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)

    doc = SRC_HTML.read_text(encoding="utf-8")

    # --- separar partes de la exportación ---
    helmet = re.search(r"<helmet>(.*?)</helmet>", doc, re.S).group(1)
    font_link = re.search(r'<link href="https://fonts\.googleapis\.com[^>]*>', helmet).group(0)
    style = re.search(r"<style>(.*?)</style>", helmet, re.S).group(1)
    body = re.search(r"</helmet>(.*?)</x-dc>", doc, re.S).group(1).strip()

    # --- bloques condicionales del área (sc-if) -> atributos hidden ---
    cond = {"esTanatologia": "tanatologia", "esPsicologia": "psicologia"}

    def inline_if(m):
        area = cond[m.group(1)]
        hidden = "" if area == "tanatologia" else " hidden"
        return f'<span data-area-show="{area}"{hidden}><span aria-hidden="true" '

    body = re.sub(r'<sc-if value="\{\{ (\w+) \}\}" hint-placeholder-val="\{\{ \w+ \}\}"><span ',
                  inline_if, body)
    body = body.replace("</span></sc-if>", "</span></span>")

    def block_if(m):
        area = cond[m.group(1)]
        hidden = "" if area == "tanatologia" else " hidden"
        return f'<div data-area-show="{area}"{hidden}>'

    body = re.sub(r'<sc-if value="\{\{ (\w+) \}\}" hint-placeholder-val="\{\{ \w+ \}\}">',
                  block_if, body)
    body = body.replace("</sc-if>", "</div>")
    assert "sc-if" not in body

    # región que anuncia el cambio de área a lectores de pantalla
    body = body.replace('<div data-area-show="tanatologia">\n<div id="tanatologia"',
                        '<p id="cn-area-status" class="sr-only" role="status" aria-live="polite"></p>\n'
                        '<div data-area-show="tanatologia">\n<div id="tanatologia"', 1)

    body = body.replace('onClick="{{ verTanatologia }}" aria-pressed="{{ esTanatologia }}"',
                        'data-area="tanatologia" aria-pressed="true" aria-controls="tanatologia"')
    body = body.replace('onClick="{{ verPsicologia }}" aria-pressed="{{ esPsicologia }}"',
                        'data-area="psicologia" aria-pressed="false" aria-controls="psicologia"')
    assert "{{" not in body, re.findall(r"\{\{[^}]*\}\}", body)

    # --- menú y pie: cada enlace abre su área ---
    body = re.sub(r'href="#areas"((?:\s+style="[^"]*")?)>Tanatología</a>', r'href="#tanatologia"\1>Tanatología</a>', body)
    body = re.sub(r'href="#areas"((?:\s+style="[^"]*")?)>Psicología</a>', r'href="#psicologia"\1>Psicología</a>', body)

    # --- jerarquía de encabezados dentro de cada área (h3 área > h4 tarjeta > h5) ---
    def fix_headings(block):
        block = re.sub(r"<h4(\s[^>]*)>(.*?)</h4>", r"<h5\1>\2</h5>", block, flags=re.S)
        block = re.sub(r'<h3( style="margin: 1[24]px 0 0;[^"]*")>(.*?)</h3>', r"<h4\1>\2</h4>", block, flags=re.S)
        return block

    a0 = body.index('<div id="tanatologia"')
    a1 = body.index('<section id="los-100"')
    body = body[:a0] + fix_headings(body[a0:a1]) + body[a1:]

    # --- enlaces que abren pestaña nueva: avisarlo a lectores de pantalla ---
    def blank(m):
        tag, inner = m.group(1), m.group(2)
        if "aria-label=" in tag or "pestaña nueva" in inner:
            return m.group(0)
        return f'{tag}{inner}<span class="sr-only"> (se abre en una pestaña nueva)</span></a>'

    body = re.sub(r'(<a\b[^>]*target="_blank"[^>]*>)(.*?)</a>', blank, body, flags=re.S)

    # --- salto al contenido ---
    body = body.replace("<main>", '<main id="contenido" tabindex="-1">', 1)

    # --- imágenes: WebP + srcset + width/height ---
    processed = {}

    def img(m):
        tag = m.group(0)
        name = re.search(r'src="\./assets/([^"]+)"', tag).group(1)
        if name.endswith(".svg"):
            if name == LOGO_SVG and "loading=" not in tag:  # logo grande del pie
                tag = tag.replace("<img ", '<img loading="lazy" decoding="async" ', 1)
            return tag
        if name not in processed:
            w0 = Image.open(SRC_ASSETS / name).size[0]
            if w0 >= 700:
                processed[name] = ("photo",) + process_photo(name)
            else:
                max_w = 360 if w0 > 400 else None
                out, (w, h) = process_small(name, max_w)
                processed[name] = ("small", out, None, w, h)
        kind, src, srcset, w, h = processed[name]
        tag = tag.replace(f'src="./assets/{name}"', f'src="./assets/{src}"')
        extra = f' width="{w}" height="{h}"'
        if srcset:
            extra += f' srcset="{srcset}" sizes="{SIZES.get(name, DEFAULT_SIZES)}"'
        if "loading=" not in tag:
            extra += ' loading="lazy"'
        if 'decoding=' not in tag:
            extra += ' decoding="async"'
        return tag.replace("<img ", "<img" + extra + " ", 1)

    body = re.sub(r"<img\b[^>]*>", img, body)

    # --- fondos CSS ---
    raiz_src, _, _, _ = process_photo(RAIZ_BG)
    raiz_small = raiz_src.replace("-1440.webp", "-800.webp")
    style = style.replace(f"url(./assets/{RAIZ_BG})",
                          f'image-set(url(./assets/{raiz_small}) 1x, url(./assets/{raiz_src}) 2x)')
    shutil.copy2(SRC_ASSETS / HERO_BG, DIST / "assets" / HERO_BG)

    style += """
/* --- añadido en build --- */
[hidden] { display: none !important; }
[data-area-show] { display: contents; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
.cn-skip { position: absolute; left: 12px; top: -200px; z-index: 100; background-color: #F0D48A; color: #071610; padding: 12px 18px; font-family: 'Montserrat', Arial, sans-serif; font-weight: 800; text-decoration: none; border-radius: 4px; }
.cn-skip:focus { top: 12px; color: #071610; }
main:focus, h3[tabindex="-1"]:focus { outline: none; }
#tanatologia, #psicologia { scroll-margin-top: 16px; }
"""

    # --- copiar SVG usados ---
    for svg in set(re.findall(r'\./assets/([\w]+\.svg)', body)) | {ICON_SVG, LOGO_SVG}:
        shutil.copy2(SRC_ASSETS / svg, DIST / "assets" / svg)

    make_og(DIST / "assets" / "og-cnitp.jpg")

    # --- JS ---
    js = SRC_JS.read_bytes()
    js_name = f"main.{hashlib.sha256(js).hexdigest()[:10]}.js"
    (DIST / "js").mkdir()
    (DIST / "js" / js_name).write_bytes(js)

    # --- fuentes: solo los pesos que se usan ---
    fonts = ("https://fonts.googleapis.com/css2?family=Cinzel:wght@900"
             "&family=Cormorant+Garamond:ital,wght@1,700"
             "&family=Montserrat:wght@500;600;700;800&display=swap")
    assert "Cinzel" in font_link  # la exportación sigue usando Google Fonts

    ld = [
        {
            "@context": "https://schema.org",
            "@type": "EducationalOrganization",
            "@id": f"{site_url}/#organizacion",
            "name": "Consejo Nacional de Investigaciones Tanatológicas y Psicológicas",
            "alternateName": ["CNITP", "Instituto Nacional de Estudios Superiores en Tanatología"],
            "url": f"{site_url}/",
            "logo": f"{site_url}/assets/{LOGO_SVG}",
            "telephone": "+52 55 4187 2203",
            "areaServed": "MX",
            "description": DESCRIPTION,
        },
        {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Gala de premiación · Los 100 más destacados de la tanatología y de la psicología",
            "startDate": "2026-12-19T17:00:00-06:00",
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "location": {
                "@type": "Place",
                "name": "Colima 56, colonia Roma",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "Colima 56, colonia Roma",
                    "addressLocality": "Ciudad de México",
                    "addressRegion": "CDMX",
                    "addressCountry": "MX",
                },
            },
            "image": [f"{site_url}/assets/og-cnitp.jpg"],
            "description": "Las y los 200 reconocidos reciben su distinción en una ceremonia de gala.",
            "organizer": {"@id": f"{site_url}/#organizacion"},
            "offers": [
                {"@type": "Offer", "name": "Gala", "price": "950", "priceCurrency": "MXN",
                 "url": FORM_URL, "availability": "https://schema.org/InStock"},
                {"@type": "Offer", "name": "Gala con certificado de participación", "price": "1100",
                 "priceCurrency": "MXN", "url": FORM_URL, "availability": "https://schema.org/InStock"},
            ],
        },
    ]

    t, d = html.escape(TITLE), html.escape(DESCRIPTION)
    head = f"""<!doctype html>
<html lang="es-MX">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{site_url}/">
<meta name="theme-color" content="#071610">
<link rel="icon" href="./assets/{ICON_SVG}" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_MX">
<meta property="og:site_name" content="CNITP">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{site_url}/">
<meta property="og:image" content="{site_url}/assets/og-cnitp.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Cartel de la convocatoria Los 100 más destacados de la tanatología y de la psicología">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="image" href="./assets/{HERO_BG}" fetchpriority="high">
<link rel="stylesheet" href="{html.escape(fonts)}">
<style>{style}</style>
<script src="./js/{js_name}" defer></script>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<a class="cn-skip" href="#contenido">Saltar al contenido</a>
"""
    out = head + body + "\n</body>\n</html>\n"
    (DIST / "index.html").write_text(out, encoding="utf-8")

    # --- archivos de Cloudflare Pages ---
    (DIST / "404.html").write_text(NOT_FOUND.replace("{ICON}", ICON_SVG), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{site_url}/</loc></url>\n</urlset>\n", encoding="utf-8")
    (DIST / "_headers").write_text(HEADERS, encoding="utf-8")

    # --- verificación: todo lo referenciado existe ---
    refs = set(re.findall(r"\./(assets/[^\s\"')]+|js/[^\s\"')]+)", out))
    missing = [r for r in refs if not (DIST / r).exists()]
    if missing:
        raise SystemExit(f"Faltan archivos: {missing}")
    keep = {Path(r).name for r in refs} | {"og-cnitp.jpg", ICON_SVG, LOGO_SVG}
    for p in (DIST / "assets").iterdir():
        if p.name not in keep:
            p.unlink()  # variantes generadas que ninguna página usa
    total = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
    log(f"OK dist/ · {len(refs)} referencias · {total / 1024:.0f} KB en total · {site_url}")


NOT_FOUND = """<!doctype html>
<html lang="es-MX">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Página no encontrada · CNITP</title>
<link rel="icon" href="/assets/{ICON}" type="image/svg+xml">
<style>
body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #071610; color: #F4EEDF; font-family: 'Helvetica Neue', Arial, sans-serif; text-align: center; padding: 24px; }
h1 { font-family: 'Times New Roman', serif; font-size: 40px; margin: 0 0 12px; letter-spacing: 0.04em; }
p { color: #C9C6B4; margin: 0 0 24px; }
a { display: inline-block; background: #B8923F; color: #071610; font-weight: 800; padding: 14px 22px; border-radius: 4px; text-decoration: none; }
a:focus-visible { outline: 3px solid #F0D48A; outline-offset: 3px; }
</style>
</head>
<body>
<main>
<h1>PÁGINA NO ENCONTRADA</h1>
<p>La dirección que buscas no existe o cambió.</p>
<a href="/">Ir al inicio</a>
</main>
</body>
</html>
"""

HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
  Strict-Transport-Security: max-age=31536000
  Content-Security-Policy: default-src 'self'; script-src 'self' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://cloudflareinsights.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/js/*
  Cache-Control: public, max-age=31536000, immutable
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-url", default="https://cnitp.pages.dev")
    build(ap.parse_args().site_url)
