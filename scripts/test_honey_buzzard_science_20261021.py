"""Exact Science-only publication delta; not a general future-publishing exemption."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import os
import re
import subprocess
from urllib.parse import unquote
from lxml import html
from refresh_homepage_doors import ROOT, DOCS, render_card

AR = 'حوام-العسل-هجرة-بولندا-3750-كيلومترا'
EN = 'honey-buzzards-poland-migration-routes-3750-km'
SOURCE = ROOT / 'content/features/honey-buzzard-science-20261021.json'
PHOTO_PATHS = [
    'media/uploads/2026/10/honey-buzzard-juvenile-andrey-gulivanov.jpg',
    'media/uploads/2026/10/honey-buzzard-mirski-2026-figure-1.png',
    'media/uploads/2026/10/honey-buzzard-mirski-2026-figure-2.png',
]
DATES = {'ar': '21 تشرين الأول 2026', 'en': '21 October 2026', 'fr': '21 octobre 2026'}
LABELS = {'ar': 'علوم', 'en': 'Science', 'fr': 'Sciences'}
# The independently reviewed, owner-approved source package, including every
# translation and photograph SHA. A mutable publication_ready flag is not proof.
PACKAGE_SHA256 = '07f4054e47d58967bd4e27b8348bab8c479d147b516283d9989c0d50d1adfc4b'


def validate_package(data):
    assert list(data) == ['articles'] and len(data['articles']) == 1
    a = data['articles'][0]
    assert a['slugs'] == {'ar': AR, 'en': EN, 'fr': EN}
    assert a['date'] == '2026-10-21' and a['publication_ready'] is True
    assert (a['door'], a['category'], a['placement']) == ('science', 'علوم-واكتشافات', 'category')
    assert set(a['translations']) == {'ar', 'en', 'fr'}
    assert all(a['translations'][lang]['title'] and a['translations'][lang]['intro'] and a['translations'][lang]['sections'] for lang in ('ar','en','fr'))
    assert [p['path'] for p in a['photos']] == PHOTO_PATHS
    assert all(p['approved_for_article'] is True for p in a['photos'])
    return a


def package():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PACKAGE_SHA256, 'Unreviewed honey-buzzard package change'
    return validate_package(json.loads(raw))


def expected_config(old, current, a):
    wanted = deepcopy(old)
    wanted['omit_from_latest'].append(AR)
    wanted['primary_door'][AR] = 'science'
    p = a['photos'][0]
    wanted['card_image_overrides'][AR] = {'image': p['path'], 'position': '50% 50%', 'alt': p['alt']}
    before = next(d['slugs'] for d in old['ia_door_sections'] if d['door'] == 'science')
    cards = ([AR] + before)[:4]
    next(d for d in wanted['ia_door_sections'] if d['door'] == 'science')['slugs'] = cards
    wanted['desk_slugs']['علوم واكتشافات'] = cards
    wanted['desk_slugs']['Science & Discoveries'] = ([EN] + old['desk_slugs']['Science & Discoveries'])[:4]
    assert current == wanted, ('honey-buzzard', [k for k in set(current)|set(wanted) if current.get(k) != wanted.get(k)])
    return wanted


def assert_media_delta(paths):
    assert set(paths) == {'docs/' + p for p in PHOTO_PATHS}, 'Existing media/assets changed or unapproved media added'


def honey_expected(old, current, base):
    if not SOURCE.exists() or AR in old['primary_door']:
        return None
    a = package()
    wanted = expected_config(old, current, a)
    previous_pairs = json.loads(subprocess.check_output(['git','show',base+':content/en/pairs.json'],cwd=ROOT))
    previous_pairs['pairs'][AR] = EN
    assert json.loads((ROOT/'content/en/pairs.json').read_text()) == previous_pairs
    for p in a['photos']:
        assert hashlib.sha256((DOCS/p['path']).read_bytes()).hexdigest() == p['sha256']
    media = subprocess.check_output(['git','diff','--name-only','-z',base,'--','docs/media','docs/assets'],cwd=ROOT).decode().strip('\0').split('\0')
    # The three search-index additions are checked independently, not images.
    media = [p for p in media if p not in ['docs/assets/search/index-'+l+'.json' for l in ('ar','en','fr')]]
    assert_media_delta(media)
    existing_posts = subprocess.check_output(['git','diff','--name-only','--diff-filter=MD','-z',base,'--','docs/posts','docs/en/posts','docs/fr/posts'],cwd=ROOT)
    assert not existing_posts, 'Existing article pages changed during Science-only publication'
    return wanted


def canonical(node):
    node = deepcopy(node)
    for n in node.iter():
        if n.text is not None and not n.text.strip(): n.text = None
        if n.tail is not None and not n.tail.strip(): n.tail = None
    return html.tostring(node, encoding='unicode', with_tail=False)


def assert_honey_home(old_page, after, rel, lang, current):
    a = package()
    before = html.fromstring(old_page)
    after = deepcopy(after)
    xp = '//section[@class="home-section"][div/h2=$heading]'
    old_sections = before.xpath(xp,heading=LABELS[lang]); new_sections = after.xpath(xp,heading=LABELS[lang])
    assert len(old_sections) == len(new_sections) == 1
    old_section, new_section = old_sections[0], new_sections[0]
    old_cards = old_section.xpath('.//article'); new_cards = new_section.xpath('.//article')
    assert len(old_cards) == len(new_cards) == 4
    p = a['photos'][0]
    wanted = render_card(AR if lang == 'ar' else EN, {
        'title': a['translations'][lang]['title'], 'date': DATES[lang],
        'image': os.path.relpath(DOCS/p['path'], (ROOT/rel).parent),
        'alt': p['alt'][lang], 'position': '50% 50%',
    })
    assert canonical(new_cards[0]) == canonical(html.fromstring(wanted)), (lang,'new Science card')
    assert [canonical(n) for n in new_cards[1:]] == [canonical(n) for n in old_cards[:3]], (lang,'existing Science cards')
    shells = []
    for section in (old_section, new_section):
        shell = deepcopy(section)
        for card in shell.xpath('.//article'):
            card.drop_tree()  # Retain non-whitespace tails outside the cards.
        shells.append(canonical(shell))
    assert shells[0] == shells[1], (lang, 'Science section chrome')
    # Compare the entire remaining document, not only selected known classes.
    old_section.getparent().remove(old_section); new_section.getparent().remove(new_section)
    assert canonical(before) == canonical(after), (lang,'unrelated homepage mutation')
    post = DOCS/('' if lang=='ar' else lang)/'posts'/(AR if lang=='ar' else EN)/'index.html'
    assert post.is_file(), (lang, 'missing rendered translation')
    tree = html.parse(str(post))
    assert tree.xpath('//html/@lang') == [lang]
    assert tree.xpath('//h1/text()') == [a['translations'][lang]['title']]
    badge = tree.xpath('//header[@class="article-header"]//a[@class="badge"]')
    assert len(badge) == 1 and badge[0].text_content() == LABELS[lang]
    assert '/category/علوم-واكتشافات/' in unquote(badge[0].get('href'))
    images = tree.xpath('//article[@class="article-content"]/figure/img')
    assert [(post.parent/unquote(n.get('src'))).resolve() for n in images] == [(DOCS/p).resolve() for p in PHOTO_PATHS]
    paragraphs = tree.xpath('//article[@class="article-content"]/p')
    text = [n.text_content() for n in paragraphs]
    expected = a['translations'][lang]['intro'] + [p for _, paragraphs in a['translations'][lang]['sections'] for p in paragraphs]
    assert text[:-1] == expected, (lang,'article paragraphs')
    assert tree.xpath('//article[@class="article-content"]/h2/text()') == [s[0] for s in a['translations'][lang]['sections']]
    alternates = tree.xpath('//head/link[@rel="alternate"]/@hreflang')
    assert set(alternates) == {'ar','en','fr','x-default'}


def test_honey_negative_guards(base):
    old = json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT))
    if not SOURCE.exists() or AR in old['primary_door']: return
    current = json.loads((ROOT/'content/homepage.json').read_text()); a = package()
    expected_config(old,current,a)
    cases=[]
    def change(fn):
        c=deepcopy(current);fn(c);cases.append(c)
    change(lambda c:c['ia_slots'].__setitem__('main',AR))
    change(lambda c:c['featured'].__setitem__(0,AR))
    change(lambda c:c['ia_slots']['important'].reverse())
    change(lambda c:c['latest'].reverse())
    change(lambda c:c['ia_slots']['latest'].__setitem__(0,AR))
    change(lambda c:c['ticker_entries'].reverse())
    change(lambda c:c['ticker_entries'][0]['titles'].__setitem__('fr','changed'))
    change(lambda c:c['ticker_slugs'].__setitem__(0,AR))
    change(lambda c:c['primary_door'].__setitem__(old['latest'][0],'science'))
    change(lambda c:c['card_image_overrides'][old['featured'][0]].__setitem__('image','changed.jpg'))
    change(lambda c:c['primary_door'].__setitem__(AR,'hunting'))
    change(lambda c:c['card_image_overrides'][AR].__setitem__('image','changed.jpg'))
    change(lambda c:c['omit_from_latest'].remove(AR))
    change(lambda c:c['desk_slugs']['Science & Discoveries'].reverse())
    change(lambda c:next(d for d in c['ia_door_sections'] if d['door']=='science')['slugs'].__setitem__(0,'wrong-slug'))
    change(lambda c:next(d for d in c['ia_door_sections'] if d['door']=='science')['slugs'].append(AR))
    for door in current['ia_door_sections']:
        change(lambda c,door=door:next(d for d in c['ia_door_sections'] if d['door']==door['door'])['slugs'].reverse())
    rejected=0
    for c in cases:
        if c == current: continue  # Single-card doors have no alternate order.
        try: expected_config(old,c,a)
        except AssertionError: rejected+=1
        else: raise AssertionError('Unauthorized honey-buzzard configuration accepted')
    for kind in ('slug','language','category','photo'):
        data={'articles':[deepcopy(a)]};candidate=data['articles'][0]
        if kind=='slug': candidate['slugs']['ar']='wrong-slug'
        elif kind=='language': del candidate['translations']['fr']
        elif kind=='category': candidate['category']='صيد'
        else: candidate['photos'][0]['path']='unapproved.jpg'
        try: validate_package(data)
        except AssertionError: pass
        else: raise AssertionError('Unauthorized package accepted: '+kind)
    good=['docs/'+p for p in PHOTO_PATHS]
    for paths in (good+['docs/media/uploads/2026/10/existing.jpg'],good[:-1],good+['docs/assets/css/site.css']):
        try: assert_media_delta(paths)
        except AssertionError: pass
        else: raise AssertionError('Unapproved media mutation accepted')
    test_rendered_negative_guards(base, old, current)
    print(f'PASS: honey-buzzard exact Science-only delta; {rejected} configuration and 7 package/media mutations rejected')


def test_rendered_negative_guards(base, old, current):
    rel = 'docs/index.html'
    baseline = subprocess.check_output(['git','show',base+':'+rel],cwd=ROOT).decode()
    actual = html.fromstring((ROOT/rel).read_text())
    section = '//section[@class="home-section"][div/h2="علوم"]'
    mutations = [
        lambda t:t.xpath(section+'//article')[1].xpath('.//img')[0].set('src','changed.jpg'),
        lambda t:setattr(t.xpath(section+'//article')[1].xpath('.//h3/a')[0],'text','changed title'),
        lambda t:t.xpath(section+'//article')[1].xpath('.//h3/a')[0].set('href','wrong-slug/'),
        lambda t:t.xpath(section+'//article')[0].addprevious(t.xpath(section+'//article')[1]),
        lambda t:t.xpath(section+'//article')[0].addnext(deepcopy(t.xpath(section+'//article')[0])),
        lambda t:setattr(t.xpath('//header')[0],'tail','Unauthorized visible tail'),
        lambda t:t.xpath(section+'/div/a')[0].set('href','wrong-section/'),
        lambda t:t.xpath(section+'//article')[0].getparent().set('class','changed-grid'),
        lambda t:setattr(t.xpath(section+'//article')[0],'tail','Unauthorized card tail'),
    ]
    for mutate in mutations:
        candidate=deepcopy(actual);mutate(candidate)
        try: assert_honey_home(baseline,candidate,rel,'ar',current)
        except AssertionError: pass
        else: raise AssertionError('Rendered homepage mutation accepted')
    # Exercise the real artifact readers without modifying any approved file.
    target = DOCS / PHOTO_PATHS[0]
    read_bytes = Path.read_bytes
    with patch.object(Path, 'read_bytes', lambda p: read_bytes(p)+b'changed' if p == target else read_bytes(p)):
        try: honey_expected(old,current,base)
        except AssertionError: pass
        else: raise AssertionError('Changed approved image bytes accepted')
    rel = 'docs/fr/index.html'
    baseline = subprocess.check_output(['git','show',base+':'+rel],cwd=ROOT).decode()
    actual = html.fromstring((ROOT/rel).read_text())
    target = DOCS/'fr/posts'/EN/'index.html'
    is_file = Path.is_file
    with patch.object(Path, 'is_file', lambda p: False if p == target else is_file(p)):
        try: assert_honey_home(baseline,actual,rel,'fr',current)
        except AssertionError: pass
        else: raise AssertionError('Missing rendered French translation accepted')
    print('PASS: 9 rendered-DOM, changed-image-byte and missing-rendered-translation mutations rejected')
