#!/usr/bin/env python3
import functools,json,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import quote
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs';OUT=ROOT/'sayd-visual-qa/four-news-20261018';OUT.mkdir(parents=True,exist_ok=True)
A=json.loads((ROOT/'content/features/four-news-20261018.json').read_text())['articles'];results=[]
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(DOCS)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,label in [(1440,'desktop'),(390,'mobile')]:
   page=browser.new_page(viewport={'width':width,'height':1000 if width>500 else 844})
   page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) or r.request.url.startswith('data:') else r.abort())
   for a in A:
    for l in ['ar','en','fr']:
     page.goto(base+'/'+('' if l=='ar' else l+'/')+'posts/'+quote(a['slugs'][l])+'/index.html',wait_until='networkidle');page.locator('article.article-content').wait_for();page.locator('.article-more').scroll_into_view_if_needed();page.wait_for_timeout(200)
     assert page.locator('h1').count()==1;assert page.locator('.article-more .reading-card img').count()==2
     stats=page.locator('article.article-content > figure img').evaluate('(i)=>({loaded:i.complete&&i.naturalWidth>0,nw:i.naturalWidth,nh:i.naturalHeight,w:i.getBoundingClientRect().width,h:i.getBoundingClientRect().height})');assert stats['loaded'];assert abs(stats['w']/stats['h']-stats['nw']/stats['nh'])<.03
     assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(a['key'],l,width,'overflow')
     for image in page.locator('.article-more .reading-card img').all():assert image.evaluate('(i)=>i.complete&&i.naturalWidth>0')
     page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(200);page.screenshot(path=str(OUT/f'{a["key"]}-{l}-{label}-top.png'));page.screenshot(path=str(OUT/f'{a["key"]}-{l}-{label}.png'),full_page=True);results.append({'article':a['key'],'language':l,'width':width,'image':stats})
   for l in ['ar','en','fr']:
    page.goto(base+'/'+('' if l=='ar' else l+'/')+'index.html',wait_until='networkidle')
    section=page.locator('.home-main > .home-section').first;cards=section.locator('.home-door-grid > article');assert cards.count()==8
    tops=cards.evaluate_all('(es)=>es.map(e=>Math.round(e.getBoundingClientRect().top))');assert len(set(tops))==2 and sorted([tops.count(t) for t in set(tops)])==[4,4],(l,width,tops)
    assert '20261018-hunting-two-rows' in page.locator('link[href*="home-doors.css"]').get_attribute('href');page.screenshot(path=str(OUT/f'homepage-{l}-{label}.png'),full_page=True)
   page.close()
  browser.close()
finally:
 server.shutdown();(OUT/'results.json').write_text(json.dumps(results,indent=2))
print('PASS: 24 article layouts and six homepages, full photos, two-row hunting section, no overflow.')
