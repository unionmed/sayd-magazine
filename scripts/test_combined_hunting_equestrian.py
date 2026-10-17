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


def test_preserved(base):
    old_config=json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT))
    current=config()
    approved_interview = current['ia_slots']['main']=='شيرين-بو-رفول-مكافحة-الصيد-الجائر' and old_config['ia_slots']['main']!=current['ia_slots']['main']
    if approved_interview:
        from homepage_demotion import demote_side_cards
        expected_config=deepcopy(old_config)
        lead=current['ia_slots']['main']
        expected_config['ia_slots']['main']=lead
        expected_config['ia_slots']['important']=[old_config['ia_slots']['main']]+old_config['ia_slots']['important'][:3]
        expected_config['featured']=[lead]+expected_config['ia_slots']['important']
        demote_side_cards(expected_config,old_config['ia_slots']['important'])
        for key in ('featured','latest','ia_slots'):assert current[key]==expected_config[key],key
        assert current['ticker_slugs']==[lead]+old_config['ticker_slugs']
        assert current['ticker_entries'][1:]==old_config['ticker_entries']
        assert {k:v for k,v in current['primary_door'].items() if k!=lead}==old_config['primary_door']
        assert current['primary_door'][lead]=='interviews'
        assert {k:v for k,v in current['card_image_overrides'].items() if k!=lead}==old_config['card_image_overrides']
    else:
        for key in ('featured','latest','ia_slots','ticker_slugs','ticker_entries','card_image_overrides','primary_door','memory_after_door'):
            assert old_config[key]==current[key],key
    assert current['memory_after_door']==old_config['memory_after_door']
    assert current['memory_visible'] is False
    # Interviews is an independently reviewed chronological collection; its
    # owner-approved selection may change without changing unrelated doors.
    from interview_collection import homepage_slugs
    assert next(s['slugs'] for s in current['ia_door_sections'] if s['door']=='interviews') == homepage_slugs('ar', current)
    for old in old_config['ia_door_sections']:
        if old['door'] not in ('hunting','equestrian','interviews'):
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
        for cls in (('sayd-tv',) if approved_interview else ('feature-lead','feature-stack','latest-col','sayd-tv','ticker')):
            xp='//*[contains(concat(" ",normalize-space(@class)," ")," '+cls+' ")]'
            def canonical(n):return html.tostring(n,encoding='unicode',with_tail=False)
            assert [canonical(n) for n in before.xpath(xp)]==[canonical(n) for n in after.xpath(xp)],(lang,cls)
        assert merge_hunting_section(new,lang)==new
    # No article body, dates, media, or SEO changes are licensed by this merger.
    changed=subprocess.check_output(['git','diff','--name-only','-z',base,'--','docs'],cwd=ROOT).decode().split('\0')
    from rollout_mobile_nav_heritage_20261015 import nav_replace
    for rel in changed:
        if '/posts/' not in rel or not rel.endswith('.html'):continue
        if approved_interview and any('/posts/'+slug+'/' in rel for slug in ('شيرين-بو-رفول-مكافحة-الصيد-الجائر','shireen-bou-rafoul-anti-poaching-interview')):continue
        prior=subprocess.check_output(['git','show',base+':'+rel],cwd=ROOT).decode()
        transformed,_=nav_replace(prior,ROOT/rel)
        from build_site_search import links as search_links
        current_article=(ROOT/rel).read_text()
        if approved_interview:
            from sync_tickers import TICKER
            assert TICKER.sub('',search_links(transformed,ROOT/rel))==TICKER.sub('',current_article),rel
        else:assert search_links(transformed,ROOT/rel)==current_article,rel
    print('PASS: eight chronological mixed cards, no quota, preserved upper slots, other doors, TV, article content and legacy URLs')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='HEAD');args=parser.parse_args()
    test_rotation();test_preserved(args.base)
