"""Verify published GA4 without sending synthetic events to Google Analytics.

Runtime requests are intercepted, not accepted by GA4. This does not prove
server ingestion, filtering, or processed audience reporting.
"""
import json
import time
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright

ORIGIN = 'https://sayd-magazine.com'
ID = 'G-C3C0CEYX8Q'
OLD_ID = 'G-C3COCEYX8Q'
DOCS = Path('docs')
# Regression coverage: all nine pages repaired in PR #167, plus the three homepages.
ARTICLE_SLUGS = {
    '': ('حين-يتغير-الساحل-أين-تستريح-الطيور',
         'قطر-حماية-المناطق-البرية-والبحرية-2030',
         'معرض-الصقور-والصيد-السعودي-2026-الملواح-والمزاد-والذكاء-الاصطناعي'),
    'en/': ('when-the-coast-changes-where-do-birds-rest',
            'qatar-protected-land-marine-areas-2030',
            'saudi-falcons-hunting-exhibition-2026-highlights'),
    'fr/': ('when-the-coast-changes-where-do-birds-rest',
            'qatar-protected-land-marine-areas-2030',
            'saudi-falcons-hunting-exhibition-2026-highlights'),
}

def regression_paths():
    paths = []
    for prefix, slugs in ARTICLE_SLUGS.items():
        paths.append('/' + prefix)
        for slug in slugs:
            rel = prefix + 'posts/' + slug + '/index.html'
            if not (DOCS / rel).is_file():
                raise RuntimeError('Required regression page missing: ' + rel)
            paths.append('/' + quote(rel, safe='/'))
        categories = sorted((DOCS / prefix / 'category').glob('*/index.html'))
        candidates = [p for p in categories if ID in p.read_text(encoding='utf-8')
                      and 'http-equiv="refresh"' not in p.read_text(encoding='utf-8')]
        if candidates:
            paths.append('/' + quote(candidates[0].relative_to(DOCS).as_posix(), safe='/'))
    return paths


GTAG_URL = f'https://www.googletagmanager.com/gtag/js?id={ID}'


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        raise HTTPError(request.full_url, code, 'Redirect refused during GA4 verification', headers, fp)


def event_info(request):
    """Parse each GA4 event, including newline-delimited batched POSTs."""
    u = urlparse(request.url)
    host = u.hostname or ''
    if not (u.scheme == 'https' and u.path == '/g/collect' and
            (host == 'google-analytics.com' or host.endswith('.google-analytics.com'))):
        return []
    events = []
    for body in (request.post_data or '').splitlines() or ['']:
        fields = parse_qs(u.query)
        fields.update(parse_qs(body))
        events.append({'event': fields.get('en', [''])[0],
                       'measurement_id': fields.get('tid', [''])[0]})
    return events


def isolate_runtime(ctx, page_url, html, events, blocked, loader_body=None):
    """Fail closed: cached document + exact gtag loader; everything else aborts.

    loader_body is an offline test fixture. No browser request is continued.
    Only route.fetch of the fixed loader is permitted, with redirects disabled.
    """
    def route_request(route):
        req = route.request
        parsed_events = event_info(req)
        if parsed_events:
            events.extend(parsed_events)
            blocked.append(req.url)
            route.abort()
        elif (req.url == page_url and req.method == 'GET'
              and req.resource_type == 'document'):
            route.fulfill(status=200, content_type='text/html', body=html)
        elif (req.url == GTAG_URL and req.method == 'GET'
              and req.resource_type == 'script'):
            if loader_body is not None:
                route.fulfill(status=200, content_type='application/javascript', body=loader_body)
            else:
                response = route.fetch(max_redirects=0)
                if response.status != 200:
                    route.abort()
                    raise RuntimeError('GA4 loader did not return HTTP 200; no redirects permitted')
                route.fulfill(response=response)
        else:
            blocked.append(req.url)
            route.abort()
    ctx.route('**/*', route_request)
    # Routed sockets stay local unless connect_to_server() is called. Never call
    # it: discard messages locally. Closing synchronously here deadlocks in 1.55.
    def block_websocket(websocket):
        blocked.append(websocket.url)
        websocket.on_message(lambda message: blocked.append(websocket.url + '#message-blocked'))
    ctx.route_web_socket('**/*', block_websocket)


def correct_single_page_view(events):
    hits = [event for event in events if event['event'] == 'page_view']
    return len(hits) == 1 and hits[0]['measurement_id'] == ID


def main():
    paths = regression_paths()
    raw_results = []
    live_html = {}
    opener = build_opener(NoRedirects())
    for path in paths:
        ok = False
        for attempt in range(8):
            try:
                with opener.open(Request(ORIGIN + path, headers={'Cache-Control': 'no-cache', 'User-Agent': 'Sayd-GA4-Verification/1.0'}), timeout=25) as r:
                    html = r.read().decode('utf-8')
                    status = r.status
                ok = (status == 200 and html.count('analytics:start') == 1 and
                      html.count('googletagmanager.com/gtag/js') == 1 and
                      f'gtag/js?id={ID}' in html and
                      f"gtag('config', '{ID}');" in html and OLD_ID not in html)
                if ok:
                    break
            except Exception:
                if attempt == 7:
                    raise
            time.sleep(5)
        if not ok:
            raise RuntimeError('Missing/wrong/duplicate live GA4: ' + path)
        live_html[path] = html
        raw_results.append({'path': path, 'http_status': status, 'correct_single_tag': True})
    print('RAW_HTML_RESULTS=' + json.dumps(raw_results, ensure_ascii=False))

    runtime_paths = [p for p in paths if '/category/' not in p]
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for i, path in enumerate(runtime_paths):
            mobile = i % 2 == 0
            options = dict(pw.devices['Pixel 7']) if mobile else {'viewport': {'width': 1365, 'height': 900}}
            ctx = browser.new_context(**options, service_workers='block')
            events, blocked = [], []
            isolate_runtime(ctx, ORIGIN + path, live_html[path], events, blocked)
            page = ctx.new_page()
            page.goto(ORIGIN + path, wait_until='domcontentloaded', timeout=45000)
            for _ in range(20):
                page.wait_for_timeout(1000)
                if any(event['event'] == 'page_view' for event in events):
                    page.wait_for_timeout(2000)
                    break
            hits = [event for event in events if event['event'] == 'page_view']
            result = {'path': path, 'device': 'mobile' if mobile else 'desktop',
                      'intercepted_page_views': hits, 'analytics_transmitted': False,
                      'correct_single_page_view': correct_single_page_view(events)}
            results.append(result)
            print('BROWSER_RESULT=' + json.dumps(result, ensure_ascii=False), flush=True)
            ctx.close()
        browser.close()
    if not all(result['correct_single_page_view'] for result in results):
        raise RuntimeError('GA4 request generation not confirmed; inspect intercepted results')
    print('GA4 LIVE HTML / ISOLATED RUNTIME VERIFICATION PASSED. '
          'All nine repaired articles and AR/EN/FR homepages attempt one correct pageview each. '
          'Analytics requests were blocked, not sent. GA4 ingestion and processed reporting are not tested.')


if __name__ == '__main__':
    main()
