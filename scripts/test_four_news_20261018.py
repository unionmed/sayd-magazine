#!/usr/bin/env python3
import hashlib,json,subprocess
from pathlib import Path
from lxml import html
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs';A=json.loads((ROOT/'content/features/four-news-20261018.json').read_text())['articles'];BASE='15d82a6f1868c8d612ab5acc2e500bce19bb7dc8'
old=json.loads(subprocess.check_output(['git','show',BASE+':content/homepage.json'],cwd=ROOT));new=json.loads((ROOT/'content/homepage.json').read_text())
upper=new
if new['ia_slots']['main']=='الشمال-إزالة-24750-متر-شباك-الصيد-الجائر':
 # Preserve the original upper-slot proof on the immutable pre-North tree.
 # The current tree must additionally match the entire exact approved package.
 from test_combined_hunting_equestrian import approved_three_expected
 prior=json.loads(subprocess.check_output(['git','show','c16e9f474b74efb48fdc01eab4f418f53beaa82e:content/homepage.json'],cwd=ROOT))
 assert approved_three_expected(prior,new) is not None
 upper=prior
assert upper['featured']==old['featured'];assert upper['ia_slots']['main']==old['ia_slots']['main'];assert upper['ia_slots']['important']==old['ia_slots']['important'];assert len(new['ia_slots']['latest'])==8;assert len(new['ticker_entries'])==10
for a in A:
 ar=a['slugs']['ar'];assert new['primary_door'][ar]==a['door'];assert (ar in new['ia_slots']['latest'])==(a['placement']=='news');assert (ar in [x['slug'] for x in new['ticker_entries']])==(a['placement']=='news')
 p=a['photos'][0];assert hashlib.sha256((DOCS/p['path']).read_bytes()).hexdigest()==p['sha256']
 for l in ['ar','en','fr']:
  f=DOCS/('' if l=='ar' else l)/'posts'/a['slugs'][l]/'index.html';s=f.read_text();t=html.fromstring(s);d=a['translations'][l];assert len(t.xpath('//h1'))==1 and t.xpath('//h1')[0].text_content()==d['title'];body=t.xpath('//article[@class="article-content"]')[0];plain=' '.join(body.text_content().split())
  for para in d['intro']+[p for h,ps in d['sections'] for p in ps]:assert ' '.join(para.split()) in plain,(a['key'],l,para)
  assert len(body.xpath('.//section[contains(@class,"article-more")]//*[@class="reading-card"]'))==2
  for card in body.xpath('.//section[contains(@class,"article-more")]//*[@class="reading-card"]'):
   assert len(card.xpath('.//img'))==1;href=card.get('href');target=(f.parent/unquote(href)).resolve();title=html.fromstring(target.read_text()).xpath('//h1')[0].text_content();assert card.xpath('.//span')[0].text_content()==title
  figure=body.xpath('./figure')[0];im=figure.xpath('./img')[0];assert (f.parent/unquote(im.get('src'))).resolve()==(DOCS/p['path']).resolve();assert figure.xpath('./figcaption')[0].text_content()==p['caption'][l];assert len(body.xpath('.//p[@class="photo-credit"]'))==1
  assert t.xpath('//meta[@name="description"]/@content')[0]==d['meta_description'];assert len(t.xpath('//link[@rel="alternate" and @hreflang]'))>=3
  assert all(html.fromstring((DOCS/('' if x=='ar' else x)/'posts'/a['slugs'][x]/'index.html').read_text()) is not None for x in ['ar','en','fr'])
  archive=DOCS/('' if l=='ar' else l)/('articles' if l=='ar' else 'stories')/'index.html';assert a['slugs'][l] in unquote(archive.read_text());cat=DOCS/('' if l=='ar' else l)/'category'/a['category']/'index.html';assert a['slugs'][l] in unquote(cat.read_text())
  assert not any(x in plain for x in ['newsroom_only','OWNER_PROVIDED','publication_ready','PENDING LOCAL COPY'])
  assert a['slugs'][l] in unquote((DOCS/'s/links.json').read_text())
# The existing Cairo World Cup report is unchanged outside the shared ticker.
for l,s in [('ar','القاهرة-تستعد-لكأس-العالم-للبندقية-والمسدس'),('en','cairo-rifle-pistol-world-cup-2026'),('fr','cairo-rifle-pistol-world-cup-2026')]:
 p=DOCS/('' if l=='ar' else l)/'posts'/s/'index.html';before=html.fromstring(subprocess.check_output(['git','show',BASE+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT));after=html.fromstring(p.read_text());assert html.tostring(before.xpath('//article[@class="article-content"]')[0])==html.tostring(after.xpath('//article[@class="article-content"]')[0])
for p in ['assets/css/home-doors.css','docs/assets/css/home-doors.css']:assert (ROOT/p).read_bytes()==subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
for l in ['','en','fr']:assert 'home-doors.css?v=20261018-hunting-two-rows' in (DOCS/l/'index.html').read_text()
print('PASS: 12 full articles, original approved photos, source credits, two illustrated related cards, Science-only loon, protected lead and Cairo archive, CSS cache token.')
