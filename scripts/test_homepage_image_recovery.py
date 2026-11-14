"""Offline closed-recovery proofs. Synthetic commits are never publishable."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

import editorial_revision as revision
import homepage_image_sources as images
import homepage_image_recovery as recovery
import publication_compiler as compiler
import publication_finalize as finalizer
from test_publication_compiler import source_commit
from test_publication_finalize import FakeAPI

ROOT = Path(__file__).resolve().parents[1]
# Reachable production main, not the local-only support commit.
ORIGINAL = 'c48f5e110651d3d4cf114b6c3c2bc1b614a7b194'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()


def record(operation, base, digest, targets, before):
    return {'schema': revision.SCHEMA, 'id': operation, 'operation': operation,
            'expected_base': base, 'expected_source_sha256': digest,
            'expected_targets_sha256': compiler.sha256(compiler.canonical({p: compiler.sha256(before[p]) for p in sorted(targets)})),
            'approval_reference': 'private:synthetic-test-not-approval', 'payload': {}}


def generated(root, base, marker, value, outputs, bad_message=False):
    source = source_commit(root, base, {marker: encoded(value)})
    files = dict(outputs, **{marker: encoded(value)})
    plan = recovery.transition_plan(base, source, compiler.tree(root, base), files)
    provisional = source_commit(root, source, files)
    tree = compiler.git(root, 'rev-parse', provisional+'^{tree}').decode().strip()
    env = dict(os.environ, GIT_AUTHOR_NAME='Synthetic recovery test', GIT_AUTHOR_EMAIL='test@example.invalid',
               GIT_COMMITTER_NAME='Synthetic recovery test', GIT_COMMITTER_EMAIL='test@example.invalid')
    message = 'Forged provenance' if bad_message else compiler.provenance_message(plan)
    candidate = subprocess.check_output(['git', '-C', str(root), 'commit-tree', tree, '-p', source], input=message.encode(), env=env).decode().strip()
    return source, candidate, plan


class HomepageImageRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-recovery-test-')
        cls.repo = Path(cls.temp.name)/'repo'
        subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(cls.repo)], check=True)
        code = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'scripts').glob('*.py')}
        cls.original = source_commit(cls.repo, ORIGINAL, code)
        inputs = images.migration_inputs(cls.repo, cls.original)
        cls.originals = {p: inputs[p] for p in images.HOMES.values()}
        cls.activated, _, _ = images.migration_changes(cls.repo, cls.original, images.source_digest(inputs))
        cls.activation = record(images.OPERATION, cls.original, images.source_digest(inputs), cls.activated, inputs)
        cls.activation_source, cls.base, cls.activation_plan = generated(cls.repo, cls.original, images.MARKER, cls.activation, cls.activated)
        _, digest = recovery.recovery_evidence(cls.repo, cls.base)
        cls.value = record(recovery.OPERATION, cls.base, digest, cls.originals, cls.activated)
        cls.source, cls.candidate, cls.plan = generated(cls.repo, cls.base, recovery.MARKER, cls.value, cls.originals)
        cls.outputs = dict(cls.originals, **{recovery.MARKER: encoded(cls.value)})
        cls.changes = [(item, cls.outputs[item['path']]) for item in cls.plan['changes']]
        # Only four small/required outputs on disk for writer tests; no full checkout.
        cls.site = Path(cls.temp.name)/'files'
        for path, data in cls.outputs.items():
            target = cls.site/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        recovery._recovered.cache_clear()
        cls.temp.cleanup()

    def test_exact_append_only_inverse_and_public_byte_restoration(self):
        path, value, expected, _, _ = revision.source_input(self.repo, self.base, self.source)
        self.assertEqual(path, recovery.MARKER); self.assertEqual(value, self.value)
        self.assertEqual(expected, self.outputs)
        before, after = compiler.tree(self.repo, self.original), compiler.tree(self.repo, self.candidate)
        self.assertEqual({p:v for p,v in before.items() if p.startswith('docs/')},
                         {p:v for p,v in after.items() if p.startswith('docs/')})
        self.assertEqual(set(after)-set(before), {images.MARKER, recovery.MARKER})
        self.assertTrue(all(after[p] == v for p,v in before.items()))
        self.assertEqual(after[images.MARKER], compiler.tree(self.repo, self.base)[images.MARKER])
        self.assertTrue(all(len(raw) > finalizer.TREE_BATCH_BYTES for raw in self.originals.values()))

    def test_real_two_parent_merges_preserve_both_transition_proofs(self):
        def merge(first, second):
            tree = compiler.git(self.repo, 'rev-parse', second+'^{tree}').decode().strip()
            env = dict(os.environ, GIT_AUTHOR_NAME='Synthetic merge test', GIT_AUTHOR_EMAIL='test@example.invalid',
                       GIT_COMMITTER_NAME='Synthetic merge test', GIT_COMMITTER_EMAIL='test@example.invalid')
            return subprocess.check_output(['git', '-C', str(self.repo), 'commit-tree', tree,
                                            '-p', first, '-p', second], input=b'Synthetic normal merge', env=env).decode().strip()
        activation_merge = merge(self.original, self.base)
        originals, digest = recovery.recovery_evidence(self.repo, activation_merge)
        self.assertEqual(originals, self.originals)
        value = record(recovery.OPERATION, activation_merge, digest, self.originals, self.activated)
        _, candidate, _ = generated(self.repo, activation_merge, recovery.MARKER, value, originals)
        recovery_merge = merge(activation_merge, candidate)
        compiler.git(self.repo, 'update-ref', 'HEAD', recovery_merge)
        try:
            self.assertTrue(recovery.recovered(self.repo, encoded(self.activation), encoded(value)))
        finally:
            compiler.git(self.repo, 'update-ref', 'HEAD', self.original)
        # A squash-shaped commit is not equivalent to preserved proof history.
        squashed = source_commit(self.repo, activation_merge, dict(originals, **{recovery.MARKER: encoded(value)}))
        with self.assertRaises(ValueError):
            recovery.prove_transition(self.repo, activation_merge, squashed, recovery.MARKER, encoded(value), originals)

    def test_only_path_bound_historical_sha_reuse_fits_unchanged_limits(self):
        source_entries = finalizer.tree_entries(self.repo, self.source)
        source_tree = compiler.git(self.repo, 'rev-parse', self.source+'^{tree}').decode().strip()
        known = {sha for mode, sha in source_entries.values()}
        self.assertTrue(all(compiler.blob_sha(raw) not in known for raw in self.originals.values()))
        with self.assertRaisesRegex(finalizer.Blocked, 'Single tree entry'):
            finalizer.prepare_tree_batches(self.changes, source_entries, source_tree)
        batches, tree = finalizer.prepare_tree_batches(self.changes, source_entries, source_tree,
                                                       recovery_context=(self.repo, self.base, self.source))
        self.assertEqual((finalizer.TREE_BATCH_BYTES, finalizer.TREE_BATCH_ENTRIES, finalizer.TREE_BATCH_COUNT), (1048576,32,64))
        self.assertEqual(len(batches), 1)
        self.assertEqual(tree, compiler.git(self.repo,'rev-parse',self.candidate+'^{tree}').decode().strip())
        entries = batches[0][0]['tree']
        self.assertEqual({e['path'] for e in entries}, set(images.HOMES.values()))
        self.assertTrue(all('sha' in e and 'content' not in e for e in entries))
        self.assertLess(len(finalizer.api_json(batches[0][0])), 1024)

    def test_every_later_tree_drift_refused_including_koura_and_code(self):
        paths = ['docs/index.html','docs/en/index.html','docs/fr/index.html',
                 'docs/posts/koura-bird-protection/index.html', 'content/publications/koura-bird-protection.json',
                 'content/homepage.json', 'content/ticker.json', images.CHANNEL, images.ADONIS,
                 images.IMAGES[0][3], 'audit/image-catalog/manifest/later.tsv',
                 'docs/assets/search/index-ar.json', 'assets/new.jpg', 'scripts/later.py', 'notes/later.md']
        for path in paths:
            changed = source_commit(self.repo, self.base, {path:b'later approved content must not be overwritten'})
            with self.subTest(path=path), self.assertRaises(ValueError): recovery.recovery_evidence(self.repo, changed)
        for mode in ('100755','120000'):
            for path in (images.MARKER, *images.HOMES.values(), images.IMAGES[0][3]):
                raw = compiler.read_blob(self.repo,compiler.tree(self.repo,self.base)[path])
                changed = source_commit(self.repo, self.base, {path:raw}, {path:mode})
                with self.subTest(mode=mode,path=path), self.assertRaises(ValueError): recovery.recovery_evidence(self.repo,changed)
        # Net-zero current bytes do not erase intervening publication history.
        later = source_commit(self.repo, self.base, {'docs/later-news.html': b'later news'})
        reverted = source_commit(self.repo, later, {'docs/later-news.html': None})
        self.assertEqual(compiler.tree(self.repo, reverted), compiler.tree(self.repo, self.base))
        with self.assertRaisesRegex(ValueError, 'Intervening history drift'):
            recovery.recovery_evidence(self.repo, reverted)
        unchanged = source_commit(self.repo, self.base, {})
        self.assertEqual(recovery.recovery_evidence(self.repo, unchanged), recovery.recovery_evidence(self.repo, self.base))
        removed = source_commit(self.repo, self.base, {images.IMAGES[0][3]:None})
        with self.assertRaises(ValueError): recovery.recovery_evidence(self.repo,removed)

    def test_forged_checkpoint_marker_history_and_missing_objects_refused(self):
        for field, bad in [('expected_base', '0'*40), ('expected_base', ORIGINAL),
                           ('expected_source_sha256', '0'*64), ('expected_targets_sha256', '0'*64),
                           ('payload', {'path':'docs/index.html'}), ('operation','arbitrary'), ('id','other')]:
            value = dict(self.activation, **{field:bad})
            changed = source_commit(self.repo,self.base,{images.MARKER:encoded(value)})
            with self.subTest(field=field,bad=bad), self.assertRaises((ValueError,subprocess.CalledProcessError)):
                recovery.recovery_evidence(self.repo,changed)
        # Matching activated bytes do not replace exact generated ancestry/provenance.
        forged = source_commit(self.repo,self.original,dict(self.activated,**{images.MARKER:encoded(self.activation)}))
        with self.assertRaisesRegex(ValueError,'history|provenance'): recovery.recovery_evidence(self.repo,forged)
        _, forged, _ = generated(self.repo,self.original,images.MARKER,self.activation,self.activated,True)
        with self.assertRaisesRegex(ValueError,'history|provenance'): recovery.recovery_evidence(self.repo,forged)
        # A non-commit object cannot masquerade as the original checkpoint.
        tree = compiler.git(self.repo,'rev-parse',self.original+'^{tree}').decode().strip()
        with self.assertRaises(ValueError): recovery.commit(self.repo,tree)
        with tempfile.TemporaryDirectory() as temp:
            bare = Path(temp)/'missing-history'; subprocess.run(['git','init','-q','--bare',str(bare)],check=True)
            with self.assertRaises(subprocess.CalledProcessError): recovery.recovery_evidence(bare,self.base)

    def test_closed_inverse_schema_repeat_and_source_payload_rejection(self):
        for field,bad in [('expected_base',self.original),('expected_source_sha256','0'*64),
                          ('expected_targets_sha256','0'*64),('payload',{'blob':compiler.blob_sha(self.originals['docs/index.html'])}),
                          ('payload',{'checkpoint':self.original}),('operation','restore-anything'),('id','other')]:
            value=dict(self.value,**{field:bad})
            with self.subTest(field=field),self.assertRaises(ValueError):
                revision.expected_changes(self.repo,self.base,value,recovery.MARKER)
        for path in (images.MARKER, images.CHANNEL, 'docs/index.html', 'scripts/unsafe.py', 'content/publications/old.json'):
            source=source_commit(self.repo,self.base,{recovery.MARKER:encoded(self.value),path:b'tamper'})
            with self.subTest(path=path),self.assertRaises(ValueError): revision.source_input(self.repo,self.base,source)
        for mode in ('100755','120000'):
            source=source_commit(self.repo,self.base,{recovery.MARKER:encoded(self.value)},{recovery.MARKER:mode})
            with self.assertRaises(ValueError): revision.source_input(self.repo,self.base,source)
        with self.assertRaisesRegex(ValueError,'already applied'): recovery.recovery_evidence(self.repo,self.candidate)
        for path in (recovery.MARKER.replace('20261114','20261115'), 'content/editorial-revisions/../publication-contract.json', '/'+recovery.MARKER, recovery.MARKER.replace('.json','/nested.json')):
            with self.subTest(path=path),self.assertRaises(ValueError): finalizer.safe_output_path(path)

    def test_historical_allowance_rejects_wrong_blob_path_bytes_source_and_context(self):
        for field,bad in [('path','docs/other.html'),('new_blob',compiler.blob_sha(b'unrelated old object')),
                          ('mode','120000'),('sha256','0'*64)]:
            changes=copy.deepcopy(self.changes)
            index=next(i for i,(item,_) in enumerate(changes) if item['path']=='docs/index.html')
            changes[index][0][field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):
                recovery.historical_homepage_blobs(self.repo,self.base,self.source,changes)
        changes=list(self.changes);changes[-1]=(changes[-1][0], b'forged decoded bytes')
        with self.assertRaises(ValueError): recovery.historical_homepage_blobs(self.repo,self.base,self.source,changes)
        entries=finalizer.tree_entries(self.repo,self.source);tree=finalizer.tree_sha(entries)
        with self.assertRaises(ValueError): finalizer.prepare_tree_batches(self.changes,{},tree,recovery_context=(self.repo,self.base,self.source))
        with self.assertRaises(ValueError): finalizer.prepare_tree_batches(self.changes,entries,'0'*40,recovery_context=(self.repo,self.base,self.source))
        self.assertEqual(recovery.historical_homepage_blobs(self.repo,self.original,self.activation_source,self.changes),{})

    def test_self_consistent_forged_finalizer_plan_fails_before_any_api(self):
        # A valid plan checksum and output bytes are not historical reuse authority.
        marker = self.site/recovery.MARKER
        try:
            for field, bad in [('expected_source_sha256', '0'*64),
                               ('expected_base', self.original),
                               ('payload', {'checkpoint': self.original})]:
                value = dict(self.value, **{field: bad})
                raw = encoded(value)
                source = source_commit(self.repo, self.base, {recovery.MARKER: raw})
                outputs = dict(self.originals, **{recovery.MARKER: raw})
                plan = recovery.transition_plan(self.base, source, compiler.tree(self.repo, self.base), outputs)
                marker.write_bytes(raw)
                api = FakeAPI(SimpleNamespace(repo=self.repo, base=self.base, source=source))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    finalizer.finalize(self.repo, self.site, plan, self.base, source, self.base,
                                       plan['plan_sha256'], api, compiler.validate_report)
                self.assertEqual(api.calls, [])
        finally:
            marker.write_bytes(encoded(self.value))

    def test_runtime_requires_committed_inverse_proof_not_schema_only(self):
        # Bare object-backed worktree marker reads without allocating the full site.
        compiler.git(self.repo,'update-ref','HEAD',self.candidate)
        for marker,raw in ((images.MARKER,encoded(self.activation)),(recovery.MARKER,encoded(self.value))):
            target=self.repo/marker;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        try:
            self.assertFalse(images.active(self.repo))
            for bad in (b'{}',b'null',b'{"id":"x","id":"y"}',encoded(dict(self.value,expected_base=self.original)),encoded(self.value)+b' '):
                (self.repo/recovery.MARKER).write_bytes(bad)
                with self.subTest(bad=bad[:35]),self.assertRaises((ValueError,subprocess.CalledProcessError)):
                    images.active(self.repo)
            (self.repo/recovery.MARKER).write_bytes(encoded(self.value))
            compiler.git(self.repo,'update-ref','HEAD',self.source)
            with self.assertRaisesRegex(ValueError,'history|provenance'): images.active(self.repo)
            # After verified restoration, later commits do not re-run no-drift admission.
            later=source_commit(self.repo,self.candidate,{'docs/new-after-recovery.html':b'approved future article'})
            compiler.git(self.repo,'update-ref','HEAD',later)
            self.assertFalse(images.active(self.repo))
            (self.repo/images.MARKER).unlink()
            with self.assertRaisesRegex(ValueError,'without activation'): images.active(self.repo)
        finally:
            for marker in (images.MARKER,recovery.MARKER):
                target=self.repo/marker
                if target.exists() or target.is_symlink(): target.unlink()
            compiler.git(self.repo,'update-ref','HEAD',self.original)

    def test_finalizer_full_preflight_races_and_no_retry_offline(self):
        case=SimpleNamespace(repo=self.repo,base=self.base,source=self.source)
        for stale in (None,1,2,3,4):
            api=FakeAPI(case,stale_at=stale)
            call=lambda: finalizer.finalize(self.repo,self.site,self.plan,self.base,self.source,self.base,
                                            self.plan['plan_sha256'],api,compiler.validate_report)
            if stale is None:
                receipt=call();self.assertEqual(receipt['status'],'CREATED_REVIEW_ONLY')
                self.assertEqual(receipt['tree'],compiler.git(self.repo,'rev-parse',self.candidate+'^{tree}').decode().strip())
                self.assertFalse(receipt['published']);self.assertFalse(receipt['merged'])
            else:
                with self.subTest(stale=stale),self.assertRaisesRegex(finalizer.Blocked,'Main changed'): call()
                self.assertFalse(any(method=='POST' and endpoint=='/git/refs' for method,endpoint,_ in api.calls))
            self.assertFalse(any(endpoint=='/git/blobs' for _,endpoint,_ in api.calls))
        api=FakeAPI(case,fail_ref=True)
        with self.assertRaises(finalizer.UncertainMutation):
            finalizer.finalize(self.repo,self.site,self.plan,self.base,self.source,self.base,self.plan['plan_sha256'],api,compiler.validate_report)
        self.assertEqual(sum(method=='POST' and endpoint=='/git/refs' for method,endpoint,_ in api.calls),1)
        target=self.site/'docs/index.html';raw=target.read_bytes()
        try:
            target.unlink();target.symlink_to(self.site/'docs/en/index.html')
            api=FakeAPI(case)
            with self.assertRaises(ValueError):
                finalizer.finalize(self.repo,self.site,self.plan,self.base,self.source,self.base,self.plan['plan_sha256'],api,compiler.validate_report)
            self.assertEqual(api.calls,[])
        finally:target.unlink();target.write_bytes(raw)

    def test_full_trusted_compiler_replay_stage_and_no_content_build(self):
        # Deliberately unmocked. Peak disk usage needs an isolated sequential run.
        compiler.git(self.repo,'checkout','-q','--force','--detach',self.base)
        with tempfile.TemporaryDirectory(prefix='sayd-recovery-full-') as temp:
            root=Path(temp);stage=root/'stage'
            plan=compiler.compile_publication(self.repo,self.base,self.source,stage,root/'plan.json',False)
            self.assertEqual(plan,self.plan)
            candidate=compiler.git(stage,'rev-parse','HEAD').decode().strip()
            compiler.git(self.repo,'fetch','-q',str(stage),candidate)
            self.assertFalse(images.active(stage))
            replay=root/'replay'
            self.assertEqual(compiler.verify_candidate(self.repo,self.base,candidate,replay,root/'replay.json'),plan)
            case=SimpleNamespace(repo=self.repo,base=self.base,source=self.source)
            receipt=finalizer.finalize(self.repo,stage,plan,self.base,self.source,self.base,plan['plan_sha256'],FakeAPI(case),compiler.validate_report)
            self.assertEqual(receipt['status'],'CREATED_REVIEW_ONLY')
            # Free only this test's own verified replay before another full checkout.
            import shutil
            shutil.rmtree(replay)
            no_content=compiler.compile_publication(stage,candidate,candidate,root/'no-content',root/'empty.json',False)
            self.assertEqual(no_content['changes'],[])
            self.assertFalse(images.active(root/'no-content'))
            command=['python','-c','import sys; from pathlib import Path; sys.path.insert(0,"scripts"); import refresh_homepage_doors as home; [home.refresh(Path(p),l) for l,p in [("ar","docs/index.html"),("en","docs/en/index.html"),("fr","docs/fr/index.html")]]']
            subprocess.run(command,cwd=stage,check=True)
            self.assertFalse(compiler.git(stage,'status','--porcelain').strip())


if __name__=='__main__': unittest.main()
