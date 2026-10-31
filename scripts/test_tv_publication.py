"""Native TV insertion tests: immutable media, bounded paths and old content preservation."""
import copy, hashlib, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import tv_publication as tv
import publication_compiler as c
import publication_finalize as f
from lxml import html

ROOT=Path(__file__).resolve().parents[1]

class TVTests(unittest.TestCase):
    def setUp(self):
        self.base='b5e60fe8130c275b9aa3c058c4b8d2dbfa60b340'
        self.poster=b'\xff\xd8\xffposter'
        self.value={'schema':'sayd-tv-publication-v1','id':tv.ID,'expected_base':self.base,'approval_reference':'private:owner-20261026','published':'2026-10-26','titles':dict.fromkeys(tv.LANGS,'Mushroom'),'description':dict.fromkeys(tv.LANGS,'Description'),'disclosure':dict.fromkeys(tv.LANGS,'AI illustration'),'credit':dict.fromkeys(tv.LANGS,'Science Every Day'),'study':{'authors':'Domnauer & Dentinger','journal':'Mycologia','date':'2026-06-05','doi':'https://doi.org/10.1080/00275514.2026.2670968'},'poster_sha256':c.sha256(self.poster),'expected_channel_sha256':c.sha256((ROOT/tv.CHANNEL).read_bytes()),'rights':{'status':'owner-authorized-reuse','evidence_reference':'private:owner-mushroom-video-20261026','statement':'Independent magazine copy authorized by the owner; source video unchanged. AI imagery disclosure retained.'}}
    def test_schema_rejects_unauthorized_fields_and_markup(self):
        for key,value in [('id','other'),('published','2099-10-27'),('expected_base','a'*40),('approval_reference','chat transcript'),('titles',{'ar':'x'}),('description',dict.fromkeys(tv.LANGS,'<script>')),('poster_sha256','bad'),('study',{})]:
            with self.subTest(key=key):
                candidate=copy.deepcopy(self.value);candidate[key]=value
                with self.assertRaises(ValueError):tv.validate(candidate,self.base)
        candidate=dict(self.value,html='danger')
        with self.assertRaises(ValueError):tv.validate(candidate,self.base)
    def test_actual_release_date_without_backdating_or_future_dates(self):
        from datetime import date
        class ReleaseDay(date):
            @classmethod
            def today(cls):return cls(2026,10,27)
        with patch.object(tv,'date',ReleaseDay):
            for day in ('2026-10-26','2026-10-27'):
                value=dict(self.value,published=day)
                self.assertEqual(tv.validate(value,self.base)['published'],day)
            for day in ('2026-10-25','2026-10-28','2026-02-30','27/10/2026'):
                with self.subTest(day=day):
                    with self.assertRaises(ValueError):tv.validate(dict(self.value,published=day),self.base)

    def test_reuses_player_without_external_embed(self):
        for lang in tv.LANGS:
            player=html.fromstring(tv.player(self.value,lang))
            self.assertEqual(len(player.xpath('.//video[@controls and @playsinline and @preload="metadata"]')),1)
            self.assertFalse(player.xpath('.//iframe|.//script'))
            self.assertTrue(player.xpath('.//source/@src')[0].endswith('mushroom.mp4'))
    def test_preserves_every_old_card_and_player(self):
        changes=tv.expected_changes(ROOT,self.base,self.value,self.poster)
        self.assertEqual(set(changes),{*('docs/'+p+'index.html' for p in ('','en/','fr/')),*('docs/'+p+tv.TV_PATH for p in ('','en/','fr/'))})
        for lang in tv.LANGS:
            prefix='' if lang=='ar' else lang+'/'
            path='docs/'+prefix+tv.TV_PATH;old=c.git(ROOT,'show',self.base+':'+path).decode();new=changes[path].decode()
            self.assertEqual(new.replace(tv.player(self.value,lang),'',1),old)
            path='docs/'+prefix+'index.html';old=html.fromstring(c.git(ROOT,'show',self.base+':'+path));new=html.fromstring(changes[path])
            select='//*[@data-tv-group="sayd-channel"]'
            self.assertEqual(html.tostring(old.xpath(select)[0]),html.tostring(new.xpath(select)[0]))
            a=old.xpath('//*[@data-tv-group="sayd-selections"]//article');b=new.xpath('//*[@data-tv-group="sayd-selections"]//article')
            self.assertEqual([html.tostring(x,with_tail=False) for x in a],[html.tostring(x,with_tail=False) for x in b[1:]])
            self.assertEqual(b[0].get('data-native-video'),tv.ID)
    def test_stale_channel_digest_and_duplicate_rejected(self):
        bad=dict(self.value,expected_channel_sha256='a'*64)
        with self.assertRaises(ValueError):tv.expected_changes(ROOT,self.base,bad,self.poster)
    def test_finalizer_and_compiler_allow_only_narrow_new_paths(self):
        for p in (tv.SOURCE,tv.VIDEO,tv.POSTER,tv.SHARD):
            self.assertTrue(c.allowed_output_path(p));f.safe_output_path(p)
        for p in ('content/tv-publications/other.json',tv.MEDIA+'other.mp4',tv.VIDEO+'/x','docs/media/video/evil.mp4','scripts/evil.py','../'+tv.VIDEO):
            self.assertFalse(c.allowed_output_path(p))
            with self.assertRaises(f.Blocked):f.safe_output_path(p)
    def test_source_only_rejection(self):
        # Wrong/extra source input is rejected before any source bytes execute.
        before={};after={tv.SOURCE:('100644','blob','1'*40),'scripts/evil.py':('100644','blob','2'*40)}
        with patch.object(c,'tree',side_effect=[before,after]):
            with self.assertRaises(ValueError):tv.source_input(ROOT,self.base,'b'*40)

    def test_historical_snapshot_requires_unchanged_payload_or_exact_tv_replay(self):
        import publication_guard as guard
        with patch.object(guard,'unchanged_current_payload',return_value=True), patch.object(guard,'verified_publication') as replay:
            self.assertTrue(tv.historical_placement_snapshot(ROOT,self.base));replay.assert_not_called()
        with patch.object(guard,'unchanged_current_payload',return_value=False), patch.object(guard,'git',return_value=b'docs/index.html\n'), patch.object(guard,'verified_publication') as replay:
            self.assertFalse(tv.historical_placement_snapshot(ROOT,self.base));replay.assert_not_called()
        with patch.object(guard,'unchanged_current_payload',return_value=False), patch.object(guard,'git',return_value=(tv.SOURCE+'\n').encode()), patch.object(guard,'verified_publication',return_value=None):
            self.assertFalse(tv.historical_placement_snapshot(ROOT,self.base))
        with patch.object(guard,'unchanged_current_payload',return_value=False), patch.object(guard,'git',return_value=(tv.SOURCE+'\n').encode()), patch.object(guard,'verified_publication',side_effect=AssertionError('tampered tree')):
            with self.assertRaises(AssertionError):tv.historical_placement_snapshot(ROOT,self.base)

    def test_real_payload_mutation_cannot_claim_historical_snapshot(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix='native-tv-negative-') as temp:
            root=Path(temp);(root/'docs').mkdir();(root/'docs/index.html').write_text('original')
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE)
            git('init','-q');git('config','user.name','Isolated test');git('config','user.email','test@example.invalid')
            git('add','.');git('commit','-qm','base');base=git('rev-parse','HEAD').decode().strip()
            (root/'scripts').mkdir();(root/'scripts/fixture.py').write_text('# code-only change')
            git('add','.');git('commit','-qm','infrastructure')
            with patch.dict(os.environ,{'GITHUB_ACTIONS':'false','SAYD_PUBLICATION_HEAD':''}):
                self.assertTrue(tv.historical_placement_snapshot(root,base))
                (root/'docs/index.html').write_text('unauthorized ticker change');git('add','.');git('commit','-qm','tamper')
                self.assertFalse(tv.historical_placement_snapshot(root,base))

from test_adonis_tv_publication import AdonisTVTests

if __name__=='__main__':unittest.main()
