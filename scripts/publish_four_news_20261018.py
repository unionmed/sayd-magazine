#!/usr/bin/env python3
"""Render the four owner-approved 18 October packages; no social publication."""
import hashlib,html as esc,json,os,re
from pathlib import Path
from urllib.parse import quote,unquote
from lxml import html
import seo_foundation as seo
from refresh_related_reading import image_markup,image_size
from refresh_homepage_doors import main as refresh,DOORS
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs';LANGS=('ar','en','fr');DATE='2026-10-18'
DATES={'ar':'18 تشرين الأول 2026','en':'18 October 2026','fr':'18 octobre 2026'}
LABELS={d[0]:dict(zip(LANGS,d[1:4])) for d in DOORS};LABELS['equestrian']=LABELS['hunting']
A=json.loads((ROOT/'content/features/four-news-20261018.json').read_text())['articles']
PAIRS=json.loads((ROOT/'content/en/pairs.json').read_text())
def cls(t,c):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+c+' ")]')
def save(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def page(a,l):return DOCS/('' if l=='ar' else l)/'posts'/a['slugs'][l]/'index.html'
def url(a,l):return 'https://sayd-magazine.com/'+('' if l=='ar' else l+'/')+'posts/'+quote(a['slugs'][l])+'/'
def body(a,l):
 d=a['translations'][l];p=a['photos'][0];im=DOCS/p['path'];w,h=image_size(im);src=os.path.relpath(im,page(a,l).parent)
 out='<figure><img src="'+src+'" alt="'+esc.escape(p['alt'][l],quote=True)+'" width="'+str(w)+'" height="'+str(h)+'" decoding="async" style="display:block;width:100%;height:auto"><figcaption>'+esc.escape(p['caption'][l])+'</figcaption></figure>'
 out+='<p class="excerpt">'+esc.escape(d['deck'])+'</p>'
 def para(s):return '<p>'+esc.escape(s).replace('Gavia immer','<i>Gavia immer</i>')+'</p>'
 out+=''.join(map(para,d['intro']))
 for title,paras in d['sections']:out+='<h2>'+esc.escape(title)+'</h2>'+''.join(map(para,paras))
 out+='<p>'+{'ar':'المصادر','en':'Sources','fr':'Sources'}[l]+': '+'؛ '.join('<a href="'+esc.escape(s['url'],quote=True)+'">'+esc.escape(s.get('label',s.get('title','Source')))+'</a>' for s in d['sources'])+'</p>'
 out+='<p class="photo-credit"><small><a href="'+esc.escape(p['source_url'],quote=True)+'">'+esc.escape(p['credit'][l])+'</a>'
 if p.get('license_url'):out+=' · <a href="'+p['license_url']+'">'+p['license']+'</a>'
 out+='</small></p><section class="article-more"><h2>'+{'ar':'اقرأ أيضًا','en':'Read also','fr':'À lire aussi'}[l]+'</h2><div class="reading-grid">'
 for ar in a['related']:
  slug=ar if l=='ar' else PAIRS['pairs'][ar];slug=seo.FR_SLUG_BY_EN.get(slug,slug) if l=='fr' else slug
  target=DOCS/('' if l=='ar' else l)/'posts'/slug/'index.html';tree=html.fromstring(target.read_text());title=tree.xpath('//h1')[0].text_content();href=quote(os.path.relpath(target,page(a,l).parent),safe='/')
  out+='<a class="reading-card" href="'+href+'">'+image_markup(page(a,l),href,title)+'<span>'+esc.escape(title)+'</span></a>'
 return out+'</div></section>'
def render(a,l):
 d=a['translations'][l];p=a['photos'][0];slug='الرياض-تستعيد-صهيلها-موسم-السباقات-2026' if l=='ar' else 'riyadh-racing-season-2026-2027-begins';template=DOCS/('' if l=='ar' else l)/'posts'/slug/'index.html';t=html.fromstring(template.read_text())
 for n in t.xpath('//title'):n.text=d.get('seo_title',d['title'])+' — '+('مجلة صيد' if l=='ar' else 'Sayd Magazine')
 for n in t.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):n.set('content',d['meta_description'])
 for n in t.xpath('//meta[@property="og:title" or @name="twitter:title"]'):n.set('content',d['title'])
 for n in t.xpath('//meta[@property="og:image" or @name="twitter:image"]'):n.set('content','https://sayd-magazine.com/'+p['path'])
 for n in t.xpath('//meta[@property="og:url"]'):n.set('content',url(a,l))
 for n in t.xpath('//link[@rel="canonical"]'):n.set('href',url(a,l))
 for n in t.xpath('//link[@rel="alternate"]'):n.set('href',url(a,n.get('hreflang') if n.get('hreflang') in LANGS else 'ar'))
 for n in cls(t,'lang-switch')[0].xpath('.//a'):n.set('href',url(a,n.get('lang')))
 header=cls(t,'article-header')[0];header.xpath('.//h1')[0].text=d['title'];metas=cls(header,'meta-item');metas[0].text=DATES[l];metas[1].text='صيد' if l=='ar' else 'Sayd'
 for n in t.xpath('//a[contains(@href,"category/")]'):
  if n in header.xpath('.//a') or any(n in b.xpath('.//a') for b in cls(t,'breadcrumb')):n.set('href','../../category/'+quote(a['category'])+'/index.html');n.text=LABELS[a['door']][l]
 content=cls(t,'article-content')[0]
 for n in list(content):content.remove(n)
 content.text=None
 for n in html.fragments_fromstring(body(a,l)):content.append(n)
 for name in ['article-featured','related-block','article-kicker','author-role']:
  for n in cls(t,name):n.getparent().remove(n)
 for n in cls(t,'article-more'):
  if content not in n.iterancestors():n.getparent().remove(n)
 for n in t.xpath('//script[@type="application/ld+json"]'):n.getparent().remove(n)
 schema={'@context':'https://schema.org','@type':'NewsArticle','headline':d['title'],'description':d['meta_description'],'inLanguage':l,'datePublished':DATE,'dateModified':DATE,'author':{'@type':'Organization','name':'Sayd Magazine'},'image':['https://sayd-magazine.com/'+p['path']],'articleSection':LABELS[a['door']][l],'mainEntityOfPage':url(a,l),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
 node=html.Element('script',{'type':'application/ld+json'});node.text=json.dumps(schema,ensure_ascii=False);t.xpath('//head')[0].append(node)
 for n in cls(t,'article-share')+cls(t,'share-bar'):
  for link in n.xpath('.//a[@href]'):link.set('href',re.sub(r'https%3A%2F%2Fsayd-magazine.com%2F[^&]+',quote(url(a,l),safe=''),link.get('href')))
 save(page(a,l),seo.add_ga4('<!DOCTYPE html>\n'+html.tostring(t,encoding='unicode',method='html')))
 front={'title':d['title'],'slug':a['slugs'][l],'date':DATE,'author':'صيد' if l=='ar' else 'Sayd','categories':[LABELS[a['door']][l]],'featured':p['path'],'subtitle':d['deck']}
 save(ROOT/'content'/('posts' if l=='ar' else l)/(a['slugs'][l]+'.md'),'---\n'+''.join(k+': '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in front.items())+'---\n\n'+body(a,l)+'\n')
def listing(a,l,path):
 text=path.read_text();slug=a['slugs'][l];text=re.sub(r'<article\b[^>]*>.*?</article>',lambda m:'' if '/posts/'+slug+'/' in unquote(m[0]) else m[0],text,flags=re.S);m=re.search(r'<article\b[^>]*class="(?:post-row|card)[^"]*"',text);assert m,path
 style='post-row' if 'post-row' in m[0] else 'card overlay' if 'overlay' in m[0] else 'card';d=a['translations'][l];p=a['photos'][0];href=quote(os.path.relpath(page(a,l),path.parent),safe='/');im=os.path.relpath(DOCS/p['path'],path.parent)
 row='<article class="'+style+'"><a class="thumb" href="'+href+'"><img src="'+im+'" alt="'+esc.escape(p['alt'][l],quote=True)+'" loading="lazy"></a><div class="body"><h2><a href="'+href+'">'+esc.escape(d['title'])+'</a></h2><div class="meta">'+DATES[l]+'</div><p class="excerpt">'+esc.escape(d['deck'])+'</p></div></article>\n'
 save(path,text[:m.start()]+row+text[m.start():])
def run():
 for a in A:
  assert a['publication_ready'] and set(a['translations'])==set(LANGS)
  p=a['photos'][0];data=(DOCS/p['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==p['sha256'];assert p['approved_for_article'];assert image_size(DOCS/p['path'])[0]>=600
  PAIRS['pairs'][a['slugs']['ar']]=a['slugs']['en']
 save(ROOT/'content/en/pairs.json',json.dumps(PAIRS,ensure_ascii=False,indent=2)+'\n')
 for a in A:
  for l in LANGS:render(a,l)
 twins=seo.load_twins(DOCS)
 for a in A:
  for l in LANGS:
   p=page(a,l);save(p,seo.apply_html(p.read_text(),p,DOCS,p.relative_to(DOCS),twins))
 for a in reversed(A):
  for l in LANGS:
   base=DOCS/('' if l=='ar' else l)
   for p in [base/'category'/a['category']/'index.html',base/('articles' if l=='ar' else 'stories')/'index.html']:listing(a,l,p)
 c=json.loads((ROOT/'content/homepage.json').read_text());news=[a for a in A if a['placement']=='news'];oldlatest=c['ia_slots']['latest']
 newslugs=[a['slugs']['ar'] for a in news];latest=(newslugs+[x for x in oldlatest if x not in newslugs])[:8];c['ia_slots']['latest']=latest;c['latest']=latest
 for a in A:
  ar=a['slugs']['ar'];p=a['photos'][0];c['primary_door'][ar]=a['door'];c['card_image_overrides'][ar]={'image':p['path'],'position':'50% 50%','alt':p['alt']}
 c['ticker_entries']=[{'slug':a['slugs']['ar'],'titles':{l:a['translations'][l]['ticker'] for l in LANGS}} for a in news]+[x for x in c['ticker_entries'] if x['slug'] not in newslugs]
 top=set([c['ia_slots']['main']]+c['ia_slots']['important']+latest)
 for d in c['ia_door_sections']:
  if d['door'] in ['gear','wildlife','science']:
   additions=[a['slugs']['ar'] for a in A if a['door']==d['door'] and a['placement']=='category']+[s for s in oldlatest if s not in latest and c['primary_door'].get(s)==d['door']]
   d['slugs']=list(dict.fromkeys(s for s in additions+d['slugs'] if s not in top))[:4]
   for name in { 'gear':['رماية وعتاد','Shooting & Gear'],'wildlife':['الحياة البرية والتخييم','Wildlife & Camping'],'science':['علوم واكتشافات','Science & Discoveries']}[d['door']]:c['desk_slugs'][name]=d['slugs'] if not name.isascii() else [PAIRS['pairs'][s] for s in d['slugs']]
 save(ROOT/'content/homepage.json',json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 short=json.loads((DOCS/'s/links.json').read_text());stubs={p:p.read_bytes() for p in (DOCS/'s').glob('*/index.html')};sitemap=(DOCS/'sitemap.xml').read_text();refresh()
 after=json.loads((DOCS/'s/links.json').read_text());slugs={s for a in A for s in a['slugs'].values()}
 for target,value in after.items():
  if target not in short:
   if any(s in unquote(target) for s in slugs):short[target]=value
   else:(DOCS/value.strip('/')/'index.html').unlink()
 for p,data in stubs.items():p.write_bytes(data)
 save(DOCS/'s/links.json',json.dumps(dict(sorted(short.items())),ensure_ascii=False,indent=2)+'\n')
 for a in A:
  for l in LANGS:
   if '<loc>'+url(a,l)+'</loc>' not in sitemap:sitemap=sitemap.replace('</urlset>','<url><loc>'+url(a,l)+'</loc><lastmod>'+DATE+'</lastmod></url>\n</urlset>')
 save(DOCS/'sitemap.xml',sitemap)
 p=ROOT/'audit/image-catalog/manifest/2026-01.tsv';rows=p.read_text().splitlines()
 for a in A:
  key='docs/'+a['photos'][0]['path'];data=(ROOT/key).read_bytes();row=key+'\t'+hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()+'\t'+str(len(data));rows=[x for x in rows if not x.startswith(key+'\t')]+[row]
 save(p,'\n'.join(rows[:1]+sorted(rows[1:],key=lambda x:x.split('\t')[0]))+'\n')
 print('Four complete AR/EN/FR packages rendered. Three news stories in Updates/ticker; loon Science only.')
if __name__=='__main__':run()
