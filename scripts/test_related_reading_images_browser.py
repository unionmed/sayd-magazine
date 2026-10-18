#!/usr/bin/env python3
"""Real local browser QA of existing recommendation variants; zero analytics."""
import argparse
import functools
import json
import os
from pathlib import Path
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ('trafficking-ar', 'ar', 'posts/طيور-في-الحقائب-تهريب-الطيور-2026/index.html', '.trafficking-related', 2),
    ('trafficking-en', 'en', 'en/posts/birds-in-bags-illegal-bird-trade-2026/index.html', '.trafficking-related', 2),
    ('trafficking-fr', 'fr', 'fr/posts/birds-in-bags-illegal-bird-trade-2026/index.html', '.trafficking-related', 2),
    ('archive-owl-ar', 'ar', 'posts/صيّاد-بس-هيك-قالت-مرتو/index.html', '.related-block', 2),
    ('archive-kestrel-ar', 'ar', 'posts/4935/index.html', '.related-block', 2),
    ('coast-ar', 'ar', 'posts/حين-يتغير-الساحل-أين-تستريح-الطيور/index.html', '.article-more', 1),
    ('riyadh-fr', 'fr', 'fr/posts/riyadh-racing-season-2026-2027-begins/index.html', '.riyadh-related', 2),
    ('reporting-en', 'en', 'en/posts/alexandra-cabs-illegal-hunting-interview/index.html', '.editorial-background', 1),
)


class QuietHandler(SimpleHTTPRequestHandler):
    overrides = {}
    def log_message(self, *args):
        pass
    def do_GET(self):
        key = unquote(urlsplit(self.path).path).lstrip('/')
        if key in self.overrides:
            data = self.overrides[key]
            self.send_response(200)
            self.send_header('Content-Type', 'text/css' if key.endswith('.css') else 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers();self.wfile.write(data)
        else:
            super().do_GET()


def serve(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(handler, directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}'


def capture(page, section, path):
    section.scroll_into_view_if_needed()
    box = section.bounding_box()
    top = max(0, box['y'] + page.evaluate('scrollY') - 100)
    page.screenshot(path=str(path), full_page=True, clip={'x': max(0, box['x']), 'y': top, 'width': box['width'], 'height': box['height'] + box['y'] + page.evaluate('scrollY') - top})


def main(base=None):
    server, origin = serve(QuietHandler)
    old_server = None
    output = ROOT/'sayd-visual-qa/related-reading'
    output.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        with sync_playwright() as p:
            options = {'executable_path': os.environ['SAYD_CHROMIUM_PATH']} if os.environ.get('SAYD_CHROMIUM_PATH') else {}
            browser = p.chromium.launch(**options)
            context = browser.new_context()
            origins = [origin]
            context.route('**/*', lambda route: route.continue_() if any(route.request.url.startswith(o+'/') for o in origins) else route.abort())
            page = context.new_page()
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({'width': width, 'height': 1000})
                for name, lang, rel, selector, count in CASES:
                    url = origin+'/'+quote(rel)
                    page.goto(url, wait_until='networkidle')
                    section = page.locator(selector)
                    assert section.count() == 1
                    cards = section.locator('a.reading-card, article.card')
                    assert cards.count() == count
                    for i in range(count):
                        image = cards.nth(i).locator('img')
                        image.scroll_into_view_if_needed()
                        image.wait_for(state='visible')
                        image.evaluate('(img) => img.decode()')
                        assert image.evaluate('(img) => img.complete && img.naturalWidth > 0')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), (name, width, 'horizontal overflow')
                    boxes = [cards.nth(i).bounding_box() for i in range(count)]
                    assert all(b['width'] >= 44 and b['height'] >= 44 and b['x'] >= -1 and b['x']+b['width'] <= width+1 for b in boxes)
                    if count > 1 and selector != '.related-block':
                        if width <= 560:
                            assert abs(boxes[0]['x']-boxes[1]['x']) <= 1 and boxes[1]['y'] > boxes[0]['y']+boxes[0]['height']
                        else:
                            assert abs(boxes[0]['y']-boxes[1]['y']) <= 1
                    capture(page, section, output/f'{name}-{width}.png')
                    destinations = []
                    for i in range(count):
                        unit = cards.nth(i)
                        link = unit if selector != '.related-block' else unit.locator('h3 a')
                        destinations.append(link.get_attribute('href'))
                    for i in range(min(2, count)):
                        page.goto(url, wait_until='networkidle')
                        unit = page.locator(selector).locator('a.reading-card, article.card').nth(i)
                        link = unit if selector != '.related-block' else unit.locator('h3 a')
                        expected = link.evaluate('(a) => a.href')
                        with page.expect_navigation(wait_until='domcontentloaded'):
                            if i == 0:
                                link.focus();link.press('Enter')
                            else:
                                link.click()
                        assert unquote(page.url) == unquote(expected)
                        assert page.locator('h1').count() == 1
                        assert page.locator('html').get_attribute('lang') == lang
                    results.append({'case': name, 'language': lang, 'width': width, 'card_boxes': boxes, 'destinations': destinations, 'passed': True})
            if base:
                class BaselineHandler(QuietHandler):
                    overrides = {rel: subprocess.check_output(['git','show',base+':docs/'+rel], cwd=ROOT) for _,_,rel,_,_ in CASES[:5]}
                BaselineHandler.overrides['assets/css/related-reading.css'] = subprocess.check_output(['git','show',base+':docs/assets/css/related-reading.css'], cwd=ROOT)
                old_server, old_origin = serve(BaselineHandler);origins.append(old_origin)
                for width in (390, 1440):
                    page.set_viewport_size({'width':width,'height':1000})
                    for name, _, rel, selector, _ in (CASES[0], CASES[3], CASES[4]):
                        page.goto(old_origin+'/'+quote(rel), wait_until='networkidle')
                        section = page.locator(selector)
                        for image in section.locator('img').all():
                            image.scroll_into_view_if_needed();image.evaluate('(img) => img.decode()')
                        capture(page, section, output/f'before-{name}-{width}.png')
            browser.close()
    finally:
        server.shutdown()
        if old_server:old_server.shutdown()
    (output/'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
    print('PASS: 32 real layouts, local original photos, keyboard/click destinations, no overflow; external requests blocked; before/after previews retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--base');main(parser.parse_args().base)
