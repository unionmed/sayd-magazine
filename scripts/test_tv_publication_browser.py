"""Play the independent native video in AR/EN/FR, without any external writes."""
import argparse, functools, http.server, json, os, threading, re
from pathlib import Path
from lxml import html
import tv_publication as tv
import publication_compiler as c

ROOT=Path(__file__).resolve().parents[1]

class MediaHandler(http.server.SimpleHTTPRequestHandler):
    """Match the existing native-media QA server's byte-range support."""
    def send_head(self):
        self._range=None
        path=Path(self.translate_path(self.path));header=self.headers.get('Range','')
        match=re.fullmatch(r'bytes=(\d+)-(\d*)',header)
        if path.is_file() and match:
            size=path.stat().st_size;start=int(match[1]);end=min(int(match[2]) if match[2] else size-1,size-1)
            if start>end:self.send_error(416);return None
            source=path.open('rb');source.seek(start);self._range=(start,end)
            self.send_response(206);self.send_header('Content-Type',self.guess_type(str(path)))
            self.send_header('Accept-Ranges','bytes');self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.send_header('Content-Length',str(end-start+1));self.end_headers();return source
        return super().send_head()
    def copyfile(self,source,outputfile):
        if self._range is None:return super().copyfile(source,outputfile)
        remaining=self._range[1]-self._range[0]+1
        while remaining:
            data=source.read(min(65536,remaining))
            if not data:break
            outputfile.write(data);remaining-=len(data)

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
    handler=functools.partial(MediaHandler,directory=str(ROOT/'docs'))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';results=[]
    try:
        with sync_playwright() as p:
            # Record the original harness browser's codec support; this is diagnostic,
            # never a substitute for the actual six-view playback acceptance below.
            probe=p.chromium.launch(headless=True)
            probe_page=probe.new_page()
            codec_support=probe_page.evaluate('''()=>document.createElement('video').canPlayType('video/mp4; codecs="avc1.64001e, mp4a.40.2"')''')
            (out/'chromium-codec-diagnostic.json').write_text(json.dumps({'version':probe.version,'codec_support':codec_support},indent=2))
            probe.close()
            # The existing Proudfoot native MP4 acceptance uses installed Chrome for H.264/AAC.
            browser=p.chromium.launch(channel="chrome",headless=True)
            (out/'browser.json').write_text(json.dumps({'channel':'chrome','version':browser.version},indent=2))
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
                    capability=video.evaluate('''(v)=>v.canPlayType('video/mp4; codecs="avc1.64001e, mp4a.40.2"')''')
                    assert capability, 'Acceptance browser must support original H.264/AAC media'
                    video.evaluate('(v)=>{v.muted=true;v.load()}')
                    try:
                        page.wait_for_function('(()=>{const v=document.querySelector("[data-native-video] video");return v.readyState>=1||v.error})()')
                        assert video.evaluate('(v)=>v.readyState>=1 && !v.error'), 'Native media metadata failed'
                    except Exception:
                        diagnostic=video.evaluate('(v)=>({src:v.currentSrc,state:v.readyState,network:v.networkState,error:v.error&&{code:v.error.code,message:v.error.message}})')
                        (out/f'{lang}-{width}-media-failure.json').write_text(json.dumps(diagnostic,indent=2))
                        raise
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
