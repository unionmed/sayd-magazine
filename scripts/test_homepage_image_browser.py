"""Local-only, content-exact browser proof for three image representations.

The fixed Saudi JPEG alone permits a reviewed <=3 RGB scaled-raster residual;
encoded bytes, full-natural RGBA, DOM/layout/paint inputs, alpha and all other
pixels stay exact. This is not a claim of bit-identical scaled screenshots or
of a proven Chromium cause. No CSS mutation, masking, live request or writer.
"""
import argparse
import functools
import hashlib
import http.server
import io
import json
import math
import os
from pathlib import Path
import shutil
import threading
from urllib.parse import unquote, urlsplit

from PIL import Image
import homepage_image_sources as images
import homepage_image_browser_proof as proof
import publication_compiler as compiler

ROOT = Path(__file__).resolve().parents[1]


def selector(entry):
    return 'section#sayd-tv [data-tv-group="'+entry[0]+'"] article['+entry[1]+'="'+entry[2]+'"] img'


def paint_frames(page):
    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')


def natural_pixels(page):
    """Read full-resolution decoded RGBA offscreen without changing the DOM."""
    results = {}
    for entry in images.IMAGES:
        results[entry[2]] = page.locator(selector(entry)).evaluate('''async(i)=>{
            await i.decode();
            const c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;
            const ctx=c.getContext('2d');ctx.drawImage(i,0,0);
            const digest=await crypto.subtle.digest('SHA-256',ctx.getImageData(0,0,c.width,c.height).data);
            return {width:c.width,height:c.height,rgba_sha256:Array.from(new Uint8Array(digest)).map(x=>x.toString(16).padStart(2,'0')).join('')};
        }''')
    return results


def state(page, target, expected, origin):
    """Record actual capture inputs and hit-test the full selected image."""
    return page.evaluate('''async({target,entries,origin})=>{
        const hash=async(data)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data))).map(x=>x.toString(16).padStart(2,'0')).join('');
        const rect=e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]};
        const section=document.querySelector('section#sayd-tv'),header=document.querySelector('.site-sticky');
        if(!section||!header)throw Error('Missing actual TV/header');
        const selected={},nodes=new Map(),clone=section.cloneNode(true);
        for(const e of entries){
            const found=document.querySelectorAll(e.selector);if(found.length!==1)throw Error('Ambiguous image identity');
            const i=found[0];if(i.getAttribute('src')!==e.src||i.currentSrc!==new URL(e.src,document.baseURI).href)throw Error('Unexpected image source');
            nodes.set(i,e.identity);selected[e.identity]={rect:rect(i),grid:rect(i.closest('.home-door-grid'))};
            const ci=clone.querySelector(e.selector.replace('section#sayd-tv ',''));
            ci.setAttribute('src','verified-fixed-image:'+e.identity);
        }
        const source=async i=>{
            if(nodes.has(i))return 'verified-fixed-image:'+nodes.get(i);
            const src=i.currentSrc;
            if(src.startsWith('data:'))return {scheme:'data',length:src.length,sha256:await hash(new TextEncoder().encode(src))};
            for(const side of ['before','after'])if(src.startsWith(origin+'/'+side+'/'))return src.slice((origin+'/'+side).length);
            return src;
        };
        const imgs=[];
        for(const i of section.querySelectorAll('img')){
            const s=getComputedStyle(i);
            imgs.push({source:await source(i),rect:rect(i),natural:[i.naturalWidth,i.naturalHeight],complete:i.complete,
                alt:i.alt,href:i.parentElement.getAttribute('href'),transform:s.transform,filter:s.filter,opacity:s.opacity,
                transition:s.transition,objectFit:s.objectFit,objectPosition:s.objectPosition});
        }
        const intersection=(a,b)=>[Math.max(a[0],b[0]),Math.max(a[1],b[1]),Math.min(a[0]+a[2],b[0]+b[2]),Math.min(a[1]+a[3],b[1]+b[3])];
        const hit=(node,b)=>{
            if(b[2]<=b[0]||b[3]<=b[1])return true;
            const inset=Math.min(1,(b[2]-b[0])/4,(b[3]-b[1])/4);
            for(const x of [b[0]+inset,(b[0]+b[2])/2,b[2]-inset])for(const y of [b[1]+inset,(b[1]+b[3])/2,b[3]-inset])
                if(document.elementFromPoint(x,y)!==node)return false;
            return true;
        };
        const ti=[...nodes].find(([i,id])=>id===target)[0],tr=rect(ti),tg=rect(ti.closest('.home-door-grid')),hr=rect(header);
        const full=tr[0]>=0&&tr[1]>=hr[1]+hr[3]+24&&tr[0]+tr[2]<=innerWidth&&tr[1]+tr[3]<=innerHeight&&
            tr[0]>=tg[0]&&tr[1]>=tg[1]&&tr[0]+tr[2]<=tg[0]+tg[2]&&tr[1]+tr[3]<=tg[1]+tg[3];
        const si=[...nodes].find(([i,id])=>id==='-Id9SK67khA')[0];
        const sb=intersection(rect(si),rect(si.closest('.home-door-grid')));
        const visible=[Math.max(0,sb[0]),Math.max(hr[1]+hr[3]+24,sb[1]),Math.min(innerWidth,sb[2]),Math.min(innerHeight,sb[3])];
        return {dom_sha256:await hash(new TextEncoder().encode(clone.outerHTML)),
            state:{dpr:devicePixelRatio,viewport:[innerWidth,innerHeight],overflow:document.documentElement.scrollWidth-innerWidth,
                scroll:[scrollX,scrollY],section:rect(section),header:hr,selected,images:imgs,
                grids:Array.from(section.querySelectorAll('.home-door-grid')).map(e=>({rect:rect(e),scroll:[e.scrollLeft,e.scrollTop],snap:getComputedStyle(e).scrollSnapType})),
                target_unobscured:full&&hit(ti,[tr[0],tr[1],tr[0]+tr[2],tr[1]+tr[3]]),saudi_unobscured:hit(si,visible)}};
    }''', {'target': target, 'entries': expected, 'origin': origin})


def measure(page):
    return page.evaluate('''()=>{
        const t=document.querySelector('section#sayd-tv').getBoundingClientRect(),h=document.querySelector('.site-sticky').getBoundingClientRect();
        return {section:[t.x+scrollX,t.y+scrollY,t.width,t.height],header_height:h.height};
    }''')


def set_scroll(page, frame):
    page.evaluate('''f=>{
        const grids=[...document.querySelectorAll('section#sayd-tv .home-door-grid')];
        if(grids.length!==f.grids.length)throw Error('Grid count drift');
        grids.forEach((g,i)=>g.scrollTo({left:f.grids[i][0],top:f.grids[i][1],behavior:'instant'}));
        window.scrollTo({left:f.scroll[0],top:f.scroll[1],behavior:'instant'});
    }''', frame)
    paint_frames(page)


def main(output):
    # Browser dependencies are deliberately lazy: pure proof unit tests run in
    # the existing lxml/Pillow-only protected job without dependency changes.
    from playwright.sync_api import sync_playwright
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    head = compiler.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    # Before initial activation use this exact support candidate. After activation
    # replay its immutable migration base so this regression remains repeatable.
    images.active(ROOT)  # Validate any append-only inverse before historical QA.
    marker = images.read_regular(ROOT, images.MARKER, missing=True)
    base = json.loads(marker)['expected_base'] if marker is not None else head
    blobs = images.migration_inputs(ROOT, base)
    sources = images.source_images(blobs.__getitem__)
    after, _, _ = images.migration_changes(ROOT, base, images.source_digest(blobs))
    pages = {}
    for path in images.HOMES.values():
        pages['/before/'+path[5:]] = blobs[path]
        pages['/after/'+path[5:]] = after[path]
    encoded = {}
    for entry in images.IMAGES:
        body = images.read_regular(ROOT, entry[3])
        assert body == blobs[entry[3]], 'Current image differs from immutable migration bytes'
        images.verified_bytes(sources[entry[2]], body, entry)
        encoded[entry[2]] = hashlib.sha256(body).hexdigest()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path in pages:
                data = pages[path]
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data); return
            for prefix in ('/before/', '/after/'):
                if path.startswith(prefix): self.path = '/' + path[len(prefix):]; break
            super().do_GET()
        def log_message(self, *args): pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    cases, failures = [], []
    try:
        with sync_playwright() as playwright:
            executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None
            browser = playwright.chromium.launch(headless=True, executable_path=executable)
            version = browser.version
            try:
                for lang, home in images.HOMES.items():
                    for width in (320, 390, 820, 1440):
                        case = {'language': lang, 'width': width, 'captures': {}, 'comparisons': [], 'requests': []}
                        context = browser.new_context(viewport={'width': width, 'height': 900}, device_scale_factor=1, service_workers='block')
                        blocked_external = []
                        def local_only(route):
                            if route.request.url.startswith(origin+'/'): route.continue_()
                            else: blocked_external.append(route.request.url); route.abort()
                        context.route('**/*', local_only)
                        page = context.new_page(); responses = []
                        page.on('response', lambda response: responses.append(response))
                        baseline, frames, captured = None, {}, {}
                        try:
                            # One context/page navigates A -> B -> A. Two fixed captures
                            # on each first side give A/A and B/B controls; no retries.
                            for stage, side, samples in (('A', 'before', 2), ('B', 'after', 2), ('returnA', 'before', 1)):
                                response = page.goto(origin+'/'+side+'/'+home[5:], wait_until='domcontentloaded')
                                assert response.status == 200
                                page.evaluate('document.fonts.ready')
                                for img in page.locator('section#sayd-tv img').all():
                                    img.scroll_into_view_if_needed(); img.evaluate('(i)=>i.decode()')
                                dimensions = measure(page)
                                if baseline is None:
                                    height = math.ceil(dimensions['section'][3] + 2*dimensions['header_height'] + 96)
                                    assert 900 <= height <= 2400, ('Unbounded capture height', height)
                                    page.set_viewport_size({'width': width, 'height': height}); paint_frames(page)
                                    assert measure(page) == dimensions, 'Height-only viewport changed TV geometry'
                                    y = math.floor(dimensions['section'][1] - dimensions['header_height'] - 48)
                                    assert y > 0
                                    baseline = {'dimensions': dimensions, 'height': height, 'scroll': [0, y]}
                                else:
                                    assert dimensions == baseline['dimensions'], 'Section/header layout drift'
                                page.evaluate('s=>window.scrollTo({left:s[0],top:s[1],behavior:"instant"})', baseline['scroll']); paint_frames(page)
                                rgba = natural_pixels(page)
                                expected = [{'identity': e[2], 'selector': selector(e), 'src': sources[e[2]] if side == 'before' else images.local_src(lang, e)} for e in images.IMAGES]
                                if side == 'after':
                                    for entry in images.IMAGES:
                                        url = origin+'/after/'+entry[3][5:]
                                        matches = [r for r in responses if r.url == url]
                                        assert len(matches) == 1 and matches[0].status == 200, ('Missing exact image response', url)
                                        body = matches[0].body()
                                        assert body == blobs[entry[3]] and hashlib.sha256(body).hexdigest() == entry[4]
                                        case['requests'].append({'path': entry[3], 'status': 200, 'sha256': entry[4], 'bytes': len(body)})
                                for entry in images.IMAGES:
                                    identity = entry[2]
                                    if stage == 'A':
                                        page.locator(selector(entry)).evaluate('(i)=>i.scrollIntoView({block:"nearest",inline:"center",behavior:"instant"})')
                                        page.evaluate('s=>window.scrollTo({left:s[0],top:s[1],behavior:"instant"})', baseline['scroll']); paint_frames(page)
                                        observed = state(page, identity, expected, origin)
                                        r = observed['state']['section']
                                        clip = {'x': math.floor(r[0]), 'y': math.floor(r[1]),
                                                'width': math.ceil(r[0]+r[2])-math.floor(r[0]), 'height': math.ceil(r[1]+r[3])-math.floor(r[1])}
                                        frames[identity] = {'scroll': baseline['scroll'], 'grids': [g['scroll'] for g in observed['state']['grids']], 'clip': clip}
                                    else:
                                        set_scroll(page, frames[identity])
                                    for sample in range(samples):
                                        paint_frames(page)
                                        before_state = state(page, identity, expected, origin)
                                        name = f'{lang}-{width}-{identity}-{stage}{sample+1}'
                                        raw = page.screenshot(path=str(output/(name+'.png')), clip=frames[identity]['clip'], animations='disabled', caret='hide', scale='css')
                                        after_state = state(page, identity, expected, origin)
                                        assert before_state['dom_sha256'] == after_state['dom_sha256'], 'DOM changed during capture'
                                        record = {'encoded_sha256': encoded, 'native_rgba': rgba, 'dom_sha256': before_state['dom_sha256'],
                                                  'target': identity, 'clip': frames[identity]['clip'], 'state': before_state['state'], 'after_state': after_state['state']}
                                        proof.check_proof(record)
                                        pixels = Image.open(io.BytesIO(raw)).convert('RGBA')
                                        key = identity+':'+stage+str(sample+1)
                                        captured[key] = (pixels, record)
                                        case['captures'][key] = {'file': name+'.png', 'png_sha256': hashlib.sha256(raw).hexdigest(),
                                                                 'rgba_sha256': hashlib.sha256(pixels.tobytes()).hexdigest(), 'proof': record}
                            for entry in images.IMAGES:
                                identity = entry[2]
                                for a, b in (('A1','A2'), ('B1','B2'), ('A1','B1'), ('A2','B2'), ('A1','returnA1'), ('B1','returnA1')):
                                    old, new = captured[identity+':'+a], captured[identity+':'+b]
                                    result = proof.compare(old[0], new[0], old[1], new[1])
                                    case['comparisons'].append({'identity': identity, 'pair': [a,b], **result})
                                    if not result['passed']: failures.append({'language': lang, 'width': width, 'identity': identity, 'pair': [a,b], **result})
                            assert len(case['captures']) == 15 and len(case['comparisons']) == 18 and len(case['requests']) == 3
                            case['framing'] = baseline
                        except Exception as error:
                            case['error'] = repr(error)
                            failures.append({'language': lang, 'width': width, 'error': repr(error)})
                        finally:
                            case['blocked_external_requests'] = {'count': len(blocked_external), 'urls': sorted(set(blocked_external))}
                            cases.append(case); context.close()
            finally:
                browser.close()
    finally:
        server.shutdown(); server.server_close()
    assert len(cases) == 12
    receipt = {'status': 'failed' if failures else 'passed', 'criterion': 'exact-content-and-layout; Saudi-only RGB<=3, alpha exact, all other pixels exact',
               'local_only': True, 'head': head, 'immutable_migration_base': base, 'browser_version': version, 'executable_override': executable,
               'cases': cases, 'failures': failures}
    (output/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    assert not failures, ('Homepage browser equivalence/control failures', failures)
    assert sum(len(c['requests']) for c in cases) == 36
    print('PASS: 12 language/width cases, 36 exact HTTP images, 180 unobscured target captures and 216 fixed equivalence/control comparisons')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
