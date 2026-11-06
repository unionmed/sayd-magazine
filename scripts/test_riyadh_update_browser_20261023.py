#!/usr/bin/env python3
"""Read-only Riyadh responsive QA with exact October/November editorial states."""
import functools
import hashlib
import html
import http.server
import json
import re
import threading
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'riyadh-update-visual-qa'
# The original 23 October section is immutable. The only added state is the
# approved 5 November update sourced from JCSA's 20261105_riyadh_wk4_previewrelease.
EXPECTED = {'ar': {'slug': 'الرياض-تستعيد-صهيلها-موسم-السباقات-2026',
        'title': 'الرياض تستعيد صهيلها ..وموسم السباقات ينطلق',
        'historical_sha256': '69c94d0cc855cc285ff8637571430d9408b9d6fa51f5bb7c09f3d1b60bba2ef6',
        'heading': 'تحديث 5 تشرين الثاني 2026: 24 شوطًا في الأسبوع الرابع',
        'paragraphs': ['يستضيف ميدان الملك عبدالعزيز للفروسية بالرياض، يومَي الجمعة والسبت 6 و7 تشرين '
                       'الثاني، الحفلين السابع والعشرين والثامن والعشرين من موسم السباقات، ببرنامج يضم 24 '
                       'شوطًا، بواقع 12 شوطًا في كل أمسية، وجوائز تتجاوز 2.1 مليون ريال.',
                       'وتبرز يوم الجمعة الأشواط التحضيرية لكأسَي ولي العهد للإنتاج ومفتوح الدرجات، وكلاهما '
                       'لمسافة 2000 متر. وتشمل منافسات الأسبوع كأس نادي سباقات الخيل، المصنف ضمن الفئة '
                       'الثالثة محليًا، على مسافة 1600 متر وبجائزة 165 ألف ريال.',
                       'أما السبت، فيشهد كأسَي الأمير سعود بن سلمان للأفراس والحصن بعمر السنتين، على مسافة '
                       '1600 متر وبجائزة 300 ألف ريال لكل كأس.']},
 'en': {'slug': 'riyadh-racing-season-2026-2027-begins',
        'title': 'Riyadh hears the horses again… the racing season begins',
        'historical_sha256': 'e0c5f228f02ba65d44433443fc2bcbb34c432c1aad57689843f9a3f3369bb223',
        'heading': 'Update, 5 November 2026: 24 races in week four',
        'paragraphs': ['King Abdulaziz Racecourse in Riyadh hosts the season’s 27th and 28th meetings on '
                       'Friday and Saturday, 6 and 7 November. The programme features 24 races, with 12 on '
                       'each evening and more than SAR 2.1 million in total prize money.',
                       'Friday’s highlights include the Crown Prince Cup preparation races for locally bred '
                       'horses and the open division, both over 2,000 metres. The week’s programme also '
                       'includes the Jockey Club Cup, a domestic Group 3 over 1,600 metres worth SAR '
                       '165,000.',
                       'Saturday features the Prince Saud bin Salman Cups for two-year-old fillies and '
                       'colts, both over 1,600 metres and each offering SAR 300,000.']},
 'fr': {'slug': 'riyadh-racing-season-2026-2027-begins',
        'title': 'Riyad retrouve les hennissements… la saison des courses commence',
        'historical_sha256': '642ae607792dbcea40ffd95702cf7c57f7e6216d37362477a1b31e639f257535',
        'heading': 'Mise à jour du 5 novembre 2026 : 24 courses pour la quatrième semaine',
        'paragraphs': ['L’hippodrome du roi Abdelaziz, à Riyad, accueille les 27e et 28e réunions de la '
                       'saison les vendredi 6 et samedi 7 novembre. Le programme compte 24 courses, soit 12 '
                       'par soirée, pour une dotation totale supérieure à 2,1 millions de riyals.',
                       'Vendredi, les préparatoires aux Coupes du prince héritier, l’une réservée aux '
                       'chevaux élevés dans le pays et l’autre ouverte, se disputent sur 2 000 mètres. Le '
                       'programme de la semaine comprend aussi la Coupe du Jockey Club, classée Groupe 3 au '
                       'niveau national, sur 1 600 mètres et dotée de 165 000 riyals.',
                       'Samedi, les Coupes du prince Saoud ben Salmane sont réservées aux pouliches et aux '
                       'poulains de deux ans. Chacune se court sur 1 600 mètres et offre 300 000 riyals.']}}


def validate_html_state(source, lang):
    expected = EXPECTED[lang]
    sections = re.findall(r'<section class="riyadh-season-update"[^>]*>.*?</section>', source, re.S)
    assert len(sections) in (1, 2), (lang, 'unexpected update count')
    historical = sections[-1]
    assert historical.startswith('<section class="riyadh-season-update">')
    assert hashlib.sha256(historical.encode()).hexdigest() == expected['historical_sha256'], (lang, 'historical update changed')
    if len(sections) == 2:
        exact_new = '<section class="riyadh-season-update" data-update="2026-11-05"><h2>' + html.escape(expected['heading']) + '</h2>'
        exact_new += ''.join('<p>' + html.escape(p) + '</p>' for p in expected['paragraphs']) + '</section>'
        assert sections[0] == exact_new, (lang, 'unexpected November update')
        modified = '2026-11-05'
    else:
        modified = '2026-10-23'
    assert re.search(r'<h1[^>]*>(.*?)</h1>', source, re.S).group(1) == expected['title']
    schemas = [json.loads(block) for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', source, re.S)]
    article = next(s for s in schemas if s.get('@type') == 'NewsArticle')
    assert article['datePublished'] == '2026-10-16T21:00:00+03:00'
    assert article['dateModified'] == modified
    return modified, len(sections)


def main():
    from playwright.sync_api import sync_playwright

    states = {}
    for lang, expected in EXPECTED.items():
        path = ROOT / 'docs' / ('' if lang == 'ar' else lang) / 'posts' / expected['slug'] / 'index.html'
        states[lang] = validate_html_state(path.read_text(), lang)
    assert len(set(states.values())) == 1, 'Riyadh language update states differ'
    OUT.mkdir(exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'docs'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    records = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome', headless=True)
            try:
                for lang, expected in EXPECTED.items():
                    modified, section_count = states[lang]
                    for device, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
                        page = browser.new_page(viewport={'width': width, 'height': height})
                        page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin + '/') or route.request.url.startswith('data:') else route.abort())
                        url = origin + '/' + ('' if lang == 'ar' else lang + '/') + 'posts/' + quote(expected['slug']) + '/index.html'
                        response = page.goto(url, wait_until='networkidle')
                        assert response.status == 200
                        updates = page.locator('.riyadh-season-update')
                        assert updates.count() == section_count
                        assert updates.last.get_attribute('data-update') is None
                        if section_count == 2:
                            assert updates.first.get_attribute('data-update') == '2026-11-05'
                            assert updates.first.locator('h2').inner_text() == expected['heading']
                            assert updates.first.locator('p').all_inner_texts() == expected['paragraphs']
                        assert page.locator('.article-updated time').get_attribute('datetime') == modified
                        assert page.locator('.article-content a[href^="http"]').count() == 0
                        assert page.locator('.riyadh-related a').count() == 2
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (lang, device, 'overflow')
                        for image in page.locator('.article-content img').all():
                            image.scroll_into_view_if_needed()
                            image.evaluate('(img)=>img.decode()')
                            assert image.evaluate('(img)=>img.complete&&img.naturalWidth>0')
                        page.locator('.article-header').screenshot(path=str(OUT / f'{lang}-{device}-header.png'))
                        updates.first.scroll_into_view_if_needed()
                        page.screenshot(path=str(OUT / f'{lang}-{device}-update.png'))
                        if section_count == 2:
                            updates.last.scroll_into_view_if_needed()
                            page.screenshot(path=str(OUT / f'{lang}-{device}-historical-update.png'))
                        records.append({'lang': lang, 'device': device, 'width': width, 'status': 'PASS', 'updated': modified, 'title': page.locator('h1').inner_text()})
                        page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
    (OUT / 'results.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(records, ensure_ascii=False))


if __name__ == '__main__':
    main()
