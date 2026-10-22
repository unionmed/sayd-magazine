#!/usr/bin/env python3
"""Local-only responsive QA of every mapped laws article, without analytics traffic."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import threading
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from sync_laws_card_landmarks import ROOT, DOCS, config
from sync_laws_article_landmarks import article_items, article_path
from test_laws_article_landmarks import main as check_static


def run(base, output):
    check_static(base)
    output.mkdir(parents=True, exist_ok=True)
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    report = {'base': base, 'external_requests_blocked': True, 'cases': []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None)
            for mode, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844), ('narrow-mobile', 320, 800)]:
                ctx = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1)
                ctx.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin + '/') else route.abort())
                page = ctx.new_page()
                for item in article_items():
                    for lang in item['slugs']:
                        path = article_path(item, lang)
                        response = page.goto(origin + '/' + quote(str(path.relative_to(DOCS))), wait_until='networkidle')
                        assert response.status == 200
                        hero = page.locator('article.article-content > figure.laws-landmark-hero')
                        assert hero.count() == 1
                        image = hero.locator('img')
                        image.evaluate('(i) => i.decode()')
                        image.scroll_into_view_if_needed()
                        assert image.is_visible()
                        info = image.evaluate('i => ({src:i.getAttribute("src"),naturalWidth:i.naturalWidth,naturalHeight:i.naturalHeight,width:i.getBoundingClientRect().width,height:i.getBoundingClientRect().height})')
                        assert (info['naturalWidth'], info['naturalHeight']) == (item['width'], item['height'])
                        assert info['width'] > 100 and info['height'] > 50
                        assert abs(info['width'] / info['height'] - item['width'] / item['height']) < .01
                        size = page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                        assert size['scroll'] <= size['width'] + 1, (item['id'], lang, mode, size)
                        assert page.locator('p.photo-credit a[rel="license external"]').get_attribute('href') == item['license_url']
                        label = item['id'] + '-' + lang + '-' + mode
                        page.screenshot(path=str(output / (label + '.png')))
                        report['cases'].append({'id': item['id'], 'lang': lang, 'viewport': mode, 'image': info, 'overflow': False})
                ctx.close()
            browser.close()
        assert len(report['cases']) == 54
        print('PASS: 54 article views; all images decode, correct dimensions/aspect, responsive and no overflow.')
    finally:
        (output / 'article-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        server.shutdown()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', required=True)
    p.add_argument('--output', type=Path, default=ROOT / 'laws-landmark-visual-qa/articles')
    a = p.parse_args()
    run(a.base, a.output)
