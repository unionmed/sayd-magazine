#!/usr/bin/env python3
"""Build only Nayef-approved, trilingual Sayd Market coming-soon pages.

Reuse each edition's current homepage chrome; run before shared chrome rollouts.
No product listings, affiliate claims, checkout or signup are introduced.
"""
from pathlib import Path
import html
import json
import posixpath
import re
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
ORIGIN = 'https://sayd-magazine.com/'
COPY = {
    'ar': ('سوق صيد', 'قريبًا', 'نحضّر لإطلاق سوق صيد، مساحة لمنتجات وخدمات تهمّ محبّي الصيد والفروسية والطبيعة. يهدف السوق إلى دعم نشاطات المجلة واستمرار تقديم محتوى متخصص وموثوق. نشارككم التفاصيل عند الإطلاق.', 'الرئيسية', 'مجلة صيد', 'ar_AR'),
    'en': ('Sayd Market', 'Coming soon', 'We are preparing to launch Sayd Market, a space for products and services of interest to hunting, equestrian and nature enthusiasts. The market aims to support the magazine’s activities and the continued publication of specialized, reliable content. We will share the details at launch.', 'Home', 'Sayd Magazine', 'en_US'),
    'fr': ('Marché Sayd', 'Bientôt', 'Nous préparons le lancement du Marché Sayd, un espace de produits et de services destinés aux passionnés de chasse, d’équitation et de nature. Ce marché vise à soutenir les activités du magazine et la publication continue de contenus spécialisés et fiables. Nous vous communiquerons les détails lors du lancement.', 'Accueil', 'Sayd Magazine', 'fr_FR'),
}
ROUTES = {lang: ('' if lang == 'ar' else lang + '/') + 'market/' for lang in COPY}


def build(lang):
    label, status, paragraph, home_label, magazine, locale = COPY[lang]
    source_dir = '' if lang == 'ar' else lang
    target_dir = ROUTES[lang].rstrip('/')
    source = DOCS / source_dir / 'index.html'
    page = source.read_text(encoding='utf-8')
    title = f'{label} — {status} | {magazine}'
    canonical = ORIGIN + ROUTES[lang]
    home = ORIGIN + ('' if lang == 'ar' else lang + '/')
    # Strip the homepage content before rebasing so only shared chrome survives.
    body = f'''<main class="page-main" id="content">
  <div class="container">
    <div class="article-shell">
      <div class="breadcrumb"><a href="index.html">{home_label}</a> / {label}</div>
      <header class="article-header"><p class="market-name">{label}</p><h1>{status}</h1></header>
      <article class="article-content"><p>{paragraph}</p></article>
    </div>
  </div>
</main>'''
    page, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: body, page, count=1, flags=re.S)
    assert count == 1
    # Relative URLs are rooted in the source edition; rebase for /market/.
    def rebase(match):
        attr, quote, raw = match.groups()
        url = urlsplit(html.unescape(raw))
        if url.scheme or url.netloc or not url.path or url.path.startswith('/'):
            return match.group(0)
        absolute = posixpath.normpath(posixpath.join(source_dir, url.path))
        path = posixpath.relpath(absolute, target_dir)
        return attr + '=' + quote + html.escape(urlunsplit(('', '', path, url.query, url.fragment)), quote=True) + quote
    page = re.sub(r'\b(href|src)=([\"\'])(.*?)\2', rebase, page)
    switch = '<nav class="lang-switch" aria-label="Language">' + ''.join(
        f'<a href="{posixpath.relpath(route + "index.html", target_dir)}" lang="{code}" hreflang="{code}"' + (' class="is-current" aria-current="page"' if code == lang else '') + f'>{name}</a>'
        for (code, route), name in zip(ROUTES.items(), ('العربية', 'English', 'Français'))
    ) + '</nav>'
    page = re.sub(r'<nav class="lang-switch".*?</nav>', lambda _: switch, page, count=1, flags=re.S)
    page = re.sub(r'<title>.*?</title>', '<title>' + html.escape(title) + '</title>', page, count=1)
    page = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="' + html.escape(paragraph, quote=True) + '">', page, count=1)
    seo = ['<!-- seo:start -->', f'<link rel="canonical" href="{canonical}">']
    for key, value in [('og:locale', locale), ('og:type', 'website'), ('og:site_name', magazine), ('og:title', title), ('og:description', paragraph), ('og:url', canonical)]:
        seo.append(f'<meta property="{key}" content="{html.escape(value, quote=True)}">')
    for key, value in [('twitter:card', 'summary'), ('twitter:title', title), ('twitter:description', paragraph)]:
        seo.append(f'<meta name="{key}" content="{html.escape(value, quote=True)}">')
    for code, route in {**ROUTES, 'x-default': ROUTES['ar']}.items():
        seo.append(f'<link rel="alternate" hreflang="{code}" href="{ORIGIN}{route}">')
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': home_label, 'item': home},
        {'@type': 'ListItem', 'position': 2, 'name': label, 'item': canonical},
    ]}
    seo.append('<script type="application/ld+json">' + json.dumps(crumbs, ensure_ascii=False) + '</script>')
    seo.append('<!-- seo:end -->')
    page, count = re.subn(r'<!-- seo:start -->.*?<!-- seo:end -->', lambda _: '\n  '.join(seo), page, count=1, flags=re.S)
    assert count == 1
    target = DOCS / target_dir / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding='utf-8')
    return target

if __name__ == '__main__':
    for lang in COPY:
        print(build(lang).relative_to(ROOT))
