#!/usr/bin/env python3
"""Render the approved team roster at desktop and phone widths."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
from urllib.parse import quote
import json
root=Path(__file__).resolve().parents[1];out=root/'sayd-visual-qa/team';out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root/'docs')));Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}/'
rows=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 for width in (390,1440):
  for lang,path in [('ar','pages/من-نحن/'),('en','en/team/'),('fr','fr/team/')]:
   page=browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
   page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
   page.goto(base+quote(path),wait_until='networkidle');page.evaluate('window.scrollTo({top:0,left:0,behavior:"instant"})');page.screenshot(path=str(out/f'{lang}-{width}.png'),full_page=True)
   data=page.evaluate('''() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,linkedIn:[...document.querySelectorAll('article a')].filter(a=>a.href.includes('linkedin.com')).length,phones:[...document.querySelectorAll('article a[href^="tel:"]')].map(a=>a.getAttribute('href'))})''')
   assert data['scrollWidth']<=width+1,data;assert data['linkedIn']==1;assert data['phones']==['tel:+9613897443','tel:+9613004693'];rows.append({'language':lang,**data});page.close()
 browser.close()
srv.shutdown();(out/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
