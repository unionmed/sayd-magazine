#!/usr/bin/env python3
"""Real local HTTP browser search QA; external requests blocked and inspected."""
import base64,json
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from datetime import date
from playwright.sync_api import sync_playwright,expect
from test_merged_section_browser import server
ROOT=Path(__file__).resolve().parents[1]

def run():
    out=ROOT/'sayd-visual-qa';out.mkdir(exist_ok=True)
    registry=json.loads((ROOT/'content/interviews.json').read_text())['entries']
    assert all(row['reviewed_as']=='interview' for row in registry)
    srv,url=server(ROOT/'docs'); external=[]; failures=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context()
            def route(r):
                if r.request.url.startswith(url+'/'):r.continue_()
                else:external.append(r.request.url);r.abort()
            context.route('**/*',route)
            page=context.new_page();page.on('pageerror',lambda error:failures.append(str(error)))
            for lang,prefix,word in [('ar','','طائر'),('en','en/','bird'),('fr','fr/','oiseau')]:
                for width in (1440,390,320):
                    page.set_viewport_size({'width':width,'height':900})
                    page.goto(url+'/'+prefix,wait_until='networkidle')
                    search=page.locator('.site-search-link');expect(search).to_be_visible()
                    assert search.bounding_box()['width']>=44
                    boxes=[page.locator(x).bounding_box() for x in ('.brand','.market-cta','.site-search-link')]
                    for i,a in enumerate(boxes):
                        for b in boxes[i+1:]:assert a['x']+a['width']<=b['x']+.5 or b['x']+b['width']<=a['x']+.5
                    assert max(a['y']+a['height']/2 for a in boxes)-min(a['y']+a['height']/2 for a in boxes)<4
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    external.clear()
                    search.click();expect(page.locator("#site-search-form")).to_be_visible();page.wait_for_function('document.querySelector("#site-search-form") && !document.querySelector("#site-search-form").hasAttribute("aria-busy")')
                    assert not external,external
                    query=page.locator('#search-query');query.fill(word);query.press('Enter')
                    if width<=500:
                        padding=page.locator('main.search-page > .container').evaluate('(e)=>[parseFloat(getComputedStyle(e).paddingLeft),parseFloat(getComputedStyle(e).paddingRight)]')
                        assert min(padding)>=12, padding
                    expect(page.locator('.search-result').first).to_be_visible()
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    assert '?' not in page.url and '#' not in page.url
                    assert page.locator('.search-result h2 a').first.get_attribute('href').startswith(url+'/')
                    # Native-size viewport keeps controls and first results readable;
                    # do not shrink the full twenty-result page into a thumbnail.
                    page.locator('main').evaluate('(el) => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY)')
                    page.screenshot(path=str(out/f'search-{lang}-{width}.png'), full_page=False, animations='disabled', caret='hide')
                    query.fill('<img src=x onerror=alert(1)>');query.press('Enter');expect(page.locator('.search-result')).to_have_count(0)
                    assert not page.locator('#search-results img').count()
                    assert page.locator('#search-status').inner_text()==page.locator('#search-copy').evaluate('(e)=>JSON.parse(e.textContent).none')
                    query.fill('');query.press('Enter');expect(page.locator('.search-result')).to_have_count(0)
                    assert page.locator('#search-status').inner_text()==page.locator('#search-copy').evaluate('(e)=>JSON.parse(e.textContent).empty')
                    query.fill('Phoenicurus phoenicurus');query.press('Enter');expect(page.locator('.search-result').first).to_be_visible()
                    page.locator('#search-year').select_option('2026');expect(page.locator('.search-result').first).to_be_visible()
                    page.locator('#search-year').select_option('')
                    selected=page.locator('.search-result-meta').first.inner_text().split(' · ')[1]
                    page.locator('#search-category').select_option(label=selected)
                    expect(page.locator('.search-result').first).to_be_visible()
                    assert all(selected in text for text in page.locator('.search-result-meta').all_text_contents())
                    page.locator('#search-category').select_option('')
                    query.fill('');query.press('Enter')
                    interview={'ar':'مقابلات','en':'Interviews','fr':'Entretiens'}[lang]
                    page.locator('#search-category').select_option(label=interview)
                    expect(page.locator('.search-result').first).to_be_visible()
                    eligible=[{'date':row['published_at'], 'url':'/'+prefix+'posts/'+quote(row['languages'][lang])+'/'}
                              for row in registry if lang in row['languages'] and
                              (lang=='ar' or date.fromisoformat(row['published_at']).year>=2026)]
                    # Empty-query facet results rank by original date then URL,
                    # just like search, without freezing the newest identity.
                    ordered=page.evaluate('(rows)=>rows.sort((a,b)=>b.date.localeCompare(a.date)||a.url.localeCompare(b.url)).map(row=>row.url)',eligible)
                    assert page.locator('#search-status').inner_text().startswith(str(len(ordered))+' ')
                    expect(page.locator('.search-result')).to_have_count(min(20,len(ordered)))
                    actual=[unquote(urlsplit(href).path) for href in page.locator('.search-result h2 a').evaluate_all('(links)=>links.map(a=>a.href)')]
                    assert actual==[unquote(path) for path in ordered[:20]], 'Interview result identities/chronology differ from registry'
                    assert all(' · ' not in text for text in page.locator('#search-category option').all_text_contents())
                    page.locator('#search-category').select_option('')
                    query.fill('Phoenicurus phoenicurus');query.press('Enter')
                    page.locator('#search-language').select_option('en');page.locator('#search-language').select_option('fr');page.locator('#search-language').select_option('ar')
                    page.wait_for_function('!document.querySelector("form").hasAttribute("aria-busy")');expect(page.locator('.search-result').first).to_be_visible()
                    assert not external,external
                    assert page.evaluate('localStorage.length')==0
                # Establish the result navigation before exercising Back; the
                # click alone does not prove its history entry has committed.
                search_url=page.url
                result=page.locator('.search-result h2 a').first
                result_url=result.get_attribute('href');result_title=result.inner_text()
                result.click();page.wait_for_url(result_url,wait_until='domcontentloaded')
                expect(page.locator('main h1')).to_have_text(result_title)
                page.go_back(wait_until='domcontentloaded')
                expect(page).to_have_url(search_url)
                expect(page.locator('#search-query')).to_be_visible()
            # A failed index fetch is recoverable by the same Search button.
            page2=context.new_page()
            page2.route('**/index-ar.json*',lambda r:r.abort())
            page2.goto(url+'/search/');page2.wait_for_function('!document.querySelector("form").hasAttribute("aria-busy")')
            assert 'تعذّر' in page2.locator('#search-status').inner_text()
            page2.unroute('**/index-ar.json*');page2.locator('#search-query').fill('طائر');page2.locator('#search-query').press('Enter');expect(page2.locator('.search-result').first).to_be_visible()
            browser.close()
        assert not failures,failures
        for lang in ('ar','en','fr'):
            for width in (1440,390):
                path=out/f'search-{lang}-{width}.png'
                print('SAYD_PNG_BEGIN '+path.name);print(base64.b64encode(path.read_bytes()).decode());print('SAYD_PNG_END '+path.name)
        print('PASS: browser search at 1440/390/320, header geometry, scientific names, filters, hostile/empty query, rapid language switches, Back, privacy and retry')
    finally:srv.shutdown()
if __name__=='__main__':run()
