"""Exact approved Gulf lead publication; no generic future-date exemption."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
import hashlib
import json
import os
import subprocess
from lxml import html
from refresh_homepage_doors import ROOT, DOCS, DOORS, collect, local_slug, render_card, render_li

AR = 'الصيد-السياحي-في-بلدان-الخليج-العربية'
EN = 'hunting-tourism-arab-gulf-countries'
SOURCE = ROOT / 'content/features/gulf-tourism-20261022.json'
# Set only after independent review of the final complete AR/EN/FR source.
PACKAGE_SHA256 = '4952d6446c828a4541e5b07d2a34c8cc1b2d3992bd95f8d161c6e188909a7a40'
DATES = {'ar': '22 تشرين الأول 2026', 'en': '22 October 2026', 'fr': '22 octobre 2026'}
PHOTO_SHA256 = {
    'gulf-original-cover': 'f185a6e90aeb71975814fd9d3c55a3f9ac04821e1181481eaa16688f083656a6',
    'gulf-hospitality-photo-01': 'c3ac17ca42aba9b00e597f8137d5a11253aebc8c26a68c2f9019ce5ce9a4d9ef',
    'gulf-original-north-houbara': 'f96d1f425e435ee7c3119ae2e167c754b4debc4a980b39904ab4614399794da9',
    'gulf-community-photo-01': '38de5cc4eea6ff3c445f30b29bc47604eb1f354debb4347d0ffc360919ca172a',
    'gulf-community-photo-02': 'f953cfd80d7f3807fa90472ed0971895c40d3340f487b8d7427066913ef7b46d',
    'gulf-hospitality-photo-02': 'aba08f2d86ac04d7ea5981e537d2326fca5e0da28e2d63f52c1111e9ca721761',
    'gulf-original-qatar-camp': 'af631546bd6b1895485fb97a654da90cbe97684e5c3e95c60642504f68055df9',
    'gulf-original-qatar-vehicle': '0f51631af8df5b3942d1537f29366eff7b20767addda2c136ca46d14742b85d9',
}
BOX_IDS = ['gulf-box-03', 'gulf-box-01', 'gulf-box-04', 'gulf-box-02']


def validate_package(data):
    assert list(data) == ['articles'] and len(data['articles']) == 1
    a = data['articles'][0]
    assert a['slugs'] == {'ar': AR, 'en': EN, 'fr': EN}
    assert a['date'] == '2026-10-22' and a['publication_ready'] is True
    assert (a['door'], a['category'], a['placement']) == ('hunting', 'صيد', 'lead')
    assert set(a['translations']) == {'ar', 'en', 'fr'}
    assert a['translations']['ar']['title'] == 'الصيد السياحي في بلدان الخليج العربية'
    assert a['translations']['ar']['kicker'] == 'الصيد كسياحة ومورد تنمية ١من ٣'
    assert [p['id'] for p in a['photos']] == list(PHOTO_SHA256)
    for p in a['photos']:
        assert p['sha256'] == PHOTO_SHA256[p['id']]
        assert p['path'].startswith('media/uploads/2026/10/gulf-tourism-' + p['id'] + '.')
        assert p['approved_for_article'] is True
        assert set(p['alt']) == set(p['credit']) == {'ar', 'en', 'fr'}
        assert p['source_url'].startswith('https://')
    signatures = []
    for lang in ('ar', 'en', 'fr'):
        d = a['translations'][lang]
        assert all(d[k] for k in ('title', 'kicker', 'series_intro', 'episodes', 'deck', 'meta_description', 'ticker', 'blocks'))
        assert len(d['episodes']) == 2
        assert [b['id'] for b in d['blocks'] if b['type'] == 'image'] == list(PHOTO_SHA256)
        assert [b['id'] for b in d['blocks'] if b['type'] == 'box'] == BOX_IDS
        assert all(b['type'] in ('paragraph', 'heading', 'image', 'box', 'sources') for b in d['blocks'])
        assert sum(b['type'] == 'sources' for b in d['blocks']) == 1
        signatures.append([(b['type'], b.get('id')) for b in d['blocks']])
    assert signatures[0] == signatures[1] == signatures[2], 'Translated content order or completeness drift'
    return a


def package():
    raw = SOURCE.read_bytes()
    assert PACKAGE_SHA256 and hashlib.sha256(raw).hexdigest() == PACKAGE_SHA256, 'Unreviewed Gulf package change'
    return validate_package(json.loads(raw))


def expected_config(old, current, a):
    from homepage_demotion import demote_side_cards
    from homepage_hunting_rotation import expected
    from ticker_policy import select
    wanted = deepcopy(old)
    wanted['ia_slots']['main'] = AR
    wanted['ia_slots']['important'] = [old['ia_slots']['main']] + old['ia_slots']['important'][:3]
    wanted['featured'] = [AR] + wanted['ia_slots']['important']
    demote_side_cards(wanted, old['ia_slots']['important'])
    p = a['photos'][0]
    wanted['primary_door'][AR] = 'hunting'
    wanted['card_image_overrides'][AR] = {'image': p['path'], 'position': '50% 50%', 'alt': p['alt']}
    wanted['ticker_entries'] = select([{'slug': AR, 'titles': {l: a['translations'][l]['ticker'] for l in ('ar','en','fr')}}] + old['ticker_entries'])
    wanted['ticker_slugs'] = [e['slug'] for e in wanted['ticker_entries']]
    selected = expected(wanted)
    next(d for d in wanted['ia_door_sections'] if d['door'] == 'hunting')['slugs'] = selected
    pairs = json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    wanted['desk_slugs']['صيد'] = selected
    wanted['desk_slugs']['Hunting'] = [pairs[s] for s in selected]
    assert current == wanted, ('gulf', [k for k in set(current)|set(wanted) if current.get(k) != wanted.get(k)])
    assert wanted['ia_slots']['important'][0] == old['ia_slots']['main']
    assert old['ia_slots']['main'] not in wanted['latest']
    assert wanted['ticker_slugs'][0] == AR and len(wanted['ticker_slugs']) == 10
    return wanted


def assert_media_delta(paths, a):
    assert set(paths) == {'docs/' + p['path'] for p in a['photos']}, 'Existing media/assets changed or unapproved media added'


def gulf_expected(old, current, base):
    if not SOURCE.exists() or AR in old['primary_door']:
        return None
    a = package()
    wanted = expected_config(old, current, a)
    pairs = json.loads(subprocess.check_output(['git','show',base+':content/en/pairs.json'], cwd=ROOT))
    pairs['pairs'][AR] = EN
    assert json.loads((ROOT/'content/en/pairs.json').read_text()) == pairs
    for p in a['photos']:
        assert hashlib.sha256((DOCS/p['path']).read_bytes()).hexdigest() == p['sha256']
    media = subprocess.check_output(['git','diff','--name-only','-z',base,'--','docs/media','docs/assets'], cwd=ROOT).decode().strip('\0').split('\0')
    media = [p for p in media if p not in ['docs/assets/search/index-'+l+'.json' for l in ('ar','en','fr')]]
    assert_media_delta(media, a)
    from sync_tickers import TICKER
    paths = subprocess.check_output(['git','diff','--name-only','--diff-filter=MD','-z',base,'--','docs/posts','docs/en/posts','docs/fr/posts'], cwd=ROOT).decode().strip('\0').split('\0')
    for rel in filter(None, paths):
        path = ROOT/rel
        assert path.is_file(), ('Existing article deleted', rel)
        before = subprocess.check_output(['git','show',base+':'+rel], cwd=ROOT).decode()
        after = path.read_text()
        assert TICKER.sub('', before) == TICKER.sub('', after), ('Existing article changed beyond shared ticker', rel)
    return wanted


def canonical(node):
    node = deepcopy(node)
    for n in node.iter():
        if n.text is not None and not n.text.strip(): n.text = None
        if n.tail is not None and not n.tail.strip(): n.tail = None
    return html.tostring(node, encoding='unicode', with_tail=False)


def cls(node, name):
    return node.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," '+name+' ")]')


def assert_gulf_article(lang, a=None):
    a = a or package(); d = a['translations'][lang]
    path = DOCS/('' if lang == 'ar' else lang)/'posts'/a['slugs'][lang]/'index.html'
    assert path.is_file(), (lang, 'missing rendered translation')
    t = html.parse(str(path)); root = t.getroot()
    assert t.xpath('//html/@lang') == [lang]
    assert t.xpath('//h1/text()') == [d['title']]
    assert [n.text_content() for n in cls(root, 'article-kicker')] == [d['kicker']]
    content = cls(root, 'article-content')
    assert len(content) == 1
    intro = cls(content[0], 'series-intro')
    assert len(intro) == 1 and intro[0].text_content() == d['series_intro']
    assert list(content[0])[0] is intro[0], (lang, 'series intro before original article')
    episodes = cls(content[0], 'series-episodes')
    assert len(episodes) == 1 and not episodes[0].xpath('.//a'), 'Forthcoming episodes must not link to nonexistent pages'
    expected_titles = [e['title'] if isinstance(e, dict) else e for e in d['episodes']]
    rendered_titles = episodes[0].xpath('.//li')
    assert len(rendered_titles) == 2
    for n, title in zip(rendered_titles, expected_titles):
        assert title in n.text_content()
    related = cls(content[0], 'article-more')
    assert len(related) == 1 and len(related[0].xpath('.//a[@class="reading-card"]')) == len(a['related']) == 2
    assert list(content[0])[-2:] == [episodes[0], related[0]]
    actual = [n for n in content[0] if n not in [intro[0], episodes[0], related[0]]]
    assert len(actual) == len(d['blocks']), (lang, 'block count')
    photos = {p['id']: p for p in a['photos']}
    for node, block in zip(actual, d['blocks']):
        kind = block['type']
        if kind in ('paragraph', 'sources', 'heading'):
            assert node.tag == ('h2' if kind == 'heading' else 'p')
            assert node.text_content() == block['text'], (lang, kind, 'text/order')
        elif kind == 'box':
            assert node.tag == 'aside' and 'article-callout' in node.get('class','').split()
            assert node.get('data-box-id') == block['id']
            assert node.xpath('./h3/text()') == [block['title']]
            assert [p.text_content() for p in node.xpath('./p')] == [block['body']]
        elif kind == 'image':
            p = photos[block['id']]
            assert node.tag == 'figure' and node.get('data-photo-id') == p['id']
            images = node.xpath('./img'); captions = node.xpath('./figcaption')
            assert len(images) == len(captions) == 1
            assert (path.parent/unquote(urlsplit(images[0].get('src')).path)).resolve() == (DOCS/p['path']).resolve()
            assert images[0].get('alt') == p['alt'][lang]
            assert captions[0].text_content() == p['credit'][lang]
            assert [unquote(u) for u in captions[0].xpath('./a/@href')] == [unquote(p['source_url'])]
    route = '/'+('' if lang == 'ar' else lang+'/')+'posts/'+a['slugs'][lang]+'/'
    assert [unquote(u) for u in t.xpath('//link[@rel="canonical"]/@href')] == ['https://sayd-magazine.com'+route]
    assert set(t.xpath('//head/link[@rel="alternate"]/@hreflang')) == {'ar','en','fr','x-default'}
    assert t.xpath('//meta[@property="og:image"]/@content') == ['https://sayd-magazine.com/'+a['photos'][0]['path']]
    schema = next(json.loads(n.text) for n in t.xpath('//script[@type="application/ld+json"]') if json.loads(n.text).get('@type') in ('NewsArticle','Article'))
    assert schema['headline'] == d['title'] and schema['datePublished'][:10] == a['date'] and schema['inLanguage'] == lang
    assert len(schema['image']) == 8
    return t


def assert_gulf_home(old_page, after, rel, lang, current):
    a = package(); d = a['translations'][lang]
    before = html.fromstring(old_page); after = deepcopy(after); path = ROOT/rel
    catalog = collect(old_page, path, path)
    def data(ar, hunting=False):
        slug = local_slug(ar, lang); item = dict(catalog[slug])
        override = current['card_image_overrides'].get(ar)
        if override:
            item.update(image=os.path.relpath(DOCS/override['image'], path.parent), position=override['position'], alt=override['alt'][lang])
            if override.get('fit'): item['fit'] = override['fit']
            if override.get('cache_version'): item['image'] += '?v='+override['cache_version']
        if ar in current.get('video_cards',{}): item['video_badge'] = current['video_cards'][ar][lang]
        if hunting:
            topic = 'equestrian' if current['primary_door'].get(ar) == 'equestrian' else 'hunting'
            item['topic_label'] = {'ar': {'hunting':'صيد','equestrian':'فروسية'}, 'en':{'hunting':'Hunting','equestrian':'Equestrian'},'fr':{'hunting':'Chasse','equestrian':'Équitation'}}[lang][topic]
        return slug, item
    oldlead = cls(before, 'feature-lead'); newlead = cls(after, 'feature-lead')
    assert len(oldlead) == len(newlead) == 1
    expected = deepcopy(oldlead[0])
    for link in expected.xpath('.//a'): link.set('href', 'posts/'+__import__('urllib.parse',fromlist=['quote']).quote(a['slugs'][lang])+'/index.html')
    expected.xpath('.//h2/a')[0].text = d['title']
    expected.xpath('.//img')[0].set('src', os.path.relpath(DOCS/a['photos'][0]['path'], path.parent))
    expected.xpath('.//img')[0].set('alt', a['photos'][0]['alt'][lang])
    cls(expected, 'meta')[0].text = DATES[lang]
    for node in cls(expected, 'migration-kicker'): node.text = d['kicker']
    assert canonical(newlead[0]) == canonical(expected), (lang,'exact Gulf lead')
    blocks = [('.feature-stack','feature-stack',current['ia_slots']['important'], True),('.latest-feed','latest-feed',current['latest'],False)]
    for _, name, slugs, stack in blocks:
        oldnodes = cls(before, name); newnodes = cls(after, name)
        assert len(oldnodes) == len(newnodes) == 1
        wanted = [html.fromstring(render_card(*data(s), stack=True) if stack else render_li(*data(s))) for s in slugs]
        actual = list(newnodes[0])
        assert [canonical(n) for n in actual] == [canonical(n) for n in wanted], (lang,name,'exact cards')
        for n in list(oldnodes[0]): oldnodes[0].remove(n)
        for n in list(newnodes[0]): newnodes[0].remove(n)
    heading = next(d[{'ar':1,'en':2,'fr':3}[lang]] for d in DOORS if d[0] == 'hunting')
    xp = '//section[@class="home-section"][div/h2=$heading]/div[@class="home-door-grid"]'
    oldgrid = before.xpath(xp, heading=heading); newgrid = after.xpath(xp, heading=heading)
    assert len(oldgrid) == len(newgrid) == 1
    slugs = next(x['slugs'] for x in current['ia_door_sections'] if x['door'] == 'hunting')
    assert [canonical(n) for n in newgrid[0]] == [canonical(html.fromstring(render_card(*data(s,True)))) for s in slugs], (lang,'hunting rotation')
    for n in list(oldgrid[0]): oldgrid[0].remove(n)
    for n in list(newgrid[0]): newgrid[0].remove(n)
    from ticker_policy import render
    expected_ticker = html.fromstring('<div>'+render(lang)+'</div>')
    for tree in (before, after):
        loops = cls(tree,'ticker'); assert len(loops) == 2
        for node in loops:
            if tree is after: assert [canonical(n) for n in node] == [canonical(n) for n in expected_ticker]
            for n in list(node): node.remove(n)
    oldlead[0].getparent().remove(oldlead[0]); newlead[0].getparent().remove(newlead[0])
    # Only the approved lead image may change in homepage social metadata.
    # Normalize the expected baseline nodes, not arbitrary candidate metadata.
    cover_url='https://sayd-magazine.com/'+a['photos'][0]['path']
    for attribute,key in [('property','og:image'),('name','twitter:image')]:
        xp='//head/meta[@'+attribute+'="'+key+'"]'
        original=before.xpath(xp); candidate=after.xpath(xp)
        assert len(original)==len(candidate)==1
        assert candidate[0].get('content')==cover_url,(lang,key,'approved Gulf cover')
        original[0].set('content',cover_url)
    assert canonical(before) == canonical(after), (lang,'unrelated homepage DOM changed')
    assert_gulf_article(lang, a)


def test_gulf_negative_guards(base):
    old = json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT))
    if not SOURCE.exists() or AR in old['primary_door']: return
    current = json.loads((ROOT/'content/homepage.json').read_text()); a = package()
    expected_config(old,current,a)
    cases = []
    def change(fn):
        c=deepcopy(current); fn(c); cases.append(c)
    change(lambda c:c['ia_slots'].__setitem__('main',old['ia_slots']['main']))
    change(lambda c:c['ia_slots']['important'].reverse())
    change(lambda c:c['latest'].reverse())
    change(lambda c:c['latest'].append(old['ia_slots']['main']))
    change(lambda c:c['ticker_entries'].reverse())
    change(lambda c:c['ticker_entries'][0]['titles'].__setitem__('fr','changed'))
    change(lambda c:c['ticker_slugs'].__setitem__(0,'wrong'))
    change(lambda c:c['primary_door'].__setitem__(AR,'science'))
    change(lambda c:c['card_image_overrides'][AR].__setitem__('image','changed.jpg'))
    change(lambda c:c['omit_from_latest'].append(AR))
    change(lambda c:c.__setitem__('memory_visible',True))
    for door in current['ia_door_sections']:
        change(lambda c,door=door:next(d for d in c['ia_door_sections'] if d['door']==door['door'])['slugs'].reverse())
    rejected=0
    for c in cases:
        if c==current:continue
        try:expected_config(old,c,a)
        except AssertionError:rejected+=1
        else:raise AssertionError('Unauthorized Gulf placement accepted')
    for kind in ('slug','language','date','placement','photo','box'):
        data={'articles':[deepcopy(a)]}; candidate=data['articles'][0]
        if kind=='slug': candidate['slugs']['ar']='wrong'
        elif kind=='language': del candidate['translations']['fr']
        elif kind=='date': candidate['date']='2026-10-21'
        elif kind=='placement': candidate['placement']='news'
        elif kind=='photo': candidate['photos'][0]['sha256']='wrong'
        else: candidate['translations']['fr']['blocks']=[b for b in candidate['translations']['fr']['blocks'] if b.get('id')!=BOX_IDS[0]]
        try:validate_package(data)
        except AssertionError:pass
        else:raise AssertionError('Unauthorized package accepted: '+kind)
    good=['docs/'+p['path'] for p in a['photos']]
    for paths in (good[:-1],good+['docs/assets/css/site.css'],good+['docs/media/extra.jpg']):
        try:assert_media_delta(paths,a)
        except AssertionError:pass
        else:raise AssertionError('Unapproved media mutation accepted')
    test_rendered_negative_guards(base, old, current, a)
    print(f'PASS: exact Gulf lead/demotion/ticker delta; {rejected} placement and 9 source/media mutations rejected')


def test_rendered_negative_guards(base, old, current, a):
    rel='docs/index.html';prior=subprocess.check_output(['git','show',base+':'+rel],cwd=ROOT).decode()
    actual=html.fromstring((ROOT/rel).read_text())
    mutations=[
        lambda t:cls(t,'feature-stack')[0][0].xpath('.//img')[0].set('src','wrong.jpg'),
        lambda t:setattr(cls(t,'feature-stack')[0][1].xpath('.//h3/a')[0],'text','changed'),
        lambda t:cls(t,'feature-stack')[0].append(deepcopy(cls(t,'feature-stack')[0][0])),
        lambda t:setattr(cls(t,'feature-lead')[0].xpath('.//h2/a')[0],'text','wrong'),
        lambda t:cls(t,'latest-feed')[0][0].xpath('.//a')[0].set('href','wrong/'),
        lambda t:setattr(t.xpath('//header')[0],'tail','Unapproved visible tail'),
        lambda t:cls(t,'ticker')[0][0].set('href','wrong/'),
        lambda t:t.xpath('//section[@class="home-section"]')[0].set('style','display:none'),
        lambda t:t.xpath('//head/meta[@property="og:image"]')[0].set('content','wrong.jpg'),
        lambda t:t.xpath('//head/meta[@name="twitter:image"]')[0].set('content','wrong.jpg'),
        lambda t:t.xpath('//head/meta[@property="og:title"]')[0].set('content','Unapproved title'),
    ]
    for mutate in mutations:
        candidate=deepcopy(actual);mutate(candidate)
        try:assert_gulf_home(prior,candidate,rel,'ar',current)
        except AssertionError:pass
        else:raise AssertionError('Unapproved rendered Gulf/home mutation accepted')
    target=DOCS/'fr/posts'/EN/'index.html';parse=html.parse;actual=parse(str(target))
    def delete_box(t):
        n=t.xpath('//aside[@class="article-callout"]')[0];n.getparent().remove(n)
    changes=[
        delete_box,
        lambda t:setattr(t.xpath('//figure/figcaption/a')[0],'text','Wrong source'),
        lambda t:t.xpath('//section[@class="series-episodes"]/ol/li')[0].append(html.fromstring('<a href="unpublished/">link</a>')),
        lambda t:t.xpath('//figure/img')[0].set('src','wrong.jpg'),
        lambda t:setattr(t.xpath('//p[@class="series-intro"]')[0],'text','Changed series intro'),
    ]
    for mutate in changes:
        candidate=deepcopy(actual);mutate(candidate)
        with patch.object(html,'parse',lambda path,*args,**kwargs:candidate if str(path)==str(target) else parse(path,*args,**kwargs)):
            try:assert_gulf_article('fr',a)
            except AssertionError:pass
            else:raise AssertionError('Invalid article structure/source or forthcoming link accepted')
    target=DOCS/a['photos'][0]['path'];read_bytes=Path.read_bytes
    with patch.object(Path,'read_bytes',lambda p:read_bytes(p)+b'changed' if p==target else read_bytes(p)):
        try:gulf_expected(old,current,base)
        except AssertionError:pass
        else:raise AssertionError('Changed approved image accepted')
    print('PASS:11 rendered-home,5 article and changed-image-byte negative fixtures rejected')


def test_gulf_browser(context, origin, output):
    if not SOURCE.exists(): return
    from playwright.sync_api import expect
    a=package(); page=context.new_page()
    try:
        for lang in ('ar','en','fr'):
            prefix='' if lang=='ar' else lang+'/'
            for width in (390,1440):
                page.set_viewport_size({'width':width,'height':1000})
                page.goto(origin+'/'+prefix,wait_until='networkidle')
                lead=page.locator('.feature-lead')
                expect(lead.locator('h2 a')).to_have_text(a['translations'][lang]['title'])
                expect(lead.locator('.migration-kicker')).to_have_text(a['translations'][lang]['kicker'])
                lead.locator('img').evaluate('(img)=>img.decode()')
                lead.screenshot(path=str(output/f'gulf-home-{lang}-{width}.png'))
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(lang,width,'Gulf homepage overflow')
                page.locator('.featured-mosaic').screenshot(path=str(output/f'gulf-home-mosaic-{lang}-{width}.png'))
                lead.locator('h2 a').click()
                page.wait_for_url(lambda url:unquote(urlsplit(url).path)=='/'+prefix+'posts/'+a['slugs'][lang]+'/index.html')
                expect(page.locator('h1')).to_have_text(a['translations'][lang]['title'])
                expect(page.locator('.article-kicker')).to_have_text(a['translations'][lang]['kicker'])
                expect(page.locator('article.article-content > figure')).to_have_count(8)
                expect(page.locator('aside.article-callout')).to_have_count(4)
                expect(page.locator('.series-episodes li')).to_have_count(2)
                expect(page.locator('.series-episodes a')).to_have_count(0)
                for index,p in enumerate(a['photos']):
                    figure=page.locator('article.article-content > figure').nth(index)
                    expect(figure.locator('figcaption')).to_have_text(p['credit'][lang])
                    figure.locator('img').scroll_into_view_if_needed()
                    figure.locator('img').evaluate('(img)=>img.decode()')
                    assert figure.locator('img').evaluate('(img)=>img.complete&&img.naturalWidth>0')
                for related_image in page.locator('.article-more .reading-card img').all():
                    related_image.scroll_into_view_if_needed()
                    related_image.evaluate('(img)=>img.decode()')
                    assert related_image.evaluate('(img)=>img.complete&&img.naturalWidth>0')
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(lang,width,'Gulf article overflow')
                page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(output/f'gulf-article-{lang}-{width}.png'),full_page=True)
    finally:page.close()
    print('PASS: Gulf lead and complete AR/EN/FR8-image4-box articles at390/1440px; forthcoming links absent')


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='HEAD');args=parser.parse_args()
    a=package()
    for lang in ('ar','en','fr'):assert_gulf_article(lang,a)
    old=json.loads(subprocess.check_output(['git','show',args.base+':content/homepage.json'],cwd=ROOT))
    current=json.loads((ROOT/'content/homepage.json').read_text())
    if gulf_expected(old,current,args.base) is not None:
        for lang,prefix in [('ar',''),('en','en/'),('fr','fr/')]:
            rel='docs/'+prefix+'index.html';before=subprocess.check_output(['git','show',args.base+':'+rel],cwd=ROOT).decode()
            assert_gulf_home(before,html.fromstring((ROOT/rel).read_text()),rel,lang,current)
        test_gulf_negative_guards(args.base)
    print('PASS: Gulf exact package, article blocks, sources, media, mirrors and authorized distribution')
