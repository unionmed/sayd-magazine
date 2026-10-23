"""Trust-boundary tests; real compiler parity is tested independently."""
import ast
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



import copy
import shutil
from types import SimpleNamespace
import test_header_social as header_counts


class SourceHeaderCounts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sayd-header-count-')
        self.addCleanup(self.temp.cleanup)
        self.site, self.root = (Path(self.temp.name) / name for name in ('expected', 'current'))
        self.record = {'articles': [{'slugs': {lang: 'fixture-' + lang for lang in ('ar', 'en', 'fr')}}]}
        self.links = {}
        nav = '<nav class="header-social"><a href="https://example.test">Social</a></nav>'
        for n, lang in enumerate(('ar', 'en', 'fr')):
            route = '/' + ('' if lang == 'ar' else lang + '/') + 'posts/fixture-' + lang + '/'
            alias = '/s/' + str(n) * 10 + '/'
            self.links[route] = alias
            head = '<head><link rel="canonical" href="https://sayd-magazine.com' + route + '"></head>'
            self.write(self.site, 'docs' + route + 'index.html', head + '<body>' + nav + 'Article</body>')
            self.write(self.site, 'docs' + alias + 'index.html', head + '<body>Redirect shell</body>')
        self.write(self.site, 'docs/s/links.json', json.dumps(self.links))
        self.write(self.site, 'content/publications/test.json', json.dumps(self.record))
        shutil.copytree(self.site, self.root)
        self.proof = SimpleNamespace(site=self.site, read=lambda name: (self.site / name).read_text())
        self.rel = 'docs/posts/fixture-ar/index.html'

    def write(self, root, path, content):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)

    def mutate(self, rel, change):
        file = self.root / rel
        file.write_text(change(file.read_text()))

    def test_exact_three_language_pairs_counted(self):
        self.assertEqual(header_counts.check_source_publication_pairs(self.proof, self.root), 3)

    def test_wrapper_requires_trusted_base_proof(self):
        with patch('publication_guard.verified_publication', return_value=self.proof) as verify:
            self.assertEqual(header_counts.source_publication_header_count('trusted-base', self.root), 3)
            verify.assert_called_once_with('trusted-base', self.root, include_baseline=True)
        with patch('publication_guard.verified_publication', return_value=None):
            self.assertEqual(header_counts.source_publication_header_count('trusted-base', self.root), 0)
        with patch('publication_guard.verified_publication', side_effect=AssertionError('unproved')):
            with self.assertRaisesRegex(AssertionError, 'unproved'):
                header_counts.source_publication_header_count('trusted-base', self.root)

    def test_missing_or_duplicate_article_header_rejected(self):
        original = (self.root / self.rel).read_text()
        for replacement in (original.replace('header-social', 'not-social'), original + '<nav class="header-social"></nav>'):
            self.write(self.root, self.rel, replacement)
            with self.assertRaises(AssertionError): header_counts.check_source_publication_pairs(self.proof, self.root)
        self.write(self.root, self.rel, original)

    def test_changed_or_duplicate_social_icon_rejected(self):
        original = (self.root / self.rel).read_text()
        for replacement in (original.replace('https://example.test', 'https://wrong.test'), original.replace('</nav>', '<a>Duplicate icon</a></nav>')):
            self.write(self.root, self.rel, replacement)
            with self.assertRaisesRegex(AssertionError, 'social markup'):
                header_counts.check_source_publication_pairs(self.proof, self.root)

    def test_wrong_article_canonical_rejected(self):
        self.mutate(self.rel, lambda value: value.replace('https://sayd-magazine.com/posts/', 'https://sayd-magazine.com/wrong/'))
        with self.assertRaises(AssertionError): header_counts.check_source_publication_pairs(self.proof, self.root)

    def test_missing_article_or_shell_rejected(self):
        for rel in (self.rel, 'docs/s/0000000000/index.html'):
            path = self.root / rel; original = path.read_bytes(); path.unlink()
            with self.assertRaises(FileNotFoundError): header_counts.check_source_publication_pairs(self.proof, self.root)
            path.write_bytes(original)

    def test_changed_alias_rejected(self):
        links = dict(self.links); links['/posts/fixture-ar/'] = '/s/9999999999/'
        self.write(self.root, 'docs/s/links.json', json.dumps(links))
        with self.assertRaisesRegex(AssertionError, 'mapping changed'):
            header_counts.check_source_publication_pairs(self.proof, self.root)

    def test_changed_or_headered_shell_rejected(self):
        rel = 'docs/s/0000000000/index.html'; original = (self.root / rel).read_text()
        for replacement in (original.replace('fixture-ar', 'wrong-target'), original + '<nav class="header-social"></nav>'):
            self.write(self.root, rel, replacement)
            with self.assertRaisesRegex(AssertionError, 'shell changed'):
                header_counts.check_source_publication_pairs(self.proof, self.root)

    def test_redirect_shell_line_endings_are_byte_preserved(self):
        rel = 'docs/s/0000000000/index.html'
        original = (self.root / rel).read_bytes().replace(b'</head>', b'</head>\n')
        for root in (self.site, self.root):
            (root / rel).write_bytes(original)
        self.assertEqual(header_counts.check_source_publication_pairs(self.proof, self.root), 3)
        (self.root / rel).write_bytes(original.replace(b'\n', b'\r\n'))
        with self.assertRaisesRegex(AssertionError, 'shell changed'):
            header_counts.check_source_publication_pairs(self.proof, self.root)

    def test_duplicate_source_route_rejected(self):
        data = copy.deepcopy(self.record); data['articles'] *= 2
        self.write(self.site, 'content/publications/test.json', json.dumps(data))
        with self.assertRaisesRegex(AssertionError, 'Duplicate source'):
            header_counts.check_source_publication_pairs(self.proof, self.root)

    def test_two_articles_cannot_share_redirect_shell(self):
        links = dict(self.links)
        links['/en/posts/fixture-en/'] = links['/posts/fixture-ar/']
        for root in (self.site, self.root):
            self.write(root, 'docs/s/links.json', json.dumps(links))
        with self.assertRaisesRegex(AssertionError, 'share a short-link'):
            header_counts.check_source_publication_pairs(self.proof, self.root)

    def test_unproved_candidate_record_does_not_increase_count(self):
        self.write(self.root, 'content/publications/unproved.json', json.dumps(self.record))
        self.assertEqual(header_counts.check_source_publication_pairs(self.proof, self.root), 3)

    def test_media_only_source_adds_no_headers(self):
        self.write(self.site, 'content/publications/test.json', '{"articles":[]}')
        self.assertEqual(header_counts.check_source_publication_pairs(self.proof, self.root), 0)



class BrowserImageWaitTests(unittest.TestCase):
    """Exercise the exact browser helper without launching a local browser."""
    @classmethod
    def setUpClass(cls):
        source = (Path(__file__).with_name('test_merged_section_browser.py')).read_text()
        module = ast.parse(source)
        helper = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'decode_visible_image')
        namespace = {}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), '<reviewed-image-helper>', 'exec'), namespace)
        cls.helper = staticmethod(namespace['decode_visible_image'])
        cls.source = source

    def expression(self):
        calls = []
        class Image:
            def scroll_into_view_if_needed(self, **kwargs):
                calls.append(('scroll', kwargs))
            def evaluate(self, expression, **kwargs):
                calls.append(('decode', kwargs, expression))
        self.helper(Image())
        self.assertEqual([c[0] for c in calls], ['scroll', 'decode'])
        self.assertEqual(calls[0][1], {'timeout': 10000})
        self.assertEqual(calls[1][1], {'timeout': 10000})
        return calls[1][2]

    def test_lazy_images_are_scrolled_before_bounded_decode(self):
        self.expression()
        self.assertEqual(self.source.count('decode_visible_image(image)'), 3)  # definition + both loops
        self.assertIn("image.evaluate('img=>img.complete&&img.naturalWidth>0')", self.source)
        self.assertIn('page.screenshot(path=str(path), full_page=True)', self.source)
        self.assertLess(self.source.index("page.evaluate('scrollTo(0,0)')"),
                        self.source.index('page.screenshot(path=str(path), full_page=True)'))

    def test_missing_image_scroll_failure_is_not_swallowed(self):
        class MissingImage:
            def scroll_into_view_if_needed(self, **kwargs):
                raise RuntimeError('missing image')
            def evaluate(self, *args, **kwargs):
                raise AssertionError('decode must not follow failed scroll')
        with self.assertRaisesRegex(RuntimeError, 'missing image'):
            self.helper(MissingImage())

    def run_decode(self, behavior):
        # Execute the exact production JS promise, accelerating only the test's
        # timer clock. Record the requested10-second deadline and cleanup.
        script = r'''
const assert = require('node:assert/strict');
const realSetTimeout = global.setTimeout, realClearTimeout = global.clearTimeout;
let deadline = null, cleared = 0;
global.setTimeout = (fn, delay) => { deadline = delay; return realSetTimeout(fn, 1); };
global.clearTimeout = timer => { cleared++; realClearTimeout(timer); };
const decodeVisible = EXPRESSION;
const image = {src: '/local/image.jpg', currentSrc: '', decode: () => BEHAVIOR};
(async () => {
  let error = null;
  try { await decodeVisible(image); } catch (e) { error = e.message; }
  assert.equal(deadline, 10000); assert.equal(cleared, 1);
  process.stdout.write(JSON.stringify({error}));
})().catch(e => { console.error(e); process.exitCode = 1; });
'''.replace('EXPRESSION', self.expression()).replace('BEHAVIOR', behavior)
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=5, check=True)
        return json.loads(result.stdout)['error']

    def test_successful_decode_clears_deadline(self):
        self.assertIsNone(self.run_decode('Promise.resolve()'))

    def test_broken_image_decode_rejection_is_not_swallowed(self):
        self.assertEqual(self.run_decode("Promise.reject(new Error('broken image'))"), 'broken image')

    def test_never_resolving_decode_rejects_at_deadline(self):
        self.assertEqual(self.run_decode('new Promise(() => {})'), 'Image decode timed out: /local/image.jpg')


if __name__ == '__main__':
    unittest.main()
