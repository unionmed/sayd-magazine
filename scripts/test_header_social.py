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
    # Current social markup and original routes remain exact. The complete
    # original whole-article migration proof runs on pinned history in
    # test_historical_search_social.py, rather than freezing later articles.
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
    # This approved batch adds twelve article headers and twelve short-link
    # shells; retain exact totals and every per-page/social preservation check.
    added=0
    package=ROOT/'content/features/four-news-20261018.json'
    if package.exists():
        articles=json.loads(package.read_text())['articles']
        assert [a['key'] for a in articles]==['godolphin','cairo','abudhabi','loon']
        assert all(a['date']=='2026-10-18' and set(a['slugs'])=={'ar','en','fr'} for a in articles)
        from urllib.parse import unquote
        links=json.loads((DOCS/'s/links.json').read_text())
        aliases=[]
        for a in articles:
            for lang in ('ar','en','fr'):
                route='/'+('' if lang=='ar' else lang+'/')+'posts/'+a['slugs'][lang]+'/'
                assert (DOCS/route.lstrip('/')/'index.html').is_file()
                matching=[v for k,v in links.items() if unquote(k)==route]
                assert len(matching)==1
                assert (DOCS/matching[0].strip('/')/'index.html').is_file()
                aliases.extend(matching)
        assert len(aliases)==len(set(aliases))==12
        added=12
    # Exact authorized Omayed publication: three language mirrors and their
    # three stable redirect shells, not an open-ended allowance for new pages.
    omayed=ROOT/'content/features/egypt-uae-omayed-20261018.json'
    if omayed.exists():
        articles=json.loads(omayed.read_text())['articles']
        assert len(articles)==1 and articles[0]['key']=='omayed'
        a=articles[0]
        assert a['date']=='2026-10-18' and a['door']=='wildlife' and a['placement']=='news'
        assert a['slugs']=={'ar':'تعاون-مصري-إماراتي-الحبارى-محمية-العميد','en':'egypt-uae-houbara-omayed-cooperation-2026','fr':'egypt-uae-houbara-omayed-cooperation-2026'}
        from urllib.parse import unquote
        links=json.loads((DOCS/'s/links.json').read_text());omayed_aliases=[]
        for lang in ('ar','en','fr'):
            route='/'+('' if lang=='ar' else lang+'/')+'posts/'+a['slugs'][lang]+'/'
            page=html.parse(str(DOCS/route.lstrip('/')/'index.html'))
            assert len(page.xpath('//nav[@class="header-social"]'))==1
            matching=[v for k,v in links.items() if unquote(k)==route]
            assert len(matching)==1
            shell=html.parse(str(DOCS/matching[0].strip('/')/'index.html'))
            assert not shell.xpath('//nav[@class="header-social"]')
            assert [unquote(url) for url in shell.xpath('//link[@rel="canonical"]/@href')]==['https://sayd-magazine.com'+route]
            omayed_aliases.extend(matching)
        assert len(omayed_aliases)==len(set(omayed_aliases))==3
        added+=3
    # Exact approved North/Science/Saluki package: nine article headers and
    # nine unique canonical short-link shells, not arbitrary new-page capacity.
    package=ROOT/'content/features/approved-three-20261020.json'
    if package.exists():
        from test_combined_hunting_equestrian import approved_three_articles
        from urllib.parse import unquote
        links=json.loads((DOCS/'s/links.json').read_text());three_aliases=[]
        for a in approved_three_articles():
            for lang in ('ar','en','fr'):
                route='/'+('' if lang=='ar' else lang+'/')+'posts/'+a['slugs'][lang]+'/'
                page=html.parse(str(DOCS/route.lstrip('/')/'index.html'))
                assert len(page.xpath('//nav[@class="header-social"]'))==1
                matching=[v for k,v in links.items() if unquote(k)==route]
                assert len(matching)==1
                shell=html.parse(str(DOCS/matching[0].strip('/')/'index.html'))
                assert not shell.xpath('//nav[@class="header-social"]')
                assert [unquote(url) for url in shell.xpath('//link[@rel="canonical"]/@href')]==['https://sayd-magazine.com'+route]
                three_aliases.extend(matching)
        assert len(three_aliases)==len(set(three_aliases))==9
        added+=9
    # The approved Science-only article adds exactly three mirrored headers
    # and three unique canonical redirect shells. Keep the existing totals,
    # per-page markup, and historical-route preservation assertions intact.
    honey=ROOT/'content/features/honey-buzzard-science-20261021.json'
    if honey.exists():
        from test_honey_buzzard_science_20261021 import package as honey_package
        from urllib.parse import unquote
        a=honey_package()
        links=json.loads((DOCS/'s/links.json').read_text());honey_aliases=[]
        for lang in ('ar','en','fr'):
            route='/'+('' if lang=='ar' else lang+'/')+'posts/'+a['slugs'][lang]+'/'
            page=html.parse(str(DOCS/route.lstrip('/')/'index.html'))
            assert len(page.xpath('//nav[@class="header-social"]'))==1
            matching=[v for k,v in links.items() if unquote(k)==route]
            assert len(matching)==1
            shell=html.parse(str(DOCS/matching[0].strip('/')/'index.html'))
            assert not shell.xpath('//nav[@class="header-social"]')
            assert [unquote(url) for url in shell.xpath('//link[@rel="canonical"]/@href')]==['https://sayd-magazine.com'+route]
            honey_aliases.extend(matching)
        assert len(honey_aliases)==len(set(honey_aliases))==3
        added+=3
    # Exactly the approved Gulf article and its three canonical short-link shells.
    gulf=ROOT/'content/features/gulf-tourism-20261022.json'
    if gulf.exists():
        from test_gulf_tourism_20261022 import package as gulf_package
        from urllib.parse import unquote
        a=gulf_package();links=json.loads((DOCS/'s/links.json').read_text());gulf_aliases=[]
        for lang in ('ar','en','fr'):
            route='/'+('' if lang=='ar' else lang+'/')+'posts/'+a['slugs'][lang]+'/'
            page=html.parse(str(DOCS/route.lstrip('/')/'index.html'))
            assert len(page.xpath('//nav[@class="header-social"]'))==1
            matching=[v for k,v in links.items() if unquote(k)==route]
            assert len(matching)==1
            shell=html.parse(str(DOCS/matching[0].strip('/')/'index.html'))
            assert not shell.xpath('//nav[@class="header-social"]')
            assert [unquote(url) for url in shell.xpath('//link[@rel="canonical"]/@href')]==['https://sayd-magazine.com'+route]
            gulf_aliases.extend(matching)
        assert len(gulf_aliases)==len(set(gulf_aliases))==3
        added+=3
    # Exactly the standing-authorized 22 October encyclopedia batch: three
    # named species, nine mirrored headers and nine unique redirect shells.
    # Preserve all historical and per-page checks; do not create an open-ended
    # allowance for arbitrary new pages or altered social navigation.
    daily=ROOT/'content/features/daily-birds-20261022.json'
    if daily.exists():
        from urllib.parse import unquote
        articles=json.loads(daily.read_text())['articles']
        expected_species={
            'northern-shoveler-arab-world':('Spatula clypeata','أبو-مجرف-في-العالم-العربي'),
            'northern-pintail-arab-world':('Anas acuta','البلبول-الشمالي-في-العالم-العربي'),
            'eurasian-wigeon-arab-world':('Mareca penelope','الصواي-الأوراسي-في-العالم-العربي'),
        }
        assert len(articles)==3 and {a['key'] for a in articles}==set(expected_species)
        links=json.loads((DOCS/'s/links.json').read_text());daily_aliases=[]
        for a in articles:
            scientific,arabic=expected_species[a['key']]
            assert a['scientific_name']==scientific and a['new'] is True
            assert a['date']=='2026-10-22' and a['category']=='موسوعة-الطيور'
            assert a['slugs']=={'ar':arabic,'en':a['key'],'fr':a['key']}
            for lang in ('ar','en','fr'):
                route='/'+('' if lang=='ar' else lang+'/')+'posts/'+a['slugs'][lang]+'/'
                page=html.parse(str(DOCS/route.lstrip('/')/'index.html'))
                assert len(page.xpath('//nav[@class="header-social"]'))==1
                matching=[v for k,v in links.items() if unquote(k)==route]
                assert len(matching)==1
                shell=html.parse(str(DOCS/matching[0].strip('/')/'index.html'))
                assert not shell.xpath('//nav[@class="header-social"]')
                assert [unquote(url) for url in shell.xpath('//link[@rel="canonical"]/@href')]==['https://sayd-magazine.com'+route]
                daily_aliases.extend(matching)
        assert len(daily_aliases)==len(set(daily_aliases))==9
        added+=9
    assert groups==1037+added and headerless==823+added,(groups,headerless)
    print(f'PASS: {groups} four-icon social groups, {headerless} headerless shells preserved, accessible secure TikTok links, exact social markup, Alexandra shown once under Interviews with original URLs')

if __name__=='__main__':run()
