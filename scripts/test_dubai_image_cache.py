#!/usr/bin/env python3
"""Local image cache keys survive rendering without editorial or placement changes."""
import json,subprocess
from pathlib import Path
from lxml import html
from publish_dubai_safari_20261012 import ROOT, DOCS, AR, INTL, IMAGES, MEDIA_VERSION, media_url
from seo_foundation import _resolve_image

BASE='4e75f77e6c34db1d64ef4c9cdf65fbfda2e6642f'
SUFFIX=('?v='+MEDIA_VERSION).encode()

def previous(path):
    return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)

def main():
    changed=subprocess.check_output(['git','diff','--name-only','-z',BASE],cwd=ROOT).decode().strip('\0').split('\0')
    for name in changed:
        if name.startswith('docs/') and name.endswith('.html'):
            assert (ROOT/name).read_bytes().replace(SUFFIX,b'')==previous(name),name
    c=json.loads((ROOT/'content/homepage.json').read_text());old=json.loads(previous('content/homepage.json'))
    assert c['card_image_overrides'][AR].pop('cache_version')==MEDIA_VERSION
    assert c==old,'Unrelated home placement/config changed'
    for image in IMAGES:
        assert (DOCS/image).read_bytes()==previous('docs/'+image),'Image bytes changed'
    for lang in ('ar','en','fr'):
        prefix='' if lang=='ar' else lang
        page=DOCS/prefix/'posts'/(AR if lang=='ar' else INTL)/'index.html'
        t=html.parse(str(page))
        imgs=t.xpath('//article[@class="article-content"]//img/@src')
        assert len(imgs)==3
        for src,path in zip(imgs,IMAGES):
            assert src.endswith(media_url(path))
            assert _resolve_image(src,page,DOCS)=='https://sayd-magazine.com/'+media_url(path)
        for src in t.xpath('//meta[@property="og:image" or @name="twitter:image"]/@content'):
            assert src=='https://sayd-magazine.com/'+media_url(IMAGES[0])
        schema=next(json.loads(s) for s in t.xpath('//script[@type="application/ld+json"]/text()') if json.loads(s).get('@type')=='NewsArticle')
        assert schema['image']==['https://sayd-magazine.com/'+media_url(p) for p in IMAGES]
    print('PASS: only versioned local Dubai image URLs changed; text, placements, other assets and image bytes preserved; SEO resolver retains cache keys')

if __name__=='__main__':main()
