"""Play the independent native video in AR/EN/FR, without any external writes."""
import argparse, functools, http.server, json, os, threading
from pathlib import Path
from lxml import html
import tv_publication as tv
import publication_compiler as c

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if not (ROOT/tv.SOURCE).is_file():
        (out/'native-tv.json').write_text(json.dumps({'status':'not applicable: no native TV source'}));return
    record=tv.loads((ROOT/tv.SOURCE).read_text())
    head=c.git(ROOT,'rev-parse','HEAD').decode().strip()
    message=c.git(ROOT,'show','-s','--format=%B',head).decode().strip()
    if message.endswith('Sayd-Publication-Request: v1\nDistribution-Review-Scope: true'):
        tv.source_input(ROOT,record['expected_base'],head)
        (out/'native-tv.json').write_text(json.dumps({'status':'source-only request: playback tested on generated candidate'}));return
    tv.check_published(ROOT)
    from playwright.sync_api import sync_playwright
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'docs'))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for lang in tv.LANGS:
                prefix='' if lang=='ar' else '/'+lang
                for width,height in ((390,844),(1440,1000)):
                    page=browser.new_page(viewport={'width':width,'height':height})
                    page.goto(base+prefix+'/index.html',wait_until='domcontentloaded')
                    selection=page.locator('[data-tv-group="sayd-selections"]')
                    assert selection.locator('article').count()==4
                    assert page.locator('[data-tv-group="sayd-channel"] article').count()==7
                    selection.scroll_into_view_if_needed();page.screenshot(path=str(out/f'{lang}-{width}-selections.png'))
                    selection.locator('[data-native-video] h3 a').click()
                    video=page.locator('[data-native-video] video');video.wait_for()
                    video.evaluate('(v)=>{v.muted=true;v.load()}')
                    page.wait_for_function('document.querySelector("[data-native-video] video").readyState>=1')
                    facts=video.evaluate('(v)=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,error:v.error&&v.error.message,src:v.currentSrc})')
                    assert 70<facts['duration']<72 and facts['width']==478 and facts['height']==850 and not facts['error']
                    assert facts['src'].startswith(base) and facts['src'].endswith('/mushroom.mp4')
                    video.evaluate('(v)=>v.play()');page.wait_for_timeout(600)
                    assert video.evaluate('(v)=>v.currentTime')>0
                    video.evaluate('(v)=>v.pause()');video.scroll_into_view_if_needed()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    page.screenshot(path=str(out/f'{lang}-{width}-player.png'))
                    assert page.locator('[data-isf-video]').count()==1
                    page.go_back(wait_until='domcontentloaded')
                    assert page.locator('[data-tv-group="sayd-selections"] article').count()==4
                    selection=page.locator('[data-tv-group="sayd-selections"]')
                    selection.locator('[data-native-video] h3 a').click();video=page.locator('[data-native-video] video');video.wait_for()
                    assert page.locator('section[data-native-video]').count()==1
                    results.append({'language':lang,'viewport':width,'video':facts,'history_navigation':'passed'})
                    page.close()
            browser.close()
    finally:server.shutdown()
    (out/'native-tv.json').write_text(json.dumps({'status':'passed','results':results},indent=2))

if __name__=='__main__':main()
