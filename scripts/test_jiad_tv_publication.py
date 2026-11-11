"""Jiad: bounded native media, seven cards, preserved site and old archive."""
import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from lxml import html
import jiad_tv_publication as tv
import publication_compiler as c
import publication_finalize as f
ROOT=Path(__file__).resolve().parents[1]
BASE='fd5ed9bfebe015beb8b0bc10120629515e3760fb'
class JiadTVTests(unittest.TestCase):
    def setUp(self):
        self.poster=b'\xff\xd8\xffposter'
        self.value={'schema':'sayd-jiad-tv-publication-v1','id':tv.ID,'expected_base':BASE,'approval_reference':tv.APPROVAL_REFERENCE,'published':'2026-11-09','titles':tv.TITLES,'description':tv.DESCRIPTIONS,'poster_sha256':tv.POSTER_HASH,'expected_channel_sha256':c.sha256(c.git(ROOT,'show',BASE+':'+tv.CHANNEL))}
    def test_approved_web_derivative_and_original_poster_are_pinned(self):
        self.assertEqual(tv.VIDEO_HASH, '13d5b53a585571e4b94a6ce9278bfb455a2d46c95d095028697419dc78baafd4')
        self.assertEqual(tv.VIDEO_BYTES, 20487595)
        self.assertEqual(tv.POSTER_HASH, '02167fb7fddf770eac2ba66fe62851c5bb58b68155ae7b49bec7d8c6d74e6567')
    def test_identity_exact_text_date_and_keys(self):
        tv.validate(self.value,BASE)
        for field,value in [('id','other'),('titles',dict.fromkeys(tv.LANGS,'other')),('description',dict.fromkeys(tv.LANGS,'<script>')),('poster_sha256','a'*64),('published','2026-11-08'),('expected_base','a'*40),('approval_reference','other')]:
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
            self.assertIn('max-width:960px',node.xpath('.//video/@style')[0])
            self.assertEqual(node.xpath('./p/text()'),self.value['description'][lang].split('\n'))
            self.assertTrue(node.xpath('.//source/@src')[0].endswith('/jiad.mp4'))
            self.assertEqual(node.xpath('.//a/@href'),node.xpath('.//source/@src'))
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
            players=html.fromstring(changes[path]).xpath('//section[@data-jiad-video or @data-radar-video or @data-native-video]')
            self.assertEqual(players[0].get('data-jiad-video'),tv.ID)
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
                channel=json.loads((root/tv.CHANNEL).read_text());jiad=channel['videos'].pop(0);channel['videos'].append(jiad)
                channel['approved_order']=[v['id'] for v in channel['videos']]
                (root/tv.CHANNEL).write_text(json.dumps(channel))
                # Restore the previous approved seven homepage cards; archive player remains.
                for prefix in ('','en/','fr/'):
                    path='docs/'+prefix+'index.html'
                    (root/path).write_bytes(c.git(ROOT,'show',BASE+':'+path))
                tv.check_published(root)

    def test_historical_reel_guard_accepts_jiad_and_rejects_tampering(self):
        import test_hunting_reels as reels
        import radar_tv_publication as radar
        poster=self.poster;video=b'approved video'
        value=dict(self.value,poster_sha256=c.sha256(poster))
        with patch.multiple(tv,POSTER_HASH=c.sha256(poster),VIDEO_HASH=c.sha256(video),VIDEO_BYTES=len(video)):
            changes=tv.expected_changes(ROOT,BASE,value,poster)
            baseline_paths=[tv.CHANNEL,'content/features/hunting-reels-autumn-2026.json']
            for prefix in ('','en/','fr/'):
                baseline_paths += ['docs/'+prefix+'index.html','docs/'+prefix+tv.TV_PATH,'docs/'+prefix+'category/قوانين/index.html']
            baseline={p:c.git(ROOT,'show',BASE+':'+p) for p in baseline_paths}
            # Radar's independent media validator is covered by its own suite.
            # Here confirm the legacy guard still invokes it while testing Jiad
            # with its real validator and bounded fixture media.
            baseline[radar.SOURCE]=b'{}'
            payload=dict(baseline,**changes,**{tv.SOURCE:json.dumps(value).encode(),tv.POSTER:poster,tv.VIDEO:video})
            with tempfile.TemporaryDirectory() as d:
                root=Path(d)
                def write(files):
                    for path,data in files.items():
                        q=root/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
                with patch.object(reels,'ROOT',root),patch.object(radar,'check_published') as radar_check:
                    write(baseline);reels.check_reels();radar_check.assert_called_once_with(root)
                    radar_check.reset_mock();write(payload);reels.check_reels();radar_check.assert_called_once_with(root)
                    for mutation in ('unknown-record','reordered-history','eight-cards','video-bytes','missing-player'):
                        with self.subTest(mutation=mutation):
                            write(payload)
                            channel=json.loads(payload[tv.CHANNEL])
                            if mutation=='unknown-record':channel['videos'].insert(1,dict(channel['videos'][2],id='unapproved'))
                            elif mutation=='reordered-history':channel['videos'][2],channel['videos'][3]=channel['videos'][3],channel['videos'][2]
                            elif mutation=='eight-cards':channel['home_limit']=8
                            elif mutation=='video-bytes':(root/tv.VIDEO).write_bytes(video+b'!')
                            else:(root/'docs'/tv.TV_PATH).write_bytes(baseline['docs/'+tv.TV_PATH])
                            if mutation in ('unknown-record','reordered-history','eight-cards'):
                                (root/tv.CHANNEL).write_text(json.dumps(channel))
                            with self.assertRaises((ValueError,AssertionError)):reels.check_reels()

    def test_request_routes_jiad_before_legacy_native(self):
        import publication_request as r
        with patch.object(r,'git',return_value=b'ignored'),patch.object(r,'request_scope',return_value=True),patch.object(c,'tree',return_value={}),patch.object(tv,'revision_paths',return_value=[tv.SOURCE]),patch.object(tv,'source_input',return_value=(self.value,{})) as load:
            self.assertTrue(r.validate_source(ROOT,BASE,'b'*40));load.assert_called_once()

    def test_report_cannot_expand_channel_scope(self):
        # A channel change must be reconstructed by the exact source-only module.
        report={'schema':c.SCHEMA,'base_commit':BASE,'source_commit':'b'*40,'compiler_commit':BASE,'policy':{'allow_distribution':True},'changes':[{'path':tv.CHANNEL},{'path':tv.SOURCE}]}
        report['plan_sha256']=c.sha256(c.canonical(report))
        with patch.object(tv,'source_input',side_effect=ValueError('not exact source')):
            with self.assertRaises(ValueError):c.validate_report(ROOT,report,BASE,'b'*40,BASE,True)
    def test_source_exact_bytes_parent_modes_and_inventory(self):
        video=b'approved video';poster=self.poster
        value=dict(self.value,poster_sha256=c.sha256(poster))
        blobs={tv.SOURCE:json.dumps(value).encode(),tv.VIDEO:video,tv.POSTER:poster}
        blobs[tv.SHARD]=('path\tgit_blob_sha\tsize_bytes\n'+tv.POSTER+'\t'+c.blob_sha(poster)+'\t'+str(len(poster))+'\n').encode()
        def run(blobs, parent=BASE, mode='100644'):
            after={p:(mode,'blob',c.blob_sha(data)) for p,data in blobs.items()}
            by_sha={c.blob_sha(data):data for data in blobs.values()}
            with patch.object(c,'tree',side_effect=[{},after]),patch.object(c,'git',return_value=parent.encode()),patch.object(c,'read_blob',side_effect=lambda root,entry:by_sha[entry[2]]),patch.object(tv,'expected_changes',return_value={}):
                return tv.source_input(ROOT,BASE,'b'*40)
        with patch.multiple(tv,POSTER_HASH=c.sha256(poster),VIDEO_HASH=c.sha256(video),VIDEO_BYTES=len(video)):
            self.assertEqual(set(run(blobs)[1]),set(blobs))
            for path in blobs:
                with self.subTest(path=path),self.assertRaises(ValueError):run(dict(blobs,**{path:blobs[path]+b'!'}))
            with self.assertRaises(ValueError):run(blobs,parent='a'*40)
            with self.assertRaises(ValueError):run(blobs,mode='120000')

    def test_verify_rejects_provenance_and_whole_tree_tampering(self):
        plan={'test':'plan'}
        with patch.object(tv,'compile_source',return_value=plan),patch.object(c,'provenance_message',return_value='trusted'):
            with patch.object(c,'git',side_effect=[BASE.encode(),b'b'*40,b'forged']):
                with self.assertRaisesRegex(ValueError,'provenance'):tv.verify(ROOT,BASE,'c'*40,'unused','unused')
            with patch.object(c,'git',side_effect=[BASE.encode(),b'b'*40,b'trusted',b'tree1',b'tree2']):
                with self.assertRaisesRegex(ValueError,'whole-tree'):tv.verify(ROOT,BASE,'c'*40,'unused','unused')

if __name__=='__main__':unittest.main()
