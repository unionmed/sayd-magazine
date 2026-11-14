"""Local-only CI browser proof for the exact three-image representation change.

Uses the existing pinned browser job. Never runs a writer or requests the live site.
Before/after pages are derived in memory from immutable Git BASE blobs, not edited
published artifacts. All other resources come from the same local checkout.
"""
import argparse
import functools
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import shutil
import threading
from urllib.parse import unquote, urlsplit

from PIL import Image
from playwright.sync_api import sync_playwright
import homepage_image_sources as images
import publication_compiler as compiler

ROOT = Path(__file__).resolve().parents[1]


def capture_state(page):
    """Observe final paint inputs without changing DOM, CSS or scroll state."""
    return page.evaluate('''async()=>{
        const hash=async(data)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data))).map(x=>x.toString(16).padStart(2,'0')).join('');
        const rect=(e)=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]};
        const imgs=[];
        for(const i of document.querySelectorAll('section#sayd-tv img')){
            const s=getComputedStyle(i), src=i.currentSrc;
            imgs.push({currentSrc:src.startsWith('data:')?{scheme:'data',length:src.length,sha256:await hash(new TextEncoder().encode(src))}:src,
                rect:rect(i),natural:[i.naturalWidth,i.naturalHeight],transform:s.transform,filter:s.filter,opacity:s.opacity,
                transition:s.transition,objectFit:s.objectFit,objectPosition:s.objectPosition});
        }
        return {dpr:devicePixelRatio,scroll:[scrollX,scrollY],images:imgs,
            grids:Array.from(document.querySelectorAll('section#sayd-tv .home-door-grid')).map(e=>({rect:rect(e),scroll:[e.scrollLeft,e.scrollTop],snap:getComputedStyle(e).scrollSnapType}))};
    }''')


def natural_pixels(page):
    """Read full-resolution decoded RGBA offscreen; do not alter the page."""
    results = []
    for entry in images.IMAGES:
        selector = 'section#sayd-tv [data-tv-group="'+entry[0]+'"] article['+entry[1]+'="'+entry[2]+'"] img'
        value = page.locator(selector).evaluate('''async(i)=>{
            await i.decode();
            const c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;
            c.getContext('2d').drawImage(i,0,0);
            const pixels=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
            const digest=await crypto.subtle.digest('SHA-256',pixels);
            return {width:c.width,height:c.height,rgba_sha256:Array.from(new Uint8Array(digest)).map(x=>x.toString(16).padStart(2,'0')).join('')};
        }''')
        results.append({'identity': entry[2], **value})
    return results


def main(output):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    head = compiler.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    # Before initial activation use this exact support candidate. After activation
    # replay its immutable migration base so this regression remains repeatable.
    base = json.loads((ROOT/images.MARKER).read_text())['expected_base'] if images.active(ROOT) else head
    blobs = images.migration_inputs(ROOT, base)
    sources = images.source_images(blobs.__getitem__)
    after, _, _ = images.migration_changes(ROOT, base, images.source_digest(blobs))
    pages = {}
    for path in images.HOMES.values():
        pages['/before/'+path[5:]] = blobs[path]
        pages['/after/'+path[5:]] = after[path]
    for entry in images.IMAGES:
        assert images.read_regular(ROOT, entry[3]) == blobs[entry[3]], 'Current image differs from immutable migration bytes'

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path in pages:
                data = pages[path]
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
                return
            for prefix in ('/before/', '/after/'):
                if path.startswith(prefix):
                    self.path = '/' + path[len(prefix):]; break
            super().do_GET()

        def log_message(self, *args): pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    cases, failures = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None)
            try:
                for lang, home in images.HOMES.items():
                    for width in (320, 390, 820, 1440):
                        sides = {}
                        for side in ('before', 'after'):
                            context = browser.new_context(viewport={'width': width, 'height': 900}, device_scale_factor=1, service_workers='block')
                            blocked_external = []
                            def local_only(route):
                                if route.request.url.startswith(origin+'/'):
                                    route.continue_()
                                else:
                                    blocked_external.append(route.request.url)
                                    route.abort()
                            context.route('**/*', local_only)
                            page = context.new_page(); responses = []
                            page.on('response', lambda response: responses.append(response))
                            try:
                                response = page.goto(origin+'/'+side+'/'+home[5:], wait_until='domcontentloaded')
                                assert response.status == 200
                                page.evaluate('document.fonts.ready')
                                facts = []
                                for entry in images.IMAGES:
                                    image = page.locator('section#sayd-tv [data-tv-group="'+entry[0]+'"] article['+entry[1]+'="'+entry[2]+'"] img')
                                    assert image.count() == 1
                                    image.scroll_into_view_if_needed()
                                    image.evaluate('(i)=>i.decode()')
                                    fact = image.evaluate('''(i)=>{const r=i.getBoundingClientRect();const s=getComputedStyle(i);return {src:i.getAttribute('src'),width:i.naturalWidth,height:i.naturalHeight,complete:i.complete,alt:i.alt,href:i.parentElement.getAttribute('href'),box:[r.x+scrollX,r.y+scrollY,r.width,r.height],fit:s.objectFit,position:s.objectPosition}}''')
                                    assert fact['complete'] and fact['width'] > 0 and fact['height'] > 0
                                    assert fact['src'] == (sources[entry[2]] if side == 'before' else images.local_src(lang, entry))
                                    facts.append({k: v for k, v in fact.items() if k != 'src'})
                                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                                # Decode all TV images before screenshots, including lazy neighbours.
                                for image in page.locator('section#sayd-tv img').all():
                                    image.scroll_into_view_if_needed(); image.evaluate('(i)=>i.decode()')
                                initial_state = capture_state(page)
                                pixels = page.locator('section#sayd-tv').screenshot(path=str(output/f'{lang}-{width}-{side}.png'), animations='disabled', caret='hide')
                                captured_state = capture_state(page)
                                decoded = Image.open(io.BytesIO(pixels)).convert('RGBA')
                                # Diagnostic only: retain the ORIGINAL screenshot assertion.
                                # Full-resolution readback and two later frames help distinguish
                                # JPEG decode/raster paths from layout/scroll/compositor drift.
                                rgba = natural_pixels(page)
                                repeats = []
                                for sample in range(2):
                                    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                                    state = capture_state(page)
                                    sample_bytes = page.locator('section#sayd-tv').screenshot(path=str(output/f'{lang}-{width}-{side}-after-canvas-{sample}.png'), animations='disabled', caret='hide')
                                    sample_image = Image.open(io.BytesIO(sample_bytes)).convert('RGBA')
                                    repeats.append({'state': state, 'captured_state': capture_state(page), 'size': sample_image.size, 'pixels_sha256': hashlib.sha256(sample_image.tobytes()).hexdigest()})
                                image_receipts = []
                                if side == 'after':
                                    for entry in images.IMAGES:
                                        expected = origin+'/after/'+entry[3][5:]
                                        matches = [response for response in responses if response.url == expected]
                                        assert len(matches) == 1 and matches[0].status == 200, ('Missing local image response', expected)
                                        body = matches[0].body()
                                        assert body == blobs[entry[3]] and hashlib.sha256(body).hexdigest() == entry[4]
                                        image_receipts.append({'path': entry[3], 'status': 200, 'sha256': entry[4], 'bytes': len(body)})
                                sides[side] = {'facts': facts, 'size': decoded.size, 'pixels_sha256': hashlib.sha256(decoded.tobytes()).hexdigest(), 'requests': image_receipts, 'blocked_external_requests': len(blocked_external),
                                    'initial_state': initial_state, 'captured_state': captured_state, 'natural_rgba': rgba, 'post_canvas_captures': repeats}
                            finally:
                                context.close()
                        assert sides['before']['facts'] == sides['after']['facts'], ('Image/geometry drift', lang, width)
                        matched = sides['before']['size'] == sides['after']['size'] and sides['before']['pixels_sha256'] == sides['after']['pixels_sha256']
                        rgba_matched = sides['before']['natural_rgba'] == sides['after']['natural_rgba']
                        if not matched or not rgba_matched:
                            failures.append({'language': lang, 'width': width, 'screenshot_pixels_match': matched, 'natural_rgba_match': rgba_matched})
                        cases.append({'language': lang, 'width': width, 'matched_screenshot_pixels': matched, 'matched_natural_rgba': rgba_matched, **sides['after'], 'before': sides['before']})
            finally:
                browser.close()
    finally:
        server.shutdown(); server.server_close()
    assert len(cases) == 12
    (output/'receipt.json').write_text(json.dumps({'status': 'failed' if failures else 'passed', 'local_only': True, 'head': head,
        'immutable_migration_base': base, 'cases': cases, 'failures': failures}, ensure_ascii=False, indent=2)+'\n')
    assert not failures, ('TV screenshot or full-resolution RGBA pixels differ', failures)
    print('PASS: three homepage mirrors / four widths; 36 exact image responses and before/after TV pixels match')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
