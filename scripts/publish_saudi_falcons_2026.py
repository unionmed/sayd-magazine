#!/usr/bin/env python3
"""Publish Nayef's approved Saudi exhibition story, 3 October 2026."""
import copy, html as esc, json, os, re, sys
from pathlib import Path
from urllib.parse import quote
from lxml import html
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/'docs'
sys.path.insert(0,str(ROOT/'scripts'))
from refresh_homepage_doors import main as refresh
AR='معرض-الصقور-والصيد-السعودي-الدولي-2026';EN='saudi-falcons-hunting-exhibition-2026'
T=json.loads((ROOT/'content/features/saudi-falcons-exhibition-2026.json').read_text())
IMAGES=['media/uploads/2026/10/saudi-falcons-exhibition-2026-close-spa.jpg','media/uploads/2026/10/saudi-falcons-exhibition-2026-auction-spa.jpg']
DATES={'ar':'3 تشرين الأول 2026','en':'3 October 2026','fr':'3 octobre 2026'}
DOOR={'ar':'صيد','en':'Hunting','fr':'Chasse'}
AUTHOR={'ar':'صيد — واس','en':'Sayd — SPA','fr':'Sayd — SPA'}
DATE='2026-10-03';TIME='2026-10-03T06:50:30+03:00'
def cls(t,c):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+c+' ")]')
def url(lang):return 'https://sayd-magazine.com/'+('' if lang=='ar' else lang+'/')+'posts/'+quote(AR if lang=='ar' else EN)+'/'
def save(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def figure(lang,i):
 d=T[lang];prefix='../../' if lang=='ar' else '../../../'
 return f'<figure><img src="{prefix+IMAGES[i]}" alt="{esc.escape(d["captions"][i],quote=True)}" decoding="async" style="display:block;width:100%;height:auto"><figcaption><span>{esc.escape(d["captions"][i])}</span><br><small style="font-size:11px;color:#777"><a href="https://www.spa.gov.sa/N2691131">'+('المصدر: وكالة الأنباء السعودية (واس)' if lang=='ar' else 'Source: Saudi Press Agency (SPA)' if lang=='en' else 'Source : Agence de presse saoudienne (SPA)')+'</a></small></figcaption></figure>'
def body(lang):
 d=T[lang];out=figure(lang,0)+f'<p class="article-deck"><em>{esc.escape(d["deck"])}</em></p>'
 for i,p in enumerate(d['paragraphs']):
  if i==3:out+=f'<h2>{esc.escape(d["heading"])}</h2>'+figure(lang,1)
  out+='<p>'+esc.escape(p)+'</p>'
 return out
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
if AR not in c['ia_slots']['important']:
 old=c['ia_slots']['important'];displaced=old[2];c['ia_slots']['important']=[AR,old[0],old[1],old[3]]
 c['latest']=[displaced]+c['latest'][:7]
c['featured']=[c['ia_slots']['main']]+c['ia_slots']['important'];c['ia_slots']['latest']=c['latest'];c['primary_door'][AR]='hunting'
c['ticker_slugs']=[AR]+[s for s in c['ticker_slugs'] if s!=AR]
c['card_image_overrides'][AR]={'image':IMAGES[0],'position':'62% 30%','alt':{l:T[l]['captions'][0] for l in T}}
c['demotion']='Nayef approved the Saudi falcons exhibition story in the first side card on 3 October 2026. Preserve Adonis return editorial in fourth side card; Hala second and autumn third. Turtle-dove feature moves to newest Updates; displaced oldest Suhail news remains in category/archive. All lower doors and protected design retained.'
save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/ticker.json';c=json.loads(p.read_text());c['items']=[{'slug':AR,'title':T['ar']['ticker']}]+[i for i in c['items'] if i['slug']!=AR];save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
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
print('Prepared three mirrors, first side card, ticker, category/archive and sitemap.')
