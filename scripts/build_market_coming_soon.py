#!/usr/bin/env python3
"""Build Nayef-approved, trilingual Sayd Market product listings.

Preserve each market edition's shared chrome; fall back to the homepage for new routes.
Products link directly to sellers. No affiliate relationship or on-site checkout
is implied. The historical filename remains for existing regeneration callers.
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
    'ar': ('سوق صيد', 'جهّز رحلتك', 'أدوات تيتانيوم للتخييم والطبخ والقهوة في الطبيعة، مع روابط مباشرة إلى المتجر الرسمي.', 'الرئيسية', 'مجلة صيد', 'ar_AR'),
    'en': ('Sayd Market', 'Gear for your next outing', 'Titanium gear for camping, outdoor cooking and coffee, with direct links to the official store.', 'Home', 'Sayd Magazine', 'en_US'),
    'fr': ('Marché Sayd', 'Équipez votre prochaine sortie', 'Équipement en titane pour le camping, la cuisine et le café en plein air, avec des liens directs vers la boutique officielle.', 'Accueil', 'Sayd Magazine', 'fr_FR'),
}
ROUTES = {lang: ('' if lang == 'ar' else lang + '/') + 'market/' for lang in COPY}
CATALOG = ROOT / 'content/market/products.json'
LABELS = {
    'ar': ('عرض السعر والشراء', 'الشراء والدفع لدى البائع. راجع السعر والتوافر والتوصيل على موقعه.', 'رسم توضيحي', 'اختيارات للهواء الطلق', 'منتجات السوق'),
    'en': ('View price & buy', 'Purchase and payment take place on the seller’s website. Check prices, availability and delivery there.', 'Illustration', 'For the outdoors', 'Market products'),
    'fr': ('Voir le prix et acheter', 'L’achat et le paiement s’effectuent sur le site du vendeur. Vérifiez les prix, la disponibilité et la livraison sur son site.', 'Illustration', 'Pour le plein air', 'Produits du marché'),
}
ILLUSTRATIONS = {'bottle': '<path d="M163 52h34v23c0 9 21 15 21 31v77c0 23-76 23-76 0v-77c0-16 21-22 21-31z" '
           'fill="#96a5a4"/><rect x="157" y="43" width="46" height="20" rx="6" fill="#4d5b58"/><path d="M200 '
           '46c27-11 30 21 8 24M154 110v66" fill="none" stroke="#c9d4cf" stroke-width="6" '
           'stroke-linecap="round"/>',
 'cup': '<ellipse cx="174" cy="90" rx="63" ry="19" fill="#c6cecb"/><path d="M111 90v78c0 28 126 28 126 0V90" '
        'fill="#8c9f9c"/><ellipse cx="174" cy="90" rx="54" ry="12" fill="#566c64"/><path d="M239 '
        '109h22v53h-22M244 115h10v41h-10" fill="none" stroke="#536b61" stroke-width="5"/><path d="M110 185h128" '
        'stroke="#bdc7bd" stroke-width="3"/>',
 'pot': '<path d="M108 105v61c0 35 144 35 144 0v-61" fill="#8c9f9c"/><ellipse cx="180" cy="105" rx="72" ry="19" '
        'fill="#c3ceca"/><path d="M111 110c-17-100 155-100 138 0" fill="none" stroke="#4f655d" '
        'stroke-width="5"/><path d="M162 84v-9h36v9" fill="none" stroke="#53685e" stroke-width="5"/><path d="M250 '
        '126h28v34h-28" fill="none" stroke="#53685e" stroke-width="5"/>',
 'cutlery': '<path d="M116 65v44c0 20 28 20 28 0V65M130 65v125M177 65v125M177 65c30 9 28 54 0 61" fill="none" '
            'stroke="#8d9f9d" stroke-width="10" stroke-linecap="round"/><ellipse cx="227" cy="87" rx="18" ry="29" '
            'fill="#a7b5b0"/><path d="M227 115v75" stroke="#8d9f9d" stroke-width="10" stroke-linecap="round"/>',
 'plate': '<ellipse cx="180" cy="140" rx="102" ry="49" fill="#7c928b"/><ellipse cx="180" cy="130" rx="102" '
          'ry="49" fill="#c4ceca"/><ellipse cx="180" cy="132" rx="80" ry="33" fill="#98aaa4"/><path d="M113 '
          '129c11-24 92-31 132-5" fill="none" stroke="#dce2dc" stroke-width="4"/>',
 'press': '<path d="M139 78v95c0 29 84 29 84 0V78" fill="#8eaaa0"/><ellipse cx="181" cy="78" rx="42" ry="13" '
          'fill="#c4d0c9"/><path d="M181 51v87M143 140h76" stroke="#506f61" stroke-width="5"/><rect x="168" '
          'y="42" width="26" height="12" rx="5" fill="#8f754e"/><path d="M224 105h23v52h-23" fill="none" '
          'stroke="#547164" stroke-width="5"/>',
 'kettle': '<path d="M126 115c0-41 109-41 109 0v52c0 36-109 36-109 0z" fill="#92a69e"/><path d="M128 121l-42-26 '
           '11 47 31 12" fill="#b4c2ba"/><path d="M146 99c-20-74 100-74 79 9" fill="none" stroke="#526b5e" '
           'stroke-width="8"/><ellipse cx="180" cy="105" rx="32" ry="9" fill="#c9d2cb"/><path d="M170 '
           '97v-10h20v10" fill="none" stroke="#526b5e" stroke-width="5"/>',
 'stakes': '<path d="M113 76l32 109M154 66l31 119M195 64l30 121M235 66l30 119" stroke="#668ca6" '
           'stroke-width="12"/><path d="M107 70c-21-26 17-37 15-2M148 60c-21-26 17-37 15-2M189 58c-21-26 17-37 '
           '15-2M229 60c-21-26 17-37 15-2" fill="none" stroke="#bea457" stroke-width="4"/>'}
STYLE = '''<style id="sayd-market-styles">
.market-shell{max-width:1120px;margin:auto}.market-intro{max-width:760px;margin:0 0 32px}.market-intro .market-name{font-weight:800;color:#667044;font-size:15px;letter-spacing:.04em}.market-intro h1{font-size:clamp(30px,4vw,46px);line-height:1.35;margin:8px 0 14px}.market-intro p{font-size:18px;line-height:1.9}.market-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:22px}.market-product{min-width:0;display:flex;flex-direction:column;background:#fff;border:1px solid #e1e1d5;border-radius:12px;overflow:hidden}.market-visual{position:relative;background:#f0f0e6;border-bottom:1px solid #e1e1d5}.market-visual svg{display:block;width:100%;height:auto;aspect-ratio:3/2}.market-illustration{position:absolute;inset-inline-end:12px;bottom:8px;color:#5c624e;font-size:11px}.market-product-copy{display:flex;flex-direction:column;flex:1;padding:22px}.market-category{font-size:13px;font-weight:700;color:#68704e;margin:0 0 8px}.market-product h2{font-size:21px;line-height:1.5;margin:0 0 12px;overflow-wrap:anywhere}.market-description{font-size:16px;line-height:1.85;margin:0 0 18px}.market-seller{font-size:13px;color:#626757;margin:auto 0 16px;padding-top:4px}.market-buy{display:block;text-align:center;background:#3e421d;color:#fff!important;border-radius:6px;padding:12px 14px;font-size:15px;font-weight:700;text-decoration:none!important}.market-buy:hover{background:#59602d}.market-buy:focus-visible{outline:3px solid #a76e25;outline-offset:4px}.market-note{font-size:14px;line-height:1.8;margin:24px 0 0;color:#535849;border-inline-start:3px solid #b3b792;padding-inline-start:14px}.market-eyebrow{margin-top:0;font-size:13px;text-transform:uppercase;color:#68704e}.market-name bdi{unicode-bidi:isolate}@media(max-width:820px){.market-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.market-grid{grid-template-columns:1fr;gap:20px}.market-product-copy{padding:20px}.market-intro h1{font-size:32px}.market-intro p{font-size:17px}.market-visual svg{max-height:220px}}
</style>'''


def product_cards(lang):
    products = json.loads(CATALOG.read_text(encoding='utf-8'))['products']
    cta, note, illustration, eyebrow, section = LABELS[lang]
    cards = []
    for product in products:
        local = product['copy'][lang]
        assert urlsplit(product['url']).scheme == 'https'
        visual = ILLUSTRATIONS[product['illustration']]
        esc = html.escape
        cards.append(f'''<article class="market-product" data-product-id="{esc(product['id'], quote=True)}">
      <div class="market-visual"><svg viewBox="0 0 360 240" role="img" aria-label="{esc(illustration + ': ' + local['name'], quote=True)}"><ellipse cx="180" cy="200" rx="112" ry="9" fill="#dedfd1"/>{visual}</svg><span class="market-illustration">{illustration}</span></div>
      <div class="market-product-copy"><p class="market-category">{esc(local['category'])}</p><h2><bdi>{esc(local['name'])}</bdi></h2><p class="market-description">{esc(local['description'])}</p><p class="market-seller"><bdi>{esc(local['seller'])}</bdi></p><a class="market-buy" href="{esc(product['url'], quote=True)}" target="_blank" rel="noopener noreferrer" data-market-product="{esc(product['id'], quote=True)}">{cta} ↗</a></div>
    </article>''')
    return f'<section class="market-grid" aria-label="{section}">' + '\n'.join(cards) + f'</section><p class="market-note">{note}</p>'


def build(lang):
    label, status, paragraph, home_label, magazine, locale = COPY[lang]
    source_dir = '' if lang == 'ar' else lang
    target_dir = ROUTES[lang].rstrip('/')
    existing = DOCS / target_dir / 'index.html'
    source = existing if existing.is_file() else DOCS / source_dir / 'index.html'
    page = source.read_text(encoding='utf-8')
    title = f'{label} — {status} | {magazine}'
    canonical = ORIGIN + ROUTES[lang]
    home = ORIGIN + ('' if lang == 'ar' else lang + '/')
    # Strip the homepage content before rebasing so only shared chrome survives.
    body = f'''<main class="page-main" id="content">
  <div class="container">
    <div class="market-shell">
      <div class="breadcrumb"><a href="{home}">{home_label}</a> / {label}</div>
      <header class="market-intro"><p class="market-name">{label}</p><h1>{status}</h1><p>{paragraph}</p></header>
      {product_cards(lang)}
    </div>
  </div>
</main>'''
    page, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: body, page, count=1, flags=re.S)
    assert count == 1
    page = re.sub(r'<style id="sayd-market-styles">.*?</style>\n?', '', page, flags=re.S)
    page = page.replace('</head>', STYLE + '\n</head>', 1)
    # Relative URLs are rooted in the source edition; rebase for /market/.
    def rebase(match):
        attr, quote, raw = match.groups()
        url = urlsplit(html.unescape(raw))
        if url.scheme or url.netloc or not url.path or url.path.startswith('/'):
            return match.group(0)
        absolute = posixpath.normpath(posixpath.join(source_dir, url.path))
        path = posixpath.relpath(absolute, target_dir)
        return attr + '=' + quote + html.escape(urlunsplit(('', '', path, url.query, url.fragment)), quote=True) + quote
    if source != existing:
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
    from ticker_scope import homepage_only, strip_internal_ticker
    if homepage_only(ROOT):
        page = strip_internal_ticker(page)
    from seo_foundation import add_ga4
    page = add_ga4(page)
    target.write_text(page, encoding='utf-8')
    return target

if __name__ == '__main__':
    for lang in COPY:
        print(build(lang).relative_to(ROOT))
