#!/usr/bin/env python3
"""Publish the approved Shireen interview, website only."""
import copy, html as esc, json, os, re, sys
from pathlib import Path
from urllib.parse import quote
from lxml import html
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/'docs'
sys.path.insert(0,str(ROOT/'scripts'))
from refresh_homepage_doors import main as refresh
from seo_foundation import add_ga4
AR='شيرين-بو-رفول-مكافحة-الصيد-الجائر';EN='shireen-bou-rafoul-anti-poaching-interview'
T=json.loads((ROOT/'content/features/shireen-interview-20261017.json').read_text())
IMAGES=['media/uploads/2026/10/'+p['filename'] for p in T['photos']]
DATES={'ar':'17 تشرين الأول 2026','en':'17 October 2026','fr':'17 octobre 2026'}
DOOR={'ar':'مقابلات','en':'Interviews','fr':'Entretiens'}
AUTHOR={'ar':'صيد','en':'Sayd','fr':'Sayd'}
DATE='2026-10-17';TIME='2026-10-17T20:40:00+03:00'
def cls(t,c):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+c+' ")]')
def url(lang):return 'https://sayd-magazine.com/'+('' if lang=='ar' else lang+'/')+'posts/'+quote(AR if lang=='ar' else EN)+'/'
def save(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.suffix=='.html':s=add_ga4(s)
 p.write_text(s)
def figure(lang,i):
 p=T['photos'][i];prefix='../../' if lang=='ar' else '../../../'
 return '<figure style="max-width:680px;margin:26px auto"><img src="'+prefix+IMAGES[i]+'" alt="'+esc.escape(p['alt'][lang],quote=True)+'" decoding="async" style="display:block;width:100%;height:auto"><figcaption>'+esc.escape(p['caption'][lang])+'</figcaption></figure>'
def body(lang):
 d=T[lang];out=figure(lang,0)+'<p><strong>'+esc.escape(d['deck'])+'</strong></p>'
 for index,para in enumerate(d['paragraphs']):
  for image in d['before_images'].get(str(index),[]):out+=figure(lang,image)
  tag='h2' if index in d['headings'] else 'p'
  out+='<'+tag+'>'+esc.escape(para)+'</'+tag+'>'
  for image in d['after_images'].get(str(index),[]):out+=figure(lang,image)
 out+='<p><small>'+esc.escape(T['global_credit'][lang])+'</small></p>'
 names={'ar':'اقرأ أيضًا','en':'Read also','fr':'À lire aussi'}
 related=[]
 for root,slug,label in d['related']:
  path=DOCS/root/'posts'/slug/'index.html';tree=html.parse(str(path))
  title=tree.xpath('//h1')[0].text_content()+label
  target=DOCS/('' if lang=='ar' else lang)/'posts'/(AR if lang=='ar' else EN)
  image=tree.xpath('//meta[@property="og:image"]/@content')[0]
  related.append('<a class="reading-card" href="'+esc.escape(os.path.relpath(path,target),quote=True)+'"><img src="'+esc.escape(image,quote=True)+'" alt="" loading="lazy"><span>'+esc.escape(title)+'</span></a>')
 return out+'<section class="article-more shireen-related"><h2>'+names[lang]+'</h2><div class="reading-grid">'+''.join(related)+'</div></section>'
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 d=T[lang];slug=AR if lang=='ar' else EN;depth=2 if lang=='ar' else 3
 old='ألكسندرا-cabs-الصيد-غير-القانوني' if lang=='ar' else 'alexandra-cabs-illegal-hunting-interview'
 t=html.parse(str(DOCS/prefix/'posts'/old/'index.html')).getroot()
 for existing in cls(t,'article-more'):existing.getparent().remove(existing)
 for n in t.xpath('//title'):n.text=d['title']+' — '+('مجلة صيد' if lang=='ar' else 'Sayd Magazine')
 for n in t.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):n.set('content',d['deck'])
 for n in t.xpath('//meta[@property="og:title" or @name="twitter:title"]'):n.set('content',d['title'])
 for n in t.xpath('//meta[@property="og:url"]'):n.set('content',url(lang))
 for n in t.xpath('//meta[@property="og:image" or @name="twitter:image"]'):n.set('content','https://sayd-magazine.com/'+IMAGES[0])
 for n in t.xpath('//link[@rel="canonical"]'):n.set('href',url(lang))
 for n in t.xpath('//link[@rel="alternate"]'):n.set('href',url(n.get('hreflang') if n.get('hreflang') in ('ar','en','fr') else 'ar'))
 for a in cls(t,'lang-switch')[0].xpath('.//a'):
  target=a.get('lang');a.set('href','../'*depth+('' if target=='ar' else target+'/')+'posts/'+quote(AR if target=='ar' else EN)+'/index.html')
 header=cls(t,'article-header')[0];header.xpath('.//h1')[0].text=d['title']
 for node in cls(header,'article-updated'):node.getparent().remove(node)
 metas=cls(header,'meta-item');metas[0].text=DATES[lang];metas[1].text=AUTHOR[lang]
 for n in cls(t,'author-role'):n.getparent().remove(n)
 for a in header.xpath('.//a[contains(@href,"category/")]'):a.set('href','../../category/'+quote('مقابلات')+'/index.html');a.text=DOOR[lang]
 for a in cls(t,'breadcrumb')[0].xpath('.//a[contains(@href,"category/")]'):a.set('href','../../category/'+quote('مقابلات')+'/index.html');a.text=DOOR[lang]
 content=cls(t,'article-content')[0]
 for n in list(content):content.remove(n)
 content.text=None
 for n in html.fragments_fromstring(body(lang)):content.append(n)
 for name in ['article-featured','related-block','article-kicker']:
  for n in cls(t,name):n.getparent().remove(n)
 for n in t.xpath('//script[@type="application/ld+json"]'):n.getparent().remove(n)
 schema={'@context':'https://schema.org','@type':'NewsArticle','headline':d['title'],'description':d['deck'],'inLanguage':lang,'datePublished':TIME,'dateModified':TIME,'author':{'@type':'Organization','name':'Sayd Magazine'},'image':['https://sayd-magazine.com/'+i for i in IMAGES],'articleSection':DOOR[lang],'mainEntityOfPage':url(lang),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
 node=html.Element('script',{'type':'application/ld+json'});node.text=json.dumps(schema,ensure_ascii=False);t.xpath('//head')[0].append(node)
 for container in cls(t,'article-share')+cls(t,'share-bar'):
  for a in container.xpath('.//a[@href]'):a.set('href',re.sub(r'(?:https%3A%2F%2Fsayd-magazine.com%2F)[^&]+',quote(url(lang),safe=''),a.get('href')))
 save(DOCS/prefix/'posts'/slug/'index.html','<!DOCTYPE html>\n'+html.tostring(t,encoding='unicode',method='html'))
 save(ROOT/'content'/('posts' if lang=='ar' else lang)/(slug+'.md'),'---\n'+f'title: {json.dumps(d["title"],ensure_ascii=False)}\nslug: {slug}\ndate: {DATE}\nauthor: {json.dumps(AUTHOR[lang],ensure_ascii=False)}\ncategories: [مقابلات]\nfeatured: {IMAGES[0]}\nsubtitle: {json.dumps(d["deck"],ensure_ascii=False)}\n---\n\n'+body(lang)+'\n')
 for path in [DOCS/prefix/('articles' if lang=='ar' else 'stories')/'index.html']:
  s=path.read_text();s=re.sub(r'<article\b[^>]*>.*?</article>',lambda m:'' if quote(slug) in m[0] or '/posts/'+slug+'/' in m[0] else m[0],s,flags=re.S)
  m=re.search(r'<article\b[^>]*class="(?:post-row|card)"',s);assert m,path
  href=os.path.relpath(DOCS/prefix/'posts'/slug/'index.html',path.parent);image=os.path.relpath(DOCS/IMAGES[0],path.parent)
  row=f'<article class="post-row"><a class="thumb" href="{href}"><img src="{image}" alt="{esc.escape(T["photos"][0]["caption"][lang],quote=True)}" loading="lazy"></a><div class="body"><h2><a href="{href}">{esc.escape(d["title"])}</a></h2><div class="meta">{DATES[lang]}</div><p class="excerpt">{esc.escape(d["deck"])}</p></div></article>'
  if 'class="card"' in m[0]:row=row.replace('class="post-row"','class="card"')
  save(path,s[:m.start()]+row+'\n'+s[m.start():])
p=ROOT/'content/en/pairs.json';c=json.loads(p.read_text());c['pairs'][AR]=EN;save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')

p=ROOT/'content/homepage.json';c=json.loads(p.read_text())
previous_side=c['ia_slots']['important'].copy()
previous_main=c['ia_slots']['main']
c['ia_slots']['main']=AR
if previous_main!=AR:c['ia_slots']['important']=[previous_main]+[x for x in previous_side if x not in (AR,previous_main)][:3]
c['featured']=[AR]+c['ia_slots']['important']
from homepage_demotion import demote_side_cards
demote_side_cards(c,previous_side)
c['primary_door'][AR]='interviews'
c['card_image_overrides'][AR]={'image':IMAGES[0],'position':'50% 30%','alt':{l:T['photos'][0]['alt'][l] for l in ('ar','en','fr')}}
save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/interviews.json';registry=json.loads(p.read_text())
registry['entries']=[{'slug':AR,'published_at':DATE,'reviewed_as':'interview','languages':{'ar':AR,'en':EN,'fr':EN}}]+[r for r in registry['entries'] if r['slug']!=AR]
save(p,json.dumps(registry,ensure_ascii=False,indent=2)+'\n')

tickers={'ar':'شيرين بو رفول لـ«صيد»: أحبّ الصيد، لكنني أختار مكافحة المخالفات وإنقاذ الطيور.','en':'Shireen Bou Rafoul tells Sayd: I love hunting, but I choose to fight violations and rescue birds.','fr':'Shireen Bou Rafoul à Sayd : j’aime la chasse, mais je choisis de lutter contre les infractions et de sauver les oiseaux.'}
p=ROOT/'content/homepage.json';c=json.loads(p.read_text())
c['ticker_entries']=[{'slug':AR,'titles':tickers}]+[x for x in c['ticker_entries'] if x['slug']!=AR]
c['ticker_slugs']=[x['slug'] for x in c['ticker_entries']]
save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
 path=DOCS/prefix/'index.html';original=path.read_text();t=html.fromstring(original);lead=cls(t,'feature-lead')[0]
 lead.set('data-hero','shireen')
 cls(lead,'body')[0].set('style','top:auto;bottom:0;padding:18px;background:linear-gradient(0deg,rgba(14,27,24,.95),rgba(14,27,24,.65) 75%,transparent)')
 for a in lead.xpath('.//a'):a.set('href','posts/'+quote(AR if lang=='ar' else EN)+'/index.html')
 lead.xpath('.//h2/a')[0].text=T[lang]['title']
 image=lead.xpath('.//img')[0];image.set('src',os.path.relpath(DOCS/IMAGES[0],path.parent));image.set('alt',T['photos'][0]['alt'][lang]);image.set('style','object-fit:cover;object-position:50% 30%')
 cls(lead,'meta')[0].text=DATES[lang]
 for kicker in cls(lead,'migration-kicker'):kicker.text=DOOR[lang]
 save(path,re.sub(r'<article class="card overlay feature-lead"[^>]*>.*?</article>',html.tostring(lead,encoding='unicode',method='html'),original,count=1,flags=re.S))
 page=path.read_text();page=re.sub(r'<style id="shireen-lead-style">.*?</style>','',page,flags=re.S)
 save(path,page.replace('</head>','<style id="shireen-lead-style">'+'.feature-lead[data-hero="shireen"] h2{font-size:33px!important;line-height:1.25!important}@media(min-width:901px){.featured-mosaic:has([data-hero="shireen"]){grid-template-columns:minmax(0,1.1fr) minmax(0,1fr)!important}.featured-mosaic>.feature-lead[data-hero="shireen"]{height:620px!important;max-height:620px!important}.featured-mosaic:has([data-hero="shireen"]) .feature-side{height:620px!important}.feature-lead[data-hero="shireen"] img{width:100%!important;height:100%!important;object-fit:cover!important;object-position:50% 30%!important}}@media(max-width:600px){.feature-lead[data-hero="shireen"],.feature-lead[data-hero="shireen"] .thumb{min-height:420px!important;height:420px!important}.feature-lead[data-hero="shireen"] img{width:100%!important;height:420px!important}.feature-lead[data-hero="shireen"] h2{font-size:24px!important;line-height:1.25!important}}'+'</style></head>',1))

sitemap_before=(DOCS/'sitemap.xml').read_text()
old_short_pages={p:p.read_bytes() for p in (DOCS/'s').glob('*/index.html')}
short_before=json.loads((DOCS/'s/links.json').read_text())
refresh()
for p,data in old_short_pages.items():p.write_bytes(data)
short_after=json.loads((DOCS/'s/links.json').read_text())
for target,short in short_after.items():
 if target not in short_before:
  if AR in target or EN in target:short_before[target]=short
  else:(DOCS/short.strip('/')/'index.html').unlink()
save(DOCS/'s/links.json',json.dumps(dict(sorted(short_before.items())),ensure_ascii=False,indent=2)+'\n')
p=DOCS/'sitemap.xml';s=sitemap_before
for l in ('ar','en','fr'):
 if url(l) not in s:s=s.replace('</urlset>',f'<url><loc>{url(l)}</loc><lastmod>{DATE}</lastmod></url>\n</urlset>')
save(p,s)

from seo_foundation import apply_html,load_twins
for lang in ('ar','en','fr'):
 homepath=DOCS/('' if lang=='ar' else lang)/'index.html'
 save(homepath,apply_html(homepath.read_text(),homepath,DOCS,homepath.relative_to(DOCS),load_twins(DOCS)))
for lang in ('ar','en','fr'):
 path=DOCS/('' if lang=='ar' else lang)/'posts'/(AR if lang=='ar' else EN)/'index.html'
 save(path,apply_html(path.read_text(),path,DOCS,path.relative_to(DOCS),load_twins(DOCS)))
from rollout_mobile_nav_heritage_20261015 import nav_replace
for lang in ('ar','en','fr'):
 page=DOCS/('' if lang=='ar' else lang)/'posts'/(AR if lang=='ar' else EN)/'index.html'
 save(page,nav_replace(page.read_text(),page)[0])
import hashlib
p=ROOT/'audit/image-catalog/manifest/2026-01.tsv';rows=p.read_text().splitlines()
for image in IMAGES:
 data=(DOCS/image).read_bytes();key='docs/'+image
 row=key+'\t'+hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()+'\t'+str(len(data))
 rows=[x for x in rows if not x.startswith(key+'\t')]+[row]
save(p,'\n'.join(rows[:1]+sorted(rows[1:],key=lambda x:x.split('\t')[0]))+'\n')
print('Prepared approved Shireen interview in three mirrors and main lead; previous lead demoted.')
