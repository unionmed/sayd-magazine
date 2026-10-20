#!/usr/bin/env python3
"""Owner-approved TikTok social chrome, without article or homepage-placement edits."""
import json, os, re, subprocess
from urllib.parse import unquote
from lxml import html
from header_social import add_approved_tiktok
from refresh_homepage_doors import DOCS, ROOT
from check_publication_contract import CONTRACT


# Freeze route preservation once, not a page count that grows with each release.
# Later PR bases also preserve any routes introduced after this snapshot.
ROUTE_BASE = '0286908f0cefc7ad05e85f9ce79a518c70db2e40'


def publication_routes(root, baseline_pairs=None):
    """Read package declarations and new central mirror mappings, never counts."""
    from seo_foundation import FR_SLUG_BY_EN
    routes=set();declared_pairs={}
    def add(slugs, source):
        assert set(slugs)=={'ar','en','fr'}, f'Incomplete publication mirrors: {source}'
        for lang,slug in slugs.items():
            assert isinstance(slug,str) and slug and '/' not in slug and slug not in ('.','..'), source
            routes.add('/'+('' if lang=='ar' else lang+'/')+'posts/'+slug+'/')
    for package in sorted((root/'content/features').glob('*.json')):
        for article in json.loads(package.read_text()).get('articles', []):
            if article.get('publication_ready') is not True:
                continue
            add(article['slugs'],package)
            declared_pairs[article['slugs']['ar']]=article['slugs']['en']
    # The central pairing input also covers older package schemas. Compare it
    # with the fixed snapshot, which contains legacy two-language/stub entries.
    # Explicit package French slugs take precedence over the legacy fallback.
    pairs=json.loads((root/'content/en/pairs.json').read_text())['pairs']
    for ar,en in pairs.items():
        if ar in declared_pairs:
            assert declared_pairs[ar]==en, f'Conflicting publication mapping: {ar}'
        elif (baseline_pairs or {}).get(ar)!=en:
            add({'ar':ar,'en':en,'fr':FR_SLUG_BY_EN.get(en,en)},'content/en/pairs.json')
    return routes


def check_route_inventory(docs, preserved, declared, links):
    """Preserve old routes; additional pages must be declared articles or redirects."""
    normalized={unquote(route):alias for route,alias in links.items()}
    assert len(normalized)==len(links), 'Duplicate canonical short-link target'
    assert len(links)==len(set(links.values())), 'Duplicate short-link alias'
    assert declared<=normalized.keys(), 'Published article missing its short link'
    required=set(preserved)
    for route in declared:
        required.add(route.strip('/')+'/index.html')
    for route,alias in normalized.items():
        assert re.fullmatch(r'/(?:en/|fr/)?posts/[^/]+/',route), route
        assert re.fullmatch(r'/s/[^/]+/',alias), alias
        article=docs/route.strip('/')/'index.html'
        assert article.is_file(), f'Missing canonical article: {route}'
        source=article.read_text()
        assert 'class="container mast-top-inner"' in source, f'Missing article header: {route}'
        assert len(html.fromstring(source).xpath('//nav[@class="header-social"]'))==1, route
        shell=docs/alias.strip('/')/'index.html'
        assert shell.is_file(), f'Missing redirect: {alias}'
        source=shell.read_text();tree=html.fromstring(source)
        assert 'class="container mast-top-inner"' not in source, alias
        assert not tree.xpath('//nav[@class="header-social"]'), alias
        target='https://sayd-magazine.com'+route
        assert [unquote(url) for url in tree.xpath('//link[@rel="canonical"]/@href')]==[target], alias
        assert [unquote(value) for value in tree.xpath('//meta[@http-equiv="refresh"]/@content')]==['0;url='+target], alias
        required.add(alias.strip('/')+'/index.html')
    actual={p.relative_to(docs).as_posix() for p in docs.rglob('*.html')}
    assert required<=actual, f'Original or declared route removed: {sorted(required-actual)}'
    assert actual<=required, f'Undeclared route added: {sorted(actual-required)}'


def check_social_pages(docs, expected):
    groups=0;headerless=0
    for path in docs.rglob('*.html'):
        current=path.read_text();tree=html.fromstring(current)
        lang=path.relative_to(docs).parts[0];lang=lang if lang in ('en','fr') else 'ar'
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
    return groups,headerless


def run(base=None):
    base=base or os.environ.get('SAYD_BASE_COMMIT',ROUTE_BASE)
    contract=json.loads(CONTRACT.read_text())
    expected=[url for key,url in contract['header_social']['links']]
    groups,headerless=check_social_pages(DOCS,expected)
    # Current social markup and original routes remain exact. The complete
    # original whole-article migration proof runs on pinned history in
    # test_historical_search_social.py, rather than freezing later articles.
    social=re.compile(r'<nav class="header-social"[^>]*>.*?</nav>',re.S)
    preserved=set()
    for baseline in sorted({ROUTE_BASE,base}):
        names=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',baseline,'--','docs'],cwd=ROOT).decode().split('\0')
        for name in filter(None,names):
            path=ROOT/name
            if path.suffix!='.html':continue
            preserved.add(path.relative_to(DOCS).as_posix())
            assert path.is_file(),f'Original route removed: {name}'
            before=subprocess.check_output(['git','show',f'{baseline}:{name}'],cwd=ROOT).decode()
            current=path.read_text()
            lang=path.relative_to(DOCS).parts[0];lang=lang if lang in ('en','fr') else 'ar'
            approved=add_approved_tiktok(before,lang)
            assert social.findall(approved)==social.findall(current),f'Non-approved social edit: {name}'
    baseline_pairs=json.loads(subprocess.check_output(['git','show',f'{ROUTE_BASE}:content/en/pairs.json'],cwd=ROOT))['pairs']
    check_route_inventory(DOCS,preserved,publication_routes(ROOT,baseline_pairs),json.loads((DOCS/'s/links.json').read_text()))
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
    # Exercise growth and failure modes without changing any published files.
    from test_publication_route_fixtures import test_route_growth
    test_route_growth()
    print(f'PASS: {groups} four-icon social groups, {headerless} headerless shells preserved, accessible secure TikTok links, exact social markup, Alexandra shown once under Interviews with original URLs')

if __name__=='__main__':run()
