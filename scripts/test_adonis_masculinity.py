#!/usr/bin/env python3
"""Regression checks for the Adonis opinion package and its publication placement."""
import json
import subprocess
from pathlib import Path
from urllib.parse import quote,unquote,urlsplit
from lxml import html
R=Path(__file__).resolve().parents[1];D=R/'docs'
DATA=json.loads((R/'content/features/adonis-masculinity-20261013.json').read_text())
AR=DATA['slug_ar'];INTL=DATA['slug_intl'];IMAGE='media/uploads/2026/10/anti-poaching-four-photo-collage-october-2026.jpg';INSET_IMAGE='media/uploads/2026/10/apu-mecshap-cabs-lebanon-05.jpg'
def cls(t,k):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+k+' ")]')
c=json.loads((R/'content/homepage.json').read_text());base=json.loads(subprocess.check_output(['git','show','30cd24d:content/homepage.json'],cwd=R,text=True))
assert c['featured']==[base['featured'][0],AR]+base['featured'][1:4]
assert c['latest']==[base['latest'][0],base['featured'][-1]]+base['latest'][1:7]
assert c['ticker_entries']==base['ticker_entries'] and c['ticker_slugs']==base['ticker_slugs']
assert c['memory_after_door']=='wildlife'
links=json.loads((D/'s/links.json').read_text())
for lang in ('ar','en','fr'):
 pref='' if lang=='ar' else lang;slug=AR if lang=='ar' else INTL
 page=D/pref/'posts'/slug/'index.html';t=html.parse(str(page));body=cls(t,'article-content')[0]
 assert [p.text_content() for p in body.xpath('./p')]==DATA[lang]['paragraphs']
 assert len(body.xpath('./p'))==18 and not body.xpath('.//*[@class="article-deck"]')
 assert t.xpath('//header[@class="article-header"]//h1/text()')==[DATA[lang]['title']]
 assert not cls(t,'article-updated')
 assert 'رئيس التحرير' in cls(t,'article-header')[0].text_content() if lang=='ar' else 'Adonis Alkhateeb' in cls(t,'article-header')[0].text_content()
 photo=body.xpath('./figure/img')[0];assert (page.parent/photo.get('src')).resolve()==(D/IMAGE).resolve()
 assert photo.get('width')=='1024' and photo.get('height')=='1280' and 'height:auto' in photo.get('style')
 assert body.xpath('./figure')[0].get('style')=='width:100%;margin:18px 0 24px;'
 assert photo.get('style')=='display:block;width:100%;height:auto;'
 assert ''.join(body.xpath('./figure/figcaption')[0].text_content().split())==''.join(DATA[lang]['photo_caption'].split())
 assert len(body.xpath('./figure'))==2 and body[0].tag=='figure'
 inset=body.xpath('./figure')[1];inset_photo=inset.xpath('./img')[0]
 assert len(inset.xpath('preceding-sibling::p'))==6
 assert (page.parent/inset_photo.get('src')).resolve()==(D/INSET_IMAGE).resolve()
 assert inset_photo.get('width')=='1241' and inset_photo.get('height')=='1536'
 assert inset_photo.get('style')=='display:block;width:100%;height:auto;'
 assert inset_photo.get('alt')==DATA[lang]['inset_alt']
 assert inset.xpath('./figcaption')[0].text_content()==DATA[lang]['inset_caption']
 assert photo.get('alt')==DATA[lang]['hero_alt']
 assert t.xpath('//meta[@property="og:image"]/@content')==['https://sayd-magazine.com/'+IMAGE]
 assert t.xpath('//meta[@name="twitter:image"]/@content')==['https://sayd-magazine.com/'+IMAGE]
 assert not any(x in body.text_content() for x in ['Worked for','J الآخرين','معاينة للمراجعة'])
 schemas=[json.loads(s.text) for s in t.xpath('//script[@type="application/ld+json"]')]
 article=next(s for s in schemas if s.get('@type')=='OpinionNewsArticle')
 assert article['author']['@type']=='Person' and article['datePublished']==DATA['published_at']
 assert article['image']==['https://sayd-magazine.com/'+IMAGE]
 assert len(t.xpath('//link[@rel="alternate"]'))==4
 for a in t.xpath('//a[@href]'):
  h=a.get('href');u=urlsplit(h)
  if u.scheme or u.netloc or not u.path:continue
  target=(D/u.path.lstrip('/') if u.path.startswith('/') else page.parent/unquote(u.path)).resolve()
  assert target.exists(),(lang,h)
 home=D/pref/'index.html';ht=html.parse(str(home));old=html.fromstring(subprocess.check_output(['git','show','30cd24d:'+home.relative_to(R).as_posix()],cwd=R,text=True))
 assert [html.tostring(n) for n in cls(ht,'ticker')]==[html.tostring(n) for n in cls(old,'ticker')]
 card=cls(ht,'feature-stack')[0].xpath('./article')[0]
 assert slug in unquote(card.xpath('.//a/@href')[0])
 assert 'object-fit:cover' in card.xpath('.//img/@style')[0]
 assert 'object-position:center 10%' in card.xpath('.//img/@style')[0]
 assert c['card_image_overrides'][AR]['image']==INSET_IMAGE
 assert c['card_image_overrides'][AR]['fit']=='cover'
 assert c['card_image_overrides'][AR]['position']=='center 10%'
 key='/'+page.relative_to(D).parent.as_posix()+'/'
 assert key in links and (D/links[key].strip('/')/'index.html').is_file()
 assert 'G-C3C0CEYX8Q' in page.read_text()
print('PASS: exact 18-paragraph mirrors, attribution, full-frame collage cover and relocated original image, internal links, SEO, short links, side-card movement, unchanged lead/tickers, preserved memory placement.')
