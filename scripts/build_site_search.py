#!/usr/bin/env python3
"""Build private-by-default client search and additive links. Run after publishing.

Only search pages load the index or search code. Queries never enter a URL,
server request, analytics event or persistent browser storage.
"""
from pathlib import Path
import html
import json
import os
import re
import shutil
from build_market_coming_soon import build as build_shell, COPY as MARKET_COPY, ROUTES as MARKET_ROUTES

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
COPY = {
 'ar': dict(title='البحث في صيد', label='بحث', intro='ابحث في مقالات صيد وأرشيفها، بالعنوان أو الكلمات أو الاسم العلمي.', query='كلمات البحث', submit='بحث', language='لغة المقالات', year='السنة', category='الباب', all='الكل', empty='اكتب كلمات للبحث في المقالات والأرشيف.', none='لا توجد نتائج. جرّب كلمات أخرى أو أزل المرشحات.', loading='جارٍ تحميل فهرس البحث…', error='تعذّر تحميل البحث. حاول مجددًا أو تصفّح الأرشيف.', results='نتيجة', more='عرض المزيد', archive='تصفّح الأرشيف', nojs='يتطلب البحث تفعيل JavaScript. يمكنك تصفّح الأرشيف عبر الرابط أدناه.', privacy='تُجرى عمليات البحث داخل متصفحك، ولا نرسل كلمات البحث إلى خدمة خارجية.'),
 'en': dict(title='Search Sayd', label='Search', intro='Explore Sayd articles and archives by title, keyword or scientific name.', query='Search terms', submit='Search', language='Article language', year='Year', category='Section', all='All', empty='Enter words to search articles and archives.', none='No results. Try different words or remove filters.', loading='Loading the search index…', error='Search could not load. Try again or browse the archive.', results='results', more='Show more', archive='Browse the archive', nojs='Search requires JavaScript. You can browse the archive using the link below.', privacy='Searches run in your browser. We do not send your search terms to an external service.'),
 'fr': dict(title='Rechercher dans Sayd', label='Rechercher', intro='Explorez les articles et les archives de Sayd par titre, mot-clé ou nom scientifique.', query='Termes de recherche', submit='Rechercher', language='Langue des articles', year='Année', category='Rubrique', all='Toutes', empty='Saisissez des mots pour rechercher dans les articles et les archives.', none='Aucun résultat. Essayez d’autres mots ou retirez les filtres.', loading='Chargement de l’index de recherche…', error='La recherche n’a pas pu être chargée. Réessayez ou consultez les archives.', results='résultats', more='Afficher plus', archive='Consulter les archives', nojs='La recherche nécessite JavaScript. Vous pouvez consulter les archives avec le lien ci-dessous.', privacy='Les recherches sont effectuées dans votre navigateur. Nous ne transmettons pas vos termes de recherche à un service externe.'),
}
ROUTES = {lang: ('' if lang == 'ar' else lang + '/') + 'search/' for lang in COPY}

def relative(path, target):
    return os.path.relpath(DOCS / target, path.parent)

def links(text, path):
    if '<header class="site-header"' not in text or 'http-equiv="refresh"' in text:
        return text
    lang = path.relative_to(DOCS).parts[0]
    lang = lang if lang in ('en', 'fr') else 'ar'
    label = COPY[lang]['label']
    href = html.escape(relative(path, ROUTES[lang]), quote=True) + '/'
    # Idempotent and byte-preserving outside these two additive link blocks.
    text = re.sub(r'<!-- search-link:start -->.*?<!-- search-link:end -->', '', text, flags=re.S)
    icon = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m16 16 5 5"></path></svg>'
    anchor = f'<!-- search-link:start --><a class="site-search-link" href="{href}" aria-label="{label}" title="{label}">{icon}</a><!-- search-link:end -->'
    text = re.sub(r'(<a class="market-cta"[^>]*>.*?</a>)', lambda m: m[1] + anchor, text, count=1, flags=re.S)
    text = re.sub(r'(<div class="container footer-bottom-inner">)', lambda m: m[1] + f'<!-- search-link:start --><a class="footer-search-link" href="{href}">{COPY[lang]["title"]}</a><!-- search-link:end -->', text, count=1)
    text = re.sub(r'<link rel="stylesheet" href="[^"]*search-entry\.css[^"]*">\n', '', text)
    css = relative(path, 'assets/css/search-entry.css')
    style = f'<link rel="stylesheet" href="{css}?v=20261017">\n'
    marker = '  <!-- analytics:start -->' if '  <!-- analytics:start -->' in text else '</head>'
    text = text.replace(marker, style + marker, 1)
    return text

def build_page(lang):
    c = COPY[lang]
    # Reuse current edition chrome using the existing rebasing/SEO shell builder,
    # redirecting only its in-memory copy and routes; market output is untouched.
    saved_copy, saved_routes = dict(MARKET_COPY), dict(MARKET_ROUTES)
    try:
        for code in COPY:
            old = saved_copy[code]
            MARKET_COPY[code] = (COPY[code]['title'], COPY[code]['label'], COPY[code]['intro'], *old[3:])
            MARKET_ROUTES[code] = ROUTES[code]
        path = build_shell(lang)
    finally:
        MARKET_COPY.clear(); MARKET_COPY.update(saved_copy)
        MARKET_ROUTES.clear(); MARKET_ROUTES.update(saved_routes)
    page = path.read_text()
    options = ''.join(f'<option value="{code}"'+(' selected' if code==lang else '')+f'>{name}</option>' for code,name in [('ar','العربية'),('en','English'),('fr','Français')])
    main = f'''<main class="page-main search-page" id="content" data-search-language="{lang}">
<div class="container"><h1>{c['title']}</h1><p>{c['intro']}</p>
<form id="site-search-form" role="search" autocomplete="off">
<label for="search-query">{c['query']}</label><div class="search-query-row"><input id="search-query" type="search" maxlength="200" autocomplete="off" spellcheck="false" aria-describedby="search-privacy"><button type="submit">{c['submit']}</button></div>
<div class="search-filters"><label>{c['language']}<select id="search-language">{options}</select></label><label>{c['year']}<select id="search-year"><option value="">{c['all']}</option></select></label><label>{c['category']}<select id="search-category"><option value="">{c['all']}</option></select></label></div>
</form><p id="search-privacy" class="search-note">{c['privacy']}</p><p id="search-status" role="status" aria-live="polite">{c['empty']}</p><noscript><p>{c['nojs']}</p></noscript>
<div id="search-results" class="search-results"></div><button id="search-more" type="button" hidden>{c['more']}</button>
<p><a href="../{'articles' if lang=='ar' else 'stories'}/index.html">{c['archive']}</a></p></div></main>'''
    page = re.sub(r'<main\b[^>]*>.*?</main>', lambda _: main, page, count=1, flags=re.S)
    page = re.sub(r'\s*<!-- analytics:start -->.*?<!-- analytics:end -->', '', page, flags=re.S)
    # Noindex utilities are not search-engine language alternates; the visible
    # language switch remains in the shared header.
    page = re.sub(r'[ \t]*<link\b[^>]*\bhreflang=[^>]*>[ \t]*(?:\r?\n)?', '', page, flags=re.M)
    # The shared font stacks already include local/system fallbacks. Search must
    # not contact Google Fonts (including its preconnect hosts) before a query.
    page = re.sub(r'[ \t]*<link\b[^>]*href="https://fonts\.(?:googleapis|gstatic)\.com[^"]*"[^>]*>[ \t]*(?:\r?\n)?', '', page)
    # No query in history, no analytics or form tracking, no search-engine results index.
    page = page.replace('</head>', '<meta name="robots" content="noindex,follow">\n<meta name="referrer" content="no-referrer">\n<link rel="stylesheet" href="'+relative(path,'assets/css/search.css')+'?v=20261017">\n</head>')
    page = page.replace('</body>', '<script id="search-copy" type="application/json">'+json.dumps(c,ensure_ascii=False).replace('<','\\u003c')+'</script>\n<script src="'+relative(path,'assets/js/site-search.js')+'?v=20261017" defer></script>\n</body>')
    path.write_text(page)

def main():
    # Establish source chrome before copying it, so a clean first build is stable.
    for lang in COPY:
        home = DOCS / ('' if lang == 'ar' else lang) / 'index.html'
        home.write_text(links(home.read_text(), home))
    for lang in COPY: build_page(lang)
    for file in ('css/search-entry.css','css/search.css','js/site-search.js'):
        target=DOCS/'assets'/file; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'assets'/file,target)
    changed = 0
    for path in DOCS.rglob('*.html'):
        old=path.read_text(); new=links(old,path)
        if old!=new:path.write_text(new);changed+=1
    from build_search_index import build
    build()
    print(f'Search pages and {changed} additive chrome updates built.')
if __name__=='__main__': main()
