#!/usr/bin/env python3
"""Publish Nayef-approved Akkar field story, three mirrors, Updates, hunting category, ticker.
Use only from the dedicated publishing branch. Image is original CABS event photo.
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

DATA=json.loads((ROOT/"content/features/akkar-sparrowhawk-20261012.json").read_text(encoding="utf-8"))
PHOTO=json.loads((ROOT/"notes/akkar-cabs-original-photo-20261012.json").read_text(encoding="utf-8"))
AR=DATA["slug_ar"]; INTL=DATA["slug_intl"]
IMAGE=PHOTO["local_path"].removeprefix("docs/")
assert IMAGE=="media/uploads/2026/10/akkar-cabs-raptor-operation.jpg"
assert (DOCS/IMAGE).is_file() and (DOCS/IMAGE).stat().st_size==PHOTO["bytes"]
DATE=DATA["date"]
DATES={"ar":"12 تشرين الأول 2026","en":"12 October 2026","fr":"12 octobre 2026"}
NAMES={"ar":"صيد","en":"Hunting","fr":"Chasse"}
AUTHORS={"ar":"مجلة صيد","en":"Sayd Magazine","fr":"Sayd Magazine"}
SLUG_BY_LANG={"ar":AR,"en":INTL,"fr":INTL}
SRC_BY_LANG={"ar":"ألكسندرا-cabs-الصيد-غير-القانوني","en":"alexandra-cabs-illegal-hunting-interview","fr":"alexandra-cabs-illegal-hunting-interview"}

def cls(root, name):
    return root.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " '+name+' ")]')

def public(lang):
    prefix="" if lang=="ar" else lang+"/"
    return "https://sayd-magazine.com/"+prefix+"posts/"+quote(SLUG_BY_LANG[lang])+"/"

def save(path, text):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8")

def related(lang):
    prefix="../../" if lang=="ar" else "../../../"
    related_ar=["البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs","ألكسندرا-cabs-الصيد-غير-القانوني"]
    labels={
        "ar":["شباك البقاع الشمالي: حصيلة إزالة 38,280 مترًا مربعًا","ألكسندرا من CABS تتحدث عن العمل الميداني في لبنان"],
        "en":["Northern Bekaa: 38,280 square metres of illegal nets removed","Alexandra of CABS on her fieldwork in Lebanon"],
        "fr":["Nord de la Bekaa : 38 280 m² de filets illégaux retirés","Alexandra de CABS raconte son travail de terrain au Liban"]
    }
    list_items=[]
    for original,title in zip(related_ar,labels[lang]):
        target=local_slug(original,lang)
        assert (DOCS/("" if lang=="ar" else lang+"/")/"posts"/target/"index.html").is_file(),target
        list_items.append('<li><a href="'+prefix+("" if lang=="ar" else lang+"/")+'posts/'+quote(target)+'/index.html">'+esc.escape(title)+'</a></li>')
    return '<section class="article-more"><h2>'+esc.escape(DATA[lang]["related_heading"])+'</h2><ul>'+"".join(list_items)+'</ul></section>'

def body(lang):
    d=DATA[lang]
    prefix="../../" if lang=="ar" else "../../../"
    b=['<figure style="max-width:350px;margin:18px auto 24px;">',
       '<img src="'+prefix+IMAGE+'" width="350" height="233" alt="'+esc.escape(d["hero_alt"],quote=True)+'" decoding="async" style="display:block;width:100%;height:auto">',
       '<figcaption>'+esc.escape(d["photo_caption"])+'</figcaption></figure>',
       '<p class="article-deck"><strong>'+esc.escape(d["deck"])+'</strong></p>']
    for i,paragraph in enumerate(d["paragraphs"]):
        if i==4: b.append('<h2>'+esc.escape(paragraph)+'</h2>')
        else: b.append('<p>'+esc.escape(paragraph)+'</p>')
    b.append(related(lang))
    b.append('<p class="photo-source"><small>'+esc.escape(d["photo_credit"])+'</small></p>')
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
        tag.set("content","https://sayd-magazine.com/"+IMAGE)
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
        tag.set("href","../../category/"+quote("صيد")+"/index.html")
        tag.text=NAMES[lang]
    for tag in cls(root,"breadcrumb")[0].xpath('.//a[contains(@href,"category/")]'):
        tag.set("href","../../category/"+quote("صيد")+"/index.html")
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
        "datePublished":DATE,"dateModified":DATE,
        "author":{"@type":"Organization","name":"Sayd Magazine"},
        "image":["https://sayd-magazine.com/"+IMAGE],
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
           "\ncategories: [صيد]\nfeatured: "+IMAGE+
           "\nsubtitle: "+json.dumps(d["deck"],ensure_ascii=False)+"\n---\n\n")
    save(src,front+body(lang)+"\n")
    return page

def insert_listing(lang,page):
    d=DATA[lang]
    path=Path(page)
    text=path.read_text(encoding="utf-8")
    slug=SLUG_BY_LANG[lang]
    # Avoid duplicate cards if the one-shot writer is retried.
    candidate=re.compile(r'<article\b[^>]*>.*?</article>',re.S)
    text=candidate.sub(lambda m:"" if slug in m.group() else m.group(),text)
    m=re.search(r'<article\b[^>]*class="(?:post-row|card)"',text)
    if not m:raise RuntimeError("Missing archive listing anchor "+str(path))
    href=os.path.relpath(DOCS/("" if lang=="ar" else lang)/"posts"/slug/"index.html",path.parent)
    image=os.path.relpath(DOCS/IMAGE,path.parent)
    row=(
        '<article class="post-row"><a class="thumb" href="'+esc.escape(href,quote=True)+'">'
        '<img src="'+esc.escape(image,quote=True)+'" alt="'+esc.escape(d["hero_alt"],quote=True)+'" loading="lazy"></a>'
        '<div class="body"><h2><a href="'+esc.escape(href,quote=True)+'">'+esc.escape(d["title"])+'</a></h2>'
        '<div class="meta">'+DATES[lang]+'</div><p class="excerpt">'+esc.escape(d["deck"])+'</p></div></article>\n'
    )
    if 'class="card"' in m.group():row=row.replace('class="post-row"','class="card"')
    save(path,text[:m.start()]+row+text[m.start():])

def update_image_manifest():
    manifest=ROOT/"audit/image-catalog/manifest/2026-01.tsv"
    relative="docs/"+IMAGE
    sha=subprocess.check_output(["git","hash-object",relative],cwd=ROOT,text=True).strip()
    size=(DOCS/IMAGE).stat().st_size
    text=manifest.read_text(encoding="utf-8")
    assert text.startswith("path\tgit_blob_sha\tsize_bytes\n")
    match=[line for line in text.splitlines() if line.startswith(relative+"\t")]
    wanted=f"{relative}\t{sha}\t{size}"
    if match:
        assert match==[wanted],(match,wanted)
    else:save(manifest,text.rstrip("\n")+"\n"+wanted+"\n")

def update_home():
    config=ROOT/"content/homepage.json"
    c=json.loads(config.read_text(encoding="utf-8"))
    original_featured=c["featured"][:]
    c["primary_door"][AR]="hunting"
    c["latest"]=[AR]+[s for s in c["latest"] if s!=AR][:7]
    c["ia_slots"]["latest"]=c["latest"][:]
    assert c["featured"]==original_featured
    # Preserve approved article circulation through Updates first.
    entry={"slug":AR,"titles":{
        "ar":"عكار: باشق داخل حقيبة ظهر خلال عملية لمكافحة صيد الجوارح",
        "en":"Akkar: Sparrowhawk found inside backpack during raptor anti-poaching operation",
        "fr":"Akkar : un épervier découvert dans un sac à dos lors d’une opération anti-braconnage"
    }}
    c["ticker_entries"]=[entry]+[x for x in c["ticker_entries"] if x["slug"]!=AR]
    c["ticker_slugs"]=[x["slug"] for x in c["ticker_entries"]]
    c.setdefault("card_image_overrides",{})[AR]={"image":IMAGE,"position":"center center","alt":{lang:DATA[lang]["hero_alt"] for lang in ("ar","en","fr")}}
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
    assert all(len(DATA[l]["paragraphs"])==8 for l in ("ar","en","fr"))
    assert not (DOCS/"posts"/AR/"index.html").exists(), "Article already published: do not duplicate"
    pairs=ROOT/"content/en/pairs.json"
    p=json.loads(pairs.read_text())
    assert AR not in p["pairs"],"Arabic slug already paired"
    p["pairs"][AR]=INTL
    save(pairs,json.dumps(p,ensure_ascii=False,indent=2)+"\n")
    paths={}
    for lang in ("ar","en","fr"):
        paths[lang]=render_article(lang)
        pref="" if lang=="ar" else lang
        insert_listing(lang,DOCS/pref/"category/صيد/index.html")
        insert_listing(lang,DOCS/pref/("articles" if lang=="ar" else "stories")/"index.html")
    update_home()
    update_image_manifest()
    add_sitemap()
    refresh_home()  # three homepages + all shared tickers + rotation + shortcuts
    twins=load_twins(DOCS)
    for lang,p in paths.items():
        out=apply_html(p.read_text(encoding="utf-8"),p,DOCS,p.relative_to(DOCS),twins)
        save(p,out)
    from refresh_related_reading import main as refresh_reading
    refresh_reading()
    # New pages contain BOTH ticker loops matching the language home.
    from sync_tickers import sync
    assert sync(DOCS,check=True)[1]==0
    for lang,p in paths.items():
        h=html.parse(str(p))
        assert h.xpath('//head/link[@rel="canonical"]/@href')==[public(lang)]
        assert len(h.xpath('//head/link[@hreflang]'))==4,(lang,h.xpath('//head/link[@hreflang]/@hreflang'))
        assert "sparrowhawk" in h.getroot().text_content().lower() if lang=="en" else True
    print("AKKAR APPROVED ARTICLE GENERATED: 3 mirrors, category/archives, 8 Updates, all-page tickers, SEO, sitemap, media manifest.")

if __name__=="__main__":
    main()
