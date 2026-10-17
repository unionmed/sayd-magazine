"""The Market is a localized announcement only, with working shared navigation."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html
from build_market_coming_soon import DOCS, ROUTES, COPY, ORIGIN

def test_pages():
    for lang,route in ROUTES.items():
        p=DOCS/route/'index.html';t=html.parse(str(p))
        assert t.xpath('//h1/text()')==[COPY[lang][1]]
        assert t.xpath('//link[@rel="canonical"]/@href')==[ORIGIN+route]
        assert {a.get('hreflang'):a.get('href') for a in t.xpath('//link[@rel="alternate"]')}=={code:ORIGIN+path for code,path in {**ROUTES,'x-default':ROUTES['ar']}.items()}
        assert not t.xpath('//form | //input | //select | //textarea')
        for code,route2 in ROUTES.items():
            a=t.xpath('//nav[@class="lang-switch"]/a[@lang="'+code+'"]')
            assert len(a)==1 and (p.parent/unquote(a[0].get('href'))).resolve()==(DOCS/route2/'index.html').resolve()
        for raw in t.xpath('//@href | //@src'):
            u=urlsplit(unquote(raw))
            if u.scheme or u.netloc or not u.path:continue
            dest=DOCS/u.path.lstrip('/') if u.path.startswith('/') else p.parent/u.path
            if dest.is_dir():dest=dest/'index.html'
            assert dest.exists(),(lang,raw)
        assert t.xpath('//nav[@class="header-social"]') and t.xpath('//footer')
    print('PASS: AR/EN/FR announcement, exact reciprocal language links, local links/assets, no commerce or signup controls')

if __name__=='__main__':test_pages()
