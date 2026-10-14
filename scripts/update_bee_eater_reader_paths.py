#!/usr/bin/env python3
"""Apply reviewed bee-eater copy and contextual reading paths, without a site rebuild.

Source: content/features/bee-eater-reader-paths.json. Run after any legacy
WXR/edition rebuild; this intentionally does not move homepage cards or tickers.
"""
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote
import article_dates
import seo_foundation as seo
from build_fr_edition import listing_card

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
DATA = json.loads((ROOT / 'content/features/bee-eater-reader-paths.json').read_text())
IMAGE = 'media/uploads/2025/09/AP4I0956-1024x683.jpg'
REPORT = {'ar': 'سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف', 'en': 'skies-losing-balance-birdlife-flyways-report', 'fr': 'skies-losing-balance-birdlife-flyways-report'}

def replace_one(pattern, replacement, text):
    result, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)
    assert count == 1, pattern
    return result

def switch(lang):
    return '\n'.join(f'<a href="/{"" if code == "ar" else code + "/"}posts/{d["slug"]}/index.html" lang="{code}" hreflang="{code}"' + (' class="is-current" aria-current="page"' if code == lang else '') + f'>{label}</a>' for (code,d),label in zip(DATA.items(), ['العربية','English','Français']))

def apply():
    if (ROOT / "content/features/arab-bird-encyclopedia-20261014.json").exists():
        from publish_arab_bird_encyclopedia_20261014 import apply as current_update
        current_update(only_bee=True)
        return
    paths = []
    for lang, d in DATA.items():
        prefix = '' if lang == 'ar' else lang
        path = DOCS / prefix / 'posts' / d['slug'] / 'index.html'
        if path.exists():
            text = path.read_text()
        else:
            assert lang == 'fr'
            text = (DOCS/'fr/posts/common-kestrel/index.html').read_text()
            text = replace_one(r'<h1>.*?</h1>', f'<h1>{d["title"]}</h1>', text)
            text = replace_one(r'<div class="article-meta">.*?</div>', '<div class="article-meta"><span class="meta-item">17 septembre 2025</span><span class="meta-item">Sayd</span></div>', text)
            text = re.sub(r'<section class="related-block">.*?</section>', '', text, flags=re.S)
            path.parent.mkdir(parents=True, exist_ok=True)
        if lang == 'fr':
            # The inherited template percent-encodes this breadcrumb href.
            # SEO canonicalization quotes paths, so retain the literal slug here.
            category = 'موسوعة-الطيور'
            text = text.replace('../../category/' + quote(category) + '/index.html', '../../category/' + category + '/index.html')
        depth = '../../' if lang == 'ar' else '../../../'
        image = f'<figure><img src="{depth}{IMAGE}" alt="{escape(d["alt"], quote=True)}" width="1024" height="683" decoding="async"><figcaption>{d["title"]} (<em>Merops apiaster</em>).</figcaption></figure>'
        if lang == 'en':
            oldbody = re.search(r'<article class="article-content">(.*?)</article>', text, re.S)[1]
            oldimage = re.search(r'<figure>.*?</figure>', oldbody, re.S)
            if oldimage:
                image = re.sub(r'alt="[^"]*"', f'alt="{d["alt"]}"', oldimage[0])
        if lang == 'ar':
            # Preserve the existing photo block and introductory visual treatment.
            oldbody = re.search(r'<article class="article-content">(.*?)</article>', text, re.S)[1]
            oldimage = re.search(r'<p dir="rtl"><a .*?</p>', oldbody, re.S)
            if oldimage:
                image = re.sub(r'alt="[^"]*"', f'alt="{d["alt"]}"', oldimage[0])
        body = image + '\n' + '\n'.join('<p'+(' dir="rtl" style="text-align: justify;"' if lang == 'ar' else '')+'>'+p+'</p>' for p in d['body'])
        if lang == 'ar':
            intro = ['طائر الوروار الأوروبي (<em>Merops apiaster</em>)، ويُعرف بالإنكليزية باسم European Bee-eater،', 'هو طائر مهاجر شائع في لبنان. وقد سُجّل وجوده في عدّة مناطق لبنانية خلال فصل الصيف،', 'مما يطرح احتمال أن يكون من الطيور المفرِّخة في البلاد أيضًا.']
            old = '<p dir="rtl" style="text-align: justify;">' + d['body'][0] + '</p>'
            body = body.replace(old, '\n'.join('<p dir="rtl" style="text-align: center;"><span style="font-size: 18px; color: #333300;">'+part+'</span></p>' for part in intro), 1)
        body += f'\n<p><strong>{d["read_label"]}:</strong> ' + ' · '.join(f'<a href="../{slug}/index.html">{label}</a>' for slug,label in d['links']) + '</p>\n'
        text = replace_one(r'(<article class="article-content">).*?</article>', '<article class="article-content">\n'+body+'</article>', text)
        text = replace_one(r'<title>.*?</title>', f'<title>{escape(d["seo_title"])}</title>', text)
        text = replace_one(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{escape(d["description"], quote=True)}">', text)
        text = re.sub(r'(\<nav class="lang-switch"[^>]*>).*?</nav>', lambda m: m[1] + switch(lang) + "</nav>", text, count=1, flags=re.S)
        text = article_dates.patch(text, '2026-10-12', lang)
        path.write_text(text)
        paths.append(path)
    # Wire the same contextual link in all three BirdLife captions.
    names = {'ar':'الوروار الأوروبي المهاجر', 'en':'Migratory European bee-eaters', 'fr':'Guêpiers d’Europe migrateurs'}
    for lang, name in names.items():
        path = DOCS / ('' if lang == 'ar' else lang) / 'posts' / REPORT[lang] / 'index.html'
        text = path.read_text()
        def caption(m):
            if f'../{DATA[lang]["slug"]}/index.html' in m[0]: return m[0]
            return m[0].replace(name, f'<a href="../{DATA[lang]["slug"]}/index.html">{name}</a>', 1)
        text, count = re.subn(r'<figcaption\b[^>]*>'+re.escape(name)+r'.*?</figcaption>', caption, text, flags=re.S)
        assert count == 1 or f'../{DATA[lang]["slug"]}/index.html' in text
        path.write_text(article_dates.patch(text, '2026-10-12', lang))
        paths.append(path)
    # Add the 2025 archive item after newer French cards; no homepage slot changes.
    d = DATA['fr']
    card = listing_card({'slug':d['slug'], 'title':d['title'], 'alt':d['alt'], 'date':'17 September 2025', 'image':'/'+IMAGE})
    for rel in ['fr/stories/index.html','fr/category/موسوعة-الطيور/index.html']:
        path = DOCS / rel
        text = path.read_text()
        if f'/fr/posts/{d["slug"]}/' not in text:
            end = text.rfind('</article>')
            assert end >= 0
            text = text[:end+len('</article>')] + '\n' + card + text[end+len('</article>'):]
            path.write_text(text)
    twins = seo.load_twins(DOCS)
    for path in paths:
        text = path.read_text()
        # Refresh only the managed SEO block; leave layout/chrome helpers alone.
        block = seo.seo_block(text, path, DOCS, path.relative_to(DOCS), twins)
        text = seo.SEO_BLOCK_RE.sub(lambda m: block, text)
        path.write_text(text)
    # Extend the existing sitemap in chronological-neutral URL form only.
    path = DOCS/'sitemap.xml'
    text = path.read_text()
    url = 'https://sayd-magazine.com/fr/posts/european-bee-eater/'
    if url not in text:
        text = text.replace('</urlset>', f'  <url><loc>{url}</loc></url>\n</urlset>')
    for page in paths:
        url = seo.public_url(page.relative_to(DOCS))
        pattern = r'<url>\s*<loc>' + re.escape(url) + r'</loc>.*?</url>'
        text, count = re.subn(pattern, lambda m: '<url><loc>'+url+'</loc><lastmod>2026-10-12</lastmod></url>', text, flags=re.S)
        assert count == 1, url
    path.write_text(text)
    print('Updated three bee-eater mirrors and BirdLife captions; preserved homepage/tickers.')

if __name__ == '__main__': apply()
