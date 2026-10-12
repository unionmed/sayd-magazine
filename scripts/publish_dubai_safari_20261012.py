#!/usr/bin/env python3
"""Publish approved Dubai Safari copy only to Wildlife, and promote Europe below lead.
Idempotent regeneration preserves the existing lead, ticker and unrelated articles.
"""
from __future__ import annotations
import copy
import html as esc
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"
sys.path.insert(0,str(ROOT/"scripts"))
from refresh_homepage_doors import main as refresh_home, local_slug
from seo_foundation import apply_html, load_twins, add_ga4

DATA=json.loads((ROOT/"content/features/dubai-safari-20261012.json").read_text(encoding="utf-8"))
AR=DATA["slug_ar"]; INTL=DATA["slug_intl"]
IMAGES=["media/uploads/2026/10/dubai-safari-archive-"+n+".jpg" for n in ("lions","macaw","giraffes")]
IMAGE=IMAGES[0]
MEDIA_VERSION="20261012"

def media_url(path):
    return path+"?v="+MEDIA_VERSION

DATE=DATA["date"]; TIME=DATA["published_at"]
DATES={"ar":"12 تشرين الأول 2026","en":"12 October 2026","fr":"12 octobre 2026"}
NAMES={"ar":"برية وتخييم","en":"Wildlife & Camping","fr":"Faune et camping"}
AUTHORS={"ar":"مجلة صيد","en":"Sayd Magazine","fr":"Sayd Magazine"}
SLUG_BY_LANG={"ar":AR,"en":INTL,"fr":INTL}
SRC_BY_LANG={"ar":"موسم-الطوقي-محمية-الملك-عبدالعزيز-2026","en":"touqi-season-king-abdulaziz-royal-reserve-2026","fr":"touqi-season-king-abdulaziz-royal-reserve-2026"}
EU="تحذير-أوروبي-11-36-مليون-طائر-في-المتوسط"

def cls(root, name):
    return root.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " '+name+' ")]')

def public(lang):
    prefix="" if lang=="ar" else lang+"/"
    return "https://sayd-magazine.com/"+prefix+"posts/"+quote(SLUG_BY_LANG[lang])+"/"

def save(path, text):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8")

def body(lang):
    d=DATA[lang]
    prefix="../../" if lang=="ar" else "../../../"
    def figure(i):
        width,height=(2000,1333) if i==1 else (2000,1125)
        return ('<figure><img src="'+prefix+media_url(IMAGES[i])+'" width="'+str(width)+'" height="'+str(height)+'" alt="'+esc.escape(d["alts"][i],quote=True)+'" decoding="async" style="display:block;width:100%;height:auto">'
                '<figcaption>'+esc.escape(d["captions"][i])+'</figcaption></figure>')
    b=[figure(0),'<p class="article-deck"><strong>'+esc.escape(d["deck"])+'</strong></p>']
    for i,paragraph in enumerate(d["paragraphs"]):
        b.append('<p>'+esc.escape(paragraph)+'</p>')
        if i==2:b.append(figure(1))
        if i==3:b.append(figure(2))
    b.append('<p class="photo-source"><small>'+esc.escape(d["photo_credit"])+'</small></p>')
    sources=[DATA["source_urls"][0 if lang=="ar" else 1],DATA["source_urls"][2]]
    b.append('<p class="article-sources">'+' · '.join('<a href="'+esc.escape(url,quote=True)+'" rel="noopener">'+esc.escape(label)+'</a>' for url,label in zip(sources,d["source_labels"]))+'</p>')
    return "\n".join(b)

def render_article(lang):
    d=DATA[lang]
    pref="" if lang=="ar" else lang
    template=DOCS/pref/"posts"/SRC_BY_LANG[lang]/"index.html"
    root=html.parse(str(template)).getroot()
    new_url=public(lang)
    title_suffix=" — مجلة صيد" if lang=="ar" else " — Sayd Magazine"
    for tag in root.xpath("//title"):tag.text=d["title"]+title_suffix
    for tag in root.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):
        tag.set("content",d["deck"])
    for tag in root.xpath('//meta[@property="og:title" or @name="twitter:title"]'):
        tag.set("content",d["title"]+title_suffix)
    for tag in root.xpath('//meta[@property="og:url"]'):tag.set("content",new_url)
    for tag in root.xpath('//meta[@property="og:image" or @name="twitter:image"]'):
        tag.set("content","https://sayd-magazine.com/"+media_url(IMAGE))
    for tag in root.xpath('//link[@rel="canonical"]'):tag.set("href",new_url)
    for tag in root.xpath('//link[@rel="alternate"]'):
        l=tag.get("hreflang","ar")
        tag.set("href",public(l if l in ("ar","en","fr") else "ar"))
    depth=2 if lang=="ar" else 3
    for anchor in cls(root,"lang-switch")[0].xpath(".//a[@lang]"):
        l=anchor.get("lang")
        anchor.set("href","../"*depth+("" if l=="ar" else l+"/")+"posts/"+quote(SLUG_BY_LANG[l])+"/index.html")
        anchor.attrib.pop("class",None);anchor.attrib.pop("aria-current",None)
        if l==lang:
            anchor.set("class","is-current");anchor.set("aria-current","page")
    head=cls(root,"article-header")[0]
    head.xpath(".//h1")[0].text=d["title"]
    metas=cls(head,"meta-item")
    assert len(metas)>=2
    metas[0].text=DATES[lang]
    metas[1].text=AUTHORS[lang]
    for tag in cls(root,"author-role"):tag.getparent().remove(tag)
    for tag in head.xpath('.//a[contains(@href,"category/")]'):
        tag.set("href","../../category/"+quote("حياة-برية-وتخييم")+"/index.html")
        tag.text=NAMES[lang]
    for tag in cls(root,"breadcrumb")[0].xpath('.//a[contains(@href,"category/")]'):
        tag.set("href","../../category/"+quote("حياة-برية-وتخييم")+"/index.html")
        tag.text=NAMES[lang]
    article=cls(root,"article-content")[0]
    for child in list(article):article.remove(child)
    article.text=None
    for el in html.fragments_fromstring(body(lang)):
        if isinstance(el,str):raise ValueError("Unexpected unwrapped body text")
        article.append(el)
    for name in ("article-featured","related-block"):
        for tag in cls(root,name):tag.getparent().remove(tag)
    for tag in root.xpath('//script[@type="application/ld+json"]'):tag.getparent().remove(tag)
    schema={
        "@context":"https://schema.org","@type":"NewsArticle",
        "headline":d["title"],"description":d["deck"],"inLanguage":lang,
        "datePublished":TIME,"dateModified":TIME,
        "author":{"@type":"Organization","name":"Sayd Magazine"},
        "image":["https://sayd-magazine.com/"+media_url(img) for img in IMAGES],
        "articleSection":NAMES[lang],
        "mainEntityOfPage":new_url,
        "publisher":{"@type":"Organization","name":"Sayd Magazine","url":"https://sayd-magazine.com/"}
    }
    tag=html.Element("script",{"type":"application/ld+json"})
    tag.text=json.dumps(schema,ensure_ascii=False)
    root.xpath("//head")[0].append(tag)
    # Do not carry the source article share links into a new article.
    for name in ("article-share","share-bar"):
        for wrapper in cls(root,name):
            for anchor in wrapper.xpath(".//a[@href]"):
                h=anchor.get("href","")
                h=re.sub(r'https%3A%2F%2Fsayd-magazine.com%2F[^&]+',quote(new_url,safe=""),h)
                anchor.set("href",h)
    page=DOCS/pref/"posts"/SLUG_BY_LANG[lang]/"index.html"
    output="<!DOCTYPE html>\n"+html.tostring(root,encoding="unicode",method="html")
    # A canonical source of truth for the three new HTML mirrors.
    save(page,add_ga4(output))
    src=ROOT/"content"/("posts" if lang=="ar" else lang)/(SLUG_BY_LANG[lang]+".md")
    front=("---\ntitle: "+json.dumps(d["title"],ensure_ascii=False)+
           "\nslug: "+SLUG_BY_LANG[lang]+"\ndate: "+DATE+
           "\nauthor: "+json.dumps(AUTHORS[lang],ensure_ascii=False)+
           "\ncategories: [الحياة البرية والتخييم]\nfeatured: "+media_url(IMAGE)+
           "\nsubtitle: "+json.dumps(d["deck"],ensure_ascii=False)+"\n---\n\n")
    save(src,front+body(lang)+"\n")
    return page

def insert_listing(lang,page):
    d=DATA[lang]
    path=Path(page)
    text=path.read_text(encoding="utf-8")
    slug=SLUG_BY_LANG[lang]
    # Avoid duplicate cards if the one-shot writer is retried.
    candidate=re.compile(r'<article\b[^>]*>.*?</article>\n?',re.S)
    text=candidate.sub(lambda m:"" if slug in m.group() else m.group(),text)
    m=re.search(r'<article\b[^>]*class="(?:post-row|card)"',text)
    if not m:raise RuntimeError("Missing archive listing anchor "+str(path))
    href=os.path.relpath(DOCS/("" if lang=="ar" else lang)/"posts"/slug/"index.html",path.parent)
    image=media_url(os.path.relpath(DOCS/IMAGE,path.parent))
    row=(
        '<article class="post-row"><a class="thumb" href="'+esc.escape(href,quote=True)+'">'
        '<img src="'+esc.escape(image,quote=True)+'" alt="'+esc.escape(d["alts"][0],quote=True)+'" loading="lazy"></a>'
        '<div class="body"><h2><a href="'+esc.escape(href,quote=True)+'">'+esc.escape(d["title"])+'</a></h2>'
        '<div class="meta">'+DATES[lang]+'</div><p class="excerpt">'+esc.escape(d["deck"])+'</p></div></article>\n'
    )
    if 'class="card"' in m.group():row=row.replace('class="post-row"','class="card"')
    save(path,text[:m.start()]+row+text[m.start():])

def update_image_manifest():
    manifest=ROOT/"audit/image-catalog/manifest/2026-01.tsv"
    text=manifest.read_text(encoding="utf-8")
    assert text.startswith("path\tgit_blob_sha\tsize_bytes\n")
    for image in IMAGES:
        relative="docs/"+image
        sha=subprocess.check_output(["git","hash-object",relative],cwd=ROOT,text=True).strip()
        size=(DOCS/image).stat().st_size
        match=[line for line in text.splitlines() if line.startswith(relative+"\t")]
        wanted=f"{relative}\t{sha}\t{size}"
        if match:assert match==[wanted],(match,wanted)
        else:text=text.rstrip("\n")+"\n"+wanted+"\n"
    save(manifest,text)

def update_home():
    from homepage_demotion import demote_side_cards
    config=ROOT/"content/homepage.json"
    c=json.loads(config.read_text(encoding="utf-8"))
    ticker_before=copy.deepcopy((c["ticker_entries"],c["ticker_slugs"]))
    original_lead=c["ia_slots"]["main"]
    previous_side=c["ia_slots"]["important"][:]
    side=[EU]+[s for s in previous_side if s!=EU][:3]
    c["ia_slots"]["important"]=side
    c["featured"]=[original_lead]+side
    c["latest"]=[s for s in c["latest"] if s!=EU]
    demote_side_cards(c,previous_side)
    assert len(c["latest"])==8
    c["primary_door"][AR]="wildlife"
    door=next(d for d in c["ia_door_sections"] if d["door"]=="wildlife")
    door["slugs"]=[AR]+[s for s in door["slugs"] if s!=AR][:3]
    for label in ("الحياة البرية والتخييم","Wildlife & Camping"):
        c["desk_slugs"][label]=[local_slug(s,"en") if label=="Wildlife & Camping" else s for s in door["slugs"]]
    for key in ("omit_from_latest","omit_from_ticker"):
        c[key]=list(dict.fromkeys(c[key]+[AR,INTL]))
    c.setdefault("card_image_overrides",{})[AR]={"image":IMAGE,"cache_version":MEDIA_VERSION,"position":"50% 50%","alt":{lang:DATA[lang]["alts"][0] for lang in ("ar","en","fr")}}
    assert (c["ticker_entries"],c["ticker_slugs"])==ticker_before
    save(config,json.dumps(c,ensure_ascii=False,indent=2)+"\n")

def add_sitemap():
    file=DOCS/"sitemap.xml"
    source=file.read_text(encoding="utf-8")
    for lang in ("ar","en","fr"):
        entry=public(lang)
        if "<loc>"+entry+"</loc>" not in source:
            source=source.replace("</urlset>","  <url><loc>"+entry+"</loc><lastmod>"+DATE+"</lastmod></url>\n</urlset>")
    save(file,source)

def main():
    assert all(len(DATA[l]["paragraphs"])==5 for l in ("ar","en","fr"))
    assert all((DOCS/image).is_file() for image in IMAGES)
    pairs=ROOT/"content/en/pairs.json"
    p=json.loads(pairs.read_text())
    assert p["pairs"].get(AR,INTL)==INTL
    p["pairs"][AR]=INTL
    save(pairs,json.dumps(p,ensure_ascii=False,indent=2)+"\n")
    paths={}
    for lang in ("ar","en","fr"):
        paths[lang]=render_article(lang)
        pref="" if lang=="ar" else lang
        insert_listing(lang,DOCS/pref/"category/حياة-برية-وتخييم/index.html")
        insert_listing(lang,DOCS/pref/("articles" if lang=="ar" else "stories")/"index.html")
    update_home()
    update_image_manifest()
    add_sitemap()
    refresh_home()
    twins=load_twins(DOCS)
    for lang,p in paths.items():
        out=apply_html(p.read_text(encoding="utf-8"),p,DOCS,p.relative_to(DOCS),twins)
        save(p,"\n".join(line.rstrip() for line in out.splitlines())+"\n")
    from sync_tickers import sync
    assert sync(DOCS,check=True)[1]==0
    for lang,p in paths.items():
        h=html.parse(str(p))
        assert h.xpath('//head/link[@rel="canonical"]/@href')==[public(lang)]
        assert len(h.xpath('//head/link[@hreflang]'))==4
    print("Dubai published to 3 Wildlife mirrors; Europe promoted below lead; ticker preserved.")

if __name__=="__main__":main()
