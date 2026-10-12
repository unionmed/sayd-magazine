#!/usr/bin/env python3
"""Checks for the approved Dubai-only Wildlife placement and European promotion."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html
from publish_dubai_safari_20261012 import ROOT, DOCS, DATA, AR, INTL, EU, IMAGES, media_url, public, main as generate
from refresh_homepage_doors import local_slug


def old(base,name):
    return subprocess.check_output(['git','show',f'{base}:{name}'],cwd=ROOT)

def class_nodes(tree,name):
    return tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+name+' ")]')

def slugs(nodes):
    values=[]
    for node in nodes:
        a=node.xpath('.//a[contains(@href,"posts/")]/@href')
        if a:values.append(unquote(a[0]).split('posts/')[1].split('/')[0])
    return values

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',required=True);args=ap.parse_args()
    c=json.loads((ROOT/'content/homepage.json').read_text());before=json.loads(old(args.base,'content/homepage.json'))
    assert c['ia_slots']['main']==before['ia_slots']['main']
    assert c['ia_slots']['important']==[EU]+before['ia_slots']['important'][:3]
    assert EU not in c['latest'] and AR not in c['latest'] and AR not in c['featured']
    assert c['latest'][0]==before['latest'][0]
    for key in ('ticker_entries','ticker_slugs','layout_limits','tv_channel_config'):
        assert c[key]==before[key],key
    assert old(args.base,'content/ticker.json')==(ROOT/'content/ticker.json').read_bytes()
    for lang in ('ar','en','fr'):
        prefix='' if lang=='ar' else lang
        slug=AR if lang=='ar' else INTL
        p=DOCS/prefix/'posts'/slug/'index.html';t=html.parse(str(p))
        assert t.xpath('string(//h1)')==DATA[lang]['title']
        body=class_nodes(t,'article-content')[0]
        assert all(text in body.text_content() for text in DATA[lang]['paragraphs'])
        assert body[0].tag=='figure'
        images=body.xpath('.//img')
        assert len(images)==3
        for image,expected in zip(images,IMAGES):
            assert image.get('src').endswith(media_url(expected)) and not image.get('src').startswith('http')
            assert (p.parent/urlsplit(image.get('src')).path).resolve().is_file()
            assert image.get('alt')
        assert body.text_content().count(DATA[lang]['photo_credit'])==1
        assert t.xpath('//link[@rel="canonical"]/@href')==[public(lang)]
        assert set(t.xpath('//link[@hreflang]/@hreflang'))=={'ar','en','fr','x-default'}
        news=next(json.loads(s) for s in t.xpath('//script[@type="application/ld+json"]/text()') if json.loads(s).get('@type')=='NewsArticle')
        assert news['datePublished']==DATA['published_at']==news['dateModified']
        home=html.parse(str(DOCS/prefix/'index.html'))
        europe=local_slug(EU,lang)
        assert slugs(class_nodes(home,'card-stack'))[0]==europe
        assert europe not in slugs(class_nodes(home,'latest-feed')[0].xpath('./li'))
        assert slug not in slugs(class_nodes(home,'card-stack'))+slugs(class_nodes(home,'latest-feed')[0].xpath('./li'))
        door=next(n for n in class_nodes(home,'home-section') if n.xpath('.//h2') and n.xpath('.//h2')[0].text_content() in ('برية وتخييم','Wildlife & Camping','Faune et camping'))
        assert slugs(door.xpath('.//article'))[0]==slug
        assert len(door.xpath('.//article'))==4
        assert sum(s==slug for s in slugs(home.xpath('//article')))==1
        category=html.parse(str(DOCS/prefix/'category/حياة-برية-وتخييم/index.html'))
        assert slugs(category.xpath('//article'))[0]==slug
        # Europe's body, URL, date, image, and interior category are byte-preserved.
        for pth in (DOCS/prefix/'posts'/europe/'index.html',DOCS/prefix/'category/صيد/index.html'):
            assert old(args.base,str(pth.relative_to(ROOT)))==pth.read_bytes(),pth
        oldhome=html.fromstring(old(args.base,str((DOCS/prefix/'index.html').relative_to(ROOT))))
        for oldticker,newticker in zip(class_nodes(oldhome,'ticker'),class_nodes(home,'ticker')):
            assert html.tostring(oldticker)==html.tostring(newticker),'Ticker changed'
    # Publication generators must reproduce the exact same persisted output.
    paths=[p for folder in ('content','docs','audit/image-catalog/manifest') for p in (ROOT/folder).rglob('*') if p.is_file()]
    snapshot={p:hashlib.sha256(p.read_bytes()).digest() for p in paths}
    generate()
    assert all(hashlib.sha256(p.read_bytes()).digest()==sha for p,sha in snapshot.items()),'Generator is not idempotent'
    print('PASS: Dubai AR/EN/FR copy, photos, dates, SEO, Wildlife-only placement; Europe promotion with full original pages and ticker preserved; idempotence')

if __name__=='__main__':main()
