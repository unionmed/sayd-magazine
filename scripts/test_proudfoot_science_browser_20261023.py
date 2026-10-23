"""Read-only local browser acceptance of the three authorized Science pages."""
from pathlib import Path
from urllib.parse import quote
import functools,hashlib,http.server,json,threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'proudfoot-science-visual-qa';OUT.mkdir(exist_ok=True)
a=json.loads((ROOT/'content/features/proudfoot-vulture-calls-20261023.json').read_text())['articles'][0]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
for m in a['photos']+a['media']:assert hashlib.sha256((ROOT/'docs'/m['path']).read_bytes()).hexdigest()==m['sha256']
results=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  context=browser.new_context()
  context.route('**/*',lambda route:route.continue_() if route.request.url.startswith((origin+'/','data:','blob:')) else route.abort())
  for lang,slug in a['slugs'].items():
   page=context.new_page();page.set_viewport_size({'width':390,'height':844})
   page.goto(origin+'/'+('' if lang=='ar' else lang+'/')+'posts/'+quote(slug)+'/',wait_until='networkidle')
   body=page.locator('.article-content');assert page.locator('h1').inner_text()==a['translations'][lang]['title']
   assert body.locator('a[href^="http"]').count()==0
   assert body.locator('iframe, source[src^="http"],img[src^="http"]').count()==0
   assert page.locator('audio[autoplay],video[autoplay]').count()==0
   assert page.locator('meta[name=robots][content*=noindex]').count()==0
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),lang
   images=body.locator('img').evaluate_all('(xs)=>xs.map(i=>({complete:i.complete,width:i.naturalWidth,height:i.naturalHeight}))')
   # Lazy figure can be lower than initial viewport.
   body.locator('img').scroll_into_view_if_needed();page.wait_for_function('Array.from(document.querySelectorAll(".article-content img")).every(x=>x.complete&&x.naturalWidth>0)')
   images=body.locator('img').evaluate_all('(xs)=>xs.map(i=>({width:i.naturalWidth,height:i.naturalHeight}))')
   assert len(images)==1 and images[0]['width']>600
   media=page.evaluate('''async()=>{let out=[];for(const m of document.querySelectorAll('.article-content audio,.article-content video')){await new Promise((resolve,reject)=>{if(m.readyState>=1)return resolve();m.addEventListener('loadedmetadata',resolve,{once:true});m.addEventListener('error',()=>reject(m.error.message),{once:true});m.load();setTimeout(()=>reject('metadata timeout'),10000)});m.currentTime=0;await m.play();await new Promise(r=>setTimeout(r,m.tagName==='VIDEO'?650:350));let progressed=m.currentTime>0;let played=m.played.length>0;m.pause();out.push({tag:m.tagName,duration:m.duration,currentTime:m.currentTime,progressed,played,error:m.error&&m.error.message});}return out;}''')
   assert len(media)==2 and all(m['progressed'] and m['played'] and not m['error'] for m in media),media
   page.evaluate('scrollTo(0,0)');page.screenshot(path=str(OUT/f'{lang}-mobile.png'),full_page=True)
   page.set_viewport_size({'width':1440,'height':1000});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(OUT/f'{lang}-desktop.png'),full_page=True)
   results.append({'language':lang,'images':images,'media':media,'mobile_no_overflow':True,'desktop_no_overflow':True,'external_editorial_links':0});page.close()
  browser.close()
finally:
 server.shutdown();(OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False,indent=2))
