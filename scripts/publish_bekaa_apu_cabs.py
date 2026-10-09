#!/usr/bin/env python3
"""Publish the approved verbatim Bekaa statement with a separate official tally clarification."""
import copy, html as esc, json, os, re, sys
from pathlib import Path
from urllib.parse import quote
from lxml import html
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/'docs'
sys.path.insert(0,str(ROOT/'scripts'))
from refresh_homepage_doors import main as refresh
AR='البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs';EN='northern-bekaa-38280-square-metres-bird-nets-apu-cabs'
OLD='حين-يتغير-الساحل-أين-تستريح-الطيور'
T=json.loads((ROOT/'content/features/bekaa-apu-cabs-20261009.json').read_text())
IMAGES=['media/uploads/2026/10/bekaa-apu-cabs-20261009-01.jpg', 'media/uploads/2026/10/bekaa-apu-cabs-20261009-02.jpg', 'media/uploads/2026/10/bekaa-apu-cabs-20261009-03.jpg', 'media/uploads/2026/10/bekaa-apu-cabs-20261009-04.jpg', 'media/uploads/2026/10/bekaa-apu-cabs-20261009-05.jpg', 'media/uploads/2026/10/bekaa-apu-cabs-20261009-06.jpg', 'media/uploads/2026/10/bekaa-apu-cabs-20261009-07.jpg']
OFFICIAL='https://isf.gov.lb/ar/news/حملة-تفكيك-شباك-الصيد-القاتلة-مستمرّة/'
DATES={'ar':'9 تشرين الأول 2026','en':'9 October 2026','fr':'9 octobre 2026'}
DOOR={'ar':'صيد','en':'Hunting','fr':'Chasse'}
AUTHOR={'ar':'بيان','en':'Statement','fr':'Communiqué'}
DATE='2026-10-09';TIME='2026-10-09T11:50:00+03:00'
def cls(t,c):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+c+' ")]')
def url(lang):return 'https://sayd-magazine.com/'+('' if lang=='ar' else lang+'/')+'posts/'+quote(AR if lang=='ar' else EN)+'/'
def save(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def figure(lang,i):
 d=T[lang];prefix='../../' if lang=='ar' else '../../../'
 return f'<figure><img src="{prefix+IMAGES[i]}" alt="{esc.escape(d["captions"][i],quote=True)}" decoding="async" style="display:block;width:100%;height:auto"><figcaption>{esc.escape(d["captions"][i])}</figcaption></figure>'
def body(lang):
 d=T[lang];out=figure(lang,0)+'<h2>'+esc.escape(d['statement_label'])+'</h2><div class="statement-text">'
 for para in d['paragraphs']:out+='<p>'+esc.escape(para)+'</p>'
 out+='</div><section class="official-tally"><h2>'+esc.escape(d['clarification_title'])+'</h2><p>'+esc.escape(d['clarification'])+'</p><p><a href="'+esc.escape(OFFICIAL,quote=True)+'">'+esc.escape(d['official_link_label'])+'</a></p></section>'
 for i in range(1,len(IMAGES)):out+=figure(lang,i)
 return out+'<p class="photo-source"><small>'+esc.escape(d['source'])+'</small></p>'
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 d=T[lang];slug=AR if lang=='ar' else EN;depth=2 if lang=='ar' else 3
 old='حين-يصبح-الخريف-موسما-لاصطياد-الصورة' if lang=='ar' else 'when-autumn-becomes-a-season-for-hunting-images'
 t=html.parse(str(DOCS/prefix/'posts'/old/'index.html')).getroot()
 for n in t.xpath('//title'):n.text=d['title']+' — '+('مجلة صيد' if lang=='ar' else 'Sayd Magazine')
 for n in t.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):n.set('content',d['deck'])
 for n in t.xpath('//meta[@property="og:title" or @name="twitter:title"]'):n.set('content',d['title'])
 for n in t.xpath('//meta[@property="og:url"]'):n.set('content',url(lang))
 for n in t.xpath('//meta[@property="og:image" or @name="twitter:image"]'):n.set('content','https://sayd-magazine.com/'+IMAGES[0])
 for n in t.xpath('//link[@rel="canonical"]'):n.set('href',url(lang))
 for n in t.xpath('//link[@rel="alternate"]'):n.set('href',url(n.get('hreflang') if n.get('hreflang') in T else 'ar'))
 for a in cls(t,'lang-switch')[0].xpath('.//a'):
  target=a.get('lang');a.set('href','../'*depth+('' if target=='ar' else target+'/')+'posts/'+quote(AR if target=='ar' else EN)+'/index.html')
 header=cls(t,'article-header')[0];header.xpath('.//h1')[0].text=d['title']
 metas=cls(header,'meta-item');metas[0].text=DATES[lang];metas[1].text=AUTHOR[lang]
 for n in cls(t,'author-role'):n.getparent().remove(n)
 for a in header.xpath('.//a[contains(@href,"category/")]'):a.set('href','../../category/'+quote('صيد')+'/index.html');a.text=DOOR[lang]
 for a in cls(t,'breadcrumb')[0].xpath('.//a[contains(@href,"category/")]'):
  a.set('href','../../category/صيد/index.html');a.text=DOOR[lang]
 content=cls(t,'article-content')[0]
 for n in list(content):content.remove(n)
 content.text=None
 for n in html.fragments_fromstring(body(lang)):content.append(n)
 for name in ['article-featured','related-block']:
  for n in cls(t,name):n.getparent().remove(n)
 for n in t.xpath('//script[@type="application/ld+json"]'):n.getparent().remove(n)
 schema={'@context':'https://schema.org','@type':'NewsArticle','headline':d['title'],'description':d['deck'],'inLanguage':lang,'datePublished':TIME,'dateModified':TIME,'author':{'@type':'Organization','name':'Sayd Magazine'},'image':['https://sayd-magazine.com/'+i for i in IMAGES],'articleSection':DOOR[lang],'mainEntityOfPage':url(lang),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
 node=html.Element('script',{'type':'application/ld+json'});node.text=json.dumps(schema,ensure_ascii=False);t.xpath('//head')[0].append(node)
 for container in cls(t,'article-share')+cls(t,'share-bar'):
  for a in container.xpath('.//a[@href]'):a.set('href',re.sub(r'(?:https%3A%2F%2Fsayd-magazine.com%2F)[^&]+',quote(url(lang),safe=''),a.get('href')))
 save(DOCS/prefix/'posts'/slug/'index.html','<!DOCTYPE html>\n'+html.tostring(t,encoding='unicode',method='html'))
 save(ROOT/'content'/('posts' if lang=='ar' else lang)/(slug+'.md'),'---\n'+f'title: {json.dumps(d["title"],ensure_ascii=False)}\nslug: {slug}\ndate: {DATE}\nauthor: {json.dumps(AUTHOR[lang],ensure_ascii=False)}\ncategories: [صيد]\nfeatured: {IMAGES[0]}\nsubtitle: {json.dumps(d["deck"],ensure_ascii=False)}\n---\n\n'+body(lang)+'\n')
 for path in [DOCS/prefix/'category/صيد/index.html',DOCS/prefix/('articles' if lang=='ar' else 'stories')/'index.html']:
  s=path.read_text();s=re.sub(r'<article\b[^>]*>.*?</article>',lambda m:'' if quote(slug) in m[0] or '/posts/'+slug+'/' in m[0] else m[0],s,flags=re.S)
  m=re.search(r'<article\b[^>]*class="(?:post-row|card)"',s);assert m,path
  href=os.path.relpath(DOCS/prefix/'posts'/slug/'index.html',path.parent);image=os.path.relpath(DOCS/IMAGES[0],path.parent)
  row=f'<article class="post-row"><a class="thumb" href="{href}"><img src="{image}" alt="{esc.escape(d["captions"][0],quote=True)}" loading="lazy"></a><div class="body"><h2><a href="{href}">{esc.escape(d["title"])}</a></h2><div class="meta">{DATES[lang]}</div><p class="excerpt">{esc.escape(d["deck"])}</p></div></article>'
  if 'class="card"' in m[0]:row=row.replace('class="post-row"','class="card"')
  save(path,s[:m.start()]+row+'\n'+s[m.start():])
p=ROOT/'content/en/pairs.json';c=json.loads(p.read_text());c['pairs'][AR]=EN;save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/homepage.json';c=json.loads(p.read_text())
previous_side=c['ia_slots']['important'].copy()
c['ia_slots']['main']=AR
c['ia_slots']['important']=[OLD]+[x for x in c['ia_slots']['important'] if x!=OLD and x!=AR][:3]
c['featured']=[AR]+c['ia_slots']['important']
from homepage_demotion import demote_side_cards
demote_side_cards(c,previous_side)
c['primary_door'][AR]='hunting'
c['ticker_slugs']=[AR]+[x for x in c['ticker_slugs'] if x!=AR]
c['ticker_entries']=[{'slug':AR,'titles':{l:T[l]['ticker'] for l in T}}]+[x for x in c['ticker_entries'] if x['slug']!=AR]
c['card_image_overrides'][AR]={'image':IMAGES[0],'position':'50% 65%','alt':{l:T[l]['captions'][0] for l in T}}
c['demotion']='Previous lead becomes first side card. Displaced side cards enter the eight Updates in publication-date order; cards leaving Updates enter their appropriate lower door and remain in category/archive.'
save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/ticker.json';c=json.loads(p.read_text());c['items']=[{'slug':AR,'title':T['ar']['ticker'],'titles':{l:T[l]['ticker'] for l in T}}]+[x for x in c['items'] if x['slug']!=AR];save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')

for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 path=DOCS/prefix/'index.html';t=html.parse(str(path)).getroot();lead=cls(t,'feature-lead')[0]
 for a in lead.xpath('.//a'):a.set('href','posts/'+quote(AR if lang=='ar' else EN)+'/index.html')
 lead.xpath('.//h2/a')[0].text=T[lang]['title']
 lead.xpath('.//img')[0].set('src',os.path.relpath(DOCS/IMAGES[0],path.parent))
 lead.xpath('.//img')[0].set('alt',T[lang]['captions'][0]);lead.xpath('.//img')[0].set('style','object-position:50% 65%')
 cls(lead,'meta')[0].text=DATES[lang]
 original=path.read_text()
 save(path,re.sub(r'<article class="card overlay feature-lead">.*?</article>',html.tostring(lead,encoding='unicode',method='html'),original,count=1,flags=re.S))
refresh()
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 path=DOCS/prefix/'posts'/(AR if lang=='ar' else EN)/'index.html';t=html.parse(str(path)).getroot();ht=html.parse(str(DOCS/prefix/'index.html')).getroot()
 for dst,src in zip(cls(t,'ticker'),cls(ht,'ticker')):
  for n in list(dst):dst.remove(n)
  for n in src:
   a=copy.deepcopy(n);a.set('href','../../'+a.get('href'));dst.append(a)
 save(path,'<!DOCTYPE html>\n'+html.tostring(t,encoding='unicode',method='html'))
p=DOCS/'sitemap.xml';s=p.read_text()
for l in T:
 if url(l) not in s:s=s.replace('</urlset>',f'<url><loc>{url(l)}</loc><lastmod>{DATE}</lastmod></url>\n</urlset>')
save(p,s)
print('Prepared Bekaa statement in three mirrors with seven original photographs and official-tally clarification.')

from seo_foundation import apply_html, load_twins
twins=load_twins(DOCS)
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 p=DOCS/prefix/'posts'/(AR if lang=='ar' else EN)/'index.html'
 save(p,re.sub(r'(?m)^[ \t]+$','',apply_html(p.read_text(),p,DOCS,p.relative_to(DOCS),twins)))
 p=DOCS/prefix/'index.html';s=p.read_text()
 s=re.sub(r'(<meta (?:property="og:image"|name="twitter:image") content=")[^"]+',lambda m:m[1]+'https://sayd-magazine.com/'+IMAGES[0],s)
 save(p,re.sub(r'(?m)^[ \t]+$','',s))
