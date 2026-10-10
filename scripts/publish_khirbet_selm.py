#!/usr/bin/env python3
"""Publish approved Joumana Majed four-photo gallery in AR/EN/FR; Photos door only."""
import json,re,os,copy
from pathlib import Path
from html import escape
from urllib.parse import quote,unquote
from lxml import html
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs'
AR='طيور-خربة-سلم-بعدسة-جمانة-ماجد';EN='khirbet-selm-birds-joumana-majed'
OLDAR='مكافحة-الصيد-غير-القانوني-في-لبنان-بالصور';OLDEN='combating-illegal-hunting-lebanon-in-photos'
M=json.loads((ROOT/'content/galleries/khirbet-selm-joumana-majed-20261007.json').read_text())
DATES={'ar':'10 تشرين الأول 2026','en':'10 October 2026','fr':'10 octobre 2026'}
def cls(t,c):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+c+' ")]')
def write(p,t):p.parent.mkdir(parents=True,exist_ok=True);p.write_text('<!DOCTYPE html>\n'+html.tostring(t,encoding='unicode',method='html'))
def body(lang,depth):
 out=''
 for index,im in enumerate(M['images']):
  cap=im['captions'][lang];src='../'*depth+'media/uploads/2026/10/'+im['package_file']
  out+=f'<figure><img src="{src}" alt="{escape(im['alt'][lang],quote=True)}" width="{im['width']}" height="{im['height']}" loading="lazy" decoding="async" style="display:block;width:100%;height:auto;"><figcaption>{escape(cap)}</figcaption></figure>'
  if index==0:out+='<p>'+escape(M['titles'][lang][1])+'</p>'
 return out+'<p>'+escape(M['credits'][lang])+'</p>'
pairsfile=ROOT/'content/en/pairs.json';pairs=json.loads(pairsfile.read_text());pairs['pairs'][AR]=EN;pairsfile.write_text(json.dumps(pairs,ensure_ascii=False,indent=2)+'\n')
cfile=ROOT/'content/homepage.json';c=json.loads(cfile.read_text())
for d in c['ia_door_sections']:
 if d['door']=='photos':d['slugs']=[AR]+[s for s in d['slugs'] if s!=AR][:3]
c['desk_slugs']['صور']=[AR]+[s for s in c['desk_slugs']['صور'] if s!=AR][:3];c['desk_slugs']['Photos']=[EN]+[s for s in c['desk_slugs']['Photos'] if s!=EN][:3];c['primary_door'][AR]='photos'
for k in ['omit_from_latest','omit_from_ticker','omit_from_ticker_and_latest']:
 for s in [AR,EN]:
  if s not in c[k]:c[k].append(s)
c['gallery']=[AR,EN]+[s for s in c['gallery'] if s not in [AR,EN]]
cfile.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 old=OLDAR if lang=='ar' else OLDEN;s=AR if lang=='ar' else EN;depth=2 if lang=='ar' else 3
 p=DOCS/prefix/'posts'/s/'index.html';t=html.parse(str(DOCS/prefix/'posts'/old/'index.html')).getroot();title=M['titles'][lang][0]
 for n in t.xpath('//title'):n.text=title+' — '+('مجلة صيد' if lang=='ar' else 'Sayd Magazine')
 for n in t.xpath('//meta[@name="description"]'):n.set('content',M['titles'][lang][1])
 for n in cls(t,'article-header'):
  n.xpath('.//h1')[0].text=title
  metas=cls(n,'meta-item');metas[0].text=DATES[lang]
  for x in metas[1:]:x.getparent().remove(x)
 for n in cls(t,'article-featured'):n.getparent().remove(n)
 n=cls(t,'article-content')[0];n.clear();n.set('class','article-content')
 for x in html.fragments_fromstring(body(lang,depth)):n.append(x)
 for n in cls(t,'related-block'):n.getparent().remove(n)
 for n in t.iter():
  for key in ['href','content','data-url']:
   val=n.get(key)
   if val:
    val=val.replace(quote(OLDAR),quote(AR)).replace(OLDAR,AR).replace(OLDEN,EN)
    if key=='content' and n.tag=='meta':
     if n.get('property') in ['og:title']:val=title
     if n.get('property')=='og:description':val=M['titles'][lang][1]
     if n.get('property')=='og:image':val='https://sayd-magazine.com/media/uploads/2026/10/'+M['images'][0]['package_file']
    n.set(key,val)
 for n in t.xpath('//script[@type="application/ld+json"]'):n.getparent().remove(n)
 for n in t.xpath('//meta[@name="robots"]'):n.set('content','index,follow')
 for n in cls(t,'lang-switch'):
  for a in n.xpath('.//a'):
   other=a.get('lang');target=DOCS/('' if other=='ar' else other)/'posts'/(AR if other=='ar' else EN)/'index.html';a.set('href',os.path.relpath(target,p.parent))
 write(p,t)
 import seo_foundation as seo
 rel=p.relative_to(DOCS)
 p.write_text(seo.apply_html(p.read_text(),p,DOCS,rel,seo.load_twins(DOCS)))
 # Add the gallery to its Photos category and full article archive, retaining older material.
 for listing in [DOCS/prefix/'category/صور/index.html',DOCS/prefix/('articles' if lang=='ar' else 'stories')/'index.html']:
  text=listing.read_text();tree=html.fromstring(text)
  if any(s in unquote(h) for h in tree.xpath('//a/@href')):continue
  candidates=[]
  for node in tree.xpath('//article | //li'):
   if any(old in unquote(h) for h in node.xpath('.//a/@href')):candidates.append(node)
  if not candidates:raise ValueError('Missing template card '+str(listing))
  card=copy.deepcopy(candidates[-1])
  for a in card.xpath('.//a[@href]'):
   if old in unquote(a.get('href')):
    a.set('href',os.path.relpath(p,listing.parent));
    if not a.xpath('.//img'):a.text=title
  for n in cls(card,'excerpt'):n.text=M['titles'][lang][1]
  for im in card.xpath('.//img'):
   im.set('src',os.path.relpath(DOCS/'media/uploads/2026/10'/M['images'][0]['package_file'],listing.parent));im.set('alt',M['images'][0]['captions'][lang])
  for n in cls(card,'meta')+cls(card,'feed-date'):n.clear();n.set('class','meta');n.text=DATES[lang]
  first=candidates[-1].getparent();first.insert(0,card)
  write(listing,tree)
# Permanent content sources and French translation inputs.
(ROOT/'content/posts'/f'{AR}.md').write_text('---\n'+f'title: {json.dumps(M["titles"]["ar"][0],ensure_ascii=False)}\nslug: {AR}\ndate: 2026-10-10 03:53:29\nauthor: nkrayem\ncategories: [صور]\nfeatured: media/uploads/2026/10/{M["images"][0]["package_file"]}\n---\n\n'+body('ar',0)+'\n')
(ROOT/'content/en'/f'{EN}.md').write_text('# '+M['titles']['en'][0]+f'\n\n**Source AR URL:** https://sayd-magazine.com/posts/{AR}/\n**Source AR title:** '+M['titles']['ar'][0]+f'\n**Suggested slug:** {EN}\n**Category:** Photos\n\n## Lead\n\n'+M['titles']['en'][1]+'\n\n## Body\n\n'+body('en',0)+'\n')
f=ROOT/'content/fr/segments'/f'{EN}.json';f.write_text(json.dumps({'title':M['titles']['fr'][0],'blocks':[M['titles']['fr'][1],M['credits']['fr']],'figures':[im['captions']['fr'] for im in M['images']]},ensure_ascii=False,indent=2)+'\n')
f=ROOT/'content/fr/edition-2026.json';manifest=json.loads(f.read_text())
if not any(x['slug']==EN for x in manifest['articles']):manifest['articles'].append({'slug':EN,'english_title':M['titles']['en'][0],'date':DATES['en'],'category':'Photos','english_url':f'/en/posts/{EN}/'})
f.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
# Complete SEO mirrors after all three article pages exist.
import seo_foundation as seo
for prefix,slug in [('',AR),('en',EN),('fr',EN)]:
 p=DOCS/prefix/'posts'/slug/'index.html'
 p.write_text(seo.apply_html(p.read_text(),p,DOCS,p.relative_to(DOCS),seo.load_twins(DOCS)))
from refresh_homepage_doors import main
main()
# Photo albums follow the existing noindex/ sitemap exclusion policy.
print('Published four approved photos in three mirrors, newest Photos card first.')
