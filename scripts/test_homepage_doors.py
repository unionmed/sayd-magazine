"""Regression checks for the three mirrored homepages and fail-closed rules."""
from copy import deepcopy
from check_publication_contract import check
from refresh_homepage_doors import refresh, DOCS, DOORS, config, validate_config, channel_config

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
    # A French-only missing image must fail; restore the fixture even on failure.
    p=DOCS/'fr/index.html';original=p.read_text()
    try:
        p.write_text(original.replace('EQ-N02-interior-3x2.jpg','missing-test-image.jpg',1))
        try:check()
        except AssertionError:pass
        else:raise AssertionError('Broken mirrored image accepted')
    finally:p.write_text(original)
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
    # A displaced recent hunting story enters its door, replacing the oldest card.
    from homepage_hunting_rotation import select, candidates, expected
    c=config();current=expected(c)
    # Pick a published hunting story currently in Updates. A hard-coded 2026
    # fixture falls out of the rolling eight slots after legitimate publication.
    eligible={slug for slug,_ in candidates()}
    recent=next((slug for slug in c['latest'] if slug in eligible and c['primary_door'].get(slug)=='hunting'),None)
    assert recent is not None,'No hunting story in Updates for demotion regression'
    moved=deepcopy(c);moved['latest'].remove(recent)
    # The displaced story must be the newest in this fixture. New publications
    # can legitimately be newer than the historical BirdLife article.
    from datetime import timedelta
    pool=candidates();newest=max(day for _,day in pool)+timedelta(days=1)
    pool=[(slug,newest if slug==recent else day) for slug,day in pool]
    after=select(moved,pool)
    assert after[0]==recent and len(after)==8 and current[-1] not in after
    assert not set(after).intersection(moved['featured']+moved['latest'])
    # A story promoted out of the lower door cannot remain there as a duplicate.
    promoted=deepcopy(c);promoted['latest'].append(current[0])
    assert current[0] not in select(promoted,candidates())
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
