"""Bounded external TV: four cards, exact provenance, no old content loss."""
import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from lxml import html
import adonis_tv_publication as tv
import publication_compiler as c
import publication_finalize as f
ROOT=Path(__file__).resolve().parents[1]
BASE='55cff6194bbcd9a62461c83f483cd74783c36559'

class AdonisTVTests(unittest.TestCase):
    def setUp(self):
        self.poster=b'\xff\xd8\xffposter'
        self.value={'schema':'sayd-external-tv-publication-v1','id':tv.ID,'expected_base':BASE,
                    'approval_reference':'private:owner-adonis-four-20261031','published':'2026-10-31',
                    'video_id':tv.VIDEO_ID,'source_url':tv.URL,'channel':'AL Jadeed',
                    'titles':dict.fromkeys(tv.LANGS,'Interview with Editor-in-Chief Adonis'),
                    'credit':dict.fromkeys(tv.LANGS,'AL Jadeed — archive portrait'),'alt':dict.fromkeys(tv.LANGS,'Archive portrait of Editor-in-Chief Adonis'),
                    'poster_sha256':c.sha256(self.poster),'expected_channel_sha256':c.sha256((ROOT/tv.CHANNEL).read_bytes()),
                    'rights':{'status':'existing-site-archive','statement':'Original source thumbnail with a link to the original video; video is not copied.','evidence_reference':'private:youtube-source-20261031'}}
    def test_identity_date_schema_fail_closed(self):
        for key,value in [('id','other'),('video_id','other'),('source_url','https://evil.example/'),('published','2026-10-30'),('expected_base','a'*40),('channel','other'),('titles',{'ar':'x'}),('credit',dict.fromkeys(tv.LANGS,'<script>')),('rights',{}),('approval_reference','full private conversation')]:
            with self.subTest(key=key),self.assertRaises(ValueError):tv.validate(dict(self.value,**{key:value}),BASE)
        with self.assertRaises(ValueError):tv.validate(dict(self.value,html='raw'),BASE)
    def test_home_and_archive_link_no_video_copy_or_script(self):
        for lang in tv.LANGS:
            for renderer in (tv.card,tv.archive_card):
                node=html.fromstring(renderer(self.value,lang,self.poster))
                self.assertEqual(node.xpath('.//a/@href'),[tv.URL,tv.URL])
                self.assertFalse(node.xpath('.//video|.//iframe|.//script'))
                self.assertEqual(node.get('data-external-selection'),tv.ID)
    def test_exact_four_home_cards_and_preserved_archive(self):
        changes=tv.expected_changes(ROOT,BASE,self.value,self.poster)
        self.assertEqual(set(changes),{'docs/'+p+x for p in ('','en/','fr/') for x in ('index.html',tv.TV_PATH)})
        for lang in tv.LANGS:
            prefix='' if lang=='ar' else lang+'/'
            home='docs/'+prefix+'index.html';old=c.git(ROOT,'show',BASE+':'+home).decode();new=changes[home].decode()
            a=html.fromstring(old);b=html.fromstring(new)
            select='//*[@data-tv-group="sayd-selections"]//article'
            outgoing=tv.OUTGOING if lang=='ar' else tv.OUTGOING_LATIN
            old_cards=[n for n in a.xpath(select) if not any('/'+outgoing+'/' in h for h in n.xpath('.//a/@href'))]
            self.assertEqual(len(b.xpath(select)),4)
            self.assertEqual([html.tostring(x,with_tail=False) for x in old_cards],[html.tostring(x,with_tail=False) for x in b.xpath(select)[1:]])
            # Every byte outside the selections group stays unchanged.
            import re
            pattern=r'(<div class="sayd-tv-group" data-tv-group="sayd-selections">.*?<div class="home-door-grid">)(?:\s*<article\b.*?</article>){4}\s*(</div></div>)'
            outside=lambda s:re.sub(pattern,lambda m:m[1]+m[2],s,flags=re.S)
            self.assertEqual(outside(old),outside(new))
            category='docs/'+prefix+tv.TV_PATH;old=c.git(ROOT,'show',BASE+':'+category).decode();new=changes[category].decode()
            self.assertEqual(new.replace('\n'+tv.archive_card(self.value,lang,self.poster),'',1),old)
            self.assertIn(outgoing,new)
    def test_published_mirrors_and_tamper_rejection(self):
        changes=tv.expected_changes(ROOT,BASE,self.value,self.poster)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for p,data in dict(changes,**{tv.SOURCE:json.dumps(self.value).encode(),tv.POSTER:self.poster}).items():
                (root/p).parent.mkdir(parents=True,exist_ok=True);(root/p).write_bytes(data)
            tv.check_published(root)
            target=root/'docs/en/index.html';target.write_text(target.read_text().replace(tv.URL,'https://evil.example/'))
            with self.assertRaises(ValueError):tv.check_published(root)
    def test_stale_channel_and_missing_archive_rejected(self):
        with self.assertRaises(ValueError):tv.expected_changes(ROOT,BASE,dict(self.value,expected_channel_sha256='a'*64),self.poster)
    def test_only_exact_output_source_allowed(self):
        for p in (tv.SOURCE,):
            self.assertTrue(c.allowed_output_path(p));f.safe_output_path(p)
        for p in ('content/tv-publications/other.json','docs/media/publications/'+tv.ID+'/video.mp4','scripts/injected.py'):
            self.assertFalse(c.allowed_output_path(p))
            with self.assertRaises(f.Blocked):f.safe_output_path(p)
    def test_source_only_unrelated_inputs_rejected(self):
        after={tv.SOURCE:('100644','blob','1'*40),'scripts/injected.py':('100644','blob','2'*40)}
        with patch.object(c,'tree',side_effect=[{},after]):
            with self.assertRaises(ValueError):tv.source_input(ROOT,BASE,'b'*40)
    def test_missing_source_does_not_change_legacy_selection(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(tv.homepage_card(d,'ar'))
            self.assertEqual(tv.selected_slugs(d,['apu',tv.OUTGOING,'leopard']),['apu',tv.OUTGOING,'leopard'])
    def test_source_requires_exact_new_inputs_and_digest(self):
        before={};after={p:('100644','blob','1'*40) for p in (tv.SOURCE,)}
        with patch.object(c,'tree',side_effect=[before,after]),patch.object(c,'git',return_value=b'wrong-parent'):
            with self.assertRaises(ValueError):tv.source_input(ROOT,BASE,'b'*40)

if __name__=='__main__':unittest.main()
