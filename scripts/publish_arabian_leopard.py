#!/usr/bin/env python3
"""Publish the approved bilingual Sayd TV video, without visible date or extra copy."""
import html
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
AR = 'بالفيديو-النمر-العربي-في-السعودية'
EN = 'video-arabian-leopard-in-saudi-arabia'
TITLES = ['بالفيديو… النمر العربي في السعودية', 'Video… The Arabian Leopard in Saudi Arabia']
SOURCES = ['المصدر: الهيئة الملكية لمحافظة العلا', 'Source: Royal Commission for AlUla']
IMAGE = 'media/video/arabian-leopard.jpg'
VIDEO = 'media/video/arabian-leopard.mp4'
ORIGINAL = 'https://cp.slaati.com//wp-content/uploads/2024/12/X2Twitter.com_2TpGD8y182qaYtA1_720p.mp4'

def main():
    for i, (prefix, slug, old, twin) in enumerate([('', AR, 'بالفيديو-مقناص-سعود-عبد-العزيز-الباب', EN), ('en/', EN, 'video-saud-al-babtain-maqnas-afghanistan', AR)]):
        title, source = TITLES[i], SOURCES[i]
        depth = '../../../' if prefix else '../../'
        page = (DOCS / prefix / 'posts' / old / 'index.html').read_text()
        old_title = re.search(r'<h1>(.*?)</h1>', page, re.S)[1]
        page = page.replace(old_title, title).replace(old, slug)
        page = page.replace('بالفيديو-مقناص-سعود-عبد-العزيز-الباب' if prefix else 'video-saud-al-babtain-maqnas-afghanistan', twin)
        page = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m[1]+html.escape(title+' — '+source, quote=True), page, count=1)
        page = re.sub(r'<div class="article-meta">.*?</div>', '', page, flags=re.S)
        body = f'<video controls playsinline preload="metadata" poster="{depth}{IMAGE}" style="display:block;width:100%;height:auto;aspect-ratio:16/9;background:#000" aria-label="{title}"><source src="{depth}{VIDEO}" type="video/mp4"><img src="{depth}{IMAGE}" alt="{title}"></video>\n<p>{source}</p>'
        page = re.sub(r'(<article class="article-content">).*?(</article>)', lambda m:m[1]+'\n'+body+'\n'+m[2], page, count=1, flags=re.S)
        page = re.sub(r'<section class="related-block">.*?</section>', '', page, flags=re.S)
        dest = DOCS / prefix / 'posts' / slug / 'index.html'
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(page)
        for archive in (False, True):
            path = DOCS / prefix / ('stories' if prefix else 'articles') / 'index.html' if archive else DOCS / prefix / 'category/استديو-صيد/index.html'
            listing = path.read_text()
            listing = re.sub(r'<article\b[^>]*>(?:(?!</article>).)*posts/'+re.escape(slug)+r'/index\.html.*?</article>\s*', '', listing, flags=re.S)
            link = '../posts/' if archive else '../../posts/'
            media = ('../../' if prefix else '../') if archive else depth
            tag = 'h3' if archive and prefix else 'h2'
            klass = 'card overlay' if archive and prefix else 'post-row'
            row = f'<article class="{klass}" data-published="2026-09-29"><a class="thumb" href="{link}{slug}/index.html"><img src="{media}{IMAGE}" alt="{title}" loading="lazy"></a><div class="body"><{tag}><a href="{link}{slug}/index.html">{title}</a></{tag}><p class="excerpt">{source}</p></div></article>\n'
            marker = '<div class="grid-4">' if archive and prefix else '<div class="post-list">'
            assert marker in listing
            # Keep the Babtain film first in Sayd TV.
            if not archive:
                at = listing.index('</article>', listing.index(marker))+len('</article>')
                listing = listing[:at]+'\n'+row+listing[at:]
            else:
                listing = listing.replace(marker, marker+'\n'+row, 1)
            path.write_text(listing)
        content = ROOT / ('content/en' if prefix else 'content/posts') / (slug+'.md')
        content.write_text(f'# {title}\n\n{source}\n\n<!-- Sayd TV; hide publication date. Original media: {ORIGINAL} -->\n')
    pairs_path = ROOT / 'content/en/pairs.json'
    pairs = json.loads(pairs_path.read_text()); pairs['pairs'][AR] = EN
    pairs_path.write_text(json.dumps(pairs,ensure_ascii=False,indent=2)+'\n')
    config_path = ROOT / 'content/homepage.json'
    config = json.loads(config_path.read_text())
    config.setdefault('undated_stories', {}).update(dict(zip((AR,EN),SOURCES)))
    for key in ('omit_from_latest','omit_from_ticker'):
        config[key] = list(dict.fromkeys(config.get(key,[])+[AR,EN]))
    config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')

if __name__ == '__main__': main()
