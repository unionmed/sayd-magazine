"""Exact, adversarial tests for the one-way homepage ticker migration."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import publication_compiler as compiler
import editorial_revision as revision
import publication_finalize as finalize
import ticker_scope as scope
ROOT = Path(__file__).resolve().parents[1]

class TickerScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_publication_compiler import source_commit
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-ticker-scope-')
        cls.root = Path(cls.temp.name)/'repo'
        subprocess.run(['git','clone','-q','--shared',str(ROOT),str(cls.root)],check=True)
        cls.base = compiler.git(cls.root,'rev-parse','HEAD').decode().strip()
        # Test migration before its one-way application, even after future release.
        if scope.homepage_only(cls.root):
            original = 'c27b748930b782d3d3fa74d780f37e518a618503'
            compiler.git(cls.root,'checkout','-q','--detach',original)
            code = {str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'scripts').glob('*.py')}
            cls.base = source_commit(cls.root,original,code)
            compiler.git(cls.root,'checkout','-q','--detach',cls.base)
        cls.expected,_,_ = scope.migration_changes(cls.root,cls.base)
        cls.value = {'schema':revision.SCHEMA,'id':'homepage-only-ticker-20261028',
                     'expected_base':cls.base,'operation':'homepage-only-ticker',
                     'approval_reference':'private:synthetic-test-not-approval',
                     'expected_source_sha256':compiler.sha256((cls.root/'content/publication-contract.json').read_bytes()),
                     'expected_targets_sha256':compiler.sha256(compiler.canonical({p:compiler.sha256((cls.root/p).read_bytes()) for p in sorted(cls.expected)})),
                     'payload':{}}
        cls.path = revision.PREFIX+cls.value['id']+'.json'
        cls.source = source_commit(cls.root,cls.base,{cls.path:json.dumps(cls.value).encode()})
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def test_exact_scope_and_all_outside_bytes(self):
        from test_shared_ticker import without_complete_strip
        for path,new in self.expected.items():
            old=(self.root/path).read_bytes()
            if path.endswith('.html'):
                self.assertNotIn(path[5:],scope.HOMEPAGES)
                self.assertEqual(without_complete_strip(old.decode()).encode(),new)
                self.assertNotIn(b'class="news-strip"',new)
                self.assertEqual(old.count(b'nathalie-interview-typography'),new.count(b'nathalie-interview-typography'))
        old=json.loads((self.root/'content/publication-contract.json').read_text())
        self.assertEqual(json.loads(self.expected['content/publication-contract.json']),dict(old,ticker_scope=scope.POLICY))
        self.assertGreater(len(self.expected),1000)
    def test_hashes_payload_and_identity_fail_closed(self):
        for key,value in [('expected_base','0'*40),('expected_source_sha256','0'*64),
                          ('expected_targets_sha256','0'*64),('payload',{'pages':['index.html']}),
                          ('id','arbitrary-migration'),('operation','delete-anything')]:
            bad=copy.deepcopy(self.value);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                revision.expected_changes(self.root,self.base,bad,self.path)
    def test_unapproved_source_files_rejected(self):
        from test_publication_compiler import source_commit
        for path in ('docs/index.html','scripts/ticker_scope.py','content/publication-contract.json'):
            source=source_commit(self.root,self.base,{self.path:json.dumps(self.value).encode(),path:b'tampered'})
            with self.subTest(path=path),self.assertRaises(ValueError):
                scope.verified_migration_outputs(self.root,self.base,source)
    def test_exact_output_and_finalizer(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(compiler,'validate_stage'):
            out=Path(temp)/'site';report=Path(temp)/'plan.json'
            plan=revision.compile_source(self.root,self.base,self.source,out,report,False)
            expected=scope.verified_migration_outputs(out,self.base,self.source)
            self.assertEqual({e['path'] for e in plan['changes']},set(expected))
            finalize.validate_plan(out,plan,self.base,self.source,self.base,plan['plan_sha256'])
            target=out/'content/publication-contract.json';data=target.read_bytes()
            target.write_bytes(data.replace(b'"version": 1',b'"version": 2'))
            with self.assertRaises((ValueError,finalize.Blocked)):
                finalize.validate_plan(out,plan,self.base,self.source,self.base,plan['plan_sha256'])
    def test_contract_not_generally_allowed(self):
        self.assertFalse(compiler.allowed_output_path('content/publication-contract.json'))
        with self.assertRaises(finalize.Blocked):finalize.safe_output_path('content/publication-contract.json')
    def test_legacy_unknown_and_boolean_policy(self):
        self.assertFalse(scope.homepage_only_contract({}))
        self.assertTrue(scope.homepage_only_contract({'ticker_scope':scope.POLICY}))
        for value in ([],None,{'ticker_scope':None},{'ticker_scope':dict(scope.POLICY,version=True)},
                      {'ticker_scope':dict(scope.POLICY,extra=True)}):
            with self.subTest(value=value),self.assertRaises(ValueError):scope.homepage_only_contract(value)

    def test_future_ticker_publication_never_changes_old_article_bytes(self):
        from test_publication_compiler import source_commit, record, files_for
        with tempfile.TemporaryDirectory() as temp:
            migrated=Path(temp)/'migrated'
            with patch.object(compiler,'validate_stage'):
                revision.compile_source(self.root,self.base,self.source,migrated,Path(temp)/'migration.json',False)
            base=compiler.git(migrated,'rev-parse','HEAD').decode().strip()
            value=record(base,'ticker-scope-future-test',placement='latest',ticker=True)
            value['articles'][0]['primary_door']='wildlife'
            value['articles'][0]['archives']=['wildlife']
            value['articles'][0]['published']='2026-10-29'
            source=source_commit(migrated,base,files_for(value))
            future=Path(temp)/'future'
            plan=compiler.compile_publication(migrated,base,source,future,Path(temp)/'future.json',True)
            old=compiler.tree(migrated,base)
            changes=[e['path'] for e in plan['changes']]
            self.assertIn('content/ticker.json',changes)
            self.assertFalse([p for p in changes if p in old and compiler.ARTICLE.fullmatch(p)])
            for p in old:
                if compiler.ARTICLE.fullmatch(p):
                    self.assertEqual(compiler.read_blob(migrated,old[p]),(future/p).read_bytes())
            self.assertEqual([p for p in scope.HOMEPAGES if 'docs/'+p in changes],list(scope.HOMEPAGES))

    def test_market_search_shell_respects_policy_without_home_changes(self):
        import build_market_coming_soon as market
        from test_shared_ticker import without_complete_strip
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);docs=root/'docs';(root/'content').mkdir()
            policy=root/'content/publication-contract.json'
            for prefix in ('','en','fr'):
                source=docs/prefix/'index.html';source.parent.mkdir(parents=True,exist_ok=True)
                source.write_bytes((self.root/'docs'/prefix/'index.html').read_bytes())
            with patch.object(market,'ROOT',root),patch.object(market,'DOCS',docs):
                for language in ('ar','en','fr'):
                    policy.write_text('{}')
                    old=market.build(language).read_text()
                    policy.write_text(json.dumps({'ticker_scope':scope.POLICY}))
                    new=market.build(language).read_text()
                    self.assertEqual(without_complete_strip(old),new)
            for prefix in ('','en','fr'):
                self.assertEqual((docs/prefix/'index.html').read_bytes(),(self.root/'docs'/prefix/'index.html').read_bytes())
