#!/usr/bin/env python3
"""Publish six authorized reference articles, preserving every homepage and ticker."""
import hashlib, html, json, os, re
from pathlib import Path
from urllib.parse import quote, unquote
from lxml import html as dom
import publish_arab_bird_encyclopedia_20261014 as birds
import publish_three_hunting_laws_20261015 as laws
import seo_foundation as seo

ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/'docs'
LANGS=('ar','en','fr')
DATES={'ar':'15 تشرين الأول 2026','en':'15 October 2026','fr':'15 octobre 2026'}
SOURCE=ROOT/'content/features/six-reference-articles-20261015.json'
CAT_LABELS={'قوانين':laws.SECTION,'موسوعة-الطيور':birds.CATS}

def save(p,t):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t)
def replace(p,v,t):return birds.replace_one(p,v,t)
def relpage(a,l):return birds.relpage(a,l)
def url(a,l):return birds.url(a,l)
def body(a,l):
 if a['category']=='موسوعة-الطيور':return birds.article_body(a,l)
 d=a['languages'][l];im='../'*(2 if l=='ar' else 3)+a['image']
 return '<p class="excerpt">'+html.escape(d['description'])+'</p>\n<figure><img src="'+im+'" alt="'+html.escape(d['alt'],quote=True)+'" decoding="async" style="display:block;width:100%;height:auto"><figcaption>'+html.escape(a['caption'][l])+'</figcaption></figure>\n'+d['body_html']

def related(a,l,all_articles):
 candidates=sorted((x for x in all_articles if x['category']==a['category'] and x['key']!=a['key']),key=lambda x:x['published_at'],reverse=True)[:2]
 assert len(candidates)==2
 return birds.related(a,l,candidates)

def render(a,l,articles):
 template=DOCS/('' if l=='ar' else l)/'posts'/((('قانون-الصيد-اللبناني-580-2004-ما-يسمح-وما-يمنع' if l=='ar' else 'lebanon-hunting-law-580-2004-what-is-prohibited') if a['category']=='قوانين' else ('طائر-الوروار-الأوروبي' if l=='ar' else 'european-bee-eater')))/'index.html'
 text=template.read_text();d=a['languages'][l]
 text=replace(r'<title>.*?</title>','<title>'+html.escape(d['title'])+' | '+('صيد' if l=='ar' else 'Sayd Magazine')+'</title>',text)
 text=replace(r'<meta name="description" content="[^"]*">','<meta name="description" content="'+html.escape(d['description'],quote=True)+'">',text)
 header=re.search(r'<header class="article-header">.*?</header>',text,re.S)[0]
 header=replace(r'<h1>.*?</h1>','<h1>'+html.escape(d['title'])+'</h1>',header)
 header=replace(r'<div class="article-meta">.*?</div>','<div class="article-meta"><span class="meta-item">'+DATES[l]+'</span><span class="meta-item">'+('صيد' if l=='ar' else 'Sayd')+'</span></div>',header)
 text=replace(r'<header class="article-header">.*?</header>',header,text)
 text=re.sub(r'<(?:figure|div) class="article-featured".*?</(?:figure|div)>','',text,flags=re.S)
 text=replace(r'<article class="article-content">.*?</article>','<article class="article-content">\n'+body(a,l)+'\n</article>',text)
 text=re.sub(r'<section class="(?:related-block|article-more)".*?</section>','',text,flags=re.S)
 content=re.search(r'<article class="article-content">.*?</article>',text,re.S)[0]
 text=replace(r'<article class="article-content">.*?</article>',content+'\n'+related(a,l,articles),text)
 nav=''.join('<a href="'+url(a,x)+'" lang="'+x+'" hreflang="'+x+'"'+(' class="is-current" aria-current="page"' if x==l else '')+'>'+label+'</a>' for x,label in zip(LANGS,['العربية','English','Français']))
 text=replace(r'<nav class="lang-switch"[^>]*>.*?</nav>','<nav class="lang-switch" aria-label="Language">'+nav+'</nav>',text)
 # Remove inherited sharing; regenerate for the new canonical URL.
 text=re.sub(r'<div class="article-share".*?</div>','',text,flags=re.S)
 text=seo.SEO_BLOCK_RE.sub('',text)
 text=re.sub(r'<script type="application/ld\+json">.*?</script>','',text,flags=re.S)
 text=text.replace('category/'+quote(a['category'])+'/','category/'+a['category']+'/')
 schema={'@context':'https://schema.org','@type':'Article','headline':d['title'],'description':d['description'],'inLanguage':l,'datePublished':a['published_at'],'dateModified':a['date'],'author':{'@type':'Organization','name':'Sayd Magazine'},'image':['https://sayd-magazine.com/'+a['image']],'articleSection':CAT_LABELS[a['category']][l],'mainEntityOfPage':url(a,l),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
 text=text.replace('</head>','<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False)+'</script>\n</head>')
 target=DOCS/relpage(a,l);save(target,text)
 front=f'title: {json.dumps(d["title"],ensure_ascii=False)}\nslug: {a["slugs"][l]}\ndate: {a["date"]}\nauthor: Sayd\ncategories: [{"قوانين" if a["category"]=="قوانين" else "موسوعة الطيور"}]\nfeatured: {a["image"]}\n'
 save(ROOT/'content'/('posts' if l=='ar' else l)/(a['slugs'][l]+'.md'),'---\n'+front+'---\n\n'+body(a,l)+'\n')
 return target

def listings(articles):
 for l in LANGS:
  base=DOCS/('' if l=='ar' else l)
  for category in ['قوانين','موسوعة-الطيور',None]:
   page=base/'category'/category/'index.html' if category else base/('articles' if l=='ar' else 'stories')/'index.html'
   selected=sorted([a for a in articles if category is None or a['category']==category],key=lambda a:a['published_at'],reverse=True)
   text=page.read_text();slugs={a['slugs'][l] for a in selected}
   text=re.sub(r'<article\b[^>]*>.*?</article>',lambda m:'' if any('/posts/'+s+'/' in unquote(m[0]) for s in slugs) else m[0],text,flags=re.S)
   first=re.search(r'<article\b[^>]*class="(?:post-row|card)[^"]*"',text);assert first,page
   style='post-row' if 'post-row' in first[0] else 'card overlay' if 'overlay' in first[0] else 'card'
   rows=[]
   for a in selected:
    d=a['languages'][l];href=quote(os.path.relpath(DOCS/relpage(a,l),page.parent),safe='/');im=os.path.relpath(DOCS/a['image'],page.parent)
    rows.append('<article class="'+style+'"><a class="thumb" href="'+href+'"><img src="'+im+'" alt="'+html.escape(a['caption'][l],quote=True)+'" loading="lazy"></a><div class="body"><h2><a href="'+href+'">'+html.escape(d['title'])+'</a></h2><div class="meta">'+DATES[l]+'</div><p class="excerpt">'+html.escape(d['description'])+'</p></div></article>')
   text=text[:first.start()]+'\n'.join(rows)+'\n'+text[first.start():]
   if category:
    # Count actual cards rather than blindly incrementing a possibly historical badge.
    count=len(re.findall(r'<article\b[^>]*class="(?:post-row|card)',text))
    text=re.sub(r'(<h2>[^<]*<span class="badge">)\d+(</span>)',lambda m:m[1]+str(count)+m[2],text)
   save(page,re.sub(r"\n[ \t]*\n+", "\n", text))

def translations(articles):
 from build_fr_edition import source_blocks
 p=ROOT/'content/fr/edition-2026.json';manifest=json.loads(p.read_text())
 for a in articles:
  trees={l:dom.fromstring('<article>'+body(a,l)+'</article>') for l in ['en','fr']}
  en=source_blocks(trees['en']);fr=source_blocks(trees['fr'])
  assert len(en)==len(fr),(a['key'],len(en),len(fr))
  assert [x.tag for x in en]==[x.tag for x in fr],a['key']
  def inner(n):return (html.escape(n.text) if n.text else '')+''.join(dom.tostring(c,encoding='unicode',method='html') for c in n)
  data={'title':a['languages']['fr']['title'],'figures':[inner(n) for n in trees['fr'].xpath('./figure/figcaption')],'blocks':[inner(n) for n in fr]}
  save(ROOT/'content/fr/segments'/(a['slugs']['fr']+'.json'),json.dumps(data,ensure_ascii=False,indent=2)+'\n')
  if not any(x['slug']==a['slugs']['en'] for x in manifest['articles']):manifest['articles'].append({'slug':a['slugs']['en'],'english_title':a['languages']['en']['title'],'date':DATES['en'],'category':CAT_LABELS[a['category']]['en'],'english_url':'/en/posts/'+a['slugs']['en']+'/'})
 save(p,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')

def patch_existing_law_captions():
 # Authorized caption-only correction: existing article prose remains untouched.
 captions={
 'Lebanon':{'ar':'بطاقة قانون الصيد اللبناني 580/2004','en':'Lebanon: Hunting Law 580/2004','fr':'Liban : loi sur la chasse 580/2004'},
 'Qatar':{'ar':'بطاقة قانون الصيد القطري 4/2002','en':'Qatar: Hunting Law 4/2002','fr':'Qatar : loi sur la chasse 4/2002'},
 'Oman':{'ar':'بطاقة قانون المحميات وصون الأحياء الفطرية العُماني 6/2003','en':'Oman: Nature Reserves and Wildlife Conservation Law 6/2003','fr':'Oman : loi sur les réserves naturelles et la conservation de la faune 6/2003'}}
 source=ROOT/'content/features/hunting-laws-arab-20261015.json';data=json.loads(source.read_text())
 for a in data['articles']:
  a['caption']=captions[a['country']]
  for l in LANGS:
   page=DOCS/relpage(a,l);text=page.read_text();old=laws.EDITORIAL_GRAPHIC[l];new=a['caption'][l]
   text=text.replace('<figcaption>'+html.escape(old)+'</figcaption>','<figcaption>'+html.escape(new)+'</figcaption>')
   text=text.replace('alt="'+html.escape(old,quote=True)+'"','alt="'+html.escape(new,quote=True)+'"')
   save(page,text)
 save(source,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 # Keep the legacy source renderer aligned without invoking its homepage updater.
 script=ROOT/'scripts/publish_three_hunting_laws_20261015.py';text=script.read_text()
 text=text.replace('caption=EDITORIAL_GRAPHIC[lang]',"caption=a.get('caption',EDITORIAL_GRAPHIC)[lang]")
 save(script,text)

def run():
 articles=json.loads(SOURCE.read_text())['articles'];assert len(articles)==6
 assert sum(a['category']=='قوانين' for a in articles)==3
 assert all(set(a['languages'])==set(LANGS) for a in articles)
 protected=[ROOT/'content/homepage.json']+[DOCS/('' if l=='ar' else l)/'index.html' for l in LANGS]
 before={p:p.read_bytes() for p in protected}
 birds.DATES=DATES
 patch_existing_law_captions()
 p=ROOT/'content/en/pairs.json';pairs=json.loads(p.read_text())
 for a in articles:
  assert (DOCS/a['image']).is_file(),a['image']
  pairs['pairs'][a['slugs']['ar']]=a['slugs']['en']
 save(p,json.dumps(pairs,ensure_ascii=False,indent=2)+'\n')
 paths=[render(a,l,articles) for a in articles for l in LANGS]
 twins=seo.load_twins(DOCS)
 for p in paths:
  text=p.read_text();text=text.replace('</head>',seo.seo_block(text,p,DOCS,p.relative_to(DOCS),twins)+'</head>')
  save(p,seo.add_ga4(seo.add_article_sharing(text,p.relative_to(DOCS))))
 listings(articles);translations(articles);birds.sharing_links(articles)
 p=DOCS/'sitemap.xml';text=p.read_text()
 for a in articles:
  for l in LANGS:
   u=url(a,l)
   if '<loc>'+u+'</loc>' not in text:text=text.replace('</urlset>','<url><loc>'+u+'</loc><lastmod>'+a['date']+'</lastmod></url>\n</urlset>')
 save(p,text)
 p=ROOT/'audit/image-catalog/manifest/2026-01.tsv';rows=p.read_text().splitlines()
 for a in articles:
  path=DOCS/a['image'];data=path.read_bytes();key='docs/'+a['image']
  row=key+'\t'+hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()+'\t'+str(len(data))
  rows=[x for x in rows if not x.startswith(key+'\t')]+[row]
 save(p,'\n'.join(rows[:1]+sorted(rows[1:],key=lambda x:x.split('\t')[0]))+'\n')
 assert all(p.read_bytes()==v for p,v in before.items()),'Protected homepage changed'
 print('Prepared 18 reference pages. Protected homepage content is byte-identical.')

if __name__=='__main__':run()
