#!/usr/bin/env python3
"""Regression checks for the approved Arab-world encyclopedia package."""
import hashlib,json,re,subprocess
from pathlib import Path
from urllib.parse import unquote,urlparse
from lxml import html
import publish_arab_bird_encyclopedia_20261014 as pub

def check():
 articles=pub.package(); assert len(articles)==4
 expected_photos={'black-redstart-arab-world':'69ae8e1929b2b000efa47025f35107fb92810a31215bed4c8669d36980216474','common-chiffchaff-arab-world':'b5fd0acf272b03704137b8141f950379fa4066d29b2f60afebbffc8359089f55','white-wagtail-arab-world':'e3df50f0a0bd81200b5037d57ade8bfd53f5b217e5b10b8615e4bab97ebc164d'}
 for a in articles:
  if a['new']:assert hashlib.sha256((pub.DOCS/a['image']).read_bytes()).hexdigest()==expected_photos[a['key']]
  for l in pub.LANGS:
   p=pub.DOCS/pub.relpage(a,l);t=html.parse(str(p));body=pub.cls(t,'article-content')[0]
   expected=html.fromstring('<article>'+pub.article_body(a,l)+'</article>')
   assert html.tostring(body,method='text',encoding='unicode').strip()==html.tostring(expected,method='text',encoding='unicode').strip(),(a['key'],l,'body')
   assert body.xpath('.//figcaption/text()')==[a['caption'][l]]
   assert body.xpath('.//figure/img/@alt')==[a['languages'][l]['alt']]
   assert len(body.xpath('.//figure/img'))==1
   image=(p.parent/unquote(body.xpath('.//img/@src')[0])).resolve()
   assert image==(pub.DOCS/a['image']).resolve() and image.is_file()
   credits=body.xpath('.//p[@class="photo-credits"]')
   assert len(credits)==int(a['new'])
   if a['new']:assert credits[0].xpath('.//a[@rel="license"]/@href')==[a['photo_credit']['license_url']]
   assert t.xpath('//link[@rel="canonical"]/@href')==[pub.url(a,l)]
   for other in pub.LANGS:assert t.xpath('//link[@rel="alternate"][@hreflang="'+other+'"]/ @href'.replace('/ @','/@'))==[pub.url(a,other)]
   assert t.xpath('//header[@class="article-header"]//h1/text()')==[a['languages'][l]['title']]
   related=pub.cls(t,'related-block'); assert len(related)==1
   assert related[0].xpath('.//h2/text()')==[pub.LABEL[l]]
   expected_related=html.fromstring(pub.related(a,l,articles))
   assert related[0].xpath('.//h3/a/@href')==expected_related.xpath('.//h3/a/@href')
   assert len(related[0].xpath('.//h3/a'))==2
   for a_tag in related[0].xpath('.//a[@href]')+t.xpath('//nav[contains(@class,"lang-switch")]/a[@href]'):
    href=unquote(a_tag.get('href'));target=pub.DOCS/href.lstrip('/') if href.startswith('/') else p.parent/href
    assert target.is_file(),target
   assert all(x not in body.text_content() for x in ['ملحق المراجعة','ملاحظات اعتماد','Source AR URL','publication approval'])
   if not a['new']:
    assert t.xpath('//time/@datetime')==['2026-10-14']
    assert '2025' in t.xpath('//div[@class="article-meta"]/span[1]/text()')[0]
    if l=='ar':assert t.xpath('//div[@class="article-meta"]/span[last()]/text()')==['jabourached']
   data=[json.loads(x) for x in t.xpath('//script[@type="application/ld+json"]/text()')]
   article=next(x for x in data if x.get('@type')=='Article')
   assert article['datePublished'].startswith(a['date']) and article['dateModified']=='2026-10-14'
   assert t.getroot().get('lang')==l
   source=p.read_text();assert source.count('analytics:start')==1 and source.count('googletagmanager.com/gtag/js')==1
   assert "gtag('config', 'G-C3C0CEYX8Q');" in source
 # Factual regression guards retained from the preceding bee-eater update.
 for l in pub.LANGS:
  text=(pub.DOCS/pub.relpage(articles[-1],l)).read_text()
  assert all(x not in text for x in ['غالبًا ما يستهدف الأفراد الضعيفة','targets weaker individuals','another for waste','أخرى للنفايات'])
 # The source-backed generator must be repeatable, including listings and aliases.
 paths=[p for p in pub.ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and p.suffix not in {'.pyc'}]
 before={p:hashlib.sha256(p.read_bytes()).digest() for p in paths}
 pub.apply()
 changed=[str(p.relative_to(pub.ROOT)) for p,h in before.items() if hashlib.sha256(p.read_bytes()).digest()!=h]
 assert not changed,changed
 print('PASS: 12 exact bodies, captions/credits/photos, 3-language SEO, preserved bee-eater identity/date, same-category links, analytics and repeatability')
if __name__=='__main__':check()
