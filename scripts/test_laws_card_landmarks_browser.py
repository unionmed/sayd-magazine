#!/usr/bin/env python3
"""Private, local-HTTP browser QA for laws thumbnails; no external requests.

Produces baseline/candidate screenshots and exercises credit disclosure,
article navigation, Back/Forward and repeated keyboard/click interactions.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from urllib.parse import quote, unquote, urlsplit
from playwright.sync_api import sync_playwright
from sync_laws_card_landmarks import ROOT, DOCS, LANGUAGES, config, category_path
from test_laws_card_landmarks import main as check_static, assert_card_geometry
from check_publication_contract import homepage_ticker_scope_repair


VIEWPORTS = [('desktop', 1440, 1000), ('mobile', 390, 844), ('narrow-mobile', 320, 800)]


def run(base, output):
    check_static(base)
    output.mkdir(parents=True, exist_ok=True)
    data = config()
    baseline = {}
    strip_migrations = {}
    for lang in LANGUAGES:
        path = category_path(lang)
        strip_migrations[lang] = homepage_ticker_scope_repair(str(path.relative_to(ROOT)), base)
        baseline['/' + str(path.relative_to(DOCS))] = subprocess.check_output(
            ['git', 'show', f'{base}:{path.relative_to(ROOT)}'], cwd=ROOT)

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            url = urlsplit(self.path)
            key = unquote(url.path)
            if url.query == 'laws_baseline=1' and key in baseline:
                body = baseline[key]
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()

    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    report = {'base': base, 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'external_requests_blocked': True, 'cases': []}

    def ready(page):
        page.evaluate('document.fonts.ready')
        for image in page.locator('main article img').all():
            image.scroll_into_view_if_needed()
            image.evaluate('(i) => i.decode()')
        page.evaluate('window.scrollTo(0, 0)')

    def metrics(page):
        return page.locator('main article').evaluate_all('''cards => cards.map(card => {
            const r = card.getBoundingClientRect(), img = card.querySelector('img');
            const title = card.querySelector('h2 a');
            return {title:title.textContent, href:title.href,
                text:card.innerText, x:r.x,y:r.y+scrollY,width:r.width,height:r.height,
                image:img.getAttribute('src'), loaded:img.complete && img.naturalWidth>0,
                naturalWidth:img.naturalWidth, fit:getComputedStyle(img).objectFit};
        })''')

    def no_overflow(page, label):
        sizes = page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
        assert sizes['scroll'] <= sizes['width'] + 1, (label, 'horizontal overflow', sizes)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True,
                executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None)
            for mode, width, height in VIEWPORTS:
                context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1)
                context.route('**/*', lambda route: route.continue_()
                              if route.request.url.startswith(origin + '/') else route.abort())
                page = context.new_page()
                for lang in LANGUAGES:
                    label = f'{lang}-{mode}'
                    path = '/' + str(category_path(lang).relative_to(DOCS))
                    url = origin + quote(path)
                    selected = [i for i in data['images'] if lang in i['slugs']]
                    response = page.goto(url + '?laws_baseline=1', wait_until='networkidle')
                    assert response.status == 200
                    ready(page)
                    no_overflow(page, label + '-before')
                    before = metrics(page)
                    removed_strip = None
                    if strip_migrations[lang]:
                        assert page.locator('.news-strip').count() == 1
                        removed_strip = page.locator('.news-strip').evaluate(
                            'e => { const r=e.getBoundingClientRect(); return {y:r.y+scrollY,height:r.height}; }')
                        assert removed_strip['height'] > 0
                    assert len(before) == (9 if lang == 'ar' else 6)
                    page.screenshot(path=str(output / f'{label}-before.png'), full_page=True)

                    response = page.goto(url, wait_until='networkidle')
                    assert response.status == 200
                    ready(page)
                    no_overflow(page, label + '-after')
                    after = metrics(page)
                    if strip_migrations[lang]:
                        assert page.locator('.news-strip, .ticker').count() == 0
                    # Retain both views and measurements even if an assertion
                    # catches a layout defect before this case completes.
                    page.screenshot(path=str(output / f'{label}-after.png'), full_page=True)
                    report['current_case'] = {'label': label, 'before': before, 'after': after}
                    assert len(after) == len(before)
                    for old, new in zip(before, after):
                        assert old['text'] == new['text'] and old['href'] == new['href'], (label, 'card content changed')
                        assert_card_geometry(old, new, label, removed_strip)
                        assert new['loaded'], (label, 'broken image', new)
                    assert sum('laws-landmark-' in i['image'] for i in after) == len(selected)
                    assert all(i['naturalWidth'] == 960 for i in after if 'laws-landmark-' in i['image'])
                    panel = page.locator('#laws-photo-credits')
                    summary = panel.locator('summary')
                    assert not panel.evaluate('(e) => e.open')

                    # Accessible disclosure, repeated keyboard/click flows, no history entry.
                    history = page.evaluate('history.length')
                    summary.focus()
                    summary.press('Enter')
                    assert panel.evaluate('(e) => e.open')
                    assert panel.locator('li').count() == len(selected)
                    no_overflow(page, label + '-credits-open')
                    for item in selected:
                        assert panel.locator(f'a[href="{item["source_page"]}"]').count() == 1
                        assert item['attribution'] in panel.inner_text()
                    page.screenshot(path=str(output / f'{label}-credits-open.png'), full_page=True)
                    summary.press('Space')
                    assert not panel.evaluate('(e) => e.open')
                    summary.click()
                    assert panel.evaluate('(e) => e.open')
                    summary.click()
                    assert not panel.evaluate('(e) => e.open')
                    assert page.evaluate('history.length') == history

                    # All article destinations remain local and return successful documents.
                    for card in after:
                        assert card['href'].startswith(origin + '/')
                        assert context.request.get(card['href']).status == 200
                    page.locator('main article a.thumb').first.click()
                    page.wait_for_url(after[0]['href'])
                    assert page.locator('h1').count() > 0
                    page.go_back(wait_until='domcontentloaded')
                    assert page.url == url
                    page.go_forward(wait_until='domcontentloaded')
                    assert page.url == after[0]['href']
                    page.go_back(wait_until='domcontentloaded')
                    page.locator('main article h2 a').last.click()
                    page.wait_for_url(after[-1]['href'])
                    page.go_back(wait_until='domcontentloaded')
                    assert page.url == url
                    report['cases'].append({'language': lang, 'viewport': mode, 'width': width,
                        'card_count': len(after), 'landmark_count': len(selected),
                        'before': before, 'after': after, 'no_overflow': True,
                        'card_geometry_and_text_unchanged_except_verified_strip': True,
                        'removed_strip': removed_strip, 'credits_keyboard_and_repeated_clicks': True,
                        'article_links_and_back_forward': True})
                    report.pop('current_case', None)
                    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    assert len(report['cases']) == 9
    print('PASS: 9 AR/EN/FR desktop/mobile cases, 27 before/after/disclosure screenshots, links and Back/Forward.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--output', type=Path, default=Path('laws-landmark-visual-qa'))
    args = parser.parse_args()
    run(args.base, args.output)
