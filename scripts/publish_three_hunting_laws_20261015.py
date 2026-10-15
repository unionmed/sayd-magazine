#!/usr/bin/env python3
"""Publish three 2026 EXPLAINERS of original Arab hunting laws, not 2026 enactments.

Requires the locked source package, never fabricates event photos. Builds local
Sayd-branded typographic cards and fully translated article pages, preserving
lead, sidecards, ticker and unrelated category archives.
"""
import hashlib, json, html, re, sys, os
from pathlib import Path
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/'docs'
SOURCE=ROOT/'content/features/hunting-laws-arab-20261015.json'
LANGS=('ar','en','fr');COUNTRIES={'Lebanon':('LEBANON','580 / 2004'),'Qatar':('QATAR','4 / 2002'),'Oman':('OMAN','6 / 2003')}
DATES={'ar':'15 تشرين الأول 2026','en':'15 October 2026','fr':'15 octobre 2026'}
SECTION={'ar':'قوانين الصيد','en':'Hunting Laws','fr':'Réglementation de la chasse'}
EDITORIAL_GRAPHIC={'ar':'رسم توضيحي من صيد، وليس صورة أو نسخة رسمية من القانون','en':'Sayd editorial graphic, not a photograph or an official document','fr':'Visuel éditorial de Sayd, ni photographie ni document officiel'}

def locale_root(lang):return DOCS if lang=='ar' else DOCS/lang
def relpost(a,lang):return Path('' if lang=='ar' else lang)/'posts'/a['slugs'][lang]/'index.html'
def public(lang,article):
    return 'https://sayd-magazine.com/'+quote(relpost(article,lang).parent.as_posix(),safe='/')+'/'

def once(text,regex,subst,label):
    out,count=re.subn(regex,lambda m:subst,text,count=1,flags=re.S)
    assert count==1,(label,count)
    return out

def fonts(size,bold=False):
    paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for p in paths:
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def make_card(a):
    """Author-owned typographic cover; expressly not an original law scan."""
    country,num=COUNTRIES[a['country']]
    W,H=1600,900
    im=Image.new('RGB',(W,H),(42,64,33))
    draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,W,20),fill=(171,135,74))
    draw.rectangle((105,100,1495,800),outline=(215,188,119),width=4)
    draw.line((110,230,1490,230),fill=(215,188,119),width=3)
    draw.text((160,150),"SAYD  •  LEGAL EXPLAINER",font=fonts(36,True),fill=(234,220,178))
    draw.text((160,310),country,font=fonts(85,True),fill=(255,252,244))
    draw.text((160,430),"HUNTING & WILDLIFE LAW",font=fonts(54,True),fill=(233,221,191))
    draw.text((160,555),num,font=fonts(118,True),fill=(240,198,106))
    draw.text((160,730),"LAW ENACTMENT DATE ≠ ARTICLE PUBLICATION DATE",font=fonts(23),fill=(235,232,220))
    path='media/uploads/2026/10/sayd-legal-explainer-'+a['country'].lower()+'-'+a['law_number'].lower().replace('/','-').replace(' ','-')+'.jpg'
    target=DOCS/path
    target.parent.mkdir(parents=True,exist_ok=True);im.save(target,quality=90,optimize=True)
    return path,target

def body_html(a,lang,image):
    d=a['text'][lang]
    media='../'*(2 if lang=='ar' else 3)+image
    source=a['official_primary']
    blocks=[]
    for para in d['body'].strip().split('\n\n'):
        blocks.append('<p>'+html.escape(para.strip())+'</p>')
    caption=EDITORIAL_GRAPHIC[lang]
    return '<p class="excerpt">'+html.escape(d['summary'])+'</p>\n<figure><img src="'+media+'" alt="'+html.escape(caption,quote=True)+'" loading="lazy" decoding="async" style="display:block;width:100%;height:auto"><figcaption>'+html.escape(caption)+'</figcaption></figure>\n' + '\n'.join(blocks)+'\n<p><a href="'+html.escape(source,quote=True)+'" rel="noopener noreferrer">'+{'ar':'نص القانون من الجهة الرسمية','en':'Original statute at the official source','fr':'Texte de loi sur le site officiel'}[lang]+'</a></p>'

def write_article(a,lang,image):
    template=locale_root(lang)/'posts'/('طائر-جوراسي-لا-يطير-يعيد-رسم-بدايات-تطور-الطيور' if lang=='ar' else 'jurassic-flightless-bird-yuezhuornis-evolution')/'index.html'
    s=template.read_text()
    d=a['text'][lang];src=a['official_primary'];depth='../'*(2 if lang=='ar' else 3)
    category_link='../../category/قوانين/index.html'
    date=DATES[lang]
    s=once(s,r'<title>.*?</title>','<title>'+html.escape(d['title'])+' | '+('صيد' if lang=='ar' else 'Sayd Magazine')+'</title>','title')
    s=once(s,r'<meta name="description" content="[^"]*">','<meta name="description" content="'+html.escape(d['summary'],quote=True)+'">','meta')
    badge='<header class="article-header"><div><a class="badge" href="'+category_link+'">'+SECTION[lang]+'</a></div><h1>'+html.escape(d['title'])+'</h1><div class="article-meta"><span class="meta-item">'+date+'</span><span class="meta-item">صيد / Sayd</span></div></header>'
    s=once(s,r'<header class="article-header">.*?</header>',badge,'header')
    crumb='<div class="breadcrumb"><a href="../../index.html">'+{'ar':'الرئيسية','en':'Home','fr':'Accueil'}[lang]+'</a> / <a href="'+category_link+'">'+SECTION[lang]+'</a> / '+{'ar':'مقال','en':'Article','fr':'Article'}[lang]+'</div>'
    s=once(s,r'<div class="breadcrumb">.*?</div>',crumb,'breadcrumb')
    s=once(s,r'<article class="article-content">.*?</article>','<article class="article-content">\n'+body_html(a,lang,image)+'\n</article>','body')
    s=re.sub(r'<section class="related-block".*?</section>','',s,flags=re.S)
    s=re.sub(r'<div class="article-featured">.*?</div>','',s,flags=re.S)
    s=re.sub(r'<script type="application/ld\+json">.*?</script>','',s,flags=re.S)
    schema={'@context':'https://schema.org','@type':'Article','headline':d['title'],'description':d['summary'],'inLanguage':lang,'datePublished':'2026-10-15T14:15:00+03:00','dateModified':'2026-10-15',
       'image':['https://sayd-magazine.com/'+image],'articleSection':SECTION[lang],
       'mainEntityOfPage':public(lang,a),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
    s=s.replace('</head>','<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False)+'</script>\n</head>',1)
    nav='<nav class="lang-switch" aria-label="Language">'+''.join(
      '<a href="'+public(k,a)+'" lang="'+k+'" hreflang="'+k+'"'+(' class="is-current" aria-current="page"' if lang==k else '')+'>'+label+'</a>'
      for k,label in (('ar','العربية'),('en','English'),('fr','Français'))
    )+'</nav>'
    s=once(s,r'<nav class="lang-switch"[^>]*>.*?</nav>',nav,'langs')
    target=DOCS/relpost(a,lang);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(s)
    md=ROOT/'content'/('posts' if lang=='ar' else lang)/(a['slugs'][lang]+'.md');md.parent.mkdir(parents=True,exist_ok=True)
    md.write_text('---\ntitle: '+json.dumps(d['title'],ensure_ascii=False)+'\nslug: '+a['slugs'][lang]+'\ndate: 2026-10-15\ncategories: [قوانين]\nfeatured: '+image+'\n---\n\n'+d['body']+'\n')
    return target

def card(a,lang,image,page):
    d=a['text'][lang];depth=len(page.relative_to(locale_root(lang)).parts)-1
    relative='../'*depth
    href=relative+'posts/'+quote(a['slugs'][lang])+'/index.html'
    img='../'*depth+image
    style='post-row' if lang=='ar' else 'card'
    return '<article class="'+style+'"><a class="thumb" href="'+href+'"><img src="'+img+'" alt="'+html.escape(d['title'],quote=True)+'" loading="lazy"></a><div class="body"><div class="meta">'+DATES[lang]+'</div><h2><a href="'+href+'">'+html.escape(d['title'])+'</a></h2><p class="excerpt">'+html.escape(d['summary'])+'</p></div></article>'

def append_to_listings(articles,graphics):
    for lang in LANGS:
        base=locale_root(lang)
        cat=base/'category/قوانين/index.html'
        archive=base/('articles' if lang=='ar' else 'stories')/'index.html'
        blocks='\n'.join(card(a,lang,graphics[a['id']],cat) for a in articles)
        t=cat.read_text()
        if lang=='fr':
            t=once(t,r'(<div class="home-door-grid">).*?(</div>)', '<div class="home-door-grid">\n'+blocks+'\n</div>', 'French laws grid')
            t=re.sub(r'<p>Aucun article de 2026 dans cette rubrique pour le moment\.</p>','',t)
        else:
            m=re.search(r'<div class="post-list">',t)
            assert m is not None
            t=t[:m.end()]+'\n'+blocks+'\n'+t[m.end():]
            t=re.sub(r'<p class="empty-note">.*?</p>','',t,count=1,flags=re.S)
            t=re.sub(r'(<h2>(?:قوانين الصيد|Hunting Laws)\s*<span class="badge">)\d+(</span>)',r'\g<1>'+str(3+(3 if lang=='ar' else 0))+r'\g<2>',t)
        cat.write_text(t)
        txt=archive.read_text()
        blocks='\n'.join(card(a,lang,graphics[a['id']],archive) for a in articles)
        m=re.search(r'<article class="(?:post-row|card)[^"]*"',txt)
        assert m,archive
        txt=txt[:m.start()]+blocks+'\n'+txt[m.start():]
        archive.write_text(txt)

def seo_and_sitemap(articles,paths):
    sys.path.insert(0,str(ROOT/'scripts'))
    import seo_foundation as seo
    twins=seo.load_twins(DOCS)
    for p in paths:
        s=p.read_text()
        s=seo.SEO_BLOCK_RE.sub('',s)
        rel=p.relative_to(DOCS)
        s=s.replace('</head>',seo.seo_block(s,p,DOCS,rel,twins)+'</head>',1)
        s=seo.add_article_sharing(s,rel)
        s=seo.add_ga4(s)
        p.write_text(s)
    path=DOCS/'sitemap.xml'
    xml=path.read_text()
    for a in articles:
        for lang in LANGS:
            u=public(lang,a)
            if u not in xml:
                xml=xml.replace('</urlset>','<url><loc>'+html.escape(u)+'</loc><lastmod>2026-10-15</lastmod></url>\n</urlset>')
    path.write_text(xml)

def index_photos(graphics,articles):
    manifest=ROOT/'audit/image-catalog/manifest/2026-01.tsv'
    rows=manifest.read_text().strip().splitlines()
    for a in articles:
        site=DOCS/graphics[a['id']]
        data=site.read_bytes()
        sha=hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()
        entry='docs/'+graphics[a['id']]+'\t'+sha+'\t'+str(len(data))
        assert not any(x.startswith('docs/'+graphics[a['id']]+'\t') for x in rows)
        rows.append(entry)
    header=rows[:1];rest=sorted(rows[1:],key=lambda x:x.split('\t')[0])
    manifest.write_text('\n'.join(header+rest)+'\n')

def update_home(articles):
    p=ROOT/'content/homepage.json';c=json.loads(p.read_text())
    new=[a['slugs']['ar'] for a in articles]
    assert not set(new).intersection(c['latest']+c['featured'])
    latest=new+c['latest'][:5]
    assert len(latest)==8
    c['latest']=latest;c['ia_slots']['latest']=latest
    for a in articles:c['primary_door'][a['slugs']['ar']]='laws'
    p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    sys.path.insert(0,str(ROOT/'scripts'))
    from homepage_hunting_rotation import sync
    sync()
    from refresh_homepage_doors import refresh
    for lang in LANGS:refresh(locale_root(lang)/'index.html',lang)

def register_pairs(articles):
    p=ROOT/'content/en/pairs.json';d=json.loads(p.read_text())
    for a in articles:
        # Current site's French translation convention supports matching English slug.
        a['slugs']['fr']=a['slugs']['en']
        d['pairs'][a['slugs']['ar']]=a['slugs']['en']
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def run():
    data=json.loads(SOURCE.read_text())
    assert len(data['articles'])==3 and set(a['country'] for a in data['articles'])=={'Lebanon','Qatar','Oman'}
    articles=data['articles']
    for a in articles:
        assert all(len(a['text'][lang]['body'])>=500 for lang in LANGS)
    register_pairs(articles)
    SOURCE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    graphics={}
    for a in articles:
        graphics[a['id']]=make_card(a)[0]
    paths=[write_article(a,lang,graphics[a['id']]) for lang in LANGS for a in articles]
    append_to_listings(articles,graphics)
    # Needed by Homepage renderer: the lower "laws" door is not a homepage desk.
    # The article renderer's catalogue must still consider its category cards.
    p=ROOT/'scripts/refresh_homepage_doors.py';s=p.read_text()
    needle="    # An explicit local override survives publishing from older category cards."
    insert="""    # Resolve new law explainers into Updates without adding another homepage desk.
    law_category=path.parent/'category'/'قوانين'/'index.html'
    if law_category.is_file():
        for slug,item in collect(law_category.read_text(),law_category,path).items():
            catalog.setdefault(slug,item)
"""
    if insert not in s:
        assert needle in s
        p.write_text(s.replace(needle,insert+needle))
    update_home(articles)
    seo_and_sitemap(articles,paths)
    index_photos(graphics,articles)
    from check_publication_contract import check
    check()
    report={'date':'2026-10-15','law_original_enactment_dates':[a['enacted'] for a in articles],
      'editorial_publication_date':'2026-10-15','news_top4_unchanged':True,
      'graphics':[{'article':a['id'],'source':'Sayd-original typographic design, not official document',
                   'site_media_path':graphics[a['id']],'sha256':hashlib.sha256((DOCS/graphics[a['id']]).read_bytes()).hexdigest()} for a in articles],
      'articles_trilingual':len(articles),'contract':'pass'}
    (ROOT/'notes/hunting-laws-publication-receipt-20261015.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS hunting laws publishing package',json.dumps(report,ensure_ascii=False))
if __name__=='__main__':run()
