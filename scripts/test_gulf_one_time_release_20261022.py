"""Offline fail-closed tests; never contact GitHub or production."""
from copy import deepcopy
from datetime import timedelta
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import gulf_one_time_release_20261022 as r

SHA = 'a' * 40
PR = 999


def pull():
    return {'number': PR, 'head': {'sha': SHA, 'ref': r.CONTENT_BRANCH, 'repo': {'full_name': r.REPO}},
            'base': {'sha':r.BASE, 'ref': 'main', 'repo': {'full_name': r.REPO}}, 'state': 'open', 'draft': False,
            'merged': False, 'mergeable': True, 'mergeable_state': 'clean'}


def run(path='.github/workflows/publication-contract.yml', ident=1):
    return {'id': ident, 'head_sha': SHA, 'event': 'pull_request', 'path': path,
            'pull_requests': [{'number': PR}], 'status': 'completed', 'conclusion': 'success',
            'run_started_at': '2026-10-22T01:15:00Z', 'run_attempt': 2}


class ReleaseGuards(unittest.TestCase):
    def test_fixed_boundaries(self):
        for when in [r.PREFLIGHT, r.START, r.DEADLINE]:
            r.release_window(when)
        for when in [r.PREFLIGHT - timedelta(seconds=1), r.DEADLINE + timedelta(seconds=1),
                     r.START.replace(year=2027), r.START - timedelta(days=1)]:
            with self.assertRaises(r.Blocked):
                r.release_window(when)
        with self.assertRaisesRegex(r.Blocked, 'Early'):
            r.release_window(r.START - timedelta(microseconds=1), for_merge=True)
        r.release_window(r.START, for_merge=True)

    def test_exact_pr_identity(self):
        r.valid_pr(pull(), PR, SHA, r.CONTENT_BRANCH)
        mutations = [('number', PR+1), ('draft', True), ('state', 'closed')]
        for field, value in mutations:
            p = pull(); p[field] = value
            with self.assertRaises(r.Blocked):
                r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH)
        for field, value in [('sha', 'b'*40), ('ref', 'main')]:
            p = pull(); p['head'][field] = value
            with self.assertRaises(r.Blocked):
                r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH)
        for side in ['head', 'base']:
            p = pull(); p[side]['repo']['full_name'] = 'attacker/sayd-magazine'
            with self.assertRaises(r.Blocked):
                r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH)
        p = pull(); p['base']['ref'] = 'other'
        with self.assertRaises(r.Blocked):
            r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH)

    def test_merged_elsewhere_is_idempotent_only_for_approved_head_after_time(self):
        p = pull(); p.update(merged=True, state='closed', merged_at=r.START.isoformat(), merge_commit_sha='c'*40)
        r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH, allow_merged=True)
        with self.assertRaises(r.Blocked):
            r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH)
        p['head']['sha'] = 'b'*40
        with self.assertRaises(r.Blocked):
            r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH, allow_merged=True)
        p['head']['sha'] = SHA; p['merged_at'] = (r.START - timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(r.Blocked, 'before'):
            r.valid_pr(p, PR, SHA, r.CONTENT_BRANCH, allow_merged=True)

    def test_checks_must_all_be_successful_and_real_date(self):
        r.validate_completed_runs({'x':run()}, r.CI_AFTER)
        for field, value in [('status', 'in_progress'), ('conclusion', 'failure'), ('conclusion', 'skipped'),
                             ('conclusion', 'cancelled'), ('run_started_at', '2026-10-21T20:59:59Z')]:
            check = run(); check[field] = value
            with self.assertRaises(r.Blocked):
                r.validate_completed_runs({'x':check}, r.CI_AFTER)

    def test_latest_run_failure_is_not_masked_by_old_success(self):
        old = run(ident=1); latest = run(ident=2); latest['conclusion'] = 'failure'
        with patch.object(r, 'api', return_value={'total_count':2, 'workflow_runs':[latest, old]}):
            checks = r.normal_runs(PR, SHA, {old['path']})
        self.assertEqual(checks[old['path']]['id'], 2)
        with self.assertRaises(r.Blocked):
            r.validate_completed_runs(checks)

    def test_missing_check_wrong_pr_and_wrong_sha_fail_closed(self):
        with patch.object(r, 'api', return_value={'total_count':0, 'workflow_runs':[]}):
            with self.assertRaisesRegex(r.Blocked, 'Missing'):
                r.normal_runs(PR, SHA, r.CORE_CI)
        for key, value in [('pull_requests', []), ('head_sha', 'b'*40), ('event', 'push')]:
            check = run(); check[key] = value
            with patch.object(r, 'api', return_value={'total_count':1, 'workflow_runs':[check]}):
                with self.assertRaises(r.Blocked):
                    r.normal_runs(PR, SHA, {check['path']})

    def test_merge_carries_expected_sha_without_bypass(self):
        with patch.object(r, 'api', side_effect=[pull(), {'merged':True, 'sha':'c'*40}, {'parents':[{'sha':r.BASE},{'sha':SHA}]}]) as api, \
             patch.object(r, 'record'), patch.object(r, 'now', return_value=r.START):
            self.assertEqual(r.protected_merge(PR, SHA, r.CONTENT_BRANCH, r.BASE, release=True), 'c'*40)
        self.assertEqual(api.call_args_list[1].args, ('/pulls/999/merge', 'PUT', {'sha':SHA, 'merge_method':'merge'}))

    def test_early_merge_never_writes(self):
        with patch.object(r, 'api', return_value=pull()) as api, \
             patch.object(r, 'now', return_value=r.START-timedelta(seconds=1)):
            with self.assertRaisesRegex(r.Blocked, 'Early'):
                r.protected_merge(PR, SHA, r.CONTENT_BRANCH, r.BASE, release=True)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(api.call_args.args, ('/pulls/999',))

    def test_protection_block_never_writes(self):
        for state in ['blocked', 'behind', 'dirty', 'draft', 'unknown']:
            p = pull(); p['mergeable_state'] = state
            with patch.object(r, 'api', return_value=p) as api:
                with self.assertRaises(r.Blocked):
                    r.protected_merge(PR, SHA, r.CONTENT_BRANCH, r.BASE)
            self.assertEqual(api.call_count, 1)

    def test_permission_denial_never_retries_or_bypasses(self):
        with patch.object(r, 'api', side_effect=[pull(), r.Blocked('HTTP 403')]) as api:
            with self.assertRaisesRegex(r.Blocked, '403'):
                r.protected_merge(PR, SHA, r.CONTENT_BRANCH, r.BASE)
        self.assertEqual(api.call_count, 2)
        with patch.object(r, 'api', side_effect=[{'commit':'old', 'status':'built'}, r.Blocked('HTTP 403')]) as api:
            with self.assertRaisesRegex(r.Blocked, '403'):
                r.pages_build(SHA)
        self.assertEqual(api.call_count, 2)

    def test_uncertain_merge_reads_back_without_second_write(self):
        p = pull(); p.update(merged=True, merge_commit_sha='c'*40)
        with patch.object(r, 'api', side_effect=[pull(), OSError('response lost'), p, {'parents':[{'sha':r.BASE},{'sha':SHA}]}]) as api, patch.object(r, 'record'):
            self.assertEqual(r.protected_merge(PR, SHA, r.CONTENT_BRANCH, r.BASE), 'c'*40)
        self.assertEqual([c.args[1] for c in api.call_args_list if len(c.args)>1], ['PUT'])

    def test_successful_exact_pages_build_is_reused(self):
        with patch.object(r, 'api', return_value={'commit':SHA, 'status':'built'}) as api, patch.object(r, 'record'):
            r.pages_build(SHA)
        self.assertEqual(api.call_count, 1)

    def test_unrelated_site_drift_cannot_be_overwritten(self):
        with patch.object(r, 'git', side_effect=[r.BASE, 'docs/index.html']):
            with self.assertRaisesRegex(r.Blocked, 'Intervening'):
                r.unchanged_site_base(SHA)
        with patch.object(r, 'git', side_effect=[r.BASE, r.WORKFLOW, 'tree', 'tree']):
            r.unchanged_site_base(SHA)

    def test_no_arbitrary_release_entrypoint(self):
        for event, ref in [('workflow_dispatch','refs/heads/main'), ('schedule','refs/heads/other')]:
            with patch.dict(os.environ, GITHUB_EVENT_NAME=event, GITHUB_REF=ref), patch.object(r, 'api') as api:
                with self.assertRaises(r.Blocked):
                    r.release()
            api.assert_not_called()

    def test_install_not_allowed_on_release_day(self):
        with patch.object(r, 'now', return_value=r.START), patch.object(r, 'api') as api:
            with self.assertRaisesRegex(r.Blocked, 'Installation authorized'):
                r.install({})
        api.assert_not_called()

    def test_rerun_is_exact_head_once_and_waits_for_new_attempt(self):
        stale = run(); stale['run_started_at'] = '2026-10-21T10:00:00Z'; stale['run_attempt'] = 1
        fresh = run()
        key = stale['path']
        with patch.object(r, 'normal_runs', side_effect=[{key:stale}, {key:stale}, {key:fresh}]), \
             patch.object(r, 'api', side_effect=[{}, {'jobs':[{'name':'Three-mirror publication check', 'conclusion':'success'}]}]) as api, \
             patch.object(r, 'record'), patch.object(r.time, 'sleep'):
            r.wait_ci(PR, SHA, {key}, fresh_after=r.CI_AFTER)
        self.assertEqual(api.call_args_list[0].args, ('/actions/runs/1/rerun', 'POST'))
        self.assertEqual(api.call_count, 2)

    def test_fresh_failed_ci_is_never_rerun_into_success(self):
        failed = run(); failed['conclusion'] = 'failure'
        with patch.object(r, 'normal_runs', return_value={failed['path']:failed}), patch.object(r, 'api') as api:
            with self.assertRaisesRegex(r.Blocked, 'Real-date CI failed'):
                r.wait_ci(PR, SHA, {failed['path']}, fresh_after=r.CI_AFTER)
        api.assert_not_called()

    def test_base_race_blocks_before_write(self):
        p = pull(); p['base']['sha'] = 'b'*40
        with patch.object(r, 'api', return_value=p) as api:
            with self.assertRaisesRegex(r.Blocked, 'Base SHA changed'):
                r.protected_merge(PR, SHA, r.CONTENT_BRANCH, r.BASE)
        self.assertEqual(api.call_count, 1)

    def test_merge_race_is_detected_before_any_pages_request(self):
        responses = [pull(), {'merged':True, 'sha':'c'*40}, {'parents':[{'sha':'b'*40},{'sha':SHA}]}]
        with patch.object(r, 'api', side_effect=responses) as api:
            with self.assertRaisesRegex(r.Blocked, 'Merged parents differ'):
                r.protected_merge(PR, SHA, r.CONTENT_BRANCH, r.BASE)
        self.assertFalse(any('/pages' in c.args[0] for c in api.call_args_list))

    def test_pages_same_second_timestamp_is_accepted(self):
        instant = r.START.replace(microsecond=123456)
        responses = [{'commit':'old', 'status':'built'}, {'status':'queued'},
                     {'commit':SHA, 'status':'built', 'created_at':r.START.isoformat()}]
        with patch.object(r, 'now', return_value=instant), patch.object(r, 'api', side_effect=responses) as api, \
             patch.object(r, 'record'), patch.object(r.time, 'sleep'):
            r.pages_build(SHA)
        self.assertEqual(api.call_count, 3)

    def test_duplicate_merged_content_still_checks_original_base(self):
        with patch.object(r, 'CONTENT_SHA', SHA), \
             patch.object(r, 'api', return_value={'parents':[{'sha':'bad-base'}, {'sha':SHA}]}), \
             patch.object(r, 'git', side_effect=['', 'c'*40]), \
             patch.object(r, 'unchanged_site_base', side_effect=r.Blocked('Intervening content changed')) as base:
            with self.assertRaisesRegex(r.Blocked, 'Intervening'):
                r.verify_content_merge('c'*40)
        base.assert_called_once_with('bad-base')

    def test_duplicate_wrong_head_never_reaches_pages(self):
        with patch.object(r, 'CONTENT_SHA', SHA), \
             patch.object(r, 'api', return_value={'parents':[{'sha':r.BASE}, {'sha':'b'*40}]}), \
             patch.object(r, 'git') as git:
            with self.assertRaisesRegex(r.Blocked, 'pinned head'):
                r.verify_content_merge('c'*40)
        git.assert_not_called()

    def test_workflow_has_no_external_inputs_or_cancel(self):
        raw = (Path(__file__).resolve().parents[1] / r.WORKFLOW).read_text()
        self.assertNotIn('workflow_dispatch', raw)
        self.assertNotIn('pull_request_target', raw)
        self.assertNotIn('id-token:', raw)
        self.assertIn('cancel-in-progress: false', raw)
        self.assertEqual(r.ALLOWED_INSTALL, {r.WORKFLOW, 'scripts/gulf_one_time_release_20261022.py',
                                           'scripts/test_gulf_one_time_release_20261022.py',
                                           'notes/gulf-native-release-20261022.md'})


if __name__ == '__main__':
    unittest.main()
