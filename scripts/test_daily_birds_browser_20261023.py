#!/usr/bin/env python3
"""Private, network-isolated 27-case visual QA for the three new species."""
import json, threading, os
from pathlib import Path
from functools import partial
from urllib.parse import unquote,urlsplit,quote
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'; OUT=ROOT/'daily-bird-visual-qa'
OUT.mkdir(exist_ok=True)
class H(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(H,directory=str(DOCS)))
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}'
data=json.loads((ROOT/'content/features/daily-birds-20261023.json').read_text())['articles']
report={'status':'RUNNING','external_network_blocked':True,'cases':[]}
def relative(a,l):return '/'+('' if l=='ar' else l+'/')+'posts/'+quote(a['slugs'][l])+'/index.html'
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True, executable_path=os.environ.get("SAYD_CHROMIUM_EXECUTABLE"))
  for mode,w,h in [('desktop',1440,1000),('mobile',390,844),('narrow',320,800)]:
   ctx=browser.new_context(viewport={'width':w,'height':h},device_scale_factor=1)
   def route(r):
    u=urlsplit(r.request.url)
    if r.request.url.startswith(origin+'/'):return r.continue_()
    if u.netloc=='sayd-magazine.com':
     path=DOCS/unquote(u.path).lstrip('/')
     if path.is_dir():path=path/'index.html'
     if path.is_file() and path.resolve().is_relative_to(DOCS.resolve()):return r.fulfill(path=str(path))
    r.abort()
   ctx.route('**/*',route)
   page=ctx.new_page()
   for a in data:
    for l in ['ar','en','fr']:
     name=a['key']+'-'+l+'-'+mode
     response=page.goto(origin+relative(a,l),wait_until='networkidle');assert response.status==200
     page.evaluate('document.fonts.ready')
     im=page.locator('article.article-content figure img');im.evaluate('(i)=>i.decode()')
     assert im.evaluate('(i)=>i.naturalWidth')==1600
     assert page.locator('article.article-content figure figcaption').inner_text()==a['caption'][l]
     assert page.locator('article.article-content p.photo-credits').count()==1
     sizes=page.evaluate('({w:innerWidth, s:document.documentElement.scrollWidth})');assert sizes['s']<=sizes['w']+1,(name,sizes)
     page.screenshot(path=str(OUT/(name+'-top.png')))
     page.locator('article.article-content p.photo-credits').scroll_into_view_if_needed()
     page.screenshot(path=str(OUT/(name+'-credits.png')))
     # Language click to another mirror, then Back/Forward and repeated click.
     other='en' if l=='ar' else 'ar'
     page.locator('nav.lang-switch a[lang="'+other+'"]').click()
     page.wait_for_load_state('domcontentloaded')
     assert page.locator('html').get_attribute('lang')==other
     assert page.locator('h1').inner_text()==a['languages'][other]['title']
     page.go_back(wait_until='domcontentloaded');assert page.locator('html').get_attribute('lang')==l
     page.go_forward(wait_until='domcontentloaded');assert page.locator('html').get_attribute('lang')==other
     page.go_back(wait_until='domcontentloaded')
     page.locator('section.related-block h3 a').first.click();page.wait_for_load_state('domcontentloaded')
     assert page.locator('h1').inner_text()!=a['languages'][l]['title']
     page.go_back(wait_until='domcontentloaded')
     report['cases'].append({'key':a['key'],'lang':l,'viewport':mode,'width':w,'photo_loaded':True,'no_horizontal_overflow':True,'language_and_back_forward':True,'related_navigation':True})
   for l in ['ar','en','fr']:
    path='/'+('' if l=='ar' else l+'/')+'category/'+quote('موسوعة-الطيور')+'/index.html'
    page.goto(origin+path,wait_until='networkidle')
    for a in data:
     links=page.locator('main article h2 a').all()
     assert sum(a['slugs'][l] in unquote(x.get_attribute('href')) for x in links)==1
    sizes=page.evaluate('({w:innerWidth, s:document.documentElement.scrollWidth})');assert sizes['s']<=sizes['w']+1
    page.screenshot(path=str(OUT/('category-'+l+'-'+mode+'.png')))
   ctx.close()
  browser.close()
 assert len(report['cases'])==27
 report['status']='PASS'
except Exception as error:
 report['status']='FAIL'
 report['error']=str(error)
 raise
finally:
 server.shutdown();server.server_close()
 (OUT/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PASS: 27 bird-language-viewport cases; photos, captions, credits, responsive layout, cross-language and related links, Back/Forward; category smoke checks.')
