"""Regression checks for the three mirrored homepages and fail-closed rules."""
from copy import deepcopy
from check_publication_contract import check
from refresh_homepage_doors import refresh, DOCS, config, validate_config, channel_config

def test_homepages():
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
    c=config();current=expected(c);recent='سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف'
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
