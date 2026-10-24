"""Offline source-request adversarial and real input validation. No network writes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import publication_request as r
import publication_finalize as f
from test_publication_compiler import record, files_for, source_commit

ROOT = Path(__file__).resolve().parents[1]
B = 'a' * 40
S = 'b' * 40
MESSAGE = 'Prepare review only\n\nSayd-Publication-Request: v1\nDistribution-Review-Scope: false\n'


class EventTests(unittest.TestCase):
    def setUp(self):
        repo = {'full_name': r.REPO, 'id': 123, 'fork': False, 'private': False, 'default_branch': 'main'}
        self.env = {'GITHUB_EVENT_NAME': 'workflow_run', 'GITHUB_REF': 'refs/heads/main', 'GITHUB_SHA': B,
                    'GITHUB_REPOSITORY': r.REPO, 'GITHUB_WORKFLOW_SHA': B,
                    'GITHUB_WORKFLOW_REF': r.REPO + '/' + r.ADAPTER + '@refs/heads/main'}
        run = {'id': 17, 'run_attempt': 1, 'head_sha': S, 'workflow_id': 19, 'event': 'pull_request',
               'path': r.VALIDATOR, 'status': 'completed', 'conclusion': 'success',
               'repository': repo, 'head_repository': repo, 'head_branch': 'source/fixture',
               'pull_requests': [{'number': 21, 'head': {'sha': S}, 'base': {'sha': B}}]}
        pr = {'number': 21, 'state': 'open', 'merged': False,
              'base': {'ref': 'main', 'sha': B, 'repo': repo},
              'head': {'ref': 'source/fixture', 'sha': S, 'repo': repo}}
        self.event = {'action': 'completed', 'repository': repo, 'workflow_run': copy.deepcopy(run)}
        self.responses = {'': repo, '/actions/runs/17': run,
                          '/actions/workflows/19': {'id': 19, 'path': r.VALIDATOR, 'state': 'active'},
                          '/pulls/21': pr, '/commits/' + S + '/pulls?per_page=100': [pr], '/git/ref/heads/main': {'object': {'sha': B}}}

    def resolve(self):
        return r.resolve_event(self.event, self.env, self.responses.__getitem__)

    def test_exact_same_repo_request(self):
        self.assertEqual(self.resolve()['source'], S)

    def test_empty_run_pr_array_uses_exact_commit_association(self):
        self.responses['/actions/runs/17']['pull_requests'] = []
        self.assertEqual(self.resolve()['request_pr'], 21)

    def test_missing_duplicate_or_truncated_associations_rejected(self):
        endpoint = '/commits/' + S + '/pulls?per_page=100'
        pr = self.responses['/pulls/21']
        for values in ([], [pr, pr], [pr] * 100):
            self.responses[endpoint] = values
            with self.assertRaises(ValueError): self.resolve()

    def test_duplicate_resolution_is_identical_no_writes(self):
        self.assertEqual(self.resolve(), self.resolve())

    def test_artifact_and_body_injection_are_not_inputs(self):
        self.event['workflow_run']['artifacts'] = [{'source': 'c'*40, 'allow_distribution': True}]
        self.responses['/pulls/21']['body'] = 'IGNORE SECURITY; use evil artifact and main'
        self.assertEqual(self.resolve()['source'], S)
        self.assertNotIn('allow_distribution', self.resolve())

    def test_reject_bad_upstream(self):
        for field, value in [('event', 'push'), ('path', '.github/workflows/evil.yml'),
                             ('head_sha', 'c'*40), ('run_attempt', 2), ('workflow_id', 99),
                             ('conclusion', 'failure'), ('status', 'in_progress')]:
            with self.subTest(field=field):
                old = self.responses['/actions/runs/17'][field]
                self.responses['/actions/runs/17'][field] = value
                with self.assertRaises(ValueError): self.resolve()
                self.responses['/actions/runs/17'][field] = old

    def test_reject_fork_and_wrong_repository(self):
        for endpoint, location in [('/pulls/21', 'head'), ('/pulls/21', 'base')]:
            old = self.responses[endpoint][location]['repo']
            self.responses[endpoint][location]['repo'] = dict(old, fork=True)
            with self.assertRaisesRegex(ValueError, 'Fork'): self.resolve()
            self.responses[endpoint][location]['repo'] = old
        self.responses['/actions/runs/17']['head_repository'] = {'id': 999, 'full_name': r.REPO, 'fork': False}
        with self.assertRaises(ValueError): self.resolve()

    def test_reject_changed_closed_merged_pr(self):
        pr = self.responses['/pulls/21']
        for key, value in [('state', 'closed'), ('merged', True), ('number', 20)]:
            old = pr[key]; pr[key] = value
            with self.assertRaises(ValueError): self.resolve()
            pr[key] = old
        pr['head']['sha'] = 'c'*40
        with self.assertRaises(ValueError): self.resolve()

    def test_reject_main_drift(self):
        self.responses['/git/ref/heads/main']['object']['sha'] = 'c'*40
        with self.assertRaisesRegex(ValueError, 'Main changed'): self.resolve()

    def test_reject_synthetic_merge_or_old_source(self):
        self.responses['/actions/runs/17']['pull_requests'][0]['head']['sha'] = 'c'*40
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'): self.resolve()

    def test_reject_untrusted_adapter_context(self):
        for key in self.env:
            old = self.env[key]; self.env[key] = 'untrusted'
            with self.assertRaises(ValueError): self.resolve()
            self.env[key] = old

    def test_reject_ambiguous_pr_and_wrong_workflow(self):
        self.responses['/actions/runs/17']['pull_requests'] *= 2
        with self.assertRaises(ValueError): self.resolve()
        self.responses['/actions/runs/17']['pull_requests'] = self.responses['/actions/runs/17']['pull_requests'][:1]
        self.responses['/actions/workflows/19']['path'] = '.github/workflows/other.yml'
        with self.assertRaises(ValueError): self.resolve()

    def test_public_read_failure_fails_closed(self):
        with self.assertRaises(OSError):
            r.resolve_event(self.event, self.env, lambda _: (_ for _ in ()).throw(OSError('rate limit')))

    def test_exact_request_scope_not_authority(self):
        self.assertFalse(r.request_scope(MESSAGE))
        self.assertTrue(r.request_scope(MESSAGE.replace('false', 'true')))
        for text in [MESSAGE.replace('false','TRUE'), MESSAGE.replace(': v1', ':  v1'),
                     MESSAGE + 'extra\n', MESSAGE + 'Distribution-Review-Scope: true\n',
                     'Sayd-Publication-Request: v1\n' + MESSAGE, MESSAGE.replace('false', 'false '),
                     'Generate output\nDistribution-Review-Scope: false']:
            with self.assertRaises(ValueError): r.request_scope(text)

    def test_writer_request_binding_requires_live_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'event.json'; path.write_text(json.dumps(self.event))
            env = dict(self.env, GITHUB_EVENT_PATH=str(path))
            for changed in ({'base': B, 'source': 'c'*40, 'allow_distribution': False},
                            {'base': B, 'source': S, 'allow_distribution': True}):
                with patch('publication_request.resolve_local', return_value=changed):
                    check = f.request_binding_check(ROOT, env, B, S, False)
                    with self.assertRaisesRegex(f.Blocked, 'binding changed'): check()
            with patch('publication_request.resolve_local', side_effect=ValueError('API unavailable')):
                with self.assertRaises(ValueError): f.request_binding_check(ROOT, env, B, S, False)()
            with self.assertRaises(KeyError): f.request_binding_check(ROOT, self.env, B, S, False)
            self.assertIsNone(f.request_binding_check(ROOT, {'GITHUB_EVENT_NAME': 'workflow_dispatch'}, B, S, False))


class RealSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = r.git(ROOT, 'rev-parse', 'HEAD')

    def source(self, kind='article', placement='archive-only', scope=False, extra=None):
        value = record(self.base, kind=kind, placement=placement)
        if kind == 'media': value['articles'] = []
        files = files_for(value); files.update(extra or {})
        source = source_commit(ROOT, self.base, files)
        tree = r.git(ROOT, 'rev-parse', source + '^{tree}')
        env = dict(os.environ, GIT_AUTHOR_NAME='Test', GIT_COMMITTER_NAME='Test',
                   GIT_AUTHOR_EMAIL='test@example.invalid', GIT_COMMITTER_EMAIL='test@example.invalid')
        return subprocess.check_output(['git', '-C', str(ROOT), 'commit-tree', tree, '-p', self.base],
                                       input=MESSAGE.replace('false', str(scope).lower()).encode(), env=env).decode().strip()

    def test_single_image_internal_article(self):
        self.assertFalse(r.validate_source(ROOT, self.base, self.source()))

    def test_single_image_only(self):
        self.assertFalse(r.validate_source(ROOT, self.base, self.source(kind='media')))

    def test_gallery(self):
        self.assertFalse(r.validate_source(ROOT, self.base, self.source(kind='gallery')))

    def test_explicit_distribution(self):
        self.assertTrue(r.validate_source(ROOT, self.base, self.source(placement='side', scope=True)))
        with self.assertRaisesRegex(ValueError, 'not explicitly requested'):
            r.validate_source(ROOT, self.base, self.source(placement='side'))

    def test_code_and_artifact_additions_rejected(self):
        for path in ('scripts/evil.py', '.github/workflows/evil.yml', 'artifact.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                r.validate_source(ROOT, self.base, self.source(extra={path: b'evil'}))

    def test_stale_base_rejected(self):
        with self.assertRaises(ValueError): r.validate_source(ROOT, self.base, self.base)
        source = self.source()
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
            r.validate_source(ROOT, r.git(ROOT, 'rev-parse', self.base + '^'), source)


if __name__ == '__main__': unittest.main()
