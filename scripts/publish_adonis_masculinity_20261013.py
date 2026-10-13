#!/usr/bin/env python3
"""Publish Nayef-approved Adonis opinion, three mirrors, first side card, no ticker.
Use only from the dedicated publishing branch. Article cover and inset are local, full-frame photographs.
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

DATA=json.loads((ROOT/"content/features/adonis-masculinity-20261013.json").read_text(encoding="utf-8"))
AR=DATA["slug_ar"]; INTL=DATA["slug_intl"]
IMAGE="media/uploads/2026/10/anti-poaching-four-photo-collage-october-2026.jpg"
INSET_IMAGE="media/uploads/2026/10/apu-mecshap-cabs-lebanon-05.jpg"
assert (DOCS/IMAGE).is_file()
DATE=DATA["date"]
DATES={"ar":"13 تشرين الأول 2026","en":"13 October 2026","fr":"13 octobre 2026"}
NAMES={"ar":"صيد","en":"Hunting","fr":"Chasse"}
AUTHORS={"ar":"أدونيس الخطيب، رئيس التحرير","en":"Adonis Alkhateeb, Editor-in-Chief","fr":"Adonis Alkhateeb, rédacteur en chef"}
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
    path.write_text("\n".join(line.rstrip() for line in text.splitlines())+"\n",encoding="utf-8")

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
    def figure(image, width, height, alt, caption, lazy=False):
        return ('<figure style="width:100%;margin:18px 0 24px;">\n'
                '<img src="'+prefix+image+'" width="'+str(width)+'" height="'+str(height)+'" alt="'+esc.escape(alt,quote=True)+'" decoding="async"'+(' loading="lazy"' if lazy else '')+' style="display:block;width:100%;height:auto;">\n'
                '<figcaption>'+esc.escape(caption)+'</figcaption></figure>')
    b=[figure(IMAGE,1024,1280,d["hero_alt"],d["photo_caption"])]
    for index,paragraph in enumerate(d["paragraphs"],1):
        b.append('<p>'+esc.escape(paragraph)+'</p>')
        if index==6:
            b.append(figure(INSET_IMAGE,1241,1536,d["inset_alt"],d["inset_caption"],lazy=True))
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
        tag.set("content",d["excerpt"])
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
    for tag in cls(root,"article-updated"):tag.getparent().remove(tag)
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
    for name in ("article-featured","related-block","article-more"):
        for tag in cls(root,name):tag.getparent().remove(tag)
    article.addnext(html.fragment_fromstring(related(lang)))
    for tag in root.xpath('//script[@type="application/ld+json"]'):tag.getparent().remove(tag)
    schema={
        "@context":"https://schema.org","@type":"OpinionNewsArticle",
        "headline":d["title"],"description":d["excerpt"],"inLanguage":lang,
        "datePublished":DATA["published_at"],"dateModified":DATA["published_at"],
        "author":{"@type":"Person","name":AUTHORS[lang].split(",")[0].split("،")[0],"jobTitle":{"ar":"رئيس التحرير","en":"Editor-in-Chief","fr":"rédacteur en chef"}[lang],"url":"https://sayd-magazine.com/"+({"ar":"pages/"+quote("من-نحن")+"/","en":"en/team/","fr":"fr/team/"}[lang])},
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
           "\nsubtitle: "+json.dumps(d["excerpt"],ensure_ascii=False)+"\n---\n\n")
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
    image=os.path.relpath(DOCS/INSET_IMAGE,path.parent)
    row=(
        '<article class="post-row"><a class="thumb" href="'+esc.escape(href,quote=True)+'">'
        '<img src="'+esc.escape(image,quote=True)+'" alt="'+esc.escape(d["inset_alt"],quote=True)+'" loading="lazy" style="object-fit:contain"></a>'
        '<div class="body"><h2><a href="'+esc.escape(href,quote=True)+'">'+esc.escape(d["title"])+'</a></h2>'
        '<div class="meta">'+DATES[lang]+'</div><p class="excerpt">'+esc.escape(d["excerpt"])+'</p></div></article>\n'
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
    before_ticker={k:c[k] for k in ("ticker_entries","ticker_slugs")}
    old=c["featured"][:]
    assert AR not in old
    c["featured"]=[old[0],AR]+old[1:4]
    c["ia_slots"]["important"]=c["featured"][1:]
    # The displaced side card enters Updates by its original publication date.
    # Original dates: Akkar 12 Oct, Coast 6 Oct, then the existing older Updates.
    c["latest"]=[c["latest"][0],old[4]]+c["latest"][1:7]
    c["ia_slots"]["latest"]=c["latest"][:]
    c["primary_door"][AR]="hunting"
    for slug in (AR,INTL):
        if slug not in c["omit_from_ticker"]:c["omit_from_ticker"].append(slug)
    c.setdefault("card_image_overrides",{})[AR]={"image":INSET_IMAGE,"position":"center 10%","fit":"cover","alt":{lang:DATA[lang]["inset_alt"] for lang in ("ar","en","fr")}}
    assert before_ticker=={k:c[k] for k in before_ticker}
    assert c["ia_slots"]["main"]==old[0]
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
    assert all(len(DATA[l]["paragraphs"])==18 for l in ("ar","en","fr"))
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
    # New pages contain BOTH ticker loops matching the language home.
    from sync_tickers import sync
    assert sync(DOCS,check=True)[1]==0
    for lang,p in paths.items():
        h=html.parse(str(p))
        assert h.xpath('//head/link[@rel="canonical"]/@href')==[public(lang)]
        assert len(h.xpath('//head/link[@hreflang]'))==4,(lang,h.xpath('//head/link[@hreflang]/@hreflang'))
        assert AR not in " ".join(h.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ticker ")]//a/@href'))
    print("ADONIS APPROVED OPINION GENERATED: 3 mirrors, category/archives, first side card, unchanged tickers, SEO, sitemap, existing media verified.")

if __name__=="__main__":
    main()
