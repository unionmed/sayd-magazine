"""Approved eight-card merger, without topic quotas or unrelated content drift."""
from copy import deepcopy
from datetime import date, timedelta
import json, subprocess
from lxml import html
from refresh_homepage_doors import ROOT, DOCS, config, validate_config, DOORS, merge_hunting_section, local_slug
from homepage_hunting_rotation import select, expected


def test_rotation():
    c=config()
    assert [d['door'] for d in c['ia_door_sections']]==[d[0] for d in DOORS]
    actual=next(d['slugs'] for d in c['ia_door_sections'] if d['door']=='hunting')
    assert len(actual)==8 and actual==expected(c)
    fixture=deepcopy(c)
    fixture.update(featured=[],latest=[],omit_from_home=[],omit_from_home_desks=[])
    fixture['ia_door_sections']=[{'door':'hunting','slugs':[]}]
    slugs=[f'fixture-{i}' for i in range(12)]
    pool=[(s,date(2026,10,17)-timedelta(days=i)) for i,s in enumerate(slugs)]
    for topic in ('hunting','equestrian'):
        fixture['primary_door']={s:topic for s in slugs}
        assert select(fixture,pool)==slugs[:8], 'No forced 4/4 or topic quota'
    fixture['primary_door']={s:'equestrian' if i%3==0 else 'hunting' for i,s in enumerate(slugs)}
    assert select(fixture,list(reversed(pool)))==slugs[:8]
    fixture['featured']=[slugs[0]]; fixture['latest']=[slugs[1]]
    assert select(fixture,pool)==slugs[2:10]
    for size in (7,9):
        bad=deepcopy(c);next(d for d in bad['ia_door_sections'] if d['door']=='hunting')['slugs']=slugs[:size]
        try: validate_config(bad)
        except AssertionError: pass
        else: raise AssertionError('Invalid combined door capacity accepted')


def four_news_expected(old, current):
    """Bounded owner-approved 18 October publication, not a generic bypass."""
    source=ROOT/'content/features/four-news-20261018.json'
    if not source.exists(): return None
    articles=json.loads(source.read_text())['articles']
    assert [a['key'] for a in articles]==['godolphin','cairo','abudhabi','loon']
    slugs=[a['slugs']['ar'] for a in articles]
    if any(s in old['primary_door'] for s in slugs): return None
    assert all(a['date']=='2026-10-18' and a['publication_ready'] for a in articles)
    assert [a['door'] for a in articles]==['equestrian','gear','wildlife','science']
    assert [a['placement'] for a in articles]==['news','news','news','category']
    expected=deepcopy(old); news=articles[:3]
    latest=(slugs[:3]+[s for s in old['ia_slots']['latest'] if s not in slugs[:3]])[:8]
    expected['latest']=latest;expected['ia_slots']['latest']=latest
    for a in articles:
        s=a['slugs']['ar'];p=a['photos'][0]
        expected['primary_door'][s]=a['door']
        expected['card_image_overrides'][s]={'image':p['path'],'position':'50% 50%','alt':p['alt']}
    from ticker_policy import select as select_ticker
    expected['ticker_entries']=select_ticker([{'slug':a['slugs']['ar'],'titles':{l:a['translations'][l]['ticker'] for l in ('ar','en','fr')}} for a in news]+old['ticker_entries'])
    expected['ticker_slugs']=[e['slug'] for e in expected['ticker_entries']]
    for k in ('featured','latest','ia_slots','ticker_entries','ticker_slugs','primary_door','card_image_overrides','memory_after_door'):
        assert current[k]==expected[k],('four-news',k)
    assert slugs[3] not in current['latest']+current['ticker_slugs']
    top=set(expected['featured']+latest)
    for door in ('gear','wildlife','science'):
        before=next(d['slugs'] for d in old['ia_door_sections'] if d['door']==door)
        added=[slugs[3]] if door=='science' else []
        added += [s for s in old['latest'] if s not in latest and old['primary_door'].get(s)==door]
        wanted=list(dict.fromkeys(s for s in added+before if s not in top))[:4]
        assert next(d['slugs'] for d in current['ia_door_sections'] if d['door']==door)==wanted,('four-news-door',door)
    return expected


def test_four_news_negative_guards(base):
    old=json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT));current=config()
    if four_news_expected(old,current) is None:return
    loon=json.loads((ROOT/'content/features/four-news-20261018.json').read_text())['articles'][3]['slugs']['ar']
    broken=[]
    c=deepcopy(current);c['latest'][0]=loon;broken.append(c)
    c=deepcopy(current);c['ticker_entries'][0]['slug']=loon;broken.append(c)
    c=deepcopy(current);c['ia_slots']['main']='unauthorized';broken.append(c)
    c=deepcopy(current);c['ia_slots']['important'].reverse();broken.append(c)
    c=deepcopy(current);c['ticker_entries'].reverse();broken.append(c)
    c=deepcopy(current);next(d['slugs'] for d in c['ia_door_sections'] if d['door']=='science').clear();broken.append(c)
    for candidate in broken:
        try:four_news_expected(old,candidate)
        except AssertionError:pass
        else:raise AssertionError('Unauthorized four-news mutation accepted')


def omayed_expected(old, current):
    """Exact approved Omayed addition; preserve every other configuration field."""
    source=ROOT/'content/features/egypt-uae-omayed-20261018.json'
    slug='تعاون-مصري-إماراتي-الحبارى-محمية-العميد'
    if not source.exists() or slug in old['primary_door']: return None
    articles=json.loads(source.read_text())['articles']
    assert len(articles)==1
    a=articles[0];photo=a['photos'][0]
    assert a['key']=='omayed' and a['slugs']['ar']==slug
    assert a['date']=='2026-10-18' and a['publication_ready']
    assert a['door']=='wildlife' and a['placement']=='news'
    assert a['category']=='حياة-برية-وتخييم'
    assert photo['path']=='media/uploads/2026/10/african-houbara-mourad-harzallah-algeria-2020.jpg'
    wanted=deepcopy(old)
    latest=([slug]+old['ia_slots']['latest'])[:8]
    wanted['latest']=latest;wanted['ia_slots']['latest']=latest
    wanted['primary_door'][slug]='wildlife'
    wanted['card_image_overrides'][slug]={'image':photo['path'],'position':'50% 50%','alt':photo['alt']}
    from ticker_policy import select as select_ticker
    wanted['ticker_entries']=select_ticker([{'slug':slug,'titles':{lang:a['translations'][lang]['ticker'] for lang in ('ar','en','fr')}}]+old['ticker_entries'])
    wanted['ticker_slugs']=[entry['slug'] for entry in wanted['ticker_entries']]
    # Only the existing chronological hunting rotation absorbs the displaced
    # Updates story; every other door and the Shireen upper slots stay exact.
    selected=expected(wanted)
    next(d for d in wanted['ia_door_sections'] if d['door']=='hunting')['slugs']=selected
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    wanted['desk_slugs']['صيد']=selected
    wanted['desk_slugs']['Hunting']=[pairs[s] for s in selected]
    assert current==wanted, ('omayed', [key for key in set(current)|set(wanted) if current.get(key)!=wanted.get(key)])
    return wanted


def test_omayed_negative_guards(base):
    old=json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT));current=config()
    if omayed_expected(old,current) is None:return
    broken=[]
    c=deepcopy(current);c['latest'].reverse();broken.append(c)
    c=deepcopy(current);c['ia_slots']['main']='unauthorized';broken.append(c)
    c=deepcopy(current);c['ia_slots']['important'].reverse();broken.append(c)
    c=deepcopy(current);c['ticker_entries'].reverse();broken.append(c)
    c=deepcopy(current);c['ticker_entries'][0]['titles']['en']='unauthorized';broken.append(c)
    c=deepcopy(current);c['primary_door'][c['latest'][0]]='science';broken.append(c)
    c=deepcopy(current);c['card_image_overrides'][c['latest'][0]]['image']='unapproved.jpg';broken.append(c)
    c=deepcopy(current);c['memory_visible']=True;broken.append(c)
    for door in current['ia_door_sections']:
        c=deepcopy(current);next(d for d in c['ia_door_sections'] if d['door']==door['door'])['slugs']=[];broken.append(c)
    for candidate in broken:
        try:omayed_expected(old,candidate)
        except AssertionError:pass
        else:raise AssertionError('Unauthorized Omayed mutation accepted')


APPROVED_THREE_SLUGS = (
    'الشمال-إزالة-24750-متر-شباك-الصيد-الجائر',
    'المدن-تغير-خريطة-الطيور-والشتاء-يكشف-الفارق',
    'بطولة-السلوقي-العربي-نوفمبر-2026-أبريل-2027',
)


def approved_three_articles():
    """The exact 20 October package, never permission for arbitrary additions."""
    articles=json.loads((ROOT/'content/features/approved-three-20261020.json').read_text())['articles']
    assert [a['slugs']['ar'] for a in articles]==list(APPROVED_THREE_SLUGS)
    translated=['north-lebanon-24750-square-metres-illegal-nets-2026',
                'cities-bird-diversity-winter-nature-cities-2026',
                'arabian-saluki-championship-november-2026-april-2027']
    for lang in ('en','fr'):
        assert [a['slugs'][lang] for a in articles]==translated
    assert all(a['date']=='2026-10-20' and a['publication_ready'] is True for a in articles)
    assert [a['door'] for a in articles]==['hunting','science','hunting']
    assert [a['category'] for a in articles]==['صيد','علوم-واكتشافات','صيد']
    assert [a['placement'] for a in articles]==['main','category','category']
    assert [[p['path'] for p in a['photos']] for a in articles]==[
        ['assets/images/2026/10/north-lebanon-nets-team-20261020.jpg',
         'assets/images/2026/10/north-lebanon-nets-orchard-20261020.jpg',
         'assets/images/2026/10/north-lebanon-nets-fieldwork-20261020.jpg',
         'assets/images/2026/10/north-lebanon-nets-collected-20261020.jpg'],
        ['assets/images/2026/10/istanbul-galata-seagulls-mehmetburakcoban-20150317.jpg',
         'assets/images/2026/10/beirut-aub-pelicans-bassem-20180917-frame60.jpg'],
        ['assets/images/2026/10/arabian-saluki-efc-asd22.png',
         'assets/images/2026/10/arabian-saluki-efc-asd26.jpg']]
    return articles


def approved_three_expected(old, current):
    source=ROOT/'content/features/approved-three-20261020.json'
    if not source.exists() or any(s in old['primary_door'] for s in APPROVED_THREE_SLUGS): return None
    articles=approved_three_articles()
    north,science,saluki=APPROVED_THREE_SLUGS
    assert old['ia_slots']['main']=='شيرين-بو-رفول-مكافحة-الصيد-الجائر'
    from homepage_demotion import demote_side_cards
    from ticker_policy import select as select_ticker
    wanted=deepcopy(old)
    wanted['ia_slots']['main']=north
    wanted['ia_slots']['important']=[old['ia_slots']['main']]+old['ia_slots']['important'][:3]
    wanted['featured']=[north]+wanted['ia_slots']['important']
    demote_side_cards(wanted,old['ia_slots']['important'])
    wanted['omit_from_latest']+=list(APPROVED_THREE_SLUGS[1:])
    for a in articles:
        slug=a['slugs']['ar'];photo=a['photos'][0]
        wanted['primary_door'][slug]=a['door']
        wanted['card_image_overrides'][slug]={'image':photo['path'],'position':'50% 50%','alt':photo['alt']}
    wanted['ticker_entries']=select_ticker([
        {'slug':a['slugs']['ar'],'titles':{lang:a['translations'][lang]['ticker'] for lang in ('ar','en','fr')}}
        for a in (articles[0],articles[2])]+old['ticker_entries'])
    wanted['ticker_slugs']=[e['slug'] for e in wanted['ticker_entries']]
    assert wanted['ticker_slugs'][:2]==[north,saluki] and len(wanted['ticker_slugs'])==10
    science_cards=([science]+next(d['slugs'] for d in old['ia_door_sections'] if d['door']=='science'))[:4]
    next(d for d in wanted['ia_door_sections'] if d['door']=='science')['slugs']=science_cards
    hunting_cards=expected(wanted)
    assert hunting_cards[0]==saluki
    next(d for d in wanted['ia_door_sections'] if d['door']=='hunting')['slugs']=hunting_cards
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    for cards,ar,en in ((hunting_cards,'صيد','Hunting'),(science_cards,'علوم واكتشافات','Science & Discoveries')):
        wanted['desk_slugs'][ar]=cards
        wanted['desk_slugs'][en]=[pairs[s] for s in cards]
    assert not set((science,saluki)).intersection(wanted['featured']+wanted['latest'])
    assert science not in wanted['ticker_slugs']
    assert current==wanted, ('approved-three', [k for k in set(current)|set(wanted) if current.get(k)!=wanted.get(k)])
    return wanted


def test_approved_three_negative_guards(base):
    old=json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT));current=config()
    if approved_three_expected(old,current) is None:return
    north,science,saluki=APPROVED_THREE_SLUGS
    broken=[]
    for slug in ('unauthorized',science,saluki):
        c=deepcopy(current);c['ia_slots']['main']=slug;c['featured'][0]=slug;broken.append(c)
    for slug in (science,saluki):
        c=deepcopy(current);c['latest'][0]=slug;c['ia_slots']['latest'][0]=slug;broken.append(c)
    c=deepcopy(current);c['ia_slots']['important'].reverse();c['featured']=[north]+c['ia_slots']['important'];broken.append(c)
    c=deepcopy(current);c['latest']=old['latest'];c['ia_slots']['latest']=old['ia_slots']['latest'];broken.append(c)
    c=deepcopy(current);c['ticker_entries'][1]['slug']=science;broken.append(c)
    c=deepcopy(current);c['ticker_entries'].reverse();c['ticker_slugs'].reverse();broken.append(c)
    c=deepcopy(current);c['ticker_entries'][0]['titles']['fr']='unauthorized';broken.append(c)
    c=deepcopy(current);c['ticker_entries'].append(deepcopy(c['ticker_entries'][0]));broken.append(c)
    c=deepcopy(current);c['primary_door'][saluki]='science';broken.append(c)
    c=deepcopy(current);c['primary_door']['unauthorized']='hunting';broken.append(c)
    c=deepcopy(current);c['card_image_overrides'][north]['image']='unapproved.jpg';broken.append(c)
    c=deepcopy(current);c['omit_from_latest'].remove(science);broken.append(c)
    c=deepcopy(current);c['memory_visible']=True;broken.append(c)
    c=deepcopy(current);c['desk_slugs']['Science & Discoveries'].reverse();broken.append(c)
    for door in current['ia_door_sections']:
        c=deepcopy(current);next(d for d in c['ia_door_sections'] if d['door']==door['door'])['slugs']=[];broken.append(c)
    for candidate in broken:
        try:approved_three_expected(old,candidate)
        except AssertionError:pass
        else:raise AssertionError('Unauthorized approved-three mutation accepted')


def assert_approved_three_home(old_page, after, rel, lang, current):
    """Check exact rendered cards and all nine article mirrors, not just counts."""
    from urllib.parse import unquote, urlsplit
    from refresh_homepage_doors import collect
    articles=approved_three_articles()
    additions={a['slugs']['ar']:a for a in articles}
    page_path=ROOT/rel
    baseline=collect(old_page,page_path,page_path)
    def nodes(cls):
        return after.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," '+cls+' ")]')
    def check_cards(rows,slugs):
        assert len(rows)==len(slugs),(lang,'card count',slugs)
        for row,slug in zip(rows,slugs):
            local=local_slug(slug,lang)
            links=row.xpath('.//a[contains(@href,"posts/")]')
            assert links and all(unquote(urlsplit(a.get('href')).path)==f'posts/{local}/index.html' for a in links),(lang,slug,'links')
            titles=row.xpath('.//h2/a | .//h3/a | .//*[@class="feed-title"]')
            title=additions[slug]['translations'][lang]['title'] if slug in additions else baseline[local]['title']
            assert len(titles)==1 and titles[0].text_content().strip()==title,(lang,slug,'title')
            images=row.xpath('.//img')
            assert len(images)==1,(lang,slug,'image count')
            override=current['card_image_overrides'].get(slug)
            image=(DOCS/override['image']).resolve() if override else (page_path.parent/baseline[local]['image']).resolve()
            assert (page_path.parent/unquote(urlsplit(images[0].get('src')).path)).resolve()==image,(lang,slug,'image')
            if override:assert images[0].get('alt')==override['alt'][lang],(lang,slug,'alt')
    check_cards(nodes('feature-lead'),[current['ia_slots']['main']])
    assert len(nodes('feature-stack'))==1
    check_cards(nodes('feature-stack')[0].xpath('./article'),current['ia_slots']['important'])
    check_cards(after.xpath('//ul[@class="latest-feed"]/li'),current['latest'])
    for door in ('hunting','science'):
        heading=next(d[{'ar':1,'en':2,'fr':3}[lang]] for d in DOORS if d[0]==door)
        section=after.xpath('//section[contains(concat(" ",normalize-space(@class)," ")," home-section ")][div/h2=$heading]',heading=heading)
        assert len(section)==1,(lang,door)
        check_cards(section[0].xpath('.//article'),next(d['slugs'] for d in current['ia_door_sections'] if d['door']==door))
    from sync_tickers import TICKER, sources, ticker_for
    loops=TICKER.findall(page_path.read_text())
    assert len(loops)==2 and all(loop[1]==ticker_for(page_path,sources(DOCS)[lang]) for loop in loops)
    for a in articles:
        assert local_slug(a['slugs']['ar'],lang)==a['slugs'][lang]
        post=page_path.parent/'posts'/a['slugs'][lang]/'index.html'
        tree=html.parse(str(post))
        assert tree.xpath('//h1/text()')==[a['translations'][lang]['title']]
        images=tree.xpath('//article[@class="article-content"]//figure/img')
        assert [(post.parent/unquote(urlsplit(image.get('src')).path)).resolve() for image in images]==[(DOCS/p['path']).resolve() for p in a['photos']],(lang,a['slugs']['ar'],'article images')


def test_preserved(base):
    old_config=json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT))
    current=config()
    from ticker_policy import select as select_ticker, validate as validate_ticker
    validate_ticker(current)
    approved_ticker_rotation = current['ticker_entries'] == select_ticker(old_config['ticker_entries'])
    approved_interview = current['ia_slots']['main']=='شيرين-بو-رفول-مكافحة-الصيد-الجائر' and old_config['ia_slots']['main']!=current['ia_slots']['main']
    approved_four_news=four_news_expected(old_config,current) is not None
    approved_omayed=omayed_expected(old_config,current) is not None
    approved_three=approved_three_expected(old_config,current) is not None
    if approved_four_news or approved_omayed or approved_three:
        pass  # All changed placement fields independently validated above.
    elif approved_interview:
        from homepage_demotion import demote_side_cards
        expected_config=deepcopy(old_config)
        lead=current['ia_slots']['main']
        expected_config['ia_slots']['main']=lead
        expected_config['ia_slots']['important']=[old_config['ia_slots']['main']]+old_config['ia_slots']['important'][:3]
        expected_config['featured']=[lead]+expected_config['ia_slots']['important']
        demote_side_cards(expected_config,old_config['ia_slots']['important'])
        for key in ('featured','latest','ia_slots'):assert current[key]==expected_config[key],key
        assert current['ticker_entries'][0]['slug'] == lead
        assert current['ticker_entries'] == select_ticker([current['ticker_entries'][0]] + old_config['ticker_entries'])
        assert current['ticker_slugs'] == [entry['slug'] for entry in current['ticker_entries']]
        assert {k:v for k,v in current['primary_door'].items() if k!=lead}==old_config['primary_door']
        assert current['primary_door'][lead]=='interviews'
        assert {k:v for k,v in current['card_image_overrides'].items() if k!=lead}==old_config['card_image_overrides']
    else:
        for key in ('featured','latest','ia_slots','ticker_slugs','ticker_entries','card_image_overrides','primary_door','memory_after_door'):
            if key in ('ticker_slugs', 'ticker_entries') and approved_ticker_rotation:
                continue
            assert old_config[key]==current[key],key
    assert current['memory_after_door']==old_config['memory_after_door']
    assert current['memory_visible'] is False
    # Interviews is an independently reviewed chronological collection; its
    # owner-approved selection may change without changing unrelated doors.
    from interview_collection import homepage_slugs
    assert next(s['slugs'] for s in current['ia_door_sections'] if s['door']=='interviews') == homepage_slugs('ar', current)
    changed_doors=('hunting','equestrian','interviews','gear','wildlife','science') if approved_four_news else ('hunting','equestrian','interviews','science') if approved_three else ('hunting','equestrian','interviews')
    for old in old_config['ia_door_sections']:
        if old['door'] not in changed_doors:
            assert old in current['ia_door_sections'],old['door']
    for lang,prefix in [('ar',''),('en','en/'),('fr','fr/')]:
        rel='docs/'+prefix+'index.html'
        old=subprocess.check_output(['git','show',base+':'+rel],cwd=ROOT).decode()
        new=(ROOT/rel).read_text()
        before=html.fromstring(old);after=html.fromstring(new)
        assert not after.xpath('//section[@class="memory-strip"]')
        section=after.xpath('//section[@class="home-section"]')[0]
        assert section.xpath('.//div[contains(@class,"section-head")]/a/text()')==[{'ar':'المزيد','en':'More','fr':'Voir plus'}[lang]]
        selected=next(d['slugs'] for d in current['ia_door_sections'] if d['door']=='hunting')
        rows=section.xpath('.//article')
        assert len(rows)==8 and len(after.xpath('//*[@class="card-topic"]'))==8
        for slug,row in zip(selected,rows):
            topic='equestrian' if current['primary_door'].get(slug)=='equestrian' else 'hunting'
            label={'ar':{'hunting':'صيد','equestrian':'فروسية'},'en':{'hunting':'Hunting','equestrian':'Equestrian'},'fr':{'hunting':'Chasse','equestrian':'Équitation'}}[lang][topic]
            assert row.xpath('.//*[@class="card-topic"]/text()')==[' · '+label]
            assert local_slug(slug,lang) in row.xpath('.//h3/a/@href')[0]
        if approved_three:
            assert_approved_three_home(old,after,rel,lang,current)
        for cls in (('sayd-tv',) if approved_three else ('feature-lead','feature-stack','sayd-tv') if approved_four_news or approved_omayed else ('sayd-tv',) if approved_interview else ('feature-lead','feature-stack','latest-col','sayd-tv','ticker')):
            if cls == 'ticker' and approved_ticker_rotation:
                from sync_tickers import TICKER, sources, ticker_for
                expected_ticker = ticker_for(ROOT/rel, sources(DOCS)[lang])
                loops = TICKER.findall(new)
                assert len(loops) == 2
                assert all(loop[1] == expected_ticker for loop in loops)
                continue
            xp='//*[contains(concat(" ",normalize-space(@class)," ")," '+cls+' ")]'
            def canonical(n):return html.tostring(n,encoding='unicode',with_tail=False)
            assert [canonical(n) for n in before.xpath(xp)]==[canonical(n) for n in after.xpath(xp)],(lang,cls)
        assert merge_hunting_section(new,lang)==new
    # The original merger's whole-article byte proof is still executed, against
    # its immutable original base/head, by test_historical_hunting_merger.py.
    # Applying that one-off migration transform to every future editorial PR
    # incorrectly freezes article bodies. Check its enduring navigation contract
    # on the actual current tree instead; publication/SEO/archive gates remain.
    from test_combined_archive_navigation import test_navigation_and_market_across_all_pages
    test_navigation_and_market_across_all_pages()
    print('PASS: eight chronological mixed cards, no quota, preserved upper slots, other doors, TV and current navigation/legacy URLs')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='HEAD');args=parser.parse_args()
    test_rotation();test_preserved(args.base);test_four_news_negative_guards(args.base);test_omayed_negative_guards(args.base);test_approved_three_negative_guards(args.base)
