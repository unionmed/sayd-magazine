"""Real seller products appear in each edition with working shared navigation."""
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from lxml import html
import json
import hashlib
from decimal import Decimal
from build_market_coming_soon import DOCS, ROUTES, COPY, ORIGIN, CATALOG, LABELS, DISCLOSURES, purchase_url

def test_pages():
    catalog=json.loads(CATALOG.read_text())
    products=catalog['products']
    assert catalog['link_type']=='awin_affiliate' and catalog['version']==3
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
            assert link.get('href')==product['affiliate_url'] and link.get('target')=='_blank'
            assert set(link.get('rel').split())=={'noopener','noreferrer','sponsored'}
            assert link.text==LABELS[lang][0]
            assert not card.xpath('.//svg | .//*[@class="market-illustration"]')
            image=card.xpath('.//img[@class="market-photo"]')[0]
            assert image.get('src')=='/'+product['image']['path']
            assert image.get('alt')=='SilverAnt — '+product['copy'][lang]['name']
            data=(DOCS/product['image']['path']).read_bytes()
            assert hashlib.sha256(data).hexdigest()==product['image']['sha256']
            assert card.xpath('.//a[@class="market-visual"]/@href')==[product['affiliate_url']]
            price=card.xpath('.//p[@class="market-price"]')[0]
            amount=f"{Decimal(product['price']['amount']):.2f}"
            assert price.get('data-currency')=='USD' and price.get('data-price')==amount
            assert ''.join(price.itertext())=='$'+amount+' USD'
            assert 'variant='+str(product['price']['variant_id']) in product['url']
            assert 'currency=USD' in product['url']
            assert purchase_url(product)==product['affiliate_url']
            visual=card.xpath('.//a[@class="market-visual"]')[0]
            assert visual.get('target')=='_blank'
            assert set(visual.get('rel').split())=={'noopener','noreferrer','sponsored'}
            assert parse_qs(urlsplit(product['affiliate_url']).query)=={
                'awinmid':['45577'],'awinaffid':['3146890'],'ued':[product['url']]}

        assert t.xpath('//header[@class="market-intro"]/p[@class="market-disclosure"]/text()')==[DISCLOSURES[lang]]
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
    print('PASS: eight real products and approved Awin links with visible disclosure and sponsored/security attributes in AR/EN/FR, original local product photographs and USD prices, reciprocal language links, local assets, no on-site checkout')

def test_unapproved_affiliate_links_fail_closed():
    product=json.loads(CATALOG.read_text())['products'][0]
    original=product['affiliate_url']
    bad_links=[
        original.replace('45577','45578'),
        original.replace('3146890','3146891'),
        original.replace('https://','http://',1),
        original.replace('www.awin1.com','www.awin1.com.evil.example'),
        original.replace('44477767778482','44477767778483'),
        original.replace('USD','EUR'),
        original+'&awinmid=999',
        original+'&extra=unapproved',
        original+'&extra=',
        original+'&awinmid=',
        original+'#unapproved',
    ]
    for bad in bad_links:
        try:
            purchase_url({**product,'affiliate_url':bad})
        except AssertionError:
            continue
        raise AssertionError('Unapproved affiliate link accepted: '+bad)

if __name__=='__main__':
    test_pages()
    test_unapproved_affiliate_links_fail_closed()
