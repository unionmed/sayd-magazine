#!/usr/bin/env python3
"""Build Nayef-approved, trilingual Sayd Market product listings.

Preserve each market edition's shared chrome; fall back to the homepage for new routes.
Purchase links use the owner-approved Awin program and disclose commission.
Checkout remains with the seller. The historical filename remains for existing regeneration callers.
"""
from pathlib import Path
import html
import json
from decimal import Decimal
import posixpath
import re
from urllib.parse import parse_qs, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
ORIGIN = 'https://sayd-magazine.com/'
COPY = {
    'ar': ('سوق صيد', 'جهّز رحلتك', 'أدوات تيتانيوم للتخييم والطبخ والقهوة في الطبيعة، مع روابط شراء إلى المتجر الرسمي عبر برنامج Awin.', 'الرئيسية', 'مجلة صيد', 'ar_AR'),
    'en': ('Sayd Market', 'Gear for your next outing', 'Titanium gear for camping, outdoor cooking and coffee, with purchase links to the official store through Awin.', 'Home', 'Sayd Magazine', 'en_US'),
    'fr': ('Marché Sayd', 'Équipez votre prochaine sortie', 'Équipement en titane pour le camping, la cuisine et le café en plein air, avec des liens d’achat vers la boutique officielle via Awin.', 'Accueil', 'Sayd Magazine', 'fr_FR'),
}
ROUTES = {lang: ('' if lang == 'ar' else lang + '/') + 'market/' for lang in COPY}
CATALOG = ROOT / 'content/market/products.json'
LABELS = {
    'ar': ('شراء المنتج', 'الصور والأسعار: SilverAnt. الشراء والدفع لدى البائع، بالسعر الظاهر في متجره عند الطلب.', 'SilverAnt', 'اختيارات للهواء الطلق', 'منتجات السوق'),
    'en': ('Buy product', 'Photos and prices: SilverAnt. Purchase and payment take place with the seller, at the price shown in its store when ordering.', 'SilverAnt', 'For the outdoors', 'Market products'),
    'fr': ('Acheter le produit', 'Photos et prix : SilverAnt. L’achat et le paiement s’effectuent chez le vendeur, au prix affiché dans sa boutique lors de la commande.', 'SilverAnt', 'Pour le plein air', 'Produits du marché'),
}
DISCLOSURES = {
    'ar': 'قد تحصل مجلة صيد على عمولة عند الشراء عبر هذه الروابط.',
    'en': 'Sayd Magazine may earn a commission when you buy through these links.',
    'fr': 'Le magazine Sayd peut percevoir une commission lorsque vous achetez via ces liens.',
}


def purchase_url(product):
    """Keep the seller destination intact; accept only this approved Awin link."""
    seller = urlsplit(product['url'])
    assert seller.scheme == 'https' and seller.netloc == 'silverantoutdoors.com'
    assert seller.path.startswith('/products/') and not seller.fragment
    assert parse_qs(seller.query, keep_blank_values=True, strict_parsing=True) == {
        'variant': [str(product['price']['variant_id'])], 'currency': ['USD']}
    affiliate = urlsplit(product['affiliate_url'])
    assert affiliate.scheme == 'https' and affiliate.netloc == 'www.awin1.com'
    assert affiliate.path == '/cread.php' and not affiliate.fragment
    assert parse_qs(affiliate.query, keep_blank_values=True, strict_parsing=True) == {
        'awinmid': ['45577'], 'awinaffid': ['3146890'], 'ued': [product['url']]}
    return product['affiliate_url']


STYLE = '''<style id="sayd-market-styles">
.market-shell{max-width:1120px;margin:auto}.market-intro{max-width:760px;margin:0 0 32px}.market-intro .market-name{font-weight:800;color:#667044;font-size:15px;letter-spacing:.04em}.market-intro h1{font-size:clamp(30px,4vw,46px);line-height:1.35;margin:8px 0 14px}.market-intro p{font-size:18px;line-height:1.9}.market-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:22px}.market-product{min-width:0;display:flex;flex-direction:column;background:#fff;border:1px solid #e1e1d5;border-radius:12px;overflow:hidden}.market-visual{display:block;background:#fff;border-bottom:1px solid #e1e1d5}.market-photo{display:block;width:100%;height:auto;aspect-ratio:1/1;object-fit:contain}.market-visual:focus-visible{outline:3px solid #a76e25;outline-offset:-4px}.market-product-copy{display:flex;flex-direction:column;flex:1;padding:22px}.market-category{font-size:13px;font-weight:700;color:#68704e;margin:0 0 8px}.market-product h2{font-size:21px;line-height:1.5;margin:0 0 12px;overflow-wrap:anywhere}.market-description{font-size:16px;line-height:1.85;margin:0 0 18px}.market-seller{font-size:13px;color:#626757;margin:auto 0 10px;padding-top:4px}.market-price{font-size:25px;line-height:1.3;font-weight:800;color:#3e421d;margin:0 0 17px}.market-price span{font-size:13px;font-weight:600}.market-buy{display:block;text-align:center;background:#3e421d;color:#fff!important;border-radius:6px;padding:12px 14px;font-size:15px;font-weight:700;text-decoration:none!important}.market-buy:hover{background:#59602d}.market-buy:focus-visible{outline:3px solid #a76e25;outline-offset:4px}.market-note{font-size:14px;line-height:1.8;margin:24px 0 0;color:#535849;border-inline-start:3px solid #b3b792;padding-inline-start:14px}.market-eyebrow{margin-top:0;font-size:13px;text-transform:uppercase;color:#68704e}.market-name bdi{unicode-bidi:isolate}@media(max-width:820px){.market-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.market-grid{grid-template-columns:1fr;gap:20px}.market-product-copy{padding:20px}.market-intro h1{font-size:32px}.market-intro p{font-size:17px}.market-photo{height:260px;aspect-ratio:auto}}
</style>'''


def product_cards(lang):
    products = json.loads(CATALOG.read_text(encoding='utf-8'))['products']
    cta, note, illustration, eyebrow, section = LABELS[lang]
    cards = []
    for index, product in enumerate(products):
        local = product['copy'][lang]
        destination = purchase_url(product)
        photo = product['image']
        assert product['price']['currency'] == 'USD'
        amount = f"{Decimal(product['price']['amount']):.2f}"
        image_url = '/' + photo['path']
        loading = 'eager' if index < 4 else 'lazy'
        esc = html.escape
        cards.append(f'''<article class="market-product" data-product-id="{esc(product['id'], quote=True)}">
      <a class="market-visual" href="{esc(destination, quote=True)}" target="_blank" rel="noopener noreferrer sponsored" aria-label="{esc(local['name'], quote=True)}"><img class="market-photo" src="{esc(image_url, quote=True)}" alt="{esc('SilverAnt — ' + local['name'], quote=True)}" width="{photo['width']}" height="{photo['height']}" loading="{loading}" decoding="async"></a>
      <div class="market-product-copy"><p class="market-category">{esc(local['category'])}</p><h2><bdi>{esc(local['name'])}</bdi></h2><p class="market-description">{esc(local['description'])}</p><p class="market-seller"><bdi>{esc(local['seller'])}</bdi></p><p class="market-price" data-currency="USD" data-price="{amount}"><bdi dir="ltr">${amount} <span>USD</span></bdi></p><a class="market-buy" href="{esc(destination, quote=True)}" target="_blank" rel="noopener noreferrer sponsored" data-market-product="{esc(product['id'], quote=True)}">{cta}</a></div>
    </article>''')
    return f'<section class="market-grid" aria-label="{section}">' + '\n'.join(cards) + f'</section><p class="market-note">{note}</p>'


def build(lang):
    label, status, paragraph, home_label, magazine, locale = COPY[lang]
    source_dir = '' if lang == 'ar' else lang
    target_dir = ROUTES[lang].rstrip('/')
    # Search reuses this shell with temporary COPY/ROUTES. Only real market
    # routes may preserve their existing page or receive product content/styles.
    is_market = target_dir == posixpath.join(source_dir, 'market')
    existing = DOCS / target_dir / 'index.html'
    source = existing if is_market and existing.is_file() else DOCS / source_dir / 'index.html'
    page = source.read_text(encoding='utf-8')
    title = f'{label} — {status} | {magazine}'
    canonical = ORIGIN + ROUTES[lang]
    home = ORIGIN + ('' if lang == 'ar' else lang + '/')
    # Strip the homepage content before rebasing so only shared chrome survives.
    body = f'''<main class="page-main" id="content">
  <div class="container">
    <div class="market-shell">
      <div class="breadcrumb"><a href="{home}">{home_label}</a> / {label}</div>
      <header class="market-intro"><p class="market-name">{label}</p><h1>{status}</h1><p>{paragraph}</p>{f'<p class="market-disclosure">{DISCLOSURES[lang]}</p>' if is_market else ''}</header>
      {product_cards(lang) if is_market else ''}
    </div>
  </div>
</main>'''
    page, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: body, page, count=1, flags=re.S)
    assert count == 1
    page = re.sub(r'<style id="sayd-market-styles">.*?</style>\n?', '', page, flags=re.S)
    if is_market:
        # Shared search regeneration keeps its entry CSS just before analytics.
        # Place market CSS ahead of it so both builders preserve the same order.
        search_style = re.search(r'<link rel="stylesheet" href="[^\"]*search-entry\.css[^\"]*">', page)
        insertion = search_style.start() if search_style else page.index('</head>')
        page = page[:insertion] + STYLE + '\n' + page[insertion:]
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
