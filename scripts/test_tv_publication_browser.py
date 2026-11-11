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

def check_jiad_playback(browser, base, out):
    """Exercise current channel placement and the permanent landscape archive."""
    from urllib.parse import unquote, urljoin
    import jiad_tv_publication as jiad
    if not (ROOT/jiad.SOURCE).is_file():return
    record=jiad.check_published(ROOT)
    channel=json.loads((ROOT/jiad.CHANNEL).read_text())
    visible=[v['id'] for v in channel['videos'][:channel['home_limit']]]
    assert len(visible)==7
    results=[]
    for lang in jiad.LANGS:
        prefix='' if lang=='ar' else '/'+lang
        target=base+prefix+'/'+jiad.TV_PATH+'#'+jiad.ANCHOR
        for width in (320,390,820,1440):
            page=browser.new_page(viewport={'width':width,'height':900})
            # Keep local assets/media, but never issue external analytics requests.
            page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(base+'/') else route.abort())
            def open_from_home(screenshot=False):
                assert unquote(page.url)==base+prefix+'/index.html'
                cards=page.locator('[data-tv-group="sayd-channel"] article')
                assert cards.count()==7
                assert cards.evaluate_all('(nodes)=>nodes.map(n=>n.dataset.videoId)')==visible
                card=page.locator('[data-tv-group="sayd-channel"] article[data-video-id="'+jiad.ID+'"]')
                assert card.count()==int(jiad.ID in visible)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                if jiad.ID in visible:
                    card.scroll_into_view_if_needed()
                    page.wait_for_function('(id)=>{const i=document.querySelector(\'[data-video-id="\'+id+\'"] img\');return i && i.complete && i.naturalWidth>0}',arg=jiad.ID)
                    assert card.locator('img').evaluate('(i)=>i.complete && i.naturalWidth>0')
                    assert card.locator('h3 a').inner_text()==record['titles'][lang]
                    assert unquote(urljoin(page.url,card.locator('h3 a').get_attribute('href')))==target
                    if screenshot:card.screenshot(path=str(out/f'jiad-{lang}-{width}-home-card.png'))
                    card.locator('h3 a').click()
                else:
                    # Approved future rotation may remove Jiad from the seven cards.
                    if screenshot:page.screenshot(path=str(out/f'jiad-{lang}-{width}-home-archive-only.png'))
                    page.goto(target,wait_until='domcontentloaded')
            def play_archive():
                section=page.locator('section[data-jiad-video="'+jiad.ID+'"]')
                section.wait_for();assert section.count()==1
                assert unquote(page.url)==target
                assert section.locator('h2').inner_text()==record['titles'][lang]
                assert section.locator('p').all_text_contents()==[line for line in record['description'][lang].split('\n') if line]
                video=section.locator('video')
                video.evaluate('(v)=>{v.muted=true;v.load()}')
                page.wait_for_function('(()=>{const v=document.querySelector("[data-jiad-video] video");return v.readyState>=1||v.error})()')
                facts=video.evaluate('(v)=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,src:v.currentSrc,controls:v.controls,inline:v.playsInline,error:v.error&&v.error.message})')
                assert not facts['error'] and facts['controls'] and facts['inline']
                assert abs(facts['duration']-76.1)<0.1 and (facts['width'],facts['height'])==(1280,704),facts
                assert facts['src']==base+'/'+jiad.VIDEO[5:]
                video.evaluate('(v)=>{v.currentTime=0;return v.play()}')
                page.wait_for_function('document.querySelector("[data-jiad-video] video").currentTime>0.2')
                video.evaluate('(v)=>v.pause()');assert video.evaluate('(v)=>v.paused')
                section.scroll_into_view_if_needed()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                return section,facts
            try:
                page.goto(base+prefix+'/index.html',wait_until='domcontentloaded')
                open_from_home(screenshot=True)
                section,facts=play_archive()
                section.screenshot(path=str(out/f'jiad-{lang}-{width}-player.png'))
                page.go_back(wait_until='domcontentloaded')
                open_from_home()
                play_archive()
                results.append({'language':lang,'viewport':width,'visible_on_homepage':jiad.ID in visible,'video':facts,'playback':'passed','history_navigation':'passed','reopen_playback':'passed'})
            except Exception as exc:
                (out/f'jiad-{lang}-{width}-failure.json').write_text(json.dumps({'error':str(exc),'url':page.url,'results':results},indent=2))
                page.screenshot(path=str(out/f'jiad-{lang}-{width}-failure.png'))
                raise
            finally:page.close()
    (out/'jiad-tv.json').write_text(json.dumps({'status':'passed','results':results},indent=2))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if not (ROOT/tv.SOURCE).is_file():
        (out/'native-tv.json').write_text(json.dumps({'status':'not applicable: no native TV source'}));return
    record=tv.loads((ROOT/tv.SOURCE).read_text())
    head=c.git(ROOT,'rev-parse','HEAD').decode().strip()
    message=c.git(ROOT,'show','-s','--format=%B',head).decode().strip()
    if message.endswith('Sayd-Publication-Request: v1\nDistribution-Review-Scope: true'):
        import jiad_tv_publication as jiad
        if (ROOT/jiad.SOURCE).is_file() and c.git(ROOT,'diff','--name-only',head+'^',head,'--',jiad.SOURCE).strip():
            jiad_record=jiad.loads((ROOT/jiad.SOURCE).read_text())
            jiad.source_input(ROOT,jiad_record['expected_base'],head)
        else:
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
            check_jiad_playback(browser,base,out)
            browser.close()
    finally:server.shutdown()
    (out/'native-tv.json').write_text(json.dumps({'status':'passed','results':results},indent=2))

if __name__=='__main__':main()
