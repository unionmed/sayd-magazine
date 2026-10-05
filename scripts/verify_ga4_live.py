"""Read-only live GA4 smoke test. Only six debug-marked pageviews are sent."""
import json
import time
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright

ORIGIN = 'https://sayd-magazine.com'
ID = 'G-C3C0CEYX8Q'
OLD_ID = 'G-C3COCEYX8Q'
DOCS = Path('docs')
paths = []
for prefix in ('', 'en/', 'fr/'):
    paths.append('/' + prefix)
    root = DOCS / prefix / 'posts'
    candidates = sorted(p for p in root.glob('*/index.html')
                        if ID in p.read_text(encoding='utf-8')
                        and 'http-equiv="refresh"' not in p.read_text(encoding='utf-8'))
    if not candidates:
        raise RuntimeError('No tagged article in ' + prefix)
    paths.append('/' + quote(candidates[0].relative_to(DOCS).as_posix(), safe='/'))
    categories = sorted((DOCS / prefix / 'category').glob('*/index.html'))
    candidates = [p for p in categories if ID in p.read_text(encoding='utf-8')
                  and 'http-equiv="refresh"' not in p.read_text(encoding='utf-8')]
    if candidates:
        paths.append('/' + quote(candidates[0].relative_to(DOCS).as_posix(), safe='/'))

raw_results = []
for path in paths:
    ok = False
    for attempt in range(8):
        try:
            with urlopen(Request(ORIGIN + path, headers={'Cache-Control': 'no-cache', 'User-Agent': 'Sayd-GA4-Verification/1.0'}), timeout=25) as r:
                html = r.read().decode('utf-8')
                status = r.status
            ok = (html.count('analytics:start') == 1 and
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
    raw_results.append({'path': path, 'http_status': status, 'correct_single_tag': True})
print('RAW_HTML_RESULTS=' + json.dumps(raw_results, ensure_ascii=False))

runtime_paths = [p for p in paths if '/category/' not in p]
results = []
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for i, path in enumerate(runtime_paths):
        mobile = i % 2 == 0
        options = dict(pw.devices['Pixel 7']) if mobile else {'viewport': {'width': 1365, 'height': 900}}
        ctx = browser.new_context(**options)
        # Mark authorized QA visits for DebugView without changing website code.
        ctx.add_init_script("""(() => {
            const layer = window.dataLayer = window.dataLayer || [];
            const original = layer.push;
            layer.push = function(...items) {
                for (const item of items) {
                    if (item && item[0] === 'config') {
                        item[2] = Object.assign({}, item[2] || {}, {debug_mode: true});
                    }
                }
                return original.apply(this, items);
            };
        })();""")
        page = ctx.new_page()
        requests = []
        responses = []
        def event_info(request):
            u = urlparse(request.url)
            if not (u.hostname or '').endswith('google-analytics.com') or u.path != '/g/collect':
                return None
            fields = parse_qs(u.query)
            fields.update(parse_qs(request.post_data or ''))
            return {'event': fields.get('en', [''])[0], 'measurement_id': fields.get('tid', [''])[0],
                    'debug': fields.get('_dbg', [''])[0]}
        def on_request(req):
            event = event_info(req)
            if event:
                requests.append(event)
        def on_response(resp):
            event = event_info(resp.request)
            if event:
                responses.append(dict(event, http_status=resp.status))
        page.on('request', on_request)
        page.on('response', on_response)
        page.goto(ORIGIN + path, wait_until='domcontentloaded', timeout=45000)
        for _ in range(20):
            page.wait_for_timeout(1000)
            if any(x['event'] == 'page_view' for x in responses):
                page.wait_for_timeout(2000)
                break
        hits = [x for x in requests if x['event'] == 'page_view']
        accepted = [x for x in responses if x['event'] == 'page_view' and x['measurement_id'] == ID and 200 <= x['http_status'] < 300]
        result = {'path': path, 'device': 'mobile' if mobile else 'desktop',
                  'page_view_requests': len(hits), 'accepted': accepted,
                  'correct_single_page_view': len(hits) == 1 and len(accepted) == 1}
        results.append(result)
        print('BROWSER_RESULT=' + json.dumps(result, ensure_ascii=False), flush=True)
        ctx.close()
    browser.close()
if not all(r['correct_single_page_view'] for r in results):
    raise RuntimeError('Browser telemetry not fully confirmed; inspect results, do not claim success')
print('GA4 LIVE VERIFICATION PASSED. Transport receipt is verified; processed GA4 reporting is a separate check.')
