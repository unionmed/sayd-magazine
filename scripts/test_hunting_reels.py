"""Exact autumn-reel preservation plus the approved 24 October internal TV card."""
import json,re
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
REGIONS=['saudi','gulf','maghreb','mashreq-egypt']
OLD_VISIBLE=['IJ73ib8gULw','MmOLLjHzakw','fuv6vglsx2k']
ISF_VIDEO='P2nk8V1Muls'
def check_reels():
    meta=json.loads((ROOT/'content/features/hunting-reels-autumn-2026.json').read_text())
    assert [r['id'] for r in meta['regions']]==REGIONS
    ids=[r['youtube_id'] for r in meta['regions']]
    assert len(set(ids))==4 and all(re.fullmatch(r'[A-Za-z0-9_-]{11}',x) for x in ids)
    channel=json.loads((ROOT/'content/tv-channel.json').read_text())
    assert channel['home_limit']==7
    assert [r['id'] for r in channel['videos'][:8]]==[ISF_VIDEO]+ids+OLD_VISIBLE
    first=channel['videos'][0]
    assert first['published_at']=='2026-10-24' and first['source_published_at']=='2026-10-20'
    assert first['internal_href']=='category/استديو-صيد/index.html#isf-video-heading'
    expected=[ISF_VIDEO]+ids+OLD_VISIBLE[:2]
    for prefix in ('','en','fr'):
        home=html.parse(str(ROOT/'docs'/prefix/'index.html'))
        assert home.xpath('//*[@data-tv-group="sayd-channel"]//article/@data-video-id')==expected
        card=home.xpath('//*[@data-video-id=$video]',video=ISF_VIDEO)[0]
        assert card.xpath('.//a/@href')==[first['internal_href']]*2
        for door in ('استديو-صيد',):
            page=html.parse(str(ROOT/'docs'/prefix/'category'/door/'index.html'))
            entries=page.xpath('//*[@data-hunting-reel]')
            assert [r.get('data-hunting-reel') for r in entries]==REGIONS
            assert [r.xpath('.//iframe/@src')[0] for r in entries]==['https://www.youtube-nocookie.com/embed/'+x for x in ids]
            isf=page.xpath('//*[@data-isf-video="1930823281230246"]')[0]
            assert len(isf.xpath('.//a'))==2 and all(h.startswith('../../posts/') for h in isf.xpath('.//a/@href'))
            assert '1930823281230246' in isf.xpath('.//iframe/@src')[0]
        laws=html.parse(str(ROOT/'docs'/prefix/'category/قوانين/index.html'))
        assert not laws.xpath('//*[@data-hunting-reel]'), 'Seasonal reels must stay outside Laws'
    assert meta['placements']=={'sayd_tv':True,'homepage_tv':True,'laws_category':False}
    print('PASS: internal ISF card first, seven channel cards, four regional players preserved in all languages')
if __name__=='__main__':check_reels()
