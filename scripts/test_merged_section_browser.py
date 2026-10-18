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
    return page.evaluate(r'''() => {
      const nav = [...document.querySelectorAll('nav.main-nav,nav.mobile-nav')].find(n=>n.getBoundingClientRect().height>0);
      const rect = e => {const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
      const words = a => {
        const walker=document.createTreeWalker(a,NodeFilter.SHOW_TEXT), result=[];
        let node;
        while(node=walker.nextNode()) {
          for(const match of node.textContent.matchAll(/\S+/gu)) {
            const range=document.createRange();range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);
            const rects=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);
            result.push({text:match[0],lines:new Set(rects.map(r=>Math.round(r.y))).size,width:Math.max(0,...rects.map(r=>r.width))});
          }
        }
        const style=getComputedStyle(a);
        return {tokens:result,available:a.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight),overflowWrap:style.overflowWrap,wordBreak:style.wordBreak,hyphens:style.hyphens};
      };

      return {overflow:document.documentElement.scrollWidth>innerWidth+1,
        navClass:nav.className,rows:[...new Set([...nav.querySelectorAll(':scope > a')].map(a=>Math.round(a.getBoundingClientRect().y)))].length,
        links:[...nav.querySelectorAll(':scope > a')].map(a=>({text:a.textContent,rect:rect(a),font:getComputedStyle(a).fontSize,nowrap:getComputedStyle(a).whiteSpace,contentFits:a.scrollWidth<=a.clientWidth+1&&a.scrollHeight<=a.clientHeight+1,words:words(a)})),
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
        # Only the approved marine filter and balanced mobile navigation may differ.
        # The baseline request handler serves the original navigation stylesheet.
        expected=current_contract['protected_files'][name] if name in ('assets/js/combined-archive.js','docs/assets/js/combined-archive.js','assets/css/section-navigation.css','docs/assets/css/section-navigation.css') else digest
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
                original_search_css=subprocess.check_output(['git','show',base+':docs/assets/css/search-entry.css'],cwd=ROOT)
                original_navigation_css=subprocess.check_output(['git','show',base+':docs/assets/css/section-navigation.css'],cwd=ROOT)
                def route_local(request):
                    url=request.request.url
                    if url.startswith(old_url+'/') and urlsplit(url).path=='/assets/css/section-navigation.css':
                        request.fulfill(status=200,content_type='text/css',body=original_navigation_css)
                    elif url.startswith(old_url+'/') and urlsplit(url).path=='/assets/css/search-entry.css':
                        request.fulfill(status=200,content_type='text/css',body=original_search_css)
                    elif url.startswith((old_url+'/',new_url+'/')):
                        request.continue_()
                    else:
                        request.abort()
                context.route('**/*',route_local)
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
                        result['heritageCandidate']={'rows':candidate['rows'],'overflow':candidate['overflow'],'fits':not candidate['overflow'] and (width<=900 or candidate['rows']<=new['rows']) and (width<=900 or all(x['nowrap']=='nowrap' for x in candidate['links']))}
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
                        if width>900:
                            require(all(x['nowrap']=='nowrap' for x in new['links']),'Desktop label can break inside words')
                        require(new['links'][0]['text']=={'ar':'صيد وفروسية','en':'Hunting & Equestrian','fr':'Chasse et équitation'}[lang],'Combined title mismatch')
                        require(all(n['font']==o['font'] for n,o in zip(new['links'],old['links'])),'Navigation font size changed')
                        if width>900:
                            # Preserve existing row count: AR/EN one, French two.
                            require(new['rows']<=old['rows'],'Extra desktop section row')
                        else:
                            row_sizes=sorted(Counter(round(link['rect']['y']) for link in new['links']).values())
                            expected_rows=[3,3,4] if (lang=='en' and width<=360) or (lang=='fr' and width<=500) else [5,5]
                            require(new['rows']==len(expected_rows) and row_sizes==expected_rows,'Mobile/tablet navigation must use the approved balanced rows')
                            for i,link in enumerate(new['links']):
                                r=link['rect']
                                require(32<=r['height']<=96,'Mobile navigation cell height outside readable bounds')
                                require(link['contentFits'],'Mobile navigation label overflows its cell')
                                if lang in ('en','fr'):
                                    words=link['words']
                                    require(words['overflowWrap']=='normal' and words['wordBreak']=='normal' and words['hyphens']=='none','Latin labels must wrap only at natural word boundaries')
                                    require(all(token['lines']==1 for token in words['tokens']),'Latin navigation word split across lines')
                                    require(all(token['width']<=words['available']+1 for token in words['tokens']),'Latin navigation cell smaller than a complete word')
                                require(r['x']>=-1 and r['x']+r['width']<=width+1,'Mobile navigation cell outside viewport')
                                for other in new['links'][i+1:]:
                                    q=other['rect']
                                    overlap=min(r['x']+r['width'],q['x']+q['width'])-max(r['x'],q['x'])>1 and min(r['y']+r['height'],q['y']+q['height'])-max(r['y'],q['y'])>1
                                    require(not overlap,'Mobile navigation cells overlap')
                        brand,cta=new['brand'],new['market']
                        if cta:
                            require(cta['height']>=44,'Market touch target below 44 pixels')
                            search_box=page.locator('.site-search-link').bounding_box()
                            require(search_box['width']>=44 and search_box['height']>=44,'Search touch target below 44 pixels')
                            require(page.locator('.site-search-link svg').bounding_box()['width']==12,'Compact search icon')
                            for selector in ('.market-cta','.site-search-link'):
                                require(page.locator(selector).evaluate("e=>getComputedStyle(e,'::before').top")=='11px','Language-size visible button inset')
                            require(cta['width']<=old['market']['width'],'Market entry became larger')
                            require(page.locator('.market-cta').evaluate('e=>getComputedStyle(e).fontSize')==page.locator('.lang-switch').evaluate('e=>getComputedStyle(e).fontSize'),'Market type matches language selector')
                            require(page.locator('.lang-switch a').first.bounding_box()['height']==22,'Language selector reference height')
                        require(cta is not None,'Market CTA missing')
                        if cta:
                            require(abs(brand['y']+brand['height']/2-cta['y']-cta['height']/2)<=3,'Brand/market not aligned on one row')
                            require(cta['x']>=0 and cta['x']+cta['width']<=width+1,'Market CTA outside viewport')
                            require(cta['x']+cta['width']<=brand['x'] or brand['x']+brand['width']<=cta['x'],'Market CTA overlaps brand')
                        require(new['links'][1]['text']=={'ar':'مقابلات','en':'Interviews','fr':'Entretiens'}[lang],'Interviews must immediately follow Hunting & Equestrian')
                        require(page.locator('.memory-strip').count()==0,'Memory display remains')
                        interview_cards=page.locator('section.home-section').nth(1).locator('.home-door-grid > article')
                        require(interview_cards.count()==(4 if lang=='ar' else 1),'Interview collection count')
                        interview_geometry=page.locator('section.home-section').nth(1).locator('.home-door-grid').evaluate("""grid => {
                            const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
                            return {rail:rect(grid),scrollLeft:grid.scrollLeft,cards:[...grid.querySelectorAll(':scope > article')].map(card=>({rect:rect(card),href:card.querySelector('h3 a').getAttribute('href')}))};
                        }""")
                        result['interviews']=interview_geometry
                        visual_cards=interview_geometry['cards']
                        visual_order=sorted(range(len(visual_cards)),key=lambda i:(round(visual_cards[i]['rect']['y']),-visual_cards[i]['rect']['x'] if lang=='ar' else visual_cards[i]['rect']['x']))
                        require(visual_order==list(range(len(visual_cards))),'Interview visual order differs from chronological card order')
                        expected_interviews=current_contract['interviews']['homepage_slugs'][lang]
                        from refresh_homepage_doors import local_slug
                        actual_interviews=[unquote(urlsplit(card['href']).path).split('posts/')[-1].split('/')[0] for card in visual_cards]
                        require(actual_interviews==[local_slug(slug,lang) for slug in expected_interviews],'Interview chronology/identity mismatch')
                        if visual_cards:
                            first=visual_cards[0]['rect'];rail=interview_geometry['rail']
                            require(first['x']>=max(0,rail['x'])-1 and first['x']+first['width']<=min(width,rail['x']+rail['width'])+1,'Newest interview is not fully visible at the initial horizontal position')
                            if lang=='ar':
                                first_row=[card['rect']['x'] for card in visual_cards if abs(card['rect']['y']-first['y'])<2]
                                require(first['x']==max(first_row),'Newest Arabic interview must be the rightmost card in its row')

                        # Eight cards use the unchanged grid: 2 x 4 on desktop.
                        cards=page.locator('section.home-section').first.locator('.home-door-grid > article')
                        require(cards.count()==8,'Combined homepage card count')
                        if width>=1000:
                            rects=[card.bounding_box() for card in cards.all()]
                            require(sorted(Counter(round(r['y']) for r in rects).values())==[4,4],'Desktop combined grid must be two rows of four')
                        if width in (1440,390,320):
                            path=out/f'header-{lang}-{width}.png';capture(page,page.locator('.site-sticky'),path);screens.append(path)
                            path=out/f'header-before-{lang}-{width}.png';capture(before,before.locator('.site-sticky'),path);screens.append(path)
                            path=out/f'interviews-{lang}-{width}.png';capture(page,page.locator('section.home-section').nth(1),path);screens.append(path)
                            if lang=='ar' and width==1440:
                                path=out/'combined-ar-1440.png';capture(page,page.locator('section.home-section').first,path);screens.append(path)
                    # Approved interview lead and body, in each language and viewport.
                    for article_width in (390,1440):
                        page.set_viewport_size({'width':article_width,'height':1000})
                        page.goto(new_url+'/'+prefix+'index.html',wait_until='networkidle')
                        lead=page.locator('.feature-lead[data-hero="shireen"]')
                        require(lead.count()==1,'Approved Shireen main lead missing')
                        require('shireen-monitoring-new.jpg' in lead.locator('img').get_attribute('src'),'Approved cover mismatch')
                        path=out/f'shireen-home-{lang}-{article_width}.png';capture(page,lead,path);screens.insert(0,path)
                        article=lead.locator('h2 a').get_attribute('href')
                        page.goto(new_url+'/'+prefix+article,wait_until='networkidle')
                        require(page.locator('article.article-content figure').count()==8,'Eight approved article photographs required')
                        updates=json.loads((ROOT/'content/article-updates.json').read_text())['articles']
                        recorded=[x['updated'] for x in updates if x['slugs'].get('ar')=='شيرين-بو-رفول-مكافحة-الصيد-الجائر']
                        require(page.locator('.article-updated').count()==len(recorded),'Article update label must match registry')
                        if recorded:
                            require(page.locator('.article-updated time').get_attribute('datetime')==recorded[0],'Incorrect recorded article update date')
                        require(page.locator('.article-more').count()==1,'One related-reading section required')
                        require(not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),'Interview horizontal overflow')
                        for image in page.locator('article.article-content figure img').all():
                            image.evaluate('(img)=>img.decode()')
                            require(image.evaluate('(img)=>img.complete&&img.naturalWidth>0'),'Interview image failed')
                        path=out/f'shireen-article-{lang}-{article_width}.png';page.screenshot(path=str(path));screens.insert(0,path)
                        replacement=page.locator('article.article-content figure').filter(has=page.locator('img[src*="shireen-cabs-fieldwalk-20261018"]'))
                        if replacement.count():
                            replacement.scroll_into_view_if_needed()
                            path=out/f'shireen-cabs-{lang}-{article_width}.png';capture(page,replacement,path);screens.insert(0,path)
                    # Collection cards must retain the same thumbnail/title layout,
                    # including legacy cards that previously emitted stray images.
                    collection=new_url+'/'+prefix+'category/'+__import__('urllib.parse',fromlist=['quote']).quote('مقابلات')+'/index.html'
                    for collection_width in (390,1440):
                        page.set_viewport_size({'width':collection_width,'height':1000})
                        page.goto(collection,wait_until='networkidle')
                        rows=page.locator('main .post-list > article, main .home-door-grid > article')
                        require(rows.count()==(70 if lang=='ar' else 2),'Collection count after exclusions')
                        for row in rows.all():
                            require(row.locator(':scope > img').count()==0,'Bare thumbnail outside anchor')
                            require(row.locator(':scope > a.thumb').count()<=1,'Duplicate thumb anchor')
                            require(row.locator(':scope > div.body > h2 > a').count()==1,'Stable title layout')
                        if lang=='ar':
                            for key in ('لين-عراجي','جورج-قرداحي','نادين-نجيم'):
                                row=rows.filter(has=page.locator('h2 a[href*="'+key+'"]'))
                                require(row.count()==1,'Missing reviewed interview '+key)
                                row.scroll_into_view_if_needed()
                                image=row.locator('a.thumb img')
                                image.evaluate('(img)=>img.decode()')
                                require(image.count()==1,'Exactly one thumbnail '+key)
                                require(image.evaluate('(img)=>img.complete && img.naturalWidth>0'),'Portrait failed to load '+key)
                                path=out/f'collection-{key}-{collection_width}.png';capture(page,row,path);screens.insert(0,path)
                                image_box=image.bounding_box();title_box=row.locator('h2').bounding_box()
                                require(image_box['width']<collection_width*.6,'Oversized portrait '+key)
                                require(abs(image_box['y']-title_box['y'])<90,'Thumbnail not alongside title '+key)
                    # Real rendered filters: all, repeated topic clicks, history and keyboard.
                    page.set_viewport_size({'width':390,'height':1000})
                    archive=new_url+'/'+prefix+'category/'+__import__('urllib.parse',fromlist=['quote']).quote('صيد')+'/index.html'
                    page.goto(archive,wait_until='networkidle')
                    rows=page.locator('main .post-list > article,main .home-door-grid > article')
                    total=rows.count();topic_data=json.loads(page.locator('#combined-archive-data').text_content())
                    marine=set(topic_data['marine']);mixed=set(topic_data['landMarine']);equestrian=set(topic_data['equestrian'])
                    assert len(marine)=={'ar':4,'en':1,'fr':0}[lang], (lang,'marine registry count',len(marine))
                    assert len(mixed)=={'ar':3,'en':0,'fr':0}[lang], (lang,'mixed registry count',len(mixed))
                    assert mixed<=marine and not marine.intersection(equestrian), (lang,'invalid archive topic overlap')
                    hunting_count=total-len(equestrian)-len(marine-mixed)
                    trials=[('equestrian',len(equestrian)),('equestrian',len(equestrian)),('hunting',hunting_count)]
                    if marine:
                        trials.extend([('marine',len(marine)),('marine',len(marine))])
                    else:
                        expect(page.locator('[data-archive-filter="marine"]')).to_have_count(0)
                    trials.append(('all',total))
                    for topic,count in trials:
                        button=page.locator(f'[data-archive-filter="{topic}"]');button.click()
                        expect(page.locator('main .post-list > article:visible,main .home-door-grid > article:visible')).to_have_count(count)
                        expect(button).to_have_attribute('aria-pressed','true')
                    button=page.locator('[data-archive-filter="equestrian"]');button.focus();page.keyboard.press('Enter')
                    expect(button).to_have_attribute('aria-pressed','true')
                    page.goto(archive+'#hunting');expect(page.locator('main .post-list > article:visible,main .home-door-grid > article:visible')).to_have_count(hunting_count)
                    page.goto(archive+'#equestrian');page.go_back();expect(page.locator('main .post-list > article:visible,main .home-door-grid > article:visible')).to_have_count(hunting_count)
                    # Market click and reciprocal language switches stay within the right route.
                    page.locator('.market-cta').click();expect(page).to_have_url(new_url+'/'+prefix+'market/')
                    for code,route in [('ar','/market/index.html'),('en','/en/market/index.html'),('fr','/fr/market/index.html')]:
                        page.locator(f'.lang-switch a[lang="{code}"]').click()
                        expect(page).to_have_url(new_url+route)
                        expect(page.locator('h1')).to_have_count(1)
                browser.close()
        except Exception as error:
            errors.append({'fatal':repr(error),'traceback':__import__('traceback').format_exc(),'url':page.url if 'page' in locals() else ''})
        finally:
            old_srv.shutdown();new_srv.shutdown()
            (out/'geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            (out/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2))
            budget=3_000_000
            screens.sort(key=lambda p:(0 if p.name.startswith('shireen-cabs') else 1 if p.name.startswith('shireen-home-ar') else 1 if p.name.startswith('shireen-home-en') else 2 if p.name.startswith('shireen-article-ar') else 3 if p.name.startswith('shireen-article-en') else 4,p.name))
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
