"""Real seller products appear in each edition with working shared navigation."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html
import json
from build_market_coming_soon import DOCS, ROUTES, COPY, ORIGIN, CATALOG, LABELS

def test_pages():
    catalog=json.loads(CATALOG.read_text())
    products=catalog['products']
    assert catalog['link_type']=='direct_seller'
    assert len({p['id'] for p in products})==len(products)==8
    for lang,route in ROUTES.items():
        p=DOCS/route/'index.html';t=html.parse(str(p))
        assert t.xpath('//h1/text()')==[COPY[lang][1]]
        assert t.xpath('//link[@rel="canonical"]/@href')==[ORIGIN+route]
        assert {a.get('hreflang'):a.get('href') for a in t.xpath('//link[@rel="alternate"]')}=={code:ORIGIN+path for code,path in {**ROUTES,'x-default':ROUTES['ar']}.items()}
        assert not t.xpath('//form | //input | //select | //textarea')
        cards=t.xpath('//article[@class="market-product"]')
        assert len(cards)==len(products)
        for card,product in zip(cards,products):
            assert card.get('data-product-id')==product['id']
            assert card.xpath('.//h2//text()')==[product['copy'][lang]['name']]
            link=card.xpath('.//a[@class="market-buy"]')[0]
            assert link.get('href')==product['url'] and link.get('target')=='_blank'
            assert set(link.get('rel').split())=={'noopener','noreferrer'}
            assert link.text==LABELS[lang][0]+' ↗'
            assert card.xpath('.//svg[@role="img"]/@aria-label')
            assert card.xpath('.//*[@class="market-illustration"]/text()')==[LABELS[lang][2]]
        assert t.xpath('//*[@class="market-note"]/text()')==[LABELS[lang][1]]
        assert not t.xpath('//script[contains(@src,"affiliate")]')
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
    print('PASS: eight real products and seller links in AR/EN/FR, localized illustrations, reciprocal language links, local assets, no on-site checkout')

if __name__=='__main__':test_pages()
