#!/usr/bin/env python3
"""Real local HTTP browser search QA; external requests blocked and inspected."""
import base64,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_merged_section_browser import server
ROOT=Path(__file__).resolve().parents[1]

def run():
    out=ROOT/'sayd-visual-qa';out.mkdir(exist_ok=True)
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
                    assert page.locator('#search-status').inner_text().startswith(('72 ' if lang=='ar' else '1 '))
                    assert page.locator('.search-result h2 a').first.get_attribute('href').find('cabs')>=0
                    assert all(' · ' not in text for text in page.locator('#search-category option').all_text_contents())
                    page.locator('#search-category').select_option('')
                    query.fill('Phoenicurus phoenicurus');query.press('Enter')
                    page.locator('#search-language').select_option('en');page.locator('#search-language').select_option('fr');page.locator('#search-language').select_option('ar')
                    page.wait_for_function('!document.querySelector("form").hasAttribute("aria-busy")');expect(page.locator('.search-result').first).to_be_visible()
                    assert not external,external
                    assert page.evaluate('localStorage.length')==0
                page.locator('.search-result h2 a').first.click();page.go_back();expect(page.locator('#search-query')).to_be_visible()
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
