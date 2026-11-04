"""October Radar: bounded native media, seven cards, preserved site and old archive."""
import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from lxml import html
import radar_tv_publication as tv
import publication_compiler as c
import publication_finalize as f
ROOT=Path(__file__).resolve().parents[1]
BASE='aee9517722445d05fb32138a390a6a5f4ba315f4'
class RadarTVTests(unittest.TestCase):
    def setUp(self):
        self.poster=b'\xff\xd8\xffposter'
        self.value={'schema':'sayd-radar-tv-publication-v1','id':tv.ID,'expected_base':BASE,'approval_reference':'private:Sentinel_39afad049484819185dbdaf6c58235cf','published':'2026-11-04','titles':tv.TITLES,'description':tv.DESCRIPTIONS,'poster_sha256':tv.POSTER_HASH,'expected_channel_sha256':c.sha256(c.git(ROOT,'show',BASE+':'+tv.CHANNEL))}
    def test_identity_exact_text_date_and_keys(self):
        tv.validate(self.value,BASE)
        for field,value in [('id','other'),('titles',dict.fromkeys(tv.LANGS,'other')),('description',dict.fromkeys(tv.LANGS,'<script>')),('poster_sha256','a'*64),('published','2026-11-03'),('expected_base','a'*40),('approval_reference','other')]:
            with self.subTest(field=field),self.assertRaises(ValueError):tv.validate(dict(self.value,**{field:value}),BASE)
        with self.assertRaises(ValueError):tv.validate(dict(self.value,extra=True),BASE)
    def test_bound_paths(self):
        for p in (tv.SOURCE,tv.VIDEO,tv.POSTER,tv.SHARD,tv.CHANNEL):
            self.assertTrue(c.allowed_output_path(p));f.safe_output_path(p)
        for p in (tv.MEDIA+'other.mp4','content/tv-publications/other.json','scripts/injected.py'):
            self.assertFalse(c.allowed_output_path(p))
            with self.assertRaises(f.Blocked):f.safe_output_path(p)
    def test_source_requires_exact_inputs_parent_and_media(self):
        after={tv.SOURCE:('100644','blob','1'*40),'scripts/evil.py':('100644','blob','2'*40)}
        with patch.object(c,'tree',side_effect=[{},after]):
            with self.assertRaises(ValueError):tv.source_input(ROOT,BASE,'b'*40)
    def test_player_internal_only(self):
        for lang in tv.LANGS:
            node=html.fromstring(tv.player(self.value,lang))
            self.assertEqual(len(node.xpath('.//video[@controls and @playsinline and @preload="metadata"]')),1)
            self.assertFalse(node.xpath('.//script|.//iframe'))
            self.assertTrue(node.xpath('.//source/@src')[0].endswith('/radar.mp4'))
            self.assertIn(tv.ARTICLE[lang],node.xpath('.//a/@href')[-1])
    def test_exact_seven_home_cards_and_unchanged_archive(self):
        changes=tv.expected_changes(ROOT,BASE,self.value,self.poster)
        self.assertEqual(set(changes),{tv.CHANNEL,*('docs/'+p+x for p in ('','en/','fr/') for x in ('index.html',tv.TV_PATH))})
        old=json.loads(c.git(ROOT,'show',BASE+':'+tv.CHANNEL));new=json.loads(changes[tv.CHANNEL])
        self.assertEqual(new['videos'][1:],old['videos']);self.assertEqual(new['approved_order'][1:],old['approved_order'])
        self.assertEqual(new['home_limit'],7)
        import re
        pattern=r'(<div class="sayd-tv-group" data-tv-group="sayd-channel">.*?<div class="home-door-grid">)((?:\s*<article\b.*?</article>){7}\s*)(</div></div>)'
        for lang in tv.LANGS:
            prefix='' if lang=='ar' else lang+'/'
            path='docs/'+prefix+'index.html';a=c.git(ROOT,'show',BASE+':'+path).decode();b=changes[path].decode()
            outside=lambda s:re.sub(pattern,lambda m:m[1]+m[3],s,flags=re.S)
            self.assertEqual(outside(a),outside(b))
            a=html.fromstring(a);b=html.fromstring(b);q='//*[@data-tv-group="sayd-channel"]//article'
            oldcards=a.xpath(q);newcards=b.xpath(q)
            self.assertEqual(len(newcards),7);self.assertEqual(newcards[0].get('data-video-id'),tv.ID)
            self.assertEqual([html.tostring(n,with_tail=False) for n in oldcards[:6]],[html.tostring(n,with_tail=False) for n in newcards[1:]])
            path='docs/'+prefix+tv.TV_PATH;old=c.git(ROOT,'show',BASE+':'+path).decode()
            self.assertEqual(changes[path].decode().replace(tv.player(self.value,lang),'',1),old)
    def test_stale_channel_rejected(self):
        with self.assertRaises(ValueError):tv.expected_changes(ROOT,BASE,dict(self.value,expected_channel_sha256='a'*64),self.poster)
    def test_future_approved_rotation_not_permanently_pinned(self):
        value=dict(self.value,poster_sha256=c.sha256(self.poster))
        with patch.object(tv,'POSTER_HASH',c.sha256(self.poster)),patch.object(tv,'VIDEO_HASH',c.sha256(b'video')),patch.object(tv,'VIDEO_BYTES',5):
            changes=tv.expected_changes(ROOT,BASE,value,self.poster)
            with tempfile.TemporaryDirectory() as d:
                root=Path(d)
                for p,data in dict(changes,**{tv.SOURCE:json.dumps(value).encode(),tv.POSTER:self.poster,tv.VIDEO:b'video'}).items():
                    q=root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
                tv.check_published(root)
                channel=json.loads((root/tv.CHANNEL).read_text());radar=channel['videos'].pop(0);channel['videos'].append(radar)
                channel['approved_order']=[v['id'] for v in channel['videos']]
                (root/tv.CHANNEL).write_text(json.dumps(channel))
                # Restore the previous approved seven homepage cards; archive player remains.
                for prefix in ('','en/','fr/'):
                    path='docs/'+prefix+'index.html'
                    (root/path).write_bytes(c.git(ROOT,'show',BASE+':'+path))
                tv.check_published(root)

    def test_request_routes_radar_before_legacy_native(self):
        import publication_request as r
        with patch.object(r,'git',return_value=b'ignored'),patch.object(r,'request_scope',return_value=True),patch.object(c,'tree',return_value={}),patch.object(tv,'revision_paths',return_value=[tv.SOURCE]),patch.object(tv,'source_input',return_value=(self.value,{})) as load:
            self.assertTrue(r.validate_source(ROOT,BASE,'b'*40));load.assert_called_once()

    def test_report_cannot_expand_channel_scope(self):
        # A channel change must be reconstructed by the exact source-only module.
        report={'schema':c.SCHEMA,'base_commit':BASE,'source_commit':'b'*40,'compiler_commit':BASE,'policy':{'allow_distribution':True},'changes':[{'path':tv.CHANNEL}]}
        report['plan_sha256']=c.sha256(c.canonical(report))
        with patch.object(tv,'source_input',side_effect=ValueError('not exact source')):
            with self.assertRaises(ValueError):c.validate_report(ROOT,report,BASE,'b'*40,BASE,True)
if __name__=='__main__':unittest.main()
