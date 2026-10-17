#!/usr/bin/env python3
"""Search page, regeneration, exact chrome-only gate and archive invariants."""
import hashlib, json, os, re, subprocess
from pathlib import Path
from unittest.mock import patch
from lxml import html
import build_site_search as search
import check_publication_contract as contract
import seo_foundation as seo
from rollout_mobile_nav_heritage_20261015 import nav_replace
ROOT=search.ROOT
BASE=os.environ.get('SAYD_BASE_COMMIT','591e345812138cb1a145d49a4a6c721b200ed99c')

def run():
    for lang,route in search.ROUTES.items():
        path=search.DOCS/route/'index.html'; text=path.read_text(); tree=html.fromstring(text)
        assert tree.get('lang')==lang
        assert not tree.xpath('//script[contains(@src,"googletag") or contains(@src,"analytics")]')
        assert 'gtag(' not in text
        assert tree.xpath('//meta[@name="robots"]/@content')==['noindex,follow']
        assert not tree.xpath('//head/link[@hreflang]')
        assert len(tree.xpath('//nav[@class="lang-switch"]/a')) == 3
        # Search resource hints and stylesheets must remain same-origin. Follow
        # local CSS imports so an inherited font import cannot bypass this check.
        assert not tree.xpath('//link[starts-with(@href,"http") and (@rel="stylesheet" or @rel="preconnect" or @rel="dns-prefetch" or @rel="preload")]')
        pending = [((search.DOCS / href.lstrip('/')) if href.startswith('/') else (path.parent / href)).resolve()
                   for href in (h.split('?', 1)[0] for h in tree.xpath('//link[@rel="stylesheet"]/@href'))]
        checked = set()
        while pending:
            css_path = pending.pop()
            if css_path in checked: continue
            checked.add(css_path)
            css = css_path.read_text()
            refs = re.findall(r'url\(\s*[\"\']?([^\"\')\s]+)', css, re.I)
            imports = re.findall(r'@import\s+[\"\']([^\"\']+)', css, re.I)
            for ref in refs + imports:
                assert not ref.startswith(('http:', 'https:', '//')), (css_path, ref)
                if not ref.startswith(('data:', '#')) and (ref in imports or ref.split('?',1)[0].endswith('.css')):
                    pending.append(((search.DOCS / ref.lstrip('/')) if ref.startswith('/') else (css_path.parent / ref)).resolve())
        assert tree.xpath('//meta[@name="referrer"]/@content')==['no-referrer']
        assert len(tree.xpath('//form[@role="search"]'))==1
        assert not tree.xpath('//form/@action | //input/@name')
        assert len(tree.xpath('//*[@id="search-query"]'))==1
        assert seo.apply_html(text,path,search.DOCS,path.relative_to(search.DOCS),{})==text
        assert search.links(text,path)==text
        for href in tree.xpath('//nav[@class="lang-switch"]/a/@href'):
            assert (path.parent/href).resolve().is_file(),href
    # Every old HTML URL survives; only exact approved link/style additions allowed.
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',BASE,'docs'],cwd=ROOT).decode().split('\0')
    count=0
    for name in paths:
        if not name.endswith('.html'):continue
        path=ROOT/name; assert path.exists(),name
        old=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT).decode()
        current=path.read_text()
        # Article pages admit only the exact approved UI/navigation transform.
        # Homepage/archive collection changes have dedicated publication tests.
        if '/posts/' in name:
            assert current==search.links(nav_replace(old,path)[0],path),(name,'non-UI article change')
            count+=1
        if '/posts/' in name and current!=old:
            assert contract.ten_door_navigation_only_repair(name,BASE)
    assert count>800
    name='docs/posts/أبو-حناء-الحدائق/index.html'
    if not (ROOT/name).exists():name=next(p for p in paths if '/posts/' in p and 'article-content' in (ROOT/p).read_text())
    path=ROOT/name; original=path.read_text()
    # The exemption must reject changed article body, title, metadata and extra links.
    for extra in ['<p>unauthorized body</p>','<script>alert(1)</script>','<a href="/evil">x</a>']:
        with patch.object(Path,'read_text',lambda self,*a,**kw: original.replace('</body>',extra+'</body>') if self==path else original):
            assert not contract.search_navigation_only_repair(name,BASE)
    assert not contract.search_navigation_only_repair('docs/posts/not-published/index.html',BASE)
    # Full rebuild is deterministic, including search pages copied from chrome.
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in search.DOCS.rglob('*') if p.is_file() and (p.suffix in ('.html','.json') or 'search' in p.name)}
    search.main()
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in before.items()),'non-idempotent generation'
    for name in ('css/search-entry.css','css/search.css','js/site-search.js'):
        assert (ROOT/'assets'/name).read_bytes()==(search.DOCS/'assets'/name).read_bytes()
    print(f'PASS: trilingual search, privacy, SEO regeneration, {count} preserved article pages, URL preservation, strict chrome gate and deterministic build')
if __name__=='__main__':run()
