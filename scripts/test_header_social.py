#!/usr/bin/env python3
"""Owner-approved TikTok social chrome, without article or homepage-placement edits."""
import json, subprocess
from pathlib import Path
from lxml import html
from header_social import add_approved_tiktok
from refresh_homepage_doors import DOCS, ROOT
from check_publication_contract import CONTRACT


def run(base='6778c699'):
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
    changed=subprocess.check_output(['git','diff','--name-only','-z',base,'--','docs'],cwd=ROOT).decode().split('\0')
    for name in filter(None,changed):
        path=ROOT/name
        if path.suffix!='.html':continue
        before=subprocess.check_output(['git','show',f'{base}:{name}'],cwd=ROOT).decode()
        lang=path.relative_to(DOCS).parts[0];lang=lang if lang in ('en','fr') else 'ar'
        assert add_approved_tiktok(before,lang)==path.read_text(),f'Non-social edit: {name}'
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
    assert groups==1031 and headerless==820,(groups,headerless)
    print(f'PASS: {groups} four-icon social groups, {headerless} headerless shells preserved, accessible secure TikTok links, exact chrome-only changes, Alexandra shown once under Interviews with original URLs')

if __name__=='__main__':run()
