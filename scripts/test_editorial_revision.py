"""Adversarial isolated maintenance fixtures; no test data is publishable."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import editorial_revision as revision
import publication_compiler as compiler
import publication_guard as guard
from test_publication_compiler import source_commit

ROOT = Path(__file__).resolve().parents[1]


class EditorialRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-editorial-tests-')
        cls.root = Path(cls.temp.name) / 'repo'
        subprocess.run(['git', 'clone', '-q', '--shared', str(ROOT), str(cls.root)], check=True)
        # Stable pre-maintenance snapshot; future main may already contain the revision.
        original = '5aa9a562f9485638571f2b4a5e272442af5d69ce'
        compiler.git(cls.root,'checkout','-q','--detach',original)
        code = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'scripts').glob('*.py')}
        cls.base = source_commit(cls.root,original,code)
        compiler.git(cls.root,'checkout','-q','--detach',cls.base)
        source_path = 'content/publications/adonis-respect-quarry-20261026.json'
        raw = (cls.root/source_path).read_bytes()
        cls.record=json.loads(raw)
        cls.expected, _, _ = revision.ticker_changes(cls.root,cls.base,cls.record)
        cls.value = {'schema':revision.SCHEMA,'id':'isolated-adonis-ticker-test','expected_base':cls.base,
                     'operation':'add-adonis-ticker','approval_reference':'private:synthetic-test-not-approval',
                     'expected_source_sha256':compiler.sha256(raw),
                     'expected_targets_sha256':compiler.sha256(compiler.canonical({p:compiler.sha256((cls.root/p).read_bytes()) for p in sorted(cls.expected)})),
                     'payload':{}}
        cls.path=revision.PREFIX+cls.value['id']+'.json'
        cls.source=source_commit(cls.root,cls.base,{cls.path:json.dumps(cls.value).encode()})
        with tempfile.TemporaryDirectory() as temp, patch.object(compiler,'validate_stage'):
            out=Path(temp)/'out'
            cls.plan=compiler.compile_publication(cls.root,cls.base,cls.source,out,Path(temp)/'plan.json',True)
            cls.files={e['path']:(out/e['path']).read_bytes() for e in cls.plan['changes']}
            cls.candidate=compiler.git(out,'rev-parse','HEAD').decode().strip()
            # Pull provisional local object into the fixture object database.
            compiler.git(cls.root,'fetch','-q',str(out),cls.candidate)

    @classmethod
    def tearDownClass(cls):
        guard._proofs.clear();cls.temp.cleanup()

    def test_exact_ticker_only_and_unchanged_historical_sources(self):
        import sync_tickers
        before=json.loads((self.root/'content/homepage.json').read_text())
        after=json.loads(self.files['content/homepage.json'])
        mutable={'ticker_entries','ticker_slugs','omit_from_ticker'}
        self.assertEqual({k:v for k,v in before.items() if k not in mutable},
                         {k:v for k,v in after.items() if k not in mutable})
        self.assertEqual(after['ticker_slugs'][0],self.record['articles'][0]['slugs']['ar'])
        self.assertLessEqual(len(after['ticker_slugs']),10)
        for path,data in self.files.items():
            if path.endswith('.html'):
                old=(self.root/path).read_text()
                strip=lambda text:sync_tickers.TICKER.sub(lambda m:m[1]+m[3],text)
                self.assertEqual(strip(old),strip(data.decode()))
            else:self.assertIn(path,('content/homepage.json','content/ticker.json',self.path))
        self.assertNotIn('content/publications/adonis-respect-quarry-20261026.json',self.files)

    def test_closed_operation_and_payload(self):
        for field,value in [('operation','delete-article'),('expected_base','0'*40),
                            ('expected_source_sha256','0'*64),('expected_targets_sha256','0'*64),
                            ('payload',{'title':'tampered'}),('approval_reference','full private transcript')]:
            bad=copy.deepcopy(self.value);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                revision.expected_changes(self.root,self.base,bad,self.path)
        bad=copy.deepcopy(self.value);bad['arbitrary_paths']=['docs/index.html']
        with self.assertRaises(ValueError):revision.validate_revision(bad,self.path,self.base)

    def test_mixed_source_and_existing_record_revision_rejected(self):
        for target in ('scripts/editorial_revision.py','content/publications/adonis-respect-quarry-20261026.json',
                       'content/caption-revisions/extra.json','docs/index.html'):
            source=source_commit(self.root,self.base,{self.path:json.dumps(self.value).encode(),target:b'bad'})
            with self.subTest(target=target),self.assertRaises(ValueError):revision.source_input(self.root,self.base,source)
        source=source_commit(self.root,self.source,{self.path:json.dumps(self.value).encode()})
        with self.assertRaises(ValueError):revision.source_input(self.root,self.base,source)

    def test_distribution_scope_cannot_be_forged(self):
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ValueError,'distribution scope'):
            compiler.compile_publication(self.root,self.base,self.source,Path(temp)/'out',Path(temp)/'plan.json',False)

    def test_idempotent_replay_and_repeat_application_rejected(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(compiler,'validate_stage'):
            out=Path(temp)/'out'
            plan=compiler.verify_candidate(self.root,self.base,self.candidate,out,Path(temp)/'plan.json')
            self.assertEqual(plan,self.plan)
            with self.assertRaisesRegex(ValueError,'already applied'):
                revision.ticker_changes(out,self.candidate,self.record)

    def test_candidate_whole_tree_tamper_rejected(self):
        for target,data in [('docs/index.html',b'body edited'),('content/ticker.json',b'{}'),
                            ('content/publications/adonis-respect-quarry-20261026.json',b'{}'),
                            ('scripts/editorial_revision.py',b'pass\n')]:
            files=dict(self.files);files[target]=data
            raw=source_commit(self.root,self.source,files)
            tree=compiler.git(self.root,'rev-parse',raw+'^{tree}').decode().strip()
            env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.invalid')
            candidate=subprocess.check_output(['git','-C',str(self.root),'commit-tree',tree,'-p',self.source],input=compiler.provenance_message(self.plan).encode(),env=env).decode().strip()
            with self.subTest(target=target),tempfile.TemporaryDirectory() as temp,patch.object(compiler,'validate_stage'),self.assertRaises(ValueError):
                compiler.verify_candidate(self.root,self.base,candidate,Path(temp)/'out',Path(temp)/'plan.json')

    def test_missing_hash_and_symlink_rejected(self):
        value=copy.deepcopy(self.value);del value['expected_targets_sha256']
        with self.assertRaises(ValueError):revision.validate_revision(value,self.path,self.base)
        for mode in ('100755','120000'):
            source=source_commit(self.root,self.base,{self.path:json.dumps(self.value).encode()},{self.path:mode})
            with self.assertRaises(ValueError):revision.source_input(self.root,self.base,source)


if __name__=='__main__':unittest.main()
