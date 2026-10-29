"""Historical article QA permits only independently verified publication chrome."""
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_gulf_tourism_20261022 as gulf
import test_laws_card_landmarks as laws
import check_publication_contract as contract
import sync_tickers


class HistoricalPublicationGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / 'docs'
        (self.root / 'content').mkdir()
        (self.root / 'content/publication-contract.json').write_text('{}')
        for mod, attr, value in ((gulf, 'ROOT', self.root), (laws, 'ROOT', self.root),
                                 (contract, 'ROOT', self.root),
                                 (contract, 'DOCS', self.docs)):
            p = patch.object(mod, attr, value); p.start(); self.addCleanup(p.stop)
        self.a = {'translations': {l: {'title': 'Gulf '+l, 'kicker': 'Series '+l} for l in ('ar','en','fr')},
                  'slugs': {l: 'gulf-'+l for l in ('ar','en','fr')},
                  'photos': [{'path': 'media/gulf.jpg', 'alt': {l:'Gulf photo '+l for l in ('ar','en','fr')}}]}
        self.config = {'ia_slots': {'main': 'new-lead'}}
        self.write_config()

    def write_config(self):
        (self.root/'content/homepage.json').write_text(json.dumps(self.config))

    def home(self, lang, kicker=True):
        prefix = '' if lang=='ar' else lang+'/'
        rel = 'docs/'+prefix+'index.html'
        html = ('<article class="feature-lead"><h2><a href="posts/new/index.html">New '+lang+'</a></h2>'
                '<img src="/'+ 'media/new.jpg" alt="New photo">'+
                ('<p class="migration-kicker">Series 2</p>' if kicker else '')+'</article>')
        p=self.root/rel; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(html)
        return rel, html

    def test_original_gulf_identity_without_new_proof(self):
        self.config['ia_slots']['main']=gulf.AR;self.write_config()
        for lang in ('ar','en','fr'):
            got=gulf.gulf_browser_home(lang,self.a)
            self.assertEqual(got['title'],'Gulf '+lang)
            self.assertEqual(got['image'],'/media/gulf.jpg')

    def test_verified_rotation_all_languages(self):
        for lang in ('ar','en','fr'):
            rel, page=self.home(lang)
            proof=SimpleNamespace(config=self.config,read=lambda name:page if name==rel else None)
            got=gulf.gulf_browser_home(lang,self.a,proof)
            self.assertEqual(got,{'title':'New '+lang,'href':('/' if lang=='ar' else '/'+lang+'/')+'posts/new/index.html',
                                  'image':'/media/new.jpg','alt':'New photo','kicker':'Series 2'})

    def test_verified_rotation_without_optional_kicker(self):
        rel,page=self.home('en',False)
        proof=SimpleNamespace(config=self.config,read=lambda _:page)
        self.assertIsNone(gulf.gulf_browser_home('en',self.a,proof)['kicker'])

    def test_rotated_unknown_or_missing_proof_rejected(self):
        self.home('ar')
        with self.assertRaises(AssertionError):gulf.gulf_browser_home('ar',self.a)
        proof=SimpleNamespace(config={'ia_slots':{'main':'unknown'}},read=lambda _: '')
        with self.assertRaises(AssertionError):gulf.gulf_browser_home('ar',self.a,proof)

    def test_current_home_tamper_rejected(self):
        for lang in ('ar','en','fr'):
            for old,new in [('New '+lang,'Wrong title'),('media/new.jpg','media/wrong.jpg'),
                            ('posts/new/index.html','posts/wrong/index.html'),('Series 2','Wrong series')]:
                with self.subTest(lang=lang,mutation=old):
                    rel,page=self.home(lang)
                    proof=SimpleNamespace(config=self.config,read=lambda _:page)
                    (self.root/rel).write_text(page.replace(old,new))
                    with self.assertRaises(AssertionError):gulf.gulf_browser_home(lang,self.a,proof)

    def test_only_independently_replayed_desk_kind_can_keep_unchanged_lead(self):
        import copy
        for lang in ('ar', 'en', 'fr'):
            rel, lead = self.home(lang)
            before = {'ia_slots': {'main': 'new-lead'}, 'omit_from_home_desks': ['restored'],
                      'primary_door': {'restored': 'hunting'}}
            self.config = copy.deepcopy(before); self.config['omit_from_home_desks'] = []; self.write_config()
            old = lead + '<section id="desk">Old desk</section>'
            (self.root/rel).write_text(lead + '<section id="desk">Restored desk</section>')
            proof = SimpleNamespace(config=before, read=lambda _:old, kind='verified-desk-restoration')
            self.assertEqual(gulf.gulf_browser_home(lang, self.a, proof)['title'], 'New '+lang)
            for kind in ('compiled-publication', 'baseline-publication', None):
                proof.kind = kind
                with self.assertRaises(AssertionError): gulf.gulf_browser_home(lang, self.a, proof)
            proof.kind = 'verified-desk-restoration'
            (self.root/rel).write_text(lead.replace('New '+lang, 'Corrupt lead') + '<section>Restored desk</section>')
            with self.assertRaises(AssertionError): gulf.gulf_browser_home(lang, self.a, proof)
            (self.root/rel).write_text(lead + '<section>Restored desk</section>')
            self.config['ia_slots']['main'] = 'unapproved-lead'; self.write_config()
            with self.assertRaises(AssertionError): gulf.gulf_browser_home(lang, self.a, proof)

    def test_malformed_home_structure_rejected(self):
        for kind in ('missing','duplicate','no-image'):
            rel,page=self.home('ar')
            page={'missing':'<p>No lead</p>','duplicate':page+page,'no-image':page.replace('<img src="/media/new.jpg" alt="New photo">','')}[kind]
            (self.root/rel).write_text(page)
            proof=SimpleNamespace(config=self.config,read=lambda _:page)
            with self.assertRaises(AssertionError):gulf.gulf_browser_home('ar',self.a,proof)

    def category(self,lang):
        prefix='' if lang=='ar' else lang+'/'
        path=self.docs/prefix/'category/laws/index.html'
        source={l:(self.docs/('' if l=='ar' else l),'<a href="posts/new/index.html">New '+l+'</a>') for l in ('ar','en','fr')}
        expected=sync_tickers.ticker_for(path,source[lang])
        body='<header>Header</header><article><h2><a href="../../posts/law/">Law</a></h2><a class="thumb" href="../../posts/law/"><img src="old.jpg" alt="Old"></a><p>Legal body</p></article><article>Second</article>'
        wrap=lambda text:'<div class="ticker">'+text+'</div><div class="ticker" aria-hidden="true">'+text+'</div>'+body
        return path,source,wrap('<a href="old/">Old</a>'),wrap(expected),expected

    def scope(self,lang,before,page,path,source,proof=True):
        actual=SimpleNamespace(read=lambda _:page) if proof is True else proof
        with patch('publication_guard.verified_publication',return_value=actual),patch.object(sync_tickers,'sources',return_value=source):
            laws.assert_category_scope(before,page,lang,{'images':[{'slugs':{lang:'law'}}]},path,'base')

    def test_canonical_ticker_rotation_all_languages(self):
        for lang in ('ar','en','fr'):
            path,source,before,page,_=self.category(lang)
            self.scope(lang,before,page,path,source)

    def test_homepage_only_policy_rejects_internal_loop_rotation(self):
        from ticker_scope import POLICY
        (self.root/'content/publication-contract.json').write_text(json.dumps({'ticker_scope':POLICY}))
        for lang in ('ar','en','fr'):
            path,source,before,page,_=self.category(lang)
            with self.assertRaises(AssertionError):self.scope(lang,before,page,path,source)

    def test_exact_wrapper_migration_requires_proof_and_preserves_outside_bytes(self):
        from ticker_scope import POLICY, strip_internal_ticker
        def git(*args):
            return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL)
        git('init','-q')
        originals={}
        for lang in ('ar','en','fr'):
            path,source,before,_,_=self.category(lang)
            split=before.index('<header>')
            before='<div class="site-sticky"><div class="news-strip">'+before[:split]+'</div></div>'+before[split:]
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(before)
            originals[lang]=(path,source,before)
        git('add','.')
        git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Legacy fixture')
        base=git('rev-parse','HEAD').decode().strip()
        (self.root/'content/publication-contract.json').write_text(json.dumps({'ticker_scope':POLICY}))
        for lang,(path,source,before) in originals.items():
            page=strip_internal_ticker(before);path.write_text(page)
            proof=SimpleNamespace(read=lambda _,value=page:value)
            with patch('publication_guard.verified_publication',return_value=proof):
                laws.assert_category_scope(before,page,lang,{'images':[{'slugs':{lang:'law'}}]},path,base)
            for badproof in (None,SimpleNamespace(read=lambda _:'wrong')):
                with patch('publication_guard.verified_publication',return_value=badproof),self.assertRaises(AssertionError):
                    laws.assert_category_scope(before,page,lang,{'images':[{'slugs':{lang:'law'}}]},path,base)
            for old,new in [('Header','Wrong header'),('Legal body','Wrong body'),('>Law<','>Wrong title<'),
                            ('../../posts/law/','../../posts/other/'),('old.jpg','wrong.jpg')]:
                altered=page.replace(old,new);path.write_text(altered)
                with patch('publication_guard.verified_publication',return_value=SimpleNamespace(read=lambda _:altered)),self.assertRaises(AssertionError):
                    laws.assert_category_scope(before,altered,lang,{'images':[{'slugs':{lang:'law'}}]},path,base)
            path.write_text(page)

    def test_noop_and_original_photo_only_change_need_no_proof(self):
        for lang in ('ar','en','fr'):
            path,source,before,_,_=self.category(lang)
            self.scope(lang,before,before,path,source,None)
            page=before.replace('src="old.jpg" alt="Old"','src="landmark.jpg" alt="Landmark" style="object-fit:cover"')
            self.scope(lang,before,page,path,source,None)

    def test_ticker_change_requires_exact_proof(self):
        path,source,before,page,_=self.category('ar')
        for proof in (None,SimpleNamespace(read=lambda _:'tampered')):
            with self.assertRaises(AssertionError):self.scope('ar',before,page,path,source,proof)

    def test_invalid_ticker_rotation_rejected(self):
        for lang in ('ar','en','fr'):
            path,source,before,page,expected=self.category(lang)
            variants=[page.replace('<div class="ticker">','<div class="broken-ticker">',1),
                      page.replace('<div class="ticker">'+expected+'</div>','',1),
                      page.replace(expected,'<a href="wrong/">Wrong</a>',1),
                      page.replace(expected,'<a href="old/">Stale</a>'),
                      page+'<div class="ticker">'+expected+'</div>']
            for candidate in variants:
                with self.subTest(lang=lang,candidate=candidate[:100]):
                    with self.assertRaises(AssertionError):self.scope(lang,before,candidate,path,source)

    def test_outside_ticker_mutations_rejected_even_with_matching_proof(self):
        for lang in ('ar','en','fr'):
            path,source,before,page,_=self.category(lang)
            for old,new in [('Header','Changed header'),('Legal body','Wrong body'),('>Law<','>Wrong title<'),
                            ('../../posts/law/','../../posts/other/'),('<article>Second</article>','<article>Reordered</article>')]:
                with self.subTest(lang=lang,mutation=old):
                    with self.assertRaises(AssertionError):self.scope(lang,before,page.replace(old,new),path,source)

    def test_law_card_order_change_rejected(self):
        for lang in ('ar','en','fr'):
            path,source,before,page,_=self.category(lang)
            second='<article>Second</article>'
            candidate=page.replace(second,'').replace('<article>',second+'<article>',1)
            with self.assertRaises(AssertionError):self.scope(lang,before,candidate,path,source)

    def test_historical_article_title_corruption_still_rejected(self):
        # Exercise the existing article checker, not the new homepage selector.
        for lang in ('ar','en','fr'):
            path=self.docs/('' if lang=='ar' else lang)/'posts'/self.a['slugs'][lang]/'index.html'
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('<html lang="'+lang+'"><h1>Corrupt historical title</h1></html>')
            with patch.object(gulf,'DOCS',self.docs),self.assertRaises(AssertionError):
                gulf.assert_gulf_article(lang,self.a)



class CardGeometryTests(unittest.TestCase):
    def test_only_measured_strip_shift_is_allowed(self):
        old = {'x': 100, 'y': 261.046875, 'width': 1240, 'height': 90}
        strip = {'y': 160, 'height': 38}
        shifted = dict(old, y=223.046875)
        laws.assert_card_geometry(old, shifted, 'approved', strip)
        laws.assert_card_geometry(old, old, 'legacy')
        with self.assertRaises(AssertionError):
            laws.assert_card_geometry(old, shifted, 'unapproved')
        for key in old:
            bad = dict(shifted); bad[key] += 2
            with self.subTest(key=key), self.assertRaises(AssertionError):
                laws.assert_card_geometry(old, bad, 'outside geometry', strip)
        above = dict(old, y=30)
        laws.assert_card_geometry(above, above, 'above strip', strip)
        with self.assertRaises(AssertionError):
            laws.assert_card_geometry(above, dict(above, y=-8), 'wrong above shift', strip)
        for height in (0, -38, float('nan'), float('inf')):
            with self.subTest(height=height), self.assertRaises(AssertionError):
                laws.assert_card_geometry(old, shifted, 'invalid measurement', dict(strip, height=height))


class BrowserProofPlumbingTests(unittest.TestCase):
    def test_both_browser_callers_pass_their_existing_trusted_proof(self):
        import ast
        root = Path(__file__).resolve().parent
        for filename, expected in [('test_merged_section_browser.py', 'compiled'),
                                   ('test_gulf_tourism_browser_20261022.py', 'proof')]:
            module = ast.parse((root / filename).read_text())
            calls = [node for node in ast.walk(module) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == 'test_gulf_browser']
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(calls[0].args), 4)
            self.assertIsInstance(calls[0].args[3], ast.Name)
            self.assertEqual(calls[0].args[3].id, expected)

if __name__=='__main__':unittest.main()
