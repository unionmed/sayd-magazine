#!/usr/bin/env python3
"""Local Chromium regression for the shared ten-story ticker; no external traffic.

Install Playwright's Chromium for CI, or set SAYD_CHROMIUM_PATH to an installed
Chromium executable. Optional --base compares original HTML, media and layout.
Screenshots are retained under sayd-visual-qa/ticker (never publish this folder).
"""
import argparse
import functools
import json
import os
from pathlib import Path
import re
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit

from playwright.sync_api import sync_playwright
from ticker_scope import homepage_only
from test_shared_ticker import without_complete_strip

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
WIDTHS = (1440, 390, 320)
CASES = tuple(
    (f'{kind}-{lang}', lang, prefix + rel)
    for lang, prefix, article in (
        ('ar', '', 'شيرين-بو-رفول-مكافحة-الصيد-الجائر'),
        ('en', 'en/', 'shireen-bou-rafoul-anti-poaching-interview'),
        ('fr', 'fr/', 'shireen-bou-rafoul-anti-poaching-interview'),
    )
    for kind, rel in (
        ('home', 'index.html'),
        ('article', f'posts/{article}/index.html'),
        ('category', 'category/صيد/index.html'),
    )
) + (('historical-article-ar', 'ar', 'posts/صيّاد-بس-هيك-قالت-مرتو/index.html'),)
# Independent baseline proof: home loop bodies may differ; internal strips may only be removed.
TICKER_BODY = re.compile(r'(<div class="ticker"(?: aria-hidden="true")?>).*?(</div>)', re.S)


class QuietHandler(SimpleHTTPRequestHandler):
    overrides = {}

    def log_message(self, *args):
        pass

    def do_GET(self):
        key = unquote(urlsplit(self.path).path).lstrip('/')
        if key in self.overrides:
            data = self.overrides[key]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()


def serve(handler=QuietHandler):
    server = ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(handler, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}'


def git_bytes(base, rel):
    return subprocess.check_output(['git', 'show', f'{base}:{rel}'], cwd=ROOT)


def normalized_path(url):
    return unquote(urlsplit(url).path)


def expected_paths():
    # Do not call ticker_policy.select/render: compare the browser independently
    # with the actual shared editorial source and translation mappings.
    from seo_foundation import FR_SLUG_BY_EN
    config = json.loads((ROOT / 'content/homepage.json').read_text())
    slugs = [entry['slug'] for entry in config['ticker_entries']]
    assert len(slugs) == len(set(slugs)) == 10, 'Expected ten distinct shared stories'
    assert slugs == config['ticker_slugs'], 'Shared ticker source disagrees with slugs'
    pairs = json.loads((ROOT / 'content/en/pairs.json').read_text())['pairs']
    return {
        'ar': [f'/posts/{slug}/index.html' for slug in slugs],
        'en': [f'/en/posts/{pairs[slug]}/index.html' for slug in slugs],
        'fr': [f'/fr/posts/{FR_SLUG_BY_EN.get(pairs[slug], pairs[slug])}/index.html'
               for slug in slugs],
    }


SNAPSHOT = r'''() => {
    const rect = node => {
        const r = node.getBoundingClientRect();
        return {x:r.x, y:r.y, width:r.width, height:r.height};
    };
    const track = document.querySelector('.ticker-track');
    const viewport = document.querySelector('.ticker-viewport');
    const style = track ? getComputedStyle(track) : null;
    const v = viewport ? viewport.getBoundingClientRect() : null;
    const anchors = track ? [...track.querySelectorAll('.ticker:first-child > a')] : [];
    return {
        language: document.documentElement.lang,
        direction: getComputedStyle(document.documentElement).direction,
        overflow: Math.max(0, document.documentElement.scrollWidth - innerWidth),
        strip: document.querySelector('.news-strip') ? rect(document.querySelector('.news-strip')) : null,
        viewport: viewport ? rect(viewport) : null,
        visibleLinks: anchors.filter(a => {
            const r = a.getBoundingClientRect();
            return Math.min(r.right,v.right,innerWidth) > Math.max(r.left,v.left,0)
                && Math.min(r.bottom,v.bottom,innerHeight) > Math.max(r.top,v.top,0);
        }).length,
        animation: style ? {
            name:style.animationName, duration:style.animationDuration,
            easing:style.animationTimingFunction, iterations:style.animationIterationCount,
            state:style.animationPlayState,
            x:new DOMMatrixReadOnly(style.transform).m41
        } : null,
        loops: track ? [...track.querySelectorAll(':scope > .ticker')].map(loop => ({
            hidden:loop.getAttribute('aria-hidden'),
            width:loop.getBoundingClientRect().width,
            links:[...loop.querySelectorAll(':scope > a')].map(a=>({href:a.href,text:a.textContent.trim()}))
        })) : [],
        media: [...document.querySelectorAll('img,video,audio,source,iframe')]
            .filter(node=>!node.closest('.news-strip')).map(node=>({
                tag:node.tagName, src:node.getAttribute('src'),
                srcset:node.getAttribute('srcset'), poster:node.getAttribute('poster'),
                alt:node.getAttribute('alt'), box:rect(node)
            }))
    };
}'''


def navigate(page, url):
    response = page.goto(url, wait_until='networkidle')
    assert response is not None and response.status == 200, (url, 'non-200 page')
    page.evaluate('document.fonts.ready')
    page.mouse.move(0, 990)  # Keep the real hover-to-pause rule out of motion checks.


def screenshot(page, output, name):
    # Freeze only after measuring real, running CSS animation. Both screenshots
    # start at the same animation phase; source files/styles are never modified.
    if page.locator('.ticker-track').count():
        page.locator('.ticker-track').evaluate('el => el.getAnimations().forEach(a => {a.pause();a.currentTime=0;})')
    page.screenshot(path=str(output / f'{name}.png'), full_page=False)


def compare_media(current, before, case, removed_strip=None):
    assert len(current) == len(before), (case, 'media count changed outside ticker')
    for item, old in zip(current, before):
        assert {k:v for k,v in item.items() if k != 'box'} == {
            k:v for k,v in old.items() if k != 'box'
        }, (case, 'media identity/attributes changed', item, old)
        # Only strip removal may move following media vertically. Header media
        # and every size/x coordinate remain exact; no general layout waiver.
        expected = dict(old['box'])
        if removed_strip and old['box']['height'] and old['box']['y'] >= removed_strip['y'] + removed_strip['height'] - 1:
            expected['y'] -= removed_strip['height']
        assert all(abs(item['box'][k] - expected[k]) <= 1 for k in item['box']), (
            case, 'media geometry changed outside ticker', item, old)


def run(base=None, output=ROOT / 'sayd-visual-qa/ticker'):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    expected = expected_paths()
    home_only = homepage_only(ROOT)
    homes = {"index.html", "en/index.html", "fr/index.html"}
    servers = []
    results = []
    blocked = set()
    checked_links = set()
    destinations = {}
    try:
        server, origin = serve()
        servers.append(server)
        origins = {origin}
        baseline_origin = None
        if base:
            # Baseline pages can share these large unchanged assets safely.
            changed = subprocess.check_output([
                'git', 'diff', '--name-only', base, '--', 'docs/assets', 'docs/media'
            ], cwd=ROOT).decode().strip()
            assert not changed, ('Baseline assets/media changed; use original assets', changed)
            overrides = {}
            for name, _, rel in CASES:
                old = git_bytes(base, 'docs/' + rel)
                current = (DOCS / rel).read_bytes()
                strip = lambda data: TICKER_BODY.sub(r'\1\2', data.decode())
                if home_only and rel not in homes:
                    assert without_complete_strip(old.decode()) == current.decode(), (name, 'HTML changed outside full strip removal')
                else:
                    assert strip(old) == strip(current), (name, 'HTML changed outside ticker')
                overrides[rel] = old
            handler = type('BaselineHandler', (QuietHandler,), {'overrides': overrides})
            server, baseline_origin = serve(handler)
            servers.append(server)
            origins.add(baseline_origin)

        with sync_playwright() as playwright:
            options = {'headless': True}
            if os.environ.get('SAYD_CHROMIUM_PATH'):
                options['executable_path'] = os.environ['SAYD_CHROMIUM_PATH']
            browser = playwright.chromium.launch(**options)
            context = browser.new_context(device_scale_factor=1, reduced_motion='no-preference',
                                          service_workers='block')

            def local_only(route):
                parts = urlsplit(route.request.url)
                if f'{parts.scheme}://{parts.netloc}' in origins:
                    route.continue_()
                else:
                    blocked.add(parts.netloc)
                    route.abort()

            context.route('**/*', local_only)
            page = context.new_page()
            before_page = context.new_page() if base else None
            for name, lang, rel in CASES:
                for width in WIDTHS:
                    label = f'{name}-{width}'
                    print(f'Checking {label}', flush=True)
                    page.set_viewport_size({'width': width, 'height': 1000})
                    navigate(page, origin + '/' + quote(rel))
                    if home_only and rel not in homes:
                        assert page.locator('.news-strip, .ticker, .ticker-track, .ticker-viewport').count() == 0, (label, 'internal ticker chrome remains')
                        current = page.evaluate(SNAPSHOT)
                        assert current['language'] == lang, (label, 'wrong language')
                        assert current['direction'] == ('rtl' if lang == 'ar' else 'ltr'), (label, 'wrong direction')
                        assert current['overflow'] <= 1, (label, 'horizontal page overflow')
                        old = None
                        if before_page:
                            before_page.set_viewport_size({'width': width, 'height': 1000})
                            navigate(before_page, baseline_origin + '/' + quote(rel))
                            old = before_page.evaluate(SNAPSHOT)
                            assert current['overflow'] <= old['overflow'] + 1, (label, 'new horizontal overflow')
                            compare_media(current['media'], old['media'], label, removed_strip=old['strip'])
                            screenshot(before_page, output, 'before-' + label)
                        screenshot(page, output, label)
                        results.append({'case': name, 'language': lang, 'width': width,
                                        'ticker_absent': True, 'overflow_px': current['overflow'],
                                        'media_unchanged': len(current['media']) if old else None})
                        continue
                    assert page.locator('.news-strip').count() == 1, label
                    assert page.locator('.ticker-track').count() == 1, label
                    current = page.evaluate(SNAPSHOT)
                    assert current['language'] == lang, (label, 'wrong language')
                    direction = 'rtl' if lang == 'ar' else 'ltr'
                    assert current['direction'] == direction, (label, 'wrong direction')
                    loops = current['loops']
                    assert len(loops) == 2, (label, 'expected two animation loops')
                    assert all(len(loop['links']) == 10 for loop in loops), (label, 'ten links per loop')
                    assert loops[0]['links'] == loops[1]['links'], (label, 'animation loops differ')
                    assert loops[0]['hidden'] is None and loops[1]['hidden'] == 'true', (
                        label, 'duplicate loop must retain aria-hidden')
                    assert abs(loops[0]['width'] - loops[1]['width']) <= 1, (label, 'unequal loop widths')
                    assert [normalized_path(a['href']) for a in loops[0]['links']] == expected[lang], (
                        label, 'wrong chronological shared stories or language routes')
                    assert all(a['text'] for a in loops[0]['links']), (label, 'empty ticker headline')
                    for link in loops[0]['links']:
                        parts = urlsplit(link['href'])
                        assert f'{parts.scheme}://{parts.netloc}' == origin, (label, 'non-local ticker link')
                        assert (DOCS / unquote(parts.path).lstrip('/')).is_file(), (label, 'broken link', link)
                        destinations[link['href']] = lang
                    strip, viewport = current['strip'], current['viewport']
                    assert strip['height'] >= 30 and strip['width'] >= width - 1, (label, 'ticker hidden or collapsed')
                    assert strip['y'] >= -1 and strip['y'] + strip['height'] <= 1000, (label, 'ticker outside viewport')
                    assert viewport['width'] >= 100 and viewport['height'] >= 20, (label, 'ticker text viewport collapsed')
                    assert current['visibleLinks'] > 0, (label, 'no headline visible')
                    animation = current['animation']
                    assert animation['name'] == ('sayd-ticker' if lang == 'ar' else 'sayd-ticker-ltr'), label
                    assert animation['duration'] == '58s' and animation['easing'] == 'linear', label
                    assert animation['iterations'] == 'infinite' and animation['state'] == 'running', label
                    page.wait_for_timeout(180)
                    later = page.evaluate(SNAPSHOT)
                    movement = later['animation']['x'] - animation['x']
                    assert movement > 1 if lang == 'ar' else movement < -1, (label, 'wrong/inactive ticker movement', movement)
                    old = None
                    if before_page:
                        before_page.set_viewport_size({'width': width, 'height': 1000})
                        navigate(before_page, baseline_origin + '/' + quote(rel))
                        old = before_page.evaluate(SNAPSHOT)
                        assert current['overflow'] <= old['overflow'] + 1, (label, 'new horizontal page overflow')
                        assert all(abs(current['strip'][k] - old['strip'][k]) <= 1 for k in strip), (
                            label, 'ticker strip geometry changed')
                        compare_media(current['media'], old['media'], label)
                        screenshot(before_page, output, 'before-' + label)
                    else:
                        assert current['overflow'] <= 1, (label, 'horizontal page overflow')
                    screenshot(page, output, label)
                    # An actual mouse click on the clipped first headline at all
                    # home widths proves the visible ticker remains interactive.
                    first_url = loops[0]['links'][0]['href']
                    if name.startswith('home-'):
                        point = page.locator('.ticker > a').first.evaluate('''a => {
                            const r=a.getBoundingClientRect(), v=a.closest('.ticker-viewport').getBoundingClientRect();
                            return {x:(Math.max(0,r.left,v.left)+Math.min(innerWidth,r.right,v.right))/2,
                                    y:(r.top+r.bottom)/2};
                        }''')
                        with page.expect_navigation(wait_until='domcontentloaded'):
                            page.mouse.click(point['x'], point['y'])
                        assert normalized_path(page.url) == normalized_path(first_url), (label, 'mouse destination')
                        assert page.locator('h1').count() == 1, (label, 'missing clicked article')
                        checked_links.add(first_url)
                        navigate(page, origin + '/' + quote(rel))
                    # Keyboard activation of the final story from every layout
                    # checks navigation even when that headline starts offscreen.
                    last = page.locator('.ticker').first.locator(':scope > a').last
                    last.focus()
                    with page.expect_navigation(wait_until='domcontentloaded'):
                        last.press('Enter')
                    assert normalized_path(page.url) == normalized_path(loops[0]['links'][-1]['href']), (
                        label, 'keyboard destination')
                    assert page.locator('h1').count() == 1, (label, 'missing keyboard article')
                    checked_links.add(loops[0]['links'][-1]['href'])
                    results.append({'case': name, 'language': lang, 'width': width,
                                    'stories_per_loop': [10, 10], 'movement_px': round(movement, 2),
                                    'overflow_px': current['overflow'],
                                    'baseline_overflow_px': old['overflow'] if old else None,
                                    'media_unchanged': len(current['media']) if old else None})
            # Check all thirty localized destination documents, including their
            # native article heading, language and any declared fragment target.
            for href, lang in sorted(destinations.items()):
                navigate(page, href)
                assert page.locator('h1').count() == 1, (href, 'missing article heading')
                assert page.locator('html').get_attribute('lang') == lang, (href, 'wrong destination language')
                fragment = unquote(urlsplit(href).fragment)
                if fragment:
                    assert page.evaluate('(id) => Boolean(document.getElementById(id))', fragment), (href, 'missing fragment')
                checked_links.add(href)
            browser.close()
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
    print('SAYD_TICKER_BROWSER_RESULTS ' + json.dumps(results, ensure_ascii=False))
    print(f'PASS: {len(results)} layouts; {len(checked_links)} localized ticker destinations; '
          f'9 mouse and {sum(not r.get("ticker_absent") for r in results)} keyboard activations; external requests blocked '
          f'({", ".join(sorted(blocked))}); screenshots: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Git revision for unchanged outside-ticker HTML/media and rendered geometry')
    parser.add_argument('--output', type=Path, default=ROOT / 'sayd-visual-qa/ticker')
    args = parser.parse_args()
    run(args.base, args.output)
