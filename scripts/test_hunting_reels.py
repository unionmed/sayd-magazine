"""Exact regression coverage for the four approved 2026 autumn reels."""
import json,re
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
REGIONS=['saudi','gulf','maghreb','mashreq-egypt']
OLD_VISIBLE=['IJ73ib8gULw','MmOLLjHzakw','fuv6vglsx2k']
def check_reels():
    meta=json.loads((ROOT/'content/features/hunting-reels-autumn-2026.json').read_text())
    assert [r['id'] for r in meta['regions']]==REGIONS
    ids=[r['youtube_id'] for r in meta['regions']]
    assert len(set(ids))==4 and all(re.fullmatch(r'[A-Za-z0-9_-]{11}',x) for x in ids)
    channel=json.loads((ROOT/'content/tv-channel.json').read_text())
    assert channel['home_limit']==7
    assert [r['id'] for r in channel['videos'][:7]]==ids+OLD_VISIBLE
    for prefix in ('','en','fr'):
        home=html.parse(str(ROOT/'docs'/prefix/'index.html'))
        assert home.xpath('//*[@data-tv-group="sayd-channel"]//article/@data-video-id')==ids+OLD_VISIBLE
        for door in ('استديو-صيد',):
            page=html.parse(str(ROOT/'docs'/prefix/'category'/door/'index.html'))
            entries=page.xpath('//*[@data-hunting-reel]')
            assert [r.get('data-hunting-reel') for r in entries]==REGIONS
            assert [r.xpath('.//iframe/@src')[0] for r in entries]==['https://www.youtube-nocookie.com/embed/'+x for x in ids]
        laws=html.parse(str(ROOT/'docs'/prefix/'category/قوانين/index.html'))
        assert not laws.xpath('//*[@data-hunting-reel]'), 'Seasonal reels must stay outside Laws'
    assert meta['placements']=={'sayd_tv':True,'homepage_tv':True,'laws_category':False}
    print('PASS: exact four regional players and seven channel cards in all three languages')
if __name__=='__main__':check_reels()
