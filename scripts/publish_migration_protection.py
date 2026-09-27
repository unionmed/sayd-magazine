"""Publish Nayef's approved bilingual Mediterranean bird-protection story.

Source: content/migration-protection-2026.json. Run after the normal site build.
Keeps the original publication dates of demoted homepage stories.
"""
import ast
import html
import json
import re
from pathlib import Path
from urllib.parse import quote
import homepage_unique_cards as home
import seo_foundation as seo

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
DATA=json.loads((ROOT/'content/migration-protection-2026.json').read_text())
AR,EN=DATA['ar_slug'],DATA['en_slug']
HERO='media/uploads/2026/09/european-turtle-doves-douz-skander-zarrad.jpg'
NETS='media/uploads/2026/09/bekaa-nets-isf-pickup-2026-09-25.jpg'
FLOCK='media/uploads/2026/09/migrating-white-storks-istanbul-tema.jpg'
OLD_AR=home.NETS_AR
OLD_EN=home.NETS_EN

def save_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def fig(src,caption):
    return f'<figure style="margin:28px auto;max-width:850px"><img src="{src}" alt="{html.escape(caption)}" decoding="async" style="display:block;width:100%;height:auto"><figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px">{caption}</figcaption></figure>'

def body(lang):
    prefix='../../../' if lang=='en' else '../../'
    caps=DATA[lang+'_captions']
    result=fig(prefix+HERO,caps[0])
    for i,(title,paras) in enumerate(DATA[lang+'_sections']):
        if i==5: result+=fig(prefix+FLOCK,caps[2])
        anchor=' id="libya"' if title and (title.startswith('ليبيا:') or title.startswith('Libya:')) else ''
        if title: result+=f'<h2{anchor} style="font-weight:800;font-size:1.45em;line-height:1.65;margin:32px 0 12px;color:#304b36">{html.escape(title)}</h2>'
        result+=''.join('<p>'+html.escape(p)+'</p>' for p in paras)
        if i==2: result+=fig(prefix+NETS,caps[1])
    label='Photo credits' if lang=='en' else 'اعتمادات الصور'
    result+=f'''<aside class="photo-credits" style="margin-top:32px;padding-top:12px;border-top:1px solid #ddd;font-size:11px;line-height:1.8;color:#777"><strong>{label}</strong><br>
    <a href="https://commons.wikimedia.org/wiki/File:DUO_DE_TOURTERELLES_DES_BOIS.jpg">Skander Zarrad</a> · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a> · 06/07/2025<br>
    <a href="https://commons.wikimedia.org/wiki/File:Flock_of_storks_migrating_over_Istanbul,_Turkey.JPG">Tema</a> · <a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a> · 20/08/2010
    </aside>'''
    return result

def write_articles():
    for lang,slug,old in [('ar',AR,OLD_AR),('en',EN,OLD_EN)]:
        base=DOCS/('en/posts' if lang=='en' else 'posts')
        text=(base/old/'index.html').read_text()
        tickers=iter(re.findall(r'<div class="ticker"[^>]*>.*?</div>',text))
        # Replace the source story identity, including encoded SEO URLs.
        old_title=re.search(r'<h1>(.*?)</h1>',text,re.S)[1]
        text=text.replace(old_title,html.escape(DATA[lang+'_title'],quote=False))
        for original,new in [(OLD_AR,AR),(OLD_EN,EN)]:
            text=text.replace(original,new).replace(quote(original),quote(new))
        text=re.sub(r'<div class="ticker"[^>]*>.*?</div>',lambda m:next(tickers),text)
        date='27 September 2026' if lang=='en' else '27 أيلول 2026'
        text=re.sub(r'(<div class="article-meta"><span class="meta-item">)[^<]+',lambda m:m[1]+date,text,count=1)
        text=re.sub(r'<meta name="description" content="[^"]*">',lambda m:'<meta name="description" content="'+html.escape(DATA[lang+'_description'],quote=True)+'">',text,count=1)
        text=re.sub(r'(<article class="article-content">).*?(</article>)',lambda m:m[1]+'\n'+body(lang)+'\n'+m[2],text,count=1,flags=re.S)
        dest=base/slug/'index.html';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
        md=ROOT/'content'/('en' if lang=='en' else 'posts')/(slug+'.md')
        md.write_text(f'---\ntitle: {json.dumps(DATA[lang+"_title"],ensure_ascii=False)}\nslug: {slug}\ndate: 2026-09-27 05:35:00\nauthor: Sayd\ncategories: [صيد]\nfeatured: {HERO}\n---\n\n'+body(lang)+'\n')

def card(slug,lang):
    existing=home.extract_cards_by_slug((DOCS/('en/index.html' if lang=='en' else 'index.html')).read_text())
    if slug in existing and slug not in {AR,EN}:
        return existing[slug]
    base=DOCS/('en/posts' if lang=='en' else 'posts')
    text=(base/slug/'index.html').read_text()
    title=re.search(r'<h1[^>]*>(.*?)</h1>',text,re.S)[1]
    date=re.search(r'class="article-meta".*?<span class="meta-item">([^<]+)',text,re.S)[1]
    b=re.search(r'<article class="article-content">(.*?)</article>',text,re.S)[1]
    image=re.search(r'<img[^>]+src="([^"]+)"',b)
    if not image:
        fallbacks=home.EN_FALLBACK_CARDS if lang=='en' else home.AR_FALLBACK_CARDS
        if slug in fallbacks:return fallbacks[slug]
        raise ValueError('No photograph for '+slug)
    img=image[1]
    img=img.replace('../../../','../') if lang=='en' else img.replace('../../','')
    return f'<article class="card"><a class="thumb" href="posts/{slug}/index.html"><img src="{img}" alt="{html.escape(html.unescape(re.sub("<[^>]+>","",title)))}" loading="lazy"></a><div class="body"><h3><a href="posts/{slug}/index.html">{title}</a></h3><div class="meta">{date}</div></div></article>'

def replace_assignment(path,name,value):
    text=path.read_text();lines=text.splitlines(keepends=True)
    tree=ast.parse(text)
    for node in tree.body:
        targets=node.targets if isinstance(node,ast.Assign) else [node.target] if isinstance(node,ast.AnnAssign) else []
        if any(isinstance(t,ast.Name) and t.id==name for t in targets):
            lines[node.lineno-1:node.end_lineno]=[name+' = '+repr(value)+'\n'];path.write_text(''.join(lines));return
    raise ValueError('Missing assignment '+name)

def update_home():
    config_path=ROOT/'content/homepage.json';config=json.loads(config_path.read_text())
    slots=config['ia_slots']
    if slots['main']!=AR:
        important=[slots['main']]+slots['important']
        fallen=important.pop()
        latest=list(dict.fromkeys([fallen]+slots['latest']))
        # Sort before taking ten; displaced articles retain their real dates.
        latest.sort(key=lambda s:home._parse_display_date(home._card_date(card(s,'ar'))),reverse=True)
        slots={'main':AR,'important':important,'latest':latest[:10]}
    config['ia_slots']=slots
    config['featured']=[AR]+slots['important']
    config['latest']=slots['latest']
    config['primary_door'][AR]='hunting'
    save_json(config_path,config)
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    for lang in ['ar','en']:
        path=DOCS/('en/index.html' if lang=='en' else 'index.html');text=path.read_text()
        featured=[slots['main']]+slots['important'];latest=slots['latest']
        if lang=='en':featured=[pairs[s] for s in featured];latest=[pairs[s] for s in latest]
        cards={s:card(s,lang) for s in featured+latest}
        if lang=='en':home.FEATURED_EN=featured;home.LATEST_EN=latest
        else:home.FEATURED_AR=featured;home.LATEST_AR=latest
        home.FEATURED_SLUGS=frozenset(home.FEATURED_AR+home.FEATURED_EN)
        text=home.rebuild_featured_mosaic(text,cards,en=lang=='en')
        text=home.rebuild_latest_feed(text,cards,en=lang=='en')
        # Do not duplicate featured/latest stories in lower homepage doors.
        start=text.index('<div class="home-main">');end=text.index('<div class="more-news">',start)
        chunk=text[start:end]
        chunk=home.ARTICLE_RE.sub(lambda m:'' if home._card_slug(m[0]) in featured+latest else m[0],chunk)
        chunk=re.sub(r'<section\b[^>]*>.*?</section>',lambda m:m[0] if '<article' in m[0] else '',chunk,flags=re.S)
        text=text[:start]+chunk+text[end:]
        path.write_text(text)
    # Keep both existing homepage source modules aligned with this publication.
    ia_path=ROOT/'scripts/site_ia.py';replace_assignment(ia_path,'IA_SLOTS',slots)
    import site_ia as ia
    primary=dict(ia.PRIMARY);primary[AR]={'door':'hunting','en':EN,'remove_from':[]}
    replace_assignment(ia_path,'PRIMARY',primary)
    visible=set([slots['main']]+slots['important']+slots['latest'])
    # Prefer 2026+ stories not already visible above, using the published
    # category listings and requiring an English twin for both homepages.
    doors=[]
    for door in ia.DOORS:
        listing=DOCS/'category'/door['folder']/'index.html'
        if not listing.exists():continue
        candidates=[]
        for row in re.findall(r'<article class="post-row">.*?</article>',listing.read_text(),re.S):
            match=re.search(r'href="[^\"]*posts/([^/]+)/',row)
            date=re.search(r'<div class="meta">([^<]+)',row)
            if not match or not date:continue
            slug=match[1];stamp=home._parse_display_date(date[1])
            if stamp[0]>=2026 and slug not in visible and slug in pairs and slug in primary:
                candidates.append((stamp,slug))
        slugs=list(dict.fromkeys(s for _,s in sorted(candidates,reverse=True)))[:4]
        if slugs:doors.append((door['id'],slugs))
    replace_assignment(ia_path,'DOOR_SECTIONS',doors)
    config['ia_door_sections']=[{'door':d,'slugs':ss} for d,ss in doors]
    config['approved_home_repeats']=[]
    config['demotion']='Main + four supporting stories + ten latest, dated chronologically; no duplicated homepage story.'
    replace_assignment(ia_path,'APPROVED_HOME_REPEATS',set())
    save_json(config_path,config)
    ia.PRIMARY=primary;ia.DOOR_SECTIONS=doors
    from refresh_homepage_doors import refresh
    for lang in ['ar','en']:
        refresh(DOCS/('en/index.html' if lang=='en' else 'index.html'),lang)
    hp=ROOT/'scripts/homepage_unique_cards.py'
    for name,value in [('FEATURED_AR',[AR]+slots['important']),('FEATURED_EN',[pairs[s] for s in [AR]+slots['important']]),('LATEST_AR',slots['latest']),('LATEST_EN',[pairs[s] for s in slots['latest']])]:replace_assignment(hp,name,value)
    for name,lang,slug in [('AR_FALLBACK_CARDS','ar',AR),('EN_FALLBACK_CARDS','en',EN)]:
        # Append one explicit fallback after the dictionary definitions.
        text=hp.read_text();marker='\n# Mediterranean protection story fallback\n'
        if marker not in text:text+='\n'+marker
        if name+'['+repr(slug)+']' not in text:text+=name+'['+repr(slug)+'] = '+repr(card(slug,lang))+'\n'
        hp.write_text(text)

def listing_row(lang,prefix):
    slug=EN if lang=='en' else AR;date='27 September 2026' if lang=='en' else '27 أيلول 2026'
    media=prefix+('../' if lang=='en' else '')+HERO
    return f'<article class="post-row"><a class="thumb" href="{prefix}posts/{slug}/index.html"><img src="{media}" alt="{html.escape(DATA[lang+"_captions"][0])}" loading="lazy"></a><div class="body"><div class="meta">{date}</div><h2><a href="{prefix}posts/{slug}/index.html">{html.escape(DATA[lang+"_title"])}</a></h2><p class="excerpt">{html.escape(DATA[lang+"_description"])}</p></div></article>\n'

def listings():
    for lang,rel,prefix in [('ar','category/صيد/index.html','../../'),('en','en/category/صيد/index.html','../../'),('ar','articles/index.html','../'),('en','en/stories/index.html','../')]:
        p=DOCS/rel;text=p.read_text();slug=EN if lang=='en' else AR
        row=listing_row(lang,prefix)
        if slug not in text:
            marker='<div class="post-list">' if '<div class="post-list">' in text else '<div class="grid-4">'
            assert marker in text,rel
            text=text.replace(marker,marker+'\n'+row,1)
            if lang=='ar' and rel.startswith('articles'):
                text=re.sub(r'(الأرشيف — كل المقالات \()(\d+)(\))',lambda m:m[1]+str(int(m[2])+1)+m[3],text)
            p.write_text(text)
    manifest=ROOT/'content/unified-hunting.json';data=json.loads(manifest.read_text())
    for lang,slug in [('ar',AR),('en',EN)]:
        if not any(slug in row for row in data[lang]):data[lang].insert(0,listing_row(lang,'../../'))
    save_json(manifest,data)

def main():
    p=ROOT/'content/en/pairs.json';pairs=json.loads(p.read_text());pairs['pairs'][AR]=EN;save_json(p,pairs)
    write_articles();update_home();listings()
    twins=seo.load_twins(DOCS)
    for rel in ['index.html','en/index.html',f'posts/{AR}/index.html',f'en/posts/{EN}/index.html']:
        page=DOCS/rel
        page.write_text(seo.apply_html(page.read_text(),page,DOCS,Path(rel),twins))
    sitemap=DOCS/'sitemap.xml';xml=sitemap.read_text()
    for rel in [f'posts/{AR}/index.html',f'en/posts/{EN}/index.html']:
        url=seo.public_url(Path(rel))
        if '<loc>'+url+'</loc>' not in xml:
            xml=xml.replace('</urlset>',f'  <url><loc>{url}</loc><lastmod>2026-09-27</lastmod></url>\n</urlset>')
    sitemap.write_text(xml)
    print('Published bilingual article, homepage, listings and sitemap locally.')

if __name__=='__main__':main()
