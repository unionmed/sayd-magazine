#!/usr/bin/env python3
"""Owner-approved TikTok social chrome, without article or homepage-placement edits."""
import json, os, re, subprocess
from pathlib import Path
from lxml import html
from header_social import add_approved_tiktok
from refresh_homepage_doors import DOCS, ROOT
from check_publication_contract import CONTRACT


def run(base=None):
    base=base or os.environ.get('SAYD_BASE_COMMIT','591e345812138cb1a145d49a4a6c721b200ed99c')
    contract=json.loads(CONTRACT.read_text())
    expected=[url for key,url in contract['header_social']['links']]
    groups=0;headerless=0
    for path in DOCS.rglob('*.html'):
        current=path.read_text();tree=html.fromstring(current)
        lang=path.relative_to(DOCS).parts[0];lang=lang if lang in ('en','fr') else 'ar'
        assert add_approved_tiktok(current,lang)==current,path
        navs=tree.xpath('//nav[@class="header-social"]')
        if 'class="container mast-top-inner"' in current:
            assert len(navs)==1,path
        else:
            headerless+=1
            assert not navs,path
        for nav in tree.xpath('//nav[@class="header-social"]'):
            groups+=1
            anchors=nav.xpath('./a')
            if lang=='fr':
                assert nav.get('aria-label') in ('Suivez Sayd','Suivre Sayd'),path
                assert nav.xpath('./a/span/text()')==['Instagram','Facebook','YouTube','TikTok'],path
            assert [a.get('href') for a in anchors]==expected,path
            assert len(nav.xpath('./a[@class="social-tiktok"]'))==1,path
            for anchor in anchors:
                assert anchor.get('target')=='_blank',path
                assert set(anchor.get('rel','').split())=={'noopener','noreferrer'},path
                assert anchor.get('aria-label','').strip() and anchor.xpath('./svg[@aria-hidden="true"]'),path
    # Public baseline only: connector commits may squash local development history.
    # Compare social markup exactly on every original page, and the complete
    # deterministic approved chrome transform on articles. Homepage/collection
    # changes remain subject to their separate full publication/preservation gate.
    from rollout_mobile_nav_heritage_20261015 import nav_replace
    from build_site_search import links
    social=re.compile(r'<nav class="header-social"[^>]*>.*?</nav>',re.S)
    names=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',base,'--','docs'],cwd=ROOT).decode().split('\0')
    for name in filter(None,names):
        path=ROOT/name
        if path.suffix!='.html':continue
        assert path.is_file(),f'Original route removed: {name}'
        before=subprocess.check_output(['git','show',f'{base}:{name}'],cwd=ROOT).decode()
        current=path.read_text()
        lang=path.relative_to(DOCS).parts[0];lang=lang if lang in ('en','fr') else 'ar'
        approved=add_approved_tiktok(before,lang)
        assert social.findall(approved)==social.findall(current),f'Non-approved social edit: {name}'
        if '/posts/' in name:
            from sync_tickers import TICKER
            # Shared ticker changes are validated separately by sync_tickers and the publication contract.
            assert TICKER.sub('',links(nav_replace(before,path)[0],path))==TICKER.sub('',current),f'Non-approved article edit: {name}'
    # The additive helper cannot alter article/head bytes, even when creating a
    # previously absent group. Keep these fixtures independent of Git history.
    for lang in ('ar','en','fr'):
        for original in ['<head>unchanged</head><main>legacy article</main>',
                         '<head>unchanged</head><div class="container mast-top-inner"></div><article>unchanged body</article>',
                         '<div class="container mast-top-inner"><nav class="header-social" aria-label="existing"><a href="https://example.test">existing</a></nav></div><article>unchanged body</article>']:
            approved=add_approved_tiktok(original,lang)
            assert add_approved_tiktok(approved,lang)==approved
            assert social.sub('',approved)==social.sub('',original)
            for changed in (approved+'<p>unapproved</p>',approved.replace('unchanged','changed',1)):
                assert changed!=approved
                assert changed!=add_approved_tiktok(original,lang),'Non-social mutation accepted'
    for lang,prefix,slug in [('ar','','ألكسندرا-cabs-الصيد-غير-القانوني'),('en','en','alexandra-cabs-illegal-hunting-interview'),('fr','fr','alexandra-cabs-illegal-hunting-interview')]:
        page=html.parse(str(DOCS/prefix/'index.html'))
        cards=page.xpath('//article[.//a[contains(@href,"posts/'+slug+'/")]]')
        assert len(cards)==1,(lang,'Alexandra duplicated or removed')
        section=cards[0].xpath('ancestor::section[@class="home-section"]')
        assert len(section)==1 and section[0].xpath('./div/h2/text()')==[{'ar':'مقابلات','en':'Interviews','fr':'Entretiens'}[lang]]
        assert (DOCS/prefix/'posts'/slug/'index.html').is_file()
    from header_social import apply
    generated=html.fromstring(apply('<div class="container mast-top-inner"></div>','fr'))
    assert generated.xpath('.//nav/@aria-label')==['Suivez Sayd']
    assert generated.xpath('.//nav/a/span/text()')==['Instagram','Facebook','YouTube','TikTok']
    assert groups==1034 and headerless==823,(groups,headerless)
    print(f'PASS: {groups} four-icon social groups, {headerless} headerless shells preserved, accessible secure TikTok links, exact chrome-only changes, Alexandra shown once under Interviews with original URLs')

if __name__=='__main__':run()
