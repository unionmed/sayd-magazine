#!/usr/bin/env python3
"""Read-only rendered QA: local baseline/current HTTP previews, no analytics."""
import argparse, base64, functools, hashlib, io, json, os, shutil, subprocess, tempfile, threading
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
WIDTHS=(1440,1280,1024,820,414,390,360,320)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def server(root):
    srv=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root)))
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    return srv,f'http://127.0.0.1:{srv.server_port}'

def geometry(page):
    return page.evaluate('''() => {
      const nav = [...document.querySelectorAll('nav.main-nav,nav.mobile-nav')].find(n=>n.getBoundingClientRect().height>0);
      const rect = e => {const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
      return {overflow:document.documentElement.scrollWidth>innerWidth+1,
        navClass:nav.className,rows:[...new Set([...nav.querySelectorAll(':scope > a')].map(a=>Math.round(a.getBoundingClientRect().y)))].length,
        links:[...nav.querySelectorAll(':scope > a')].map(a=>({text:a.textContent,rect:rect(a),font:getComputedStyle(a).fontSize,nowrap:getComputedStyle(a).whiteSpace})),
        controls:[...document.querySelectorAll('.site-sticky .header-social a,.site-sticky .lang-switch a,.site-sticky .market-cta,.site-sticky .site-search-link')].filter(e=>e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0).map(e=>({label:e.getAttribute('aria-label')||e.textContent,rect:rect(e)})),
        header:rect(document.querySelector('header.site-header')),
        brand:rect(document.querySelector('.brand')),market:document.querySelector('.market-cta')?rect(document.querySelector('.market-cta')):null};
    }''')

def capture(page,locator,dest):
    data=locator.screenshot()
    image=Image.open(io.BytesIO(data)).convert('RGB')
    image.thumbnail((1280,1200))
    # Bounded PNGs preserve label/shape review while keeping logs fetchable.
    image.quantize(colors=128).save(dest,optimize=True)


def run(base,out):
    out.mkdir(parents=True,exist_ok=True)
    errors=[];report=[];screens=[]
    # Baseline uses exact original homepage bytes. Shared historical CSS/JS/media
    # must be unchanged; separate newly-added styles are never linked by baseline.
    old_contract=json.loads(subprocess.check_output(['git','show',base+':content/publication-contract.json'],cwd=ROOT))
    current_contract=json.loads((ROOT/'content/publication-contract.json').read_text())
    for name,digest in old_contract['protected_files'].items():
        # Only the explicitly approved marine archive filter script may differ.
        # Baseline homepages do not load this category-only behavior.
        expected=current_contract['protected_files'][name] if name in ('assets/js/combined-archive.js','docs/assets/js/combined-archive.js') else digest
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,('Protected baseline asset changed',name)
    with tempfile.TemporaryDirectory() as temp:
        baseline=Path(temp)
        for child in (ROOT/'docs').iterdir():
            if child.name in ('index.html','en','fr'):continue
            (baseline/child.name).symlink_to(child,target_is_directory=child.is_dir())
        for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
            target=baseline/prefix;target.mkdir(exist_ok=True)
            if prefix:
                for child in (ROOT/'docs'/prefix).iterdir():
                    if child.name!='index.html':(target/child.name).symlink_to(child,target_is_directory=child.is_dir())
            (target/'index.html').write_bytes(subprocess.check_output(['git','show',base+':docs/'+(prefix+'/' if prefix else '')+'index.html'],cwd=ROOT))
        old_srv,old_url=server(baseline);new_srv,new_url=server(ROOT/'docs')
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None)
                context=browser.new_context(device_scale_factor=1)
                context.route('**/*',lambda route:route.continue_() if route.request.url.startswith((old_url+'/',new_url+'/')) else route.abort())
                page=context.new_page();before=context.new_page()
                for lang,prefix in [('ar',''),('en','en/'),('fr','fr/')]:
                    for width in WIDTHS:
                        page.set_viewport_size({'width':width,'height':1000});before.set_viewport_size({'width':width,'height':1000})
                        before.goto(old_url+'/'+prefix,wait_until='networkidle');page.goto(new_url+'/'+prefix,wait_until='networkidle')
                        old=geometry(before);new=geometry(page)
                        result={'language':lang,'width':width,'before':old,'after':new};report.append(result)
                        # Measure the optional Heritage title without changing source files.
                        heritage={'ar':('تراث','فن وتراث'),'en':('Heritage','Art & Heritage'),'fr':('Patrimoine','Art et patrimoine')}[lang]
                        page.evaluate("([oldLabel,newLabel])=>document.querySelectorAll('nav a').forEach(a=>{if(a.textContent===oldLabel)a.textContent=newLabel})",heritage)
                        candidate=geometry(page)
                        result['heritageCandidate']={'rows':candidate['rows'],'overflow':candidate['overflow'],'fits':not candidate['overflow'] and (width<=900 or candidate['rows']<=new['rows']) and all(x['nowrap']=='nowrap' for x in candidate['links'])}
                        page.evaluate("([oldLabel,newLabel])=>document.querySelectorAll('nav a').forEach(a=>{if(a.textContent===newLabel)a.textContent=oldLabel})",heritage)
                        def require(condition,message):
                            if not condition:errors.append({'language':lang,'width':width,'error':message})
                        require(not new['overflow'],'Horizontal page overflow')
                        require(page.locator('.header-social a').count()==4,'Four approved social controls required')
                        controls=new['controls']
                        for i,control in enumerate(controls):
                            r=control['rect']
                            require(r['x']>=-1 and r['x']+r['width']<=width+1,'Header control outside viewport: '+control['label'])
                            for other in controls[i+1:]:
                                q=other['rect']
                                overlap=min(r['x']+r['width'],q['x']+q['width'])-max(r['x'],q['x'])>1 and min(r['y']+r['height'],q['y']+q['height'])-max(r['y'],q['y'])>1
                                require(not overlap,'Overlapping header controls: '+control['label']+' / '+other['label'])

                        require(len(new['links'])==10,'Exactly ten direct section links required')
                        require(all(x['nowrap']=='nowrap' for x in new['links']),'A label can break inside words')
                        require(new['links'][0]['text']=={'ar':'صيد وفروسية','en':'Hunting & Equestrian','fr':'Chasse et équitation'}[lang],'Combined title mismatch')
                        require(all(n['font']==o['font'] for n,o in zip(new['links'],old['links'])),'Navigation font size changed')
                        if width>900:
                            # Preserve existing row count: AR/EN one, French two.
                            require(new['rows']<=old['rows'],'Extra desktop section row')
                        else:
                            require(new['rows']<=old['rows'],'Extra mobile section row')
                        brand,cta=new['brand'],new['market']
                        require(cta is not None,'Market CTA missing')
                        if cta:
                            require(abs(brand['y']+brand['height']/2-cta['y']-cta['height']/2)<=3,'Brand/market not aligned on one row')
                            require(cta['x']>=0 and cta['x']+cta['width']<=width+1,'Market CTA outside viewport')
                            require(cta['x']+cta['width']<=brand['x'] or brand['x']+brand['width']<=cta['x'],'Market CTA overlaps brand')
                        require(new['links'][1]['text']=={'ar':'مقابلات','en':'Interviews','fr':'Entretiens'}[lang],'Interviews must immediately follow Hunting & Equestrian')
                        require(page.locator('.memory-strip').count()==0,'Memory display remains')
                        interview_cards=page.locator('section.home-section').nth(1).locator('.home-door-grid > article')
                        require(interview_cards.count()==(4 if lang=='ar' else 1),'Interview collection count')
                        # Eight cards use the unchanged grid: 2 x 4 on desktop.
                        cards=page.locator('section.home-section').first.locator('.home-door-grid > article')
                        require(cards.count()==8,'Combined homepage card count')
                        if width>=1000:
                            rects=[card.bounding_box() for card in cards.all()]
                            require(sorted(Counter(round(r['y']) for r in rects).values())==[4,4],'Desktop combined grid must be two rows of four')
                        if width in (1440,390):
                            path=out/f'header-{lang}-{width}.png';capture(page,page.locator('.site-sticky'),path);screens.append(path)
                            if lang=='ar' and width==1440:
                                path=out/'combined-ar-1440.png';capture(page,page.locator('section.home-section').first,path);screens.append(path)
                    # Real rendered filters: all, repeated topic clicks, history and keyboard.
                    page.set_viewport_size({'width':390,'height':1000})
                    archive=new_url+'/'+prefix+'category/'+__import__('urllib.parse',fromlist=['quote']).quote('صيد')+'/index.html'
                    page.goto(archive,wait_until='networkidle')
                    rows=page.locator('main .post-list > article,main .home-door-grid > article')
                    total=rows.count();topic_data=json.loads(page.locator('#combined-archive-data').text_content())
                    marine=set(topic_data['marine']);mixed=set(topic_data['landMarine']);equestrian=set(topic_data['equestrian'])
                    assert len(marine)=={'ar':4,'en':1,'fr':0}[lang]
                    assert len(mixed)=={'ar':3,'en':0,'fr':0}[lang]
                    assert mixed<=marine and not marine.intersection(equestrian)
                    hunting_count=total-len(equestrian)-len(marine-mixed)
                    trials=[('equestrian',len(equestrian)),('equestrian',len(equestrian)),('hunting',hunting_count)]
                    if marine:
                        trials.extend([('marine',len(marine)),('marine',len(marine))])
                    else:
                        assert page.locator('[data-archive-filter="marine"]').count()==0
                    trials.append(('all',total))
                    for topic,count in trials:
                        button=page.locator(f'[data-archive-filter="{topic}"]');button.click()
                        expect(page.locator('main .post-list > article:visible,main .home-door-grid > article:visible')).to_have_count(count)
                        assert button.get_attribute('aria-pressed')=='true'
                    button=page.locator('[data-archive-filter="equestrian"]');button.focus();page.keyboard.press('Enter')
                    assert button.get_attribute('aria-pressed')=='true'
                    page.goto(archive+'#hunting');expect(page.locator('main .post-list > article:visible,main .home-door-grid > article:visible')).to_have_count(hunting_count)
                    page.goto(archive+'#equestrian');page.go_back();expect(page.locator('main .post-list > article:visible,main .home-door-grid > article:visible')).to_have_count(hunting_count)
                    # Market click and reciprocal language switches stay within the right route.
                    page.locator('.market-cta').click();assert urlsplit(page.url).path=='/'+prefix+'market/'
                    for code,route in [('ar','/market/index.html'),('en','/en/market/index.html'),('fr','/fr/market/index.html')]:
                        page.locator(f'.lang-switch a[lang="{code}"]').click()
                        assert unquote(urlsplit(page.url).path)==route
                        assert page.locator('h1').count()==1
                browser.close()
        except Exception as error:
            errors.append({'fatal':repr(error)})
        finally:
            old_srv.shutdown();new_srv.shutdown()
            (out/'geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            (out/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2))
            budget=750_000
            for path in screens:
                data=base64.b64encode(path.read_bytes()).decode()
                if len(data)<=budget:
                    print('SAYD_PNG_BEGIN '+path.name);print(data);print('SAYD_PNG_END '+path.name);budget-=len(data)
            print('SAYD_GEOMETRY_SUMMARY '+json.dumps([{'language':r['language'],'width':r['width'],'beforeRows':r['before']['rows'],'afterRows':r['after']['rows'],'overflow':r['after']['overflow']} for r in report]))
            print('SAYD_HERITAGE_CANDIDATE '+json.dumps({'fitsAll':bool(report) and all(r['heritageCandidate']['fits'] for r in report),'viewports':[{'language':r['language'],'width':r['width'],**r['heritageCandidate']} for r in report]}))
            print('SAYD_QA_ERRORS '+json.dumps(errors,ensure_ascii=False))
    assert not errors,'Rendered QA failed; see errors.json and screenshot artifacts'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--output',default='sayd-visual-qa');args=parser.parse_args()
    run(args.base,Path(args.output))
