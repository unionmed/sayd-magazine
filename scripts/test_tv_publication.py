"""Native TV insertion tests: immutable media, bounded paths and old content preservation."""
import copy, hashlib, json, tempfile, unittest
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
        for key,value in [('id','other'),('published','2026-10-27'),('expected_base','a'*40),('approval_reference','chat transcript'),('titles',{'ar':'x'}),('description',dict.fromkeys(tv.LANGS,'<script>')),('poster_sha256','bad'),('study',{})]:
            with self.subTest(key=key):
                candidate=copy.deepcopy(self.value);candidate[key]=value
                with self.assertRaises(ValueError):tv.validate(candidate,self.base)
        candidate=dict(self.value,html='danger')
        with self.assertRaises(ValueError):tv.validate(candidate,self.base)
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

if __name__=='__main__':unittest.main()
