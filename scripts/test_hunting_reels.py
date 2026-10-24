"""Exact autumn-reel preservation plus the approved 24 October internal TV card."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
REGIONS=['saudi','gulf','maghreb','mashreq-egypt']
OLD_VISIBLE=['IJ73ib8gULw','MmOLLjHzakw','fuv6vglsx2k']
ISF_VIDEO='P2nk8V1Muls'

def historical_reel_fixture(base, root=ROOT):
    """Recognize only the compiler's immutable pre-ISF, script-overlay fixture.

    Missing ISF content on the current publication base is never an exception.
    The two chronological-lead integration tests intentionally use this older
    payload with current scripts; preserve their original exact TV assertions.
    """
    pinned='493719a53adb3faf8412e281ceed3e81534dd526'
    if not re.fullmatch(r'[0-9a-f]{40}',base or ''):
        return False
    source=(root/'content/tv-channel.json').read_bytes()
    if hashlib.sha256(source).hexdigest()!='30ee9d8df9b800cb3f70bb91f1e97e1cff54deee481ce864b49355a8826a3465':
        return False
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE)
    try:
        if git('rev-list','--parents','-n','1',base).decode().split()!=[base,pinned]:
            return False
        changed=git('diff','--name-only','-z',pinned,base).decode().strip('\0').split('\0')
        if not changed or not all(path.startswith('scripts/') for path in changed):
            return False
        return source==git('show',pinned+':content/tv-channel.json')==git('show',base+':content/tv-channel.json')
    except subprocess.CalledProcessError:
        return False

def check_reels():
    meta=json.loads((ROOT/'content/features/hunting-reels-autumn-2026.json').read_text())
    assert [r['id'] for r in meta['regions']]==REGIONS
    ids=[r['youtube_id'] for r in meta['regions']]
    assert len(set(ids))==4 and all(re.fullmatch(r'[A-Za-z0-9_-]{11}',x) for x in ids)
    channel=json.loads((ROOT/'content/tv-channel.json').read_text())
    assert channel['home_limit']==7
    historical=historical_reel_fixture(os.environ.get('SAYD_BASE_COMMIT'))
    if historical:
        assert [r['id'] for r in channel['videos'][:7]]==ids+OLD_VISIBLE
        assert not any(r['id']==ISF_VIDEO for r in channel['videos'])
        expected=ids+OLD_VISIBLE
    else:
        assert [r['id'] for r in channel['videos'][:8]]==[ISF_VIDEO]+ids+OLD_VISIBLE
        first=channel['videos'][0]
        assert first['published_at']=='2026-10-24' and first['source_published_at']=='2026-10-20'
        assert first['internal_href']=='category/استديو-صيد/index.html#isf-video-heading'
        expected=[ISF_VIDEO]+ids+OLD_VISIBLE[:2]
    for prefix in ('','en','fr'):
        home=html.parse(str(ROOT/'docs'/prefix/'index.html'))
        assert home.xpath('//*[@data-tv-group="sayd-channel"]//article/@data-video-id')==expected
        if historical:
            assert not home.xpath('//*[@data-video-id=$video]',video=ISF_VIDEO)
        else:
            card=home.xpath('//*[@data-video-id=$video]',video=ISF_VIDEO)[0]
            assert card.xpath('.//a/@href')==[first['internal_href']]*2
        for door in ('استديو-صيد',):
            page=html.parse(str(ROOT/'docs'/prefix/'category'/door/'index.html'))
            entries=page.xpath('//*[@data-hunting-reel]')
            assert [r.get('data-hunting-reel') for r in entries]==REGIONS
            assert [r.xpath('.//iframe/@src')[0] for r in entries]==['https://www.youtube-nocookie.com/embed/'+x for x in ids]
            isf=page.xpath('//*[@data-isf-video="1930823281230246"]')
            if historical:
                assert not isf
            else:
                assert len(isf)==1
                assert len(isf[0].xpath('.//a'))==2 and all(h.startswith('../../posts/') for h in isf[0].xpath('.//a/@href'))
                assert '1930823281230246' in isf[0].xpath('.//iframe/@src')[0]
        laws=html.parse(str(ROOT/'docs'/prefix/'category/قوانين/index.html'))
        assert not laws.xpath('//*[@data-hunting-reel]'), 'Seasonal reels must stay outside Laws'
    assert meta['placements']=={'sayd_tv':True,'homepage_tv':True,'laws_category':False}
    print('PASS: exact pinned historical TV fixture' if historical else 'PASS: internal ISF card first, seven channel cards, four regional players preserved in all languages')
if __name__=='__main__':check_reels()
