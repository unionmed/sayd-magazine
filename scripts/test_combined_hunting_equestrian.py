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


def test_preserved(base):
    old_config=json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT))
    current=config()
    from ticker_policy import select as select_ticker, validate as validate_ticker
    validate_ticker(current)
    approved_ticker_rotation = current['ticker_entries'] == select_ticker(old_config['ticker_entries'])
    approved_interview = current['ia_slots']['main']=='شيرين-بو-رفول-مكافحة-الصيد-الجائر' and old_config['ia_slots']['main']!=current['ia_slots']['main']
    approved_four_news=four_news_expected(old_config,current) is not None
    approved_omayed=omayed_expected(old_config,current) is not None
    if approved_four_news or approved_omayed:
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
    for old in old_config['ia_door_sections']:
        if old['door'] not in (('hunting','equestrian','interviews','gear','wildlife','science') if approved_four_news else ('hunting','equestrian','interviews')):
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
        for cls in (('feature-lead','feature-stack','sayd-tv') if approved_four_news or approved_omayed else ('sayd-tv',) if approved_interview else ('feature-lead','feature-stack','latest-col','sayd-tv','ticker')):
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
    test_rotation();test_preserved(args.base);test_four_news_negative_guards(args.base);test_omayed_negative_guards(args.base)
