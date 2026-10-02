#!/usr/bin/env python3
"""Publish Nayef-approved Hala El-Khatib essay in three mirrors, first side card."""
import copy, html as esc, json, re, sys, os
from pathlib import Path
from urllib.parse import quote
from lxml import html
from docx import Document

ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/'docs'
sys.path.insert(0,str(ROOT/'scripts'))
from refresh_homepage_doors import main as refresh
AR='حين-يصبح-الخريف-موسما-لاصطياد-الصورة'; EN='when-autumn-becomes-a-season-for-hunting-images'
OLDAR='ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان'; OLDEN='over-20000-m2-bird-nets-seized-lebanon'
IMAGE='media/uploads/2026/10/storks-resting-pines-mount-lebanon.jpg'
SOURCE='https://sayd-magazine.com/'
STUDY='https://doi.org/10.1017/S0030605324000814'
DATE='2026-10-03'; TIMES='2026-10-03T00:12:31+03:00'
T=json.loads((ROOT/'content/features/autumn-photography-hala-khatib-20261003.json').read_text())
paragraphs=[p.text.strip() for p in Document(sys.argv[1]).paragraphs if p.text.strip()]
heading=paragraphs.index('من التوعية إلى المتابعة'); assert heading==6
T['ar']={'title':paragraphs[0],'author':'د. هلا الخطيب','role':'محاضرة في كلية الإعلام، الجامعة اللبنانية','deck':'من البندقية إلى العدسة: كيف يسهم الإعلام في حماية الطيور المهاجرة وتغيير ثقافة التباهي بالقتل.','heading':paragraphs[heading],'caption':'لقالق تستريح على أشجار الصنوبر في جبل لبنان.','paragraphs':[p.replace('إقتصادية','اقتصادية') for p in paragraphs[1:] if p!=paragraphs[heading]]}
assert all(len(T[l]['paragraphs'])==12 for l in ['ar','en','fr'])
DATES={'ar':'3 تشرين الأول 2026','en':'3 October 2026','fr':'3 octobre 2026'}
DOOR={'ar':'صيد','en':'Hunting','fr':'Chasse'}
PULL={'ar':'لن يوقف مقال كل بندقية، لكن الإعلام يستطيع سحب التصفيق من حولها.','en':'One article will not stop every rifle. But the media can withdraw the applause surrounding it.','fr':'Un article n’arrêtera pas tous les fusils. Mais les médias peuvent retirer les applaudissements qui les entourent.'}
PATHS=[]
def save(path,text):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);PATHS.append(path.relative_to(ROOT).as_posix())
def write_tree(path,t):save(path,'<!DOCTYPE html>\n'+html.tostring(t,encoding='unicode',method='html'))
def cls(t,c):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+c+' ")]')
def url(lang):return 'https://sayd-magazine.com/'+('' if lang=='ar' else lang+'/')+'posts/'+quote(AR if lang=='ar' else EN)+'/'
def body(lang):
 d=T[lang];prefix='../../' if lang=='ar' else '../../../'
 credit={'ar':'الصورة','en':'Photo','fr':'Photo'}[lang]
 out=f'<figure><img src="{prefix+IMAGE}" alt="{esc.escape(d["caption"],quote=True)}" decoding="async" style="display:block;width:100%;height:auto"><figcaption>{esc.escape(d["caption"])}<br><span style="font-size:11px;color:#777">{credit}: { {'ar':'بنك صور صيد','en':'Sayd photo bank','fr':'Banque de photos de Sayd'}[lang] }</span></figcaption></figure>'
 out+=f'<p class="article-deck"><em>{esc.escape(d["deck"])}</em></p>'
 for i,p in enumerate(d['paragraphs']):
  if i==5:out+=f'<blockquote style="border-inline-start:4px solid #3e421d;padding:12px 18px;background:#f5f1e5"><p>{esc.escape(PULL[lang])}</p></blockquote><h2>{esc.escape(d["heading"])}</h2>'
  rendered=esc.escape(p)
  if i==4:
   word='أوريكس' if lang=='ar' else 'Oryx'
   rendered=rendered.replace(word,f'<a href="{STUDY}">{word}</a>',1)
  out+='<p>'+rendered+'</p>'
 return out
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 d=T[lang];slug=AR if lang=='ar' else EN;old=OLDAR if lang=='ar' else OLDEN;depth=2 if lang=='ar' else 3
 t=html.parse(str(DOCS/prefix/'posts'/old/'index.html')).getroot()
 for n in t.xpath('//title'):n.text=d['title']+' — '+('مجلة صيد' if lang=='ar' else 'Sayd Magazine')
 for n in t.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):n.set('content',d['deck'])
 for n in t.xpath('//meta[@property="og:title" or @name="twitter:title"]'):n.set('content',d['title'])
 for n in t.xpath('//meta[@property="og:url"]'):n.set('content',url(lang))
 for n in t.xpath('//meta[@property="og:image" or @name="twitter:image"]'):n.set('content','https://sayd-magazine.com/'+IMAGE)
 for n in t.xpath('//link[@rel="canonical"]'):n.set('href',url(lang))
 for n in t.xpath('//link[@rel="alternate"]'):n.set('href',url(n.get('hreflang') if n.get('hreflang') in T else 'ar'))
 nav=cls(t,'lang-switch')[0]
 for a in nav.xpath('.//a'):
  target=a.get('lang');local=('' if target=='ar' else target+'/')+'posts/'+quote(AR if target=='ar' else EN)+'/index.html'
  a.set('href','../'*depth+local)
 header=cls(t,'article-header')[0];header.xpath('.//h1')[0].text=d['title']
 metas=cls(header,'meta-item');metas[0].text=DATES[lang];metas[1].text=d['author']
 role=html.Element('p',{'class':'author-role','style':'font-size:14px;margin:6px 0 0;color:#68705f'});role.text=d['role'];header.append(role)
 for a in header.xpath('.//a[contains(@href,"category/")]'):a.set('href','../../category/'+quote('صيد')+'/index.html');a.text=DOOR[lang]
 content=cls(t,'article-content')[0]
 for n in list(content):content.remove(n)
 content.text=None
 for n in html.fragments_fromstring(body(lang)):content.append(n)
 for featured in cls(t,'article-featured'):featured.getparent().remove(featured)
 for related in cls(t,'related-block'):related.getparent().remove(related)
 for n in t.xpath('//script[@type="application/ld+json"]'):n.getparent().remove(n)
 head=t.xpath('//head')[0]
 schema={'@context':'https://schema.org','@type':'Article','headline':d['title'],'description':d['deck'],'inLanguage':lang,'datePublished':TIMES,'dateModified':TIMES,'author':{'@type':'Person','name':d['author'],'jobTitle':d['role'],'affiliation':{'@type':'Organization','name':{'ar':'الجامعة اللبنانية','en':'Lebanese University','fr':'Université libanaise'}[lang]}},'image':['https://sayd-magazine.com/'+IMAGE],'articleSection':DOOR[lang],'mainEntityOfPage':url(lang),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
 node=html.Element('script',{'type':'application/ld+json'});node.text=json.dumps(schema,ensure_ascii=False);head.append(node)
 for container in cls(t,'article-share')+cls(t,'share-bar'):
  for a in container.xpath('.//a[@href]'):
   h=a.get('href');h=re.sub(r'(?:https%3A%2F%2Fsayd-magazine.com%2F)[^&]+',quote(url(lang),safe=''),h);a.set('href',h)
 # Update ticker content in this new page from current approved homepage.
 ht=html.parse(str(DOCS/prefix/'index.html')).getroot()
 for dst,src in zip(cls(t,'ticker'),cls(ht,'ticker')):
  for n in list(dst):dst.remove(n)
  for n in src:
   a=copy.deepcopy(n);a.set('href','../../'+a.get('href'));dst.append(a)
 write_tree(DOCS/prefix/'posts'/slug/'index.html',t)
 md='---\n'+f'title: {json.dumps(d["title"],ensure_ascii=False)}\nslug: {slug}\ndate: {DATE}\nauthor: {json.dumps(d["author"],ensure_ascii=False)}\nauthor_role: {json.dumps(d["role"],ensure_ascii=False)}\ncategories: [صيد]\nfeatured: {IMAGE}\nsubtitle: {json.dumps(d["deck"],ensure_ascii=False)}\n---\n\n'+body(lang)+'\n'
 save(ROOT/'content'/('posts' if lang=='ar' else lang)/(slug+'.md'),md)
 row=f'<article class="post-row"><a class="thumb" href="../../posts/{quote(slug)}/index.html"><img src="{("../"*depth)+IMAGE}" alt="{esc.escape(d["caption"],quote=True)}" loading="lazy"></a><div class="body"><h2><a href="../../posts/{quote(slug)}/index.html">{esc.escape(d["title"])}</a></h2><div class="meta">{DATES[lang]}</div><p class="excerpt">{esc.escape(d["deck"])}</p></div></article>'
 for path in [DOCS/prefix/'category/صيد/index.html',DOCS/prefix/('articles' if lang=='ar' else 'stories')/'index.html']:
  s=path.read_text()
  s=re.sub(r'<article\b[^>]*>.*?</article>',lambda m:'' if quote(slug) in m[0] or '/posts/'+slug+'/' in m[0] else m[0],s,flags=re.S)
  match=re.search(r'<article\b[^>]*class="(?:post-row|card)"',s);assert match,path
  localrow=row.replace('../../posts/'+quote(slug)+'/index.html',os.path.relpath(DOCS/prefix/'posts'/slug/'index.html',path.parent)).replace(('../'*depth)+IMAGE,os.path.relpath(DOCS/IMAGE,path.parent))
  if 'class="card"' in match[0]:localrow=localrow.replace('class="post-row"','class="card"')
  save(path,s[:match.start()]+localrow+'\n'+s[match.start():])

f=ROOT/'content/en/pairs.json';pairs=json.loads(f.read_text());pairs['pairs'][AR]=EN;save(f,json.dumps(pairs,ensure_ascii=False,indent=2)+'\n')
f=ROOT/'content/homepage.json';c=json.loads(f.read_text())
if AR not in c['ia_slots']['important']:
 displaced=c['ia_slots']['important'][-1]
 c['ia_slots']['important']=[AR]+c['ia_slots']['important'][:3]
 c['latest']=[displaced]+c['latest'][:7]
c['featured']=[c['ia_slots']['main']]+c['ia_slots']['important'];c['ia_slots']['latest']=c['latest']
c['primary_door'][AR]='hunting';c['ticker_slugs']=[AR]+[s for s in c['ticker_slugs'] if s!=AR][:7]
c['demotion']='One lead, four side cards, eight Updates in date order. Hala El-Khatib’s autumn photography essay occupies the first side card by Nayef’s instruction on 3 October 2026. Bekaa moves to second; the displaced Sicily-to-Lebanon feature moves to newest Updates. Sayd returns leaves Updates but remains in the Hunting category and archive. Preserve all lower doors and TV selections; no article deletion.'
save(f,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
f=ROOT/'content/ticker.json';tick=json.loads(f.read_text());tick['items']=[{'slug':AR,'title':T['ar']['title']}]+[item for item in tick['items'] if item['slug']!=AR][:7];save(f,json.dumps(tick,ensure_ascii=False,indent=2)+'\n')
refresh()
for prefix in ['','en','fr']:PATHS.append((DOCS/prefix/'index.html').relative_to(ROOT).as_posix())
# Match new-article tickers to the final homepage order and titles.
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 path=DOCS/prefix/'posts'/(AR if lang=='ar' else EN)/'index.html';t=html.parse(str(path)).getroot();ht=html.parse(str(DOCS/prefix/'index.html')).getroot()
 for dst,src in zip(cls(t,'ticker'),cls(ht,'ticker')):
  for n in list(dst):dst.remove(n)
  for n in src:
   a=copy.deepcopy(n);a.set('href','../../'+a.get('href'));dst.append(a)
 write_tree(path,t)
f=DOCS/'sitemap.xml';s=f.read_text()
for lang in ['ar','en','fr']:
 u=url(lang)
 if u not in s:s=s.replace('</urlset>',f'<url><loc>{u}</loc><lastmod>{DATE}</lastmod></url>\n</urlset>')
save(f,s)
PATHS+=['scripts/publish_autumn_photography.py','content/features/autumn-photography-hala-khatib-20261003.json','notes/2026-10-03-hala-autumn-photography.md']
save(ROOT/'notes/2026-10-03-hala-autumn-photography.md','# Publication record\n\n- Nayef explicitly requested publication on 3 October 2026, first side card, by Dr. Hala El-Khatib, Lecturer at the Faculty of Information, Lebanese University.\n- Arabic text preserved from supplied DOCX; only the spelling إقتصادية → اقتصادية normalized. Full English/French translations reviewed against all 12 paragraphs and the original subheading.\n- Study checked against publisher: André F. Raine et al., Oryx, published online 11 February 2025; 1,844 photographs, 2011–2023, 212 species, 94% legally protected. DOI: https://doi.org/10.1017/S0030605324000814\n- Existing archived local photo: migrating storks over Istanbul, Turkey, 20 August 2010; Tema, Wikimedia Commons, CC BY-SA 3.0. Location stated in all captions; never labelled Lebanon.\n- Same image, date, Hunting door, author/role, first side slot and ticker in all three languages. The callout quotes the author’s conclusion; editorial record and internal discussion excluded from public copy.\n- Displaced Sicily feature moves to Updates; oldest Sayd returns stays available in category/archive. Protected lower doors and TV retained. No social posting authorized.\n')
(ROOT/'publication-hala-paths.json').write_text(json.dumps(sorted(set(PATHS)),ensure_ascii=False))
print('Prepared three mirrors; first side card; archive/category/ticker/sitemap updated.')
