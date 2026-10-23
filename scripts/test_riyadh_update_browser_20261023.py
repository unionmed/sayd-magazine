#!/usr/bin/env python3
"""Read-only responsive QA for the dated Riyadh update, with external requests blocked."""
import functools, http.server, json, threading
from pathlib import Path
from urllib.parse import quote, urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'riyadh-update-visual-qa'
def main():
 OUT.mkdir(exist_ok=True)
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'docs')))
 threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
 records=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(channel='chrome',headless=True)
   try:
    for lang,slug in [('ar','الرياض-تستعيد-صهيلها-موسم-السباقات-2026'),('en','riyadh-racing-season-2026-2027-begins'),('fr','riyadh-racing-season-2026-2027-begins')]:
     for device,width,height in [('desktop',1440,1000),('mobile',390,844)]:
      page=browser.new_page(viewport={'width':width,'height':height})
      page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(origin+'/') or route.request.url.startswith('data:') else route.abort())
      url=origin+'/'+('' if lang=='ar' else lang+'/')+'posts/'+quote(slug)+'/index.html'
      response=page.goto(url,wait_until='networkidle');assert response.status==200
      update=page.locator('.riyadh-season-update');assert update.count()==1
      assert page.locator('.article-updated time').get_attribute('datetime')=='2026-10-23'
      assert page.locator('.article-content a[href^="http"]').count()==0
      assert page.locator('.riyadh-related a').count()==2
      assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(lang,device,'overflow')
      for image in page.locator('.article-content img').all():
       image.scroll_into_view_if_needed()
       image.evaluate('(img)=>img.decode()')
       assert image.evaluate('(img)=>img.complete&&img.naturalWidth>0')
      page.locator('.article-header').screenshot(path=str(OUT/f'{lang}-{device}-header.png'))
      update.scroll_into_view_if_needed();page.screenshot(path=str(OUT/f'{lang}-{device}-update.png'))
      records.append({'lang':lang,'device':device,'width':width,'status':'PASS','title':page.locator('h1').inner_text()});page.close()
   finally: browser.close()
 finally: server.shutdown()
 (OUT/'results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(records,ensure_ascii=False))
if __name__=='__main__':main()
