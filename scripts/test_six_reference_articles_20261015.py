#!/usr/bin/env python3
"""Exact-content, local-media and bounded-distribution regression checks."""
import hashlib,json,re,subprocess
from pathlib import Path
from urllib.parse import unquote,urlparse
from lxml import html
import publish_six_reference_articles_20261015 as p

def check():
 articles=json.loads(p.SOURCE.read_text())['articles'];assert len(articles)==6
 for a in articles:
  assert a['slugs']['en']==a['slugs']['fr']
  assert hashlib.sha256((p.DOCS/a['image']).read_bytes()).hexdigest()==a['image_sha256']
  for l in p.LANGS:
   path=p.DOCS/p.relpage(a,l);t=html.parse(str(path));body=t.xpath('//article[@class="article-content"]')[0]
   expected=html.fromstring('<article>'+p.body(a,l)+'</article>')
   assert html.tostring(body,method='text',encoding='unicode').strip()==html.tostring(expected,method='text',encoding='unicode').strip(),(a['key'],l,'body')
   assert t.xpath('//html/@lang')==[l]
   assert t.xpath('//header[@class="article-header"]//h1/text()')==[a['languages'][l]['title']]
   assert t.xpath('//link[@rel="canonical"]/@href')==[p.url(a,l)]
   for lang in p.LANGS:assert t.xpath('//link[@rel="alternate"][@hreflang="'+lang+'"]/@href')==[p.url(a,lang)]
   assert len(body.xpath('.//figure/img'))==1
   assert body.xpath('.//figure/figcaption/text()')==[a['caption'][l]]
   assert (path.parent/unquote(body.xpath('.//figure/img/@src')[0])).resolve()==(p.DOCS/a['image']).resolve()
   related=t.xpath('//section[@class="related-block"]');assert len(related)==1
   expected_related=html.fromstring(p.related(a,l,articles))
   assert related[0].xpath('.//h3/a/@href')==expected_related.xpath('.//h3/a/@href')
   assert len(related[0].xpath('.//h3/a'))==2
   for href in related[0].xpath('.//a/@href'):assert (path.parent/unquote(href)).is_file()
   for href in t.xpath('//nav[contains(@class,"lang-switch")]/a/@href'):
    assert (p.DOCS/unquote(urlparse(href).path.lstrip('/'))/'index.html').is_file()
   if a['category']=='موسوعة-الطيور':
    assert body.xpath('.//p[@class="photo-credits"]//a[@rel="license"]/@href')==[a['photo_credit']['license_url']]
   schemas=[json.loads(x) for x in t.xpath('//script[@type="application/ld+json"]/text()')]
   schema=next(x for x in schemas if x.get('@type')=='Article')
   assert schema['datePublished']==a['published_at'] and schema['articleSection']==p.CAT_LABELS[a['category']][l]
   source=path.read_text();assert source.count('analytics:start')==1 and source.count('googletagmanager.com/gtag/js')==1
   assert source.count('article-share:start')==1
   assert not body.xpath('.//img[starts-with(@src,"http")]')
   home=(p.DOCS/('' if l=='ar' else l)/'index.html').read_text()
   assert a['slugs'][l] not in unquote(home)
   for rel in [('category/'+a['category']+'/index.html'),('articles/index.html' if l=='ar' else 'stories/index.html')]:
    listing=html.parse(str(p.DOCS/('' if l=='ar' else l)/rel))
    matches=[el for el in listing.xpath('//article') if any('/posts/'+a['slugs'][l]+'/' in unquote(href) for href in el.xpath('.//a/@href'))]
    assert len(matches)==1,(a['key'],l,rel,len(matches))
 # No existing homepage, ticker, protected rule, unrelated category or article changes.
 changed=subprocess.check_output(['git','-c','core.quotepath=false','diff','--name-only','HEAD'],cwd=p.ROOT,text=True).splitlines()
 permitted={'content/en/pairs.json','content/fr/edition-2026.json','docs/sitemap.xml','docs/s/links.json','audit/image-catalog/manifest/2026-01.tsv','audit/image-catalog/preliminary-taxonomy.json','audit/image-catalog/article-image-links.json'}
 for l in p.LANGS:
  prefix='docs/'+('' if l=='ar' else l+'/')
  permitted.update({prefix+'category/'+c+'/index.html' for c in ['قوانين','موسوعة-الطيور']})
  permitted.add(prefix+('articles' if l=='ar' else 'stories')+'/index.html')
 for a in articles:
  for l in p.LANGS:
   permitted.add('docs/'+p.relpage(a,l).as_posix())
   permitted.add('content/'+('posts' if l=='ar' else l)+'/'+a['slugs'][l]+'.md')
  permitted.add('content/fr/segments/'+a['slugs']['fr']+'.json')
 old_source='content/features/hunting-laws-arab-20261015.json'
 old_data=json.loads(subprocess.check_output(['git','show','a7e23c80616e9848a2c01ebb5a5a3e658a647616:'+old_source],cwd=p.ROOT,text=True))
 current=json.loads((p.ROOT/old_source).read_text())
 for old,new in zip(old_data['articles'],current['articles']):
  assert {k:v for k,v in new.items() if k!='caption'}==old
  for l in p.LANGS:
   rel=p.relpage(new,l);path='docs/'+rel.as_posix();permitted.add(path)
   baseline=subprocess.check_output(['git','show','a7e23c80616e9848a2c01ebb5a5a3e658a647616:'+path],cwd=p.ROOT,text=True)
   before=p.laws.EDITORIAL_GRAPHIC[l];after=new['caption'][l]
   import html as esc
   expected=baseline.replace('<figcaption>'+esc.escape(before)+'</figcaption>','<figcaption>'+esc.escape(after)+'</figcaption>').replace('alt="'+esc.escape(before,quote=True)+'"','alt="'+esc.escape(after,quote=True)+'"')
   assert (p.ROOT/path).read_text()==expected,(path,'caption-only change')
 permitted.update({old_source,'scripts/publish_three_hunting_laws_20261015.py'})
 assert set(changed)<=permitted,set(changed)-permitted
 # Repeatability of all source/rendered outputs; image bytes are unchanged.
 paths=[x for x in p.ROOT.rglob('*') if x.is_file() and '.git' not in x.parts and x.suffix in {'.html','.md','.json','.xml','.tsv'}]
 before={x:hashlib.sha256(x.read_bytes()).digest() for x in paths}
 p.run()
 changed=[str(x.relative_to(p.ROOT)) for x,h in before.items() if hashlib.sha256(x.read_bytes()).digest()!=h]
 assert not changed,changed
 print('PASS: 18 exact article bodies, photos/rights, trilingual links/SEO, category-only distribution, same-category next reads, protected scope and repeatability')
if __name__=='__main__':check()
