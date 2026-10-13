"""Regression checks for the three mirrored homepages and fail-closed rules."""
from copy import deepcopy
from check_publication_contract import check
from refresh_homepage_doors import refresh, DOCS, DOORS, config, validate_config, channel_config, place_memory

def test_memory_placement():
    """Relocation must preserve every byte outside its position, in all mirrors."""
    import re
    from html import escape
    from lxml import html
    pattern = r'^[ \t]*<section class="memory-strip".*?</section>\n?'
    for lang, prefix in [('ar', ''), ('en', 'en'), ('fr', 'fr')]:
        page = (DOCS / prefix / 'index.html').read_text()
        tree = html.fromstring(page)
        memory = tree.xpath('//section[@class="memory-strip"]')
        assert len(memory) == 1
        assert memory[0].getparent().get('class') == 'home-main'
        heading = DOORS[3][{'ar': 1, 'en': 2, 'fr': 3}[lang]]
        assert memory[0].getprevious().xpath('./div/h2/text()') == [heading], f'{lang}: memory must immediately follow Wildlife'
        block = re.search(pattern, page, re.S | re.M)[0]
        remainder = re.sub(pattern, '', page, flags=re.S | re.M)
        # Simulate the old generator position above the lower doors.
        legacy = remainder.replace('    <div class="home-layout">', block + '    <div class="home-layout">', 1)
        moved = place_memory(legacy, lang, config()['memory_after_door'])
        assert moved == page, f'{lang}: relocation changed section/card content or unrelated markup'
        assert re.search(pattern, moved, re.S | re.M)[0] == block
        assert re.sub(pattern, '', moved, flags=re.S | re.M) == remainder
        assert place_memory(moved, lang, 'wildlife') == moved
        for broken in (remainder, legacy + block, legacy.replace('<h2>' + escape(heading) + '</h2>', '<h2>missing</h2>')):
            try: place_memory(broken, lang, 'wildlife')
            except ValueError: pass
            else: raise AssertionError(f'{lang}: invalid relocation fixture accepted')

def test_homepages():
    test_memory_placement()
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
    assert after[0]==recent and len(after)==4 and current[-1] not in after
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
