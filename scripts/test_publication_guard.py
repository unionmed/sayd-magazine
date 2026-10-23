"""Trust-boundary tests; real compiler parity is tested independently."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest
from unittest.mock import patch

import publication_guard as guard


# A deliberately tiny deterministic compiler fixture. It is committed to BASE,
# checks additive data-only input and regenerates exact output. It is NOT a stub
# that blindly blesses candidate JSON or a caller-supplied receipt.
FIXTURE_COMPILER = '''import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser()
for key in ('base','verify-candidate','output','report'):p.add_argument('--'+key)
a=p.parse_args(); root=pathlib.Path(__file__).resolve().parents[1]
def git(*args,cwd=root):return subprocess.check_output(['git','-C',str(cwd),*args]).decode().strip()
assert git('rev-parse','HEAD')==a.base
source=git('show','-s','--format=%P',a.verify_candidate)
assert git('diff','--name-only',a.base,source)=='content/publications/test.json'
assert git('show',a.base+':content/homepage.json') == '{}'
subprocess.run(['git','clone','--quiet','--shared','--no-checkout',str(root),a.output],check=True)
out=pathlib.Path(a.output);git('checkout','--quiet','--detach',source,cwd=out)
data=json.loads((out/'content/publications/test.json').read_text())
(out/'docs/new.html').write_text(data['title'])
git('add','--all',cwd=out)
assert git('write-tree',cwd=out)==git('rev-parse',a.verify_candidate+'^{tree}')
git('checkout','--quiet','--detach',a.verify_candidate,cwd=out)
pathlib.Path(a.report).write_text(json.dumps({'schema':'sayd-publication-plan-v1','base_commit':a.base,'compiler_commit':a.base}))
'''


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sayd-guard-test-')
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'GITHUB_ACTIONS': 'false', 'SAYD_PUBLICATION_HEAD': ''})
        self.env.start()
        subprocess.run(['git', 'init', '--quiet', str(self.root)], check=True)
        self.git('config', 'user.name', 'Synthetic guard tests')
        self.git('config', 'user.email', 'test@example.invalid')
        self.write('scripts/publication_compiler.py', FIXTURE_COMPILER)
        self.write('content/homepage.json', '{}')
        self.write('docs/index.html', 'Historical homepage')
        self.base = self.commit('Trusted fixture compiler, not production content')
        self.write('content/publications/test.json', json.dumps({'title': 'Synthetic generated fixture', 'articles': []}))
        self.source = self.commit('Source data only')
        self.write('docs/new.html', 'Synthetic generated fixture')
        self.candidate = self.commit('Deterministic generated fixture')

    def tearDown(self):
        for proof in guard._proofs.values():
            proof.temporary.cleanup()
        guard._proofs.clear()
        self.env.stop()
        self.tmp.cleanup()

    def git(self, *args):
        return guard.git(self.root, *args).decode().strip()

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)

    def commit(self, message):
        self.git('add', '--all'); self.git('commit', '--quiet', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def test_exact_rebuild_and_process_cache_recheck(self):
        proof = guard.verified_publication(self.base, self.root)
        self.assertEqual(proof.read('docs/new.html'), 'Synthetic generated fixture')
        self.assertEqual(proof.config, {})
        self.assertIs(proof, guard.verified_publication(self.base, self.root))
        self.write('docs/new.html', 'Unapproved changed bytes')
        with self.assertRaisesRegex(AssertionError, 'Dirty'):
            guard.verified_publication(self.base, self.root)

    def test_source_only_rejected(self):
        self.git('checkout', '--quiet', '--detach', self.source)
        with self.assertRaisesRegex(AssertionError, 'recomputation'):
            guard.verified_publication(self.base, self.root)

    def test_expected_cache_tamper_rejected(self):
        proof = guard.verified_publication(self.base, self.root)
        (proof.site / 'content/homepage.json').write_text('{"bad":true}')
        with self.assertRaisesRegex(AssertionError, 'Cached expected'):
            guard.verified_publication(self.base, self.root)

    def test_generated_tamper_rejected(self):
        self.write('docs/new.html', 'Tampered output')
        self.commit('Tamper is not independently generated')
        with self.assertRaisesRegex(AssertionError, 'recomputation'):
            guard.verified_publication(self.base, self.root)

    def test_candidate_code_never_runs(self):
        self.git('checkout', '--quiet', '--detach', self.base)
        self.write('content/publications/test.json', '{"title":"x","articles":[]}')
        self.write('scripts/publication_compiler.py', 'raise RuntimeError("UNTRUSTED CODE EXECUTED")')
        self.commit('Malicious source code')
        self.write('docs/new.html', 'x'); self.commit('Fake generation')
        with self.assertRaisesRegex(AssertionError, 'recomputation') as caught:
            guard.verified_publication(self.base, self.root)
        self.assertNotIn('UNTRUSTED CODE EXECUTED', str(caught.exception))

    def test_untracked_shadow_rejected(self):
        self.write('scripts/untracked.py', 'raise RuntimeError()')
        with self.assertRaisesRegex(AssertionError, 'Untracked'):
            guard.verified_publication(self.base, self.root)

    def test_explicit_head_tree_mismatch_rejected(self):
        with patch.dict(os.environ, {'SAYD_PUBLICATION_HEAD': self.source}):
            with self.assertRaisesRegex(AssertionError, 'head tree'):
                guard.verified_publication(self.base, self.root)

    def test_merge_checkout_same_tree_allowed(self):
        merge = subprocess.check_output(['git', '-C', str(self.root), 'commit-tree', self.git('rev-parse', 'HEAD^{tree}'), '-p', self.base, '-p', self.candidate], input=b'Synthetic merge checkout\n').decode().strip()
        self.git('checkout', '--quiet', '--detach', merge)
        with patch.dict(os.environ, {'SAYD_PUBLICATION_HEAD': self.candidate}):
            self.assertEqual(guard.verified_publication(self.base, self.root).candidate, self.candidate)

    def test_baseline_only_requires_identical_all_card_data(self):
        self.assertIsNone(guard.verified_publication(self.candidate, self.root))
        proof = guard.verified_publication(self.candidate, self.root, include_baseline=True)
        self.assertEqual(proof.additions, ())
        self.write('content/homepage.json', '{"extra":"unapproved"}'); self.commit('Other change')
        with self.assertRaisesRegex(AssertionError, 'do not authorize'):
            guard.verified_publication(self.candidate, self.root, include_baseline=True)

    def test_baseline_does_not_freeze_unrelated_legacy_article_body(self):
        self.write('docs/posts/legacy/index.html', 'Separately reviewed legacy body update')
        self.commit('Legacy-only article edit does not change home placement')
        proof = guard.verified_publication(self.candidate, self.root, include_baseline=True)
        self.assertEqual(proof.read('docs/index.html'), 'Historical homepage')

    def test_ci_requires_exact_repository_main_and_head(self):
        event = {'pull_request': {'base': {'sha': self.base, 'ref': 'main', 'repo': {'full_name': 'unionmed/sayd-magazine'}}, 'head': {'sha': self.candidate}}}
        path = self.root / 'event.json'; path.write_text(json.dumps(event))
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_REPOSITORY': 'unionmed/sayd-magazine', 'GITHUB_EVENT_PATH': str(path)}
        with patch.dict(os.environ, env):
            guard.check_context(self.base, self.candidate)
            for key, bad in [('ref', 'untrusted'), ('sha', self.source)]:
                changed = json.loads(json.dumps(event)); changed['pull_request']['base'][key] = bad
                path.write_text(json.dumps(changed))
                with self.assertRaises(AssertionError): guard.check_context(self.base, self.candidate)
            path.write_text(json.dumps(event))
            with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'other/repository'}):
                with self.assertRaises(AssertionError): guard.check_context(self.base, self.candidate)

    def test_exact_new_archive_cards_preserve_old_negative_guards(self):
        import test_combined_archive_navigation as tests
        def row(slug, day, title):
            return '<article class="post-row"><h2><a href="../../posts/'+slug+'/index.html">'+title+'</a></h2><div class="meta">'+str(day)+' October 2026</div></article>'
        old, new = row('old', 20, 'Historical title'), row('new', 23, 'Compiled title')
        with patch.object(tests.archive, 'marine_registry', return_value={}):
            tests.assert_archive_card_rows([new, old], [old], {}, {}, 'en', {'new': new})
            for rows in ([new, new, old], [old], [new], [new, old.replace('Historical title', 'Changed')],
                         [new.replace('Compiled title', 'Changed'), old], [old, new], [new, old, row('extra', 19, 'Extra')]):
                with self.assertRaises(AssertionError):
                    tests.assert_archive_card_rows(rows, [old], {}, {}, 'en', {'new': new})

    def test_exact_workflow_bootstrap_only_allows_reviewed_catalog_code(self):
        workflow = (guard.ROOT / '.github/workflows/source-publication.yml').read_text()
        self.assertIn("['git', 'diff', '--no-renames', '--name-only', '-z', base, head]", workflow)
        block = '          def bootstrap_paths_safe(paths):\n' + workflow.split('          def bootstrap_paths_safe(paths):\n', 1)[1].split('          base = ', 1)[0]
        scope = {}; exec(textwrap.dedent(block), scope)
        allowed = scope['bootstrap_paths_safe']
        self.assertTrue(allowed(['scripts/publication_compiler.py', '.github/workflows/source-publication.yml',
                                 'audit/image-catalog/link_historical_articles.py', 'audit/image-catalog/test_link_historical_articles.py']))
        for path in ['content/en/pairs.json', 'content/publications/new.json', 'docs/media/publications/x/a.png',
                     'docs/index.html', 'audit/image-catalog/manifest/x.tsv', 'audit/image-catalog/article-image-links.json',
                     'audit/image-catalog/other.py']:
            self.assertFalse(allowed([path]), path)

    def test_infrastructure_proof_requires_unchanged_entire_payload(self):
        base = self.candidate
        self.write('scripts/infrastructure.py', '# Infrastructure only\n'); self.commit('Code only')
        self.assertTrue(guard.unchanged_current_payload(base, self.root))
        self.write('docs/posts/other/index.html', 'Changed article despite unchanged homepage')
        self.commit('Unapproved payload')
        self.assertFalse(guard.unchanged_current_payload(base, self.root))

    def test_infrastructure_proof_rejects_catalog_data_deletion_and_modes(self):
        for change in ('catalog', 'delete', 'mode', 'rename_out'):
            with self.subTest(change=change):
                self.git('checkout', '--quiet', '--detach', self.candidate)
                if change == 'catalog': self.write('audit/image-catalog/provenance.json', '{}')
                elif change == 'delete': (self.root/'docs/new.html').unlink()
                elif change == 'rename_out':
                    (self.root/'notes').mkdir(exist_ok=True)
                    (self.root/'docs/new.html').rename(self.root/'notes/renamed.html')
                else: (self.root/'docs/new.html').chmod(0o755)
                self.commit('Payload '+change)
                self.assertFalse(guard.unchanged_current_payload(self.candidate, self.root))

    def test_infrastructure_proof_rejects_head_baseline_nonancestor_and_dirty(self):
        with self.assertRaisesRegex(AssertionError, 'substitute current HEAD'):
            guard.unchanged_current_payload(self.candidate, self.root)
        self.write('scripts/infrastructure.py', '# Infrastructure only\n'); self.commit('Code only')
        sibling = subprocess.check_output(['git', '-C', str(self.root), 'commit-tree', self.git('rev-parse', self.base+'^{tree}'), '-p', self.base], input=b'Unrelated sibling\n').decode().strip()
        with self.assertRaisesRegex(AssertionError, 'not an ancestor'):
            guard.unchanged_current_payload(sibling, self.root)
        with self.assertRaisesRegex(AssertionError, 'Exact infrastructure PR base'):
            guard.unchanged_current_payload('HEAD', self.root)
        self.write('scripts/infrastructure.py', '# Dirty infrastructure\n')
        with self.assertRaisesRegex(AssertionError, 'Dirty'):
            guard.unchanged_current_payload(self.candidate, self.root)

    def test_infrastructure_proof_binds_actual_pr_context_and_head(self):
        base = self.candidate
        self.write('scripts/infrastructure.py', '# Infrastructure only\n'); head = self.commit('Code only')
        event = {'pull_request': {'base': {'sha': base, 'ref': 'main', 'repo': {'full_name': 'unionmed/sayd-magazine'}}, 'head': {'sha': head}}}
        path = self.root/'event.json'; path.write_text(json.dumps(event))
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_REPOSITORY': 'unionmed/sayd-magazine', 'GITHUB_EVENT_PATH': str(path), 'SAYD_PUBLICATION_HEAD': head}
        with patch.dict(os.environ, env):
            self.assertTrue(guard.unchanged_current_payload(base, self.root))
            with self.assertRaisesRegex(AssertionError, 'current PR event'):
                guard.unchanged_current_payload(self.base, self.root)
            with patch.dict(os.environ, {'SAYD_PUBLICATION_HEAD': self.source}):
                with self.assertRaisesRegex(AssertionError, 'current PR event'):
                    guard.unchanged_current_payload(base, self.root)
            event['pull_request']['base']['ref'] = 'untrusted'; path.write_text(json.dumps(event))
            with self.assertRaisesRegex(AssertionError, 'trusted repository main'):
                guard.unchanged_current_payload(base, self.root)


if __name__ == '__main__':
    unittest.main()
