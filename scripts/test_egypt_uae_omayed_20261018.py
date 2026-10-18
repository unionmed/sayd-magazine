#!/usr/bin/env python3
"""Verify the Omayed article and the narrowly scoped publication surfaces."""
import hashlib,json,re,subprocess
from pathlib import Path
from urllib.parse import unquote
from lxml import html
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs'
BASE='dcdd205015072065e93c6278c01c457f76e75ea7'
a=json.loads((ROOT/'content/features/egypt-uae-omayed-20261018.json').read_text())['articles'][0]
old=json.loads(subprocess.check_output(['git','show',BASE+':content/homepage.json'],cwd=ROOT))
new=json.loads((ROOT/'content/homepage.json').read_text());ar=a['slugs']['ar']
assert new['featured']==old['featured']
assert new['ia_slots']['main']==old['ia_slots']['main']
assert new['ia_slots']['important']==old['ia_slots']['important']
assert new['ia_slots']['latest']==([ar]+old['ia_slots']['latest'])[:8]
assert new['primary_door'][ar]=='wildlife'
assert len(new['ticker_entries'])==10 and new['ticker_entries'][0]['slug']==ar
displaced=old['ia_slots']['latest'][-1]
assert displaced in next(x for x in new['ia_door_sections'] if x['door']==new['primary_door'][displaced])['slugs']
p=a['photos'][0]
assert hashlib.sha256((DOCS/p['path']).read_bytes()).hexdigest()==p['sha256']
links=json.loads((DOCS/'s/links.json').read_text())
for l in ['ar','en','fr']:
 base=DOCS/('' if l=='ar' else l);f=base/'posts'/a['slugs'][l]/'index.html';t=html.fromstring(f.read_text());d=a['translations'][l]
 assert t.xpath('//h1')[0].text_content()==d['title']
 body=t.xpath('//article[@class="article-content"]')[0];plain=' '.join(body.text_content().split())
 for paragraph in [d['deck']]+d['intro']+[p for h,ps in d['sections'] for p in ps]:assert ' '.join(paragraph.split()) in plain,(l,paragraph)
 assert len(body.xpath('.//section[contains(@class,"article-more")]//*[@class="reading-card"]'))==2
 for card in body.xpath('.//section[contains(@class,"article-more")]//*[@class="reading-card"]'):
  assert len(card.xpath('.//img'))==1
  target=(f.parent/unquote(card.get('href'))).resolve();assert target.is_file()
  image=(f.parent/unquote(card.xpath('.//img')[0].get('src'))).resolve();assert image.is_file()
  assert card.xpath('.//span')[0].text_content()==html.fromstring(target.read_text()).xpath('//h1')[0].text_content()
 figure=body.xpath('./figure')[0]
 assert (f.parent/unquote(figure.xpath('./img')[0].get('src'))).resolve()==(DOCS/p['path']).resolve()
 assert figure.xpath('./figcaption')[0].text_content()==p['caption'][l]
 assert len(body.xpath('.//p[@class="photo-credit"]'))==1
 assert body.xpath('.//p[@class="photo-credit"]//a[@href="https://creativecommons.org/licenses/by/4.0/"]')
 assert t.xpath('//meta[@name="description"]/@content')[0]==d['meta_description']
 assert len(t.xpath('//link[@rel="alternate" and @hreflang]'))>=3
 canonical=t.xpath('//link[@rel="canonical"]/@href')[0]
 assert a['slugs'][l] in unquote(canonical) and canonical in (DOCS/'sitemap.xml').read_text()
 assert any(a['slugs'][l] in unquote(target) for target in links)
 for relative in [('articles' if l=='ar' else 'stories')+'/index.html','category/'+a['category']+'/index.html']:
  assert a['slugs'][l] in unquote((base/relative).read_text())
 assert all(term not in plain for term in ['newsroom_only','publication_ready','PENDING LOCAL COPY'])
# Existing article text, images and editorial links are untouched by the new shared ticker.
changed=subprocess.check_output(['git','-c','core.quotePath=false','diff','--name-only',BASE,'--','docs'],cwd=ROOT).decode().splitlines()
for rel in changed:
 if '/posts/' not in rel or not rel.endswith('/index.html'):continue
 try:before=subprocess.check_output(['git','show',BASE+':'+rel],cwd=ROOT,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError:continue
 after=(ROOT/rel).read_bytes()
 for selector in ['//article[@class="article-content"]','//header[contains(@class,"article-header")]']:
  left=html.fromstring(before).xpath(selector);right=html.fromstring(after).xpath(selector)
  assert len(left)==len(right),(rel,selector)
  for x,y in zip(left,right):assert html.tostring(x)==html.tostring(y),(rel,'unrelated editorial change')
for rel in ['assets/css/home-doors.css','docs/assets/css/home-doors.css','content/publication-contract.json','AGENTS.md']:
 assert (ROOT/rel).read_bytes()==subprocess.check_output(['git','show',BASE+':'+rel],cwd=ROOT)
print('PASS: Omayed AR/EN/FR, licensed local image, illustrated related cards, SEO/short links, Updates/Land & Sea, unchanged lead and existing article content.')
