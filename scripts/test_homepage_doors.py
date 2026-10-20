"""Regression checks for the three mirrored homepages and fail-closed rules."""
from copy import deepcopy
from check_publication_contract import check
from refresh_homepage_doors import refresh, DOCS, DOORS, config, validate_config, channel_config


def test_hunting_rotation():
    """Exercise rotation independently of the current editorial selection."""
    from datetime import date, timedelta
    from unittest.mock import patch
    from homepage_hunting_rotation import select

    eligible=[f'eligible{i}' for i in range(10)]
    excluded=['featured-story','omitted-story','omitted-desk','other-door','interview']
    fixture={
        'featured':['featured-story'],
        'latest':['displaced']+[f'update{i}' for i in range(7)],
        'omit_from_home':['omitted-story'],
        'omit_from_home_desks':['omitted-desk'],
        'ia_door_sections':[{'door':'hunting','slugs':eligible[:8]},
                            {'door':'gear','slugs':['other-door']}],
        'primary_door':{slug:'hunting' for slug in eligible+excluded+['displaced','historical']},
    }
    # Both topics share one date-ordered pool, with no fixed topic quota.
    fixture['primary_door'].update({slug:'equestrian' for slug in eligible[::3]})
    fixture['primary_door']['non-hunting']='science'
    pool=[(slug,date(2026,9,20)-timedelta(days=i)) for i,slug in enumerate(eligible)]
    pool += [(slug,date(2026,9,30)) for slug in excluded+['non-hunting']]
    pool += [('displaced',date(2026,9,29)),('historical',date(2025,12,31)),pool[0]]
    # Patch only the external interview registry; keep its reservation behavior.
    with patch('interview_collection.homepage_slugs',return_value=['interview']):
        current=select(fixture,list(reversed(pool)))
        assert current==eligible[:8]
        assert 'displaced' not in current, 'Updates story entered its lower door early'
        moved=deepcopy(fixture)
        moved['latest'][0]='replacement-update'
        after=select(moved,pool)
        assert after==['displaced']+current[:7]
        assert len(after)==len(set(after))==8 and current[-1] not in after
        assert not set(after).intersection(moved['featured']+moved['latest']+excluded)
        # Promotion must remove a door story even while the count stays valid.
        promoted=deepcopy(fixture)
        promoted['latest'][1]=current[0]
        assert select(promoted,pool)==eligible[1:9]
        # Neither duplicate candidates nor historical stories may fill a gap.
        short_pool=[item for item in pool if item[0] not in eligible[7:]]
        try:select(fixture,short_pool)
        except AssertionError as error:assert 'eight eligible' in str(error)
        else:raise AssertionError('Insufficient eligible hunting cards accepted')


def test_memory_removal():
    """Only the Memory display is removed; every legacy article survives."""
    import json
    from lxml import html
    from check_publication_contract import CONTRACT
    contract=json.loads(CONTRACT.read_text())
    assert config()['memory_visible'] is False
    from refresh_homepage_doors import remove_memory
    fixture='<main>before\n<section class="memory-strip"><article>old card</article></section>\nafter</main>'
    assert remove_memory(fixture)=='<main>before\nafter</main>'
    assert remove_memory(remove_memory(fixture))==remove_memory(fixture)

    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
        page=(DOCS/prefix/'index.html').read_text()
        assert not html.fromstring(page).xpath('//section[@class="memory-strip"]')
    for slug in contract['memory_slugs']:
        assert (DOCS/'posts'/slug/'index.html').is_file(), slug


def test_homepages():
    test_memory_removal()
    test_hunting_rotation()
    from test_hunting_reels import check_reels
    check_reels()
    # Side-card overflow must enter Updates before becoming eligible for a door.
    from homepage_demotion import demote_side_cards
    from datetime import date
    fixture={'featured':['new','previous','side1','side2','side3'],
             'latest':[f'update{i}' for i in range(8)],'ia_slots':{}}
    days={f'update{i}':date(2026,9,28-i) for i in range(8)}
    days['displaced']=date(2026,9,29)
    assert demote_side_cards(fixture,['side1','side2','side3','displaced'],days.__getitem__)==['displaced']
    assert fixture['latest']==['displaced']+[f'update{i}' for i in range(7)]
    assert fixture['ia_slots']['latest']==fixture['latest']
    check()
    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
        path=DOCS/prefix/'index.html';before=path.read_bytes()
        refresh(path,lang)
        assert path.read_bytes()==before, f'{lang}: refresh is not idempotent'
    for key in ('featured','latest'):
        bad=deepcopy(config());bad[key].append('extra-card')
        try:validate_config(bad)
        except AssertionError:pass
        else:raise AssertionError('Extra card accepted')
    # A duplicate at the correct count must fail independently of overflow.
    bad=deepcopy(config())
    hunting=next(d['slugs'] for d in bad['ia_door_sections'] if d['door']=='hunting')
    assert len(hunting)==len(set(hunting))==8
    hunting[1]=hunting[0]
    assert len(hunting)==8 and len(set(hunting))==7
    try:validate_config(bad)
    except AssertionError:pass
    else:raise AssertionError('Duplicate card accepted at the valid count')
    # A French-only missing image must fail; restore the fixture even on failure.
    from html import escape
    from lxml import html
    from check_publication_contract import resolved
    p=DOCS/'fr/index.html';original=p.read_bytes()
    image_xpath='//article[contains(concat(" ",normalize-space(@class)," ")," feature-lead ")]//img/@src'
    sources=html.fromstring(original).xpath(image_xpath)
    assert len(sources)==1, 'French lead must have one current card image'
    assert (DOCS/resolved(p,sources[0])).is_file(), 'Current card image must exist'
    missing='../missing-test-homepage-image.jpg'
    missing_path=resolved(p,missing)
    assert not (DOCS/missing_path).exists(), 'Missing-image fixture must not exist'
    wrong=original.replace(f'src="{escape(sources[0],quote=True)}"'.encode(),
                           f'src="{missing}"'.encode(),1)
    assert wrong!=original, 'Missing-image mutation did not change the page'
    assert html.fromstring(wrong).xpath(image_xpath)==[missing]
    try:
        p.write_bytes(wrong)
        try:check()
        except AssertionError as error:assert str(error)==missing_path, f'Unexpected image rejection: {error}'
        else:raise AssertionError('Broken mirrored image accepted')
    finally:p.write_bytes(original)
    p=DOCS/'en/index.html';original=p.read_text()
    video_id=channel_config()["videos"][0]["id"]
    assert f'data-video-id="{video_id}"' in original, "Channel fixture must exist"
    for wrong in [original.replace('data-tv-group="sayd-channel"','data-tv-group="wrong"',1),original.replace(f'data-video-id="{video_id}"','data-video-id="missing"',1)]:
        try:
            p.write_text(wrong)
            try:check()
            except AssertionError:pass
            else:raise AssertionError('Invalid channel structure accepted')
        finally:p.write_text(original)
    # Keep the real publication selection and stale-list gate under coverage.
    from homepage_hunting_rotation import expected
    c=config();current=expected(c)
    # An outdated fixed list must fail the publication gate, not silently persist.
    config_path=DOCS.parent/'content/homepage.json';original=config_path.read_text()
    try:
        bad=deepcopy(c)
        next(d for d in bad['ia_door_sections'] if d['door']=='hunting')['slugs']=list(reversed(current))
        import json
        config_path.write_text(json.dumps(bad,ensure_ascii=False))
        try:check()
        except AssertionError as error:assert 'did not rotate' in str(error)
        else:raise AssertionError('Stale hunting card list accepted')
    finally:config_path.write_text(original)
    print('PASS: stable renderer, displaced-story rotation, duplicate exclusion and stale-card gate')
if __name__=='__main__':test_homepages()
