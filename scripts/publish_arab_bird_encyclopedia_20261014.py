#!/usr/bin/env python3
"""Publish the reviewed Arab-world bird encyclopedia package, without homepage/ticker changes.

All prose, photographs, dates and localized metadata live in the corresponding
content/features JSON. Regenerates only this package and its category/archive
entries. The older bee-eater updater delegates here to avoid restoring old copy.
"""
import copy, hashlib, html as esc, json, os, re
from pathlib import Path
from urllib.parse import quote, unquote
from lxml import html
import article_dates
import seo_foundation as seo

ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/'docs'
SOURCE=ROOT/'content/features/arab-bird-encyclopedia-20261014.json'
LANGS=('ar','en','fr')
CATEGORY='موسوعة-الطيور'
LABEL={'ar':'اقرأ أيضًا','en':'Read also','fr':'À lire aussi'}
CATS={'ar':'موسوعة الطيور','en':'Bird Encyclopedia','fr':'Encyclopédie des oiseaux'}
DATES={'ar':'14 تشرين الأول 2026','en':'14 October 2026','fr':'14 octobre 2026'}

def package():return json.loads(SOURCE.read_text())['articles']
def cls(t,c):return t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+c+' ")]')
def save(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def relpage(a,l):return Path('' if l=='ar' else l)/'posts'/a['slugs'][l]/'index.html'
def url(a,l):return 'https://sayd-magazine.com/'+quote(relpage(a,l).parent.as_posix(),safe='/')+'/'
def write(t):return '<!DOCTYPE html>\n'+html.tostring(t,encoding='unicode',method='html')
def replace_one(pattern,value,text):
 result,count=re.subn(pattern,lambda m:value,text,count=1,flags=re.S)
 assert count==1,pattern
 return result

def related(a,l,articles):
 # All three new entries have the same date; their explicit publication times
 # establish a consistent order in every mirror. Exclude the article itself.
 candidates=sorted((x for x in articles if x['new'] and x['key']!=a['key']),key=lambda x:x['published_at'],reverse=True)[:2]
 assert len(candidates)==2
 return '<section class="related-block"><div class="section-head"><h2>'+LABEL[l]+'</h2></div><div class="related-grid">'+''.join(
 '<article class="card"><a class="thumb" href="../'+x['slugs'][l]+'/index.html"><img src="'+('../'*(2 if l=='ar' else 3))+x['image']+'" alt="'+esc.escape(x['caption'][l],quote=True)+'" loading="lazy"></a><div class="body"><h3><a href="../'+x['slugs'][l]+'/index.html">'+esc.escape(x['languages'][l]['title'])+'</a></h3><div class="meta">'+DATES[l]+'</div></div></article>' for x in candidates)+'</div></section>'

def article_body(a,l):
 d=a['languages'][l]; depth=2 if l=='ar' else 3
 fig='<figure><img src="'+('../'*depth)+a['image']+'" alt="'+esc.escape(d['alt'],quote=True)+'" decoding="async" style="display:block;width:100%;height:auto"><figcaption>'+esc.escape(a['caption'][l])+'</figcaption></figure>'
 body=fig+'\n'+d['body_html']
 c=a.get('photo_credit')
 if c:
  lab={'ar':'حقوق الصورة','en':'Photo credit','fr':'Crédit photo'}[l]
  body+='\n<p class="photo-credits"><small>'+lab+': '+esc.escape(c['name'])+' — <a href="'+esc.escape(c['source_url'],quote=True)+'">Wikimedia Commons</a> — <a href="'+c['license_url']+'" rel="license">'+c['license']+'</a>.</small></p>'
 return body

def render_article(a,l,articles):
 target=DOCS/relpage(a,l)
 template=target if target.exists() else DOCS/('' if l=='ar' else l)/'posts'/('طائر-الوروار-الأوروبي' if l=='ar' else 'european-bee-eater')/'index.html'
 text=template.read_text();d=a['languages'][l]
 # Preserve the existing site chrome; replace only controlled article regions.
 text=replace_one(r'<title>.*?</title>','<title>'+esc.escape(d['title'])+' | '+('صيد' if l=='ar' else 'Sayd Magazine')+'</title>',text)
 text=replace_one(r'<meta name="description" content="[^"]*">','<meta name="description" content="'+esc.escape(d['description'],quote=True)+'">',text)
 header=re.search(r'<header class="article-header">.*?</header>',text,re.S)[0]
 header=replace_one(r'<h1>.*?</h1>','<h1>'+esc.escape(d['title'])+'</h1>',header)
 if a['new']:
  header=replace_one(r'<div class="article-meta">.*?</div>','<div class="article-meta"><span class="meta-item">'+DATES[l]+'</span><span class="meta-item">'+('صيد' if l=='ar' else 'Sayd')+'</span></div>',header)
 else:
  header=article_dates.patch(header,a['updated'],l)
  if a.get('author'):
   header=replace_one(r'<span class="meta-item">[^<]*</span></div>','<span class="meta-item">'+esc.escape(a['author'])+'</span></div>',header)
 text=replace_one(r'<header class="article-header">.*?</header>',header,text)
 text=re.sub(r'<figure class="article-featured".*?</figure>','',text,flags=re.S)
 text=replace_one(r'<article class="article-content">.*?</article>','<article class="article-content">\n'+article_body(a,l)+'\n</article>',text)
 text=re.sub(r'<section class="related-block">.*?</section>','',text,flags=re.S)
 # Anchor the related block to this article, never an earlier chrome card.
 text=replace_one(r'(<article class="article-content">.*?</article>)',re.search(r'<article class="article-content">.*?</article>',text,re.S)[0]+'\n'+related(a,l,articles),text)
 nav='\n'.join('<a href="/'+('' if x=='ar' else x+'/')+'posts/'+quote(a['slugs'][x])+'/index.html" lang="'+x+'" hreflang="'+x+'"'+(' class="is-current" aria-current="page"' if x==l else '')+'>'+label+'</a>' for x,label in zip(LANGS,['العربية','English','Français']))
 text=re.sub(r'(<nav class="lang-switch"[^>]*>).*?</nav>',lambda m:m[1]+nav+'</nav>',text,count=1,flags=re.S)
 # Replace source article sharing targets only; article chrome links remain intact.
 oldslug='طائر-الوروار-الأوروبي' if l=='ar' else 'european-bee-eater'
 oldurl='https://sayd-magazine.com/'+('' if l=='ar' else l+'/')+'posts/'+quote(oldslug)+'/'
 text=text.replace(quote(oldurl,safe=''),quote(url(a,l),safe=''))
 text=seo.SEO_BLOCK_RE.sub('',text)
 text=re.sub(r'<script type="application/ld\+json">.*?</script>','',text,flags=re.S)
 # Avoid double encoding inherited Arabic category breadcrumb paths.
 text=text.replace('category/'+quote(CATEGORY)+'/','category/'+CATEGORY+'/')
 schema={'@context':'https://schema.org','@type':'Article','headline':d['title'],'description':d['description'],'inLanguage':l,'datePublished':a['published_at'],'dateModified':a.get('updated',a['date']),'author':{'@type':'Person','name':a['author']} if a.get('author') else {'@type':'Organization','name':'Sayd Magazine'},'image':['https://sayd-magazine.com/'+a['image']],'articleSection':CATS[l],'mainEntityOfPage':url(a,l),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
 text=text.replace('</head>','<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False)+'</script>\n</head>')
 # Keep the existing analytics block exactly as inherited, without any live hit.
 save(target,text)
 return target

def source_file(a,l):
 slug=a['slugs'][l];p=ROOT/'content'/('posts' if l=='ar' else l)/(slug+'.md')
 if not a['new'] and p.exists() and p.read_text().startswith('---'):
  old=p.read_text();front=old.split('---',2)[1];front=re.sub(r'(?m)^featured:.*$', 'featured: '+a['image'],front)
 else:front='\n'+f'title: {json.dumps(a["languages"][l]["title"],ensure_ascii=False)}\nslug: {slug}\ndate: {a["date"]}\nauthor: {"صيد" if l=="ar" else "Sayd"}\ncategories: [موسوعة الطيور]\nfeatured: {a["image"]}\n'
 if a.get('author'):front=re.sub(r'(?m)^author:.*$', 'author: '+a['author'],front)
 save(p,'---'+front+'---\n\n'+article_body(a,l)+'\n')

def listings(articles):
 for l in LANGS:
  prefix='' if l=='ar' else l
  for path in [DOCS/prefix/'category'/CATEGORY/'index.html',DOCS/prefix/('articles' if l=='ar' else 'stories')/'index.html']:
   text=path.read_text()
   new=[a for a in articles if a['new']]
   slugs={a['slugs'][l] for a in new}
   text=re.sub(r'<article\b[^>]*>.*?</article>',lambda m:'' if any('/posts/'+s+'/' in unquote(m[0]) for s in slugs) else m[0],text,flags=re.S)
   first=re.search(r'<article\b[^>]*class="(?:post-row|card)[^"]*"',text);assert first,path
   style='post-row' if 'post-row' in first[0] else 'card overlay' if 'overlay' in first[0] else 'card'
   rows=[]
   for a in sorted(new,key=lambda a:a['published_at'],reverse=True):
    d=a['languages'][l];href=os.path.relpath(DOCS/relpage(a,l),path.parent);im=os.path.relpath(DOCS/a['image'],path.parent)
    rows.append('<article class="'+style+'"><a class="thumb" href="'+quote(href,safe='/')+'"><img src="'+im+'" alt="'+esc.escape(a['caption'][l],quote=True)+'" loading="lazy"></a><div class="body"><h2><a href="'+quote(href,safe='/')+'">'+esc.escape(d['title'])+'</a></h2><div class="meta">'+DATES[l]+'</div><p class="excerpt">'+esc.escape(d['description'])+'</p></div></article>')
   save(path,re.sub(r'\n[ \t]*\n+', '\n', text[:first.start()]+'\n'.join(rows)+'\n'+text[first.start():]))

def translation_sources(articles):
 from build_fr_edition import source_blocks
 path=ROOT/'content/fr/edition-2026.json';manifest=json.loads(path.read_text())
 for a in articles:
  trees={l:html.fromstring('<article>'+article_body(a,l)+'</article>') for l in ['en','fr']}
  en=source_blocks(trees['en']);fr=source_blocks(trees['fr'])
  assert len(en)==len(fr),(a['key'],len(en),len(fr))
  assert [x.tag for x in en]==[x.tag for x in fr],a['key']
  def inner(n):return (esc.escape(n.text) if n.text else '')+''.join(html.tostring(c,encoding='unicode',method='html') for c in n)
  data={'title':a['languages']['fr']['title'],'figures':[inner(n) for n in trees['fr'].xpath('./figure/figcaption')],'blocks':[inner(n) for n in fr]}
  save(ROOT/'content/fr/segments'/(a['slugs']['fr']+'.json'),json.dumps(data,ensure_ascii=False,indent=2)+'\n')
  if a['new'] and not any(x['slug']==a['slugs']['en'] for x in manifest['articles']):
   manifest['articles'].append({'slug':a['slugs']['en'],'english_title':a['languages']['en']['title'],'date':DATES['en'],'category':'Bird Encyclopedia','english_url':'/en/posts/'+a['slugs']['en']+'/'})
 save(path,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')

def sharing_links(articles):
 # Reuse the site's canonical short-link generator on only this package. An
 # isolated temporary tree prevents rewriting unrelated historical aliases.
 import tempfile,shutil
 from short_links import generate
 with tempfile.TemporaryDirectory() as tmp:
  out=Path(tmp)/'docs';out.mkdir()
  (out/'s').mkdir();shutil.copy2(DOCS/'s/links.json',out/'s/links.json')
  for a in articles:
   if not a['new']:continue
   for l in LANGS:
    p=out/relpage(a,l);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(DOCS/relpage(a,l),p)
  generate(out)
  for p in (out/'s').rglob('*'):
   if p.is_file():save(DOCS/p.relative_to(out),p.read_text())

def apply(only_bee=False):
 articles=package();assert all(set(a['languages'])==set(LANGS) for a in articles)
 p=ROOT/'content/en/pairs.json';data=json.loads(p.read_text())
 for a in articles:data['pairs'][a['slugs']['ar']]=a['slugs']['en']
 save(p,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 selected=[a for a in articles if not only_bee or not a['new']]
 paths=[render_article(a,l,articles) for a in selected for l in LANGS]
 for a in selected:
  for l in LANGS:source_file(a,l)
 twins=seo.load_twins(DOCS)
 for p in paths:
  text=p.read_text();block=seo.seo_block(text,p,DOCS,p.relative_to(DOCS),twins)
  text=re.sub(r'\n[ \t]*\n+', '\n', text.replace('</head>',block+'</head>'))
  text=seo.add_article_sharing(text,p.relative_to(DOCS))
  save(p,seo.add_ga4(text))
 if not only_bee:
  listings(articles)
  translation_sources(articles)
  sharing_links(articles)
 p=ROOT/'content/article-updates.json';data=json.loads(p.read_text())
 for item in data['articles']:
  if item['slugs'].get('en')=='european-bee-eater':item['updated']='2026-10-14'
 save(p,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 p=DOCS/'sitemap.xml';text=p.read_text()
 for a in selected:
  for l in LANGS:
   u=url(a,l);entry='<url><loc>'+u+'</loc><lastmod>2026-10-14</lastmod></url>'
   pat=r'<url>\s*<loc>'+re.escape(u)+r'</loc>.*?</url>'
   if re.search(pat,text,re.S):text=re.sub(pat,lambda m:entry,text,flags=re.S)
   else:text=text.replace('</urlset>','  '+entry+'\n</urlset>')
 save(p,text)
 print('Prepared '+str(len(paths))+' encyclopedia pages; homepage and ticker unchanged.')

if __name__=='__main__':apply()
