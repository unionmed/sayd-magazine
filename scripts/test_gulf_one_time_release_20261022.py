"""Offline fail-closed tests; never contact GitHub or production."""
from copy import deepcopy
from datetime import timedelta
import os
import hashlib
import subprocess
import tempfile
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
        with patch.object(r, 'api', side_effect=[{'commit':'old', 'status':'built'}, {'commit':{'sha':SHA}}, r.Blocked('HTTP 403')]) as api:
            with self.assertRaisesRegex(r.Blocked, '403'):
                r.pages_build(SHA)
        self.assertEqual(api.call_count, 3)

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
        with patch.object(r, 'git', side_effect=[r.BASE, r.WORKFLOW, 'tree', 'tree']), patch.object(r, 'record'):
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
        responses = [{'commit':'old', 'status':'built'}, {'commit':{'sha':SHA}}, {'status':'queued'},
                     {'commit':SHA, 'status':'built', 'created_at':r.START.isoformat()}]
        with patch.object(r, 'now', return_value=instant), patch.object(r, 'api', side_effect=responses) as api, \
             patch.object(r, 'record'), patch.object(r.time, 'sleep'):
            r.pages_build(SHA)
        self.assertEqual(api.call_count, 4)

    def test_duplicate_merged_content_still_checks_approved_payload(self):
        with patch.object(r, 'installation_base', return_value=r.BASE), \
             patch.object(r, 'api', return_value={'parents':[{'sha':r.BASE}, {'sha':SHA}]}), \
             patch.object(r, 'APPROVED_CONTENT_SHA', SHA), patch.object(r, 'git'), \
             patch.object(r, 'verify_payload', side_effect=r.Blocked('Candidate payload differs')) as payload:
            with self.assertRaisesRegex(r.Blocked, 'payload differs'):
                r.verify_content_merge('c'*40, SHA)
        payload.assert_called_once_with(r.BASE, SHA)

    def test_duplicate_wrong_head_never_reaches_pages(self):
        with patch.object(r, 'installation_base', return_value=r.BASE), \
             patch.object(r, 'api', return_value={'parents':[{'sha':r.BASE}, {'sha':'b'*40}]}), \
             patch.object(r, 'git') as git:
            with self.assertRaisesRegex(r.Blocked, 'parents differ'):
                r.verify_content_merge('c'*40, SHA)
        git.assert_not_called()

    def test_pages_moved_main_never_requests_a_build(self):
        with patch.object(r, 'api', side_effect=[{'commit':'old', 'status':'built'}, {'commit':{'sha':'b'*40}}]) as api:
            with self.assertRaisesRegex(r.Blocked, 'Main moved immediately'):
                r.pages_build(SHA)
        self.assertFalse(any(len(c.args)>1 and c.args[1]=='POST' for c in api.call_args_list))

    def test_midnight_preflight_only_reads_and_reruns_never_publishes(self):
        with patch.dict(os.environ, GITHUB_EVENT_NAME='schedule', GITHUB_REF='refs/heads/main'), \
             patch.object(r, 'now', return_value=r.CI_AFTER + timedelta(minutes=3)), \
             patch.object(r, 'CONTENT_PR', PR), \
             patch.object(r, 'candidate_snapshot', return_value={'head':SHA,'base':r.BASE}),\
             patch.object(r, 'recheck_snapshot'), \
             patch.object(r, 'api', return_value=pull()) as api, \
             patch.object(r, 'git', side_effect=['',r.BASE]), patch.object(r, 'unchanged_site_base'), \
             patch.object(r, 'wait_ci') as ci, patch.object(r, 'record'), \
             patch.object(r, 'protected_merge') as merge, patch.object(r, 'pages_build') as pages:
            r.preflight({'schedule':r.PREFLIGHT_CRON})
        ci.assert_called_once_with(PR, SHA, r.CONTENT_CI, fresh_after=r.CI_AFTER)
        self.assertTrue(all(c.args==('/pulls/999',) for c in api.call_args_list))
        merge.assert_not_called(); pages.assert_not_called()
        raw = (Path(__file__).resolve().parents[1] / r.WORKFLOW).read_text()
        job = raw.split('  midnight-preflight:',1)[1].split('  release:',1)[0]
        self.assertIn('contents: read',job); self.assertIn('pull-requests: read',job)
        self.assertIn('actions: write',job); self.assertNotIn('pages:',job)
        self.assertNotIn('contents: write',job); self.assertNotIn('pull-requests: write',job)

    def test_midnight_preflight_date_year_and_event_guard(self):
        for when in [r.CI_AFTER-timedelta(seconds=1), r.PREFLIGHT_END+timedelta(seconds=1), r.CI_AFTER.replace(year=2027)]:
            with patch.dict(os.environ, GITHUB_EVENT_NAME='schedule', GITHUB_REF='refs/heads/main'), \
                 patch.object(r, 'now', return_value=when), patch.object(r, 'api') as api:
                with self.assertRaisesRegex(r.Blocked, 'Outside fixed'):
                    r.preflight({'schedule':r.PREFLIGHT_CRON})
            api.assert_not_called()
        with patch.dict(os.environ, GITHUB_EVENT_NAME='schedule', GITHUB_REF='refs/heads/main'), patch.object(r, 'api') as api:
            with self.assertRaisesRegex(r.Blocked, 'Wrong preflight schedule'):
                r.preflight({'schedule':'7,17 2 22 10 *'})
        api.assert_not_called()

    def test_existing_queued_exact_pages_build_is_polled_without_duplicate_post(self):
        responses=[{'commit':SHA,'status':'queued','created_at':r.START.isoformat()},
                   {'commit':{'sha':SHA}}, {'commit':SHA,'status':'built','created_at':r.START.isoformat()}]
        with patch.object(r,'api',side_effect=responses) as api,patch.object(r,'record'):
            r.pages_build(SHA)
        self.assertFalse(any(len(c.args)>1 and c.args[1]=='POST' for c in api.call_args_list))

    def test_installer_forces_real_pages_write_even_if_already_built(self):
        responses=[{'commit':SHA,'status':'built','created_at':r.START.isoformat(),'url':r.API+'/pages/builds/1'},
                   {'commit':{'sha':SHA}}, {'status':'queued'},
                   {'commit':SHA,'status':'built','created_at':r.START.isoformat(),'url':r.API+'/pages/builds/2'}]
        with patch.object(r,'api',side_effect=responses) as api,patch.object(r,'record'),patch.object(r,'now',return_value=r.START):
            r.pages_build(SHA,force_request=True)
        self.assertIn(('/pages/builds','POST'),[c.args for c in api.call_args_list])

    def test_forced_dry_run_does_not_accept_old_same_second_build(self):
        old={'commit':SHA,'status':'built','created_at':r.START.isoformat(),'url':r.API+'/pages/builds/1'}
        new={**old,'url':r.API+'/pages/builds/2'}
        responses=[old, {'commit':{'sha':SHA}}, {'status':'queued'}, old, new]
        with patch.object(r,'api',side_effect=responses) as api, patch.object(r,'record'), \
             patch.object(r,'now',return_value=r.START.replace(microsecond=500000)), patch.object(r.time,'sleep') as sleep:
            r.pages_build(SHA,force_request=True)
        self.assertEqual(api.call_count,5)
        sleep.assert_called_once_with(15)

    def test_forced_dry_run_old_success_cannot_hide_new_failure(self):
        old={'commit':SHA,'status':'built','created_at':r.START.isoformat(),'url':r.API+'/pages/builds/1'}
        new={**old,'url':r.API+'/pages/builds/2','status':'errored'}
        responses=[old, {'commit':{'sha':SHA}}, {'status':'queued'}, old, new]
        with patch.object(r,'api',side_effect=responses), patch.object(r,'record'), \
             patch.object(r,'now',return_value=r.START), patch.object(r.time,'sleep'):
            with self.assertRaisesRegex(r.Blocked,'Pages build failed'):
                r.pages_build(SHA,force_request=True)

    def test_forced_dry_run_missing_old_identity_blocks_before_write(self):
        with patch.object(r,'api',return_value={'commit':SHA,'status':'built'}) as api:
            with self.assertRaisesRegex(r.Blocked,'identity is unavailable'):
                r.pages_build(SHA,force_request=True)
        self.assertEqual(api.call_count,1)

    def test_workflow_has_no_external_inputs_or_cancel(self):
        raw = (Path(__file__).resolve().parents[1] / r.WORKFLOW).read_text()
        self.assertNotIn('workflow_dispatch', raw)
        self.assertNotIn('pull_request_target', raw)
        self.assertNotIn('id-token:', raw)
        self.assertIn('cancel-in-progress: false', raw)
        self.assertEqual(r.ALLOWED_INSTALL, {r.WORKFLOW, 'scripts/gulf_one_time_release_20261022.py',
                                           'scripts/test_gulf_one_time_release_20261022.py',
                                           'notes/gulf-native-release-20261022.md'})


class RealGitManifestGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = os.getcwd(); os.chdir(self.temp.name)
        self.git('init','-q')
        self.git('config','user.name','Offline test')
        self.git('config','user.email','offline@example.invalid')
        self.git('config','commit.gpgsign','false')
        self.write('docs/index.html', 'old home')
        self.write('delete-me.txt', 'old approved removal')
        self.write('content/features/gulf-tourism-20261022.json', '{}')
        self.base = self.commit('base')
        self.write('docs/index.html','approved home')
        self.write('docs/new article\nwith quote".html','approved article')
        self.write('content/features/gulf-tourism-20261022.json','{"approved":true}')
        Path('delete-me.txt').unlink()
        self.approved = self.commit('approved original content')
        self.manifest = r.raw_manifest(self.base,self.approved)
        self.git('checkout','--detach',self.base)
        for path in r.ALLOWED_INSTALL:
            self.write(path,'reviewed operations file '+path)
        self.main = self.commit('approved operations only')
        self.git('merge','--no-ff','--no-edit',self.approved)
        self.candidate = self.git('rev-parse','HEAD')
        self.patches = [patch.object(r,'BASE',self.base), patch.object(r,'APPROVED_CONTENT_SHA',self.approved),
            patch.object(r,'PAYLOAD_MANIFEST_SHA256',hashlib.sha256(self.manifest).hexdigest()),
            patch.object(r,'SOURCE_SHA256',hashlib.sha256(b'{"approved":true}').hexdigest()), patch.object(r,'record')]
        for item in self.patches:item.start()

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        os.chdir(self.old); self.temp.cleanup()

    def git(self,*args):
        return subprocess.check_output(['git',*args],stderr=subprocess.DEVNULL,text=True).strip()

    def write(self,path,text):
        p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)

    def commit(self,message):
        self.git('add','-A');self.git('commit','-qm',message)
        return self.git('rev-parse','HEAD')

    def test_real_complete_manifest_passes_after_ops_only_base_merge(self):
        r.verify_payload(self.main,self.candidate)
        entries=r.manifest_entries(self.manifest)
        self.assertEqual(len(entries),4)
        self.assertTrue(any(b'\n' in path for _,path in entries))
        self.assertTrue(any(h.endswith(b' D') for h,_ in entries))
        self.assertEqual(r.raw_manifest(self.main,self.candidate),self.manifest)

    def test_extra_file_rejected(self):
        self.write('unapproved.txt','extra')
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.main,self.commit('extra'))

    def test_changed_approved_blob_rejected(self):
        self.write('docs/index.html','changed after approval')
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.main,self.commit('changed'))

    def test_omitted_approved_deletion_rejected(self):
        self.write('delete-me.txt','old approved removal')
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.main,self.commit('omitted deletion'))

    def test_extra_deletion_rejected(self):
        Path('docs/index.html').unlink()
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.main,self.commit('extra deletion'))

    def test_file_mode_change_rejected(self):
        Path('docs/index.html').chmod(0o755)
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.main,self.commit('mode changed'))

    def test_operations_change_rejected(self):
        self.write(r.WORKFLOW,'unapproved workflow change')
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.main,self.commit('changed operations'))

    def test_behind_original_head_rejected(self):
        with self.assertRaisesRegex(r.Blocked,'behind'):
            r.verify_payload(self.main,self.approved)

    def test_pin_digest_and_source_hash_fail_closed(self):
        with patch.object(r,'PAYLOAD_MANIFEST_SHA256','0'*64):
            with self.assertRaisesRegex(r.Blocked,'manifest hash'):
                r.verify_payload(self.main,self.candidate)
        with patch.object(r,'SOURCE_SHA256','0'*64):
            with self.assertRaisesRegex(r.Blocked,'source hash'):
                r.verify_payload(self.main,self.candidate)

    def test_ref_moves_cannot_change_frozen_candidate(self):
        with patch.object(r,'candidate_snapshot',return_value={'head':'b'*40,'base':self.main}):
            with self.assertRaisesRegex(r.Blocked,'changed after'):
                r.recheck_snapshot({'head':self.candidate,'base':self.main})

    def test_dynamic_sha_is_not_an_arbitrary_git_revision(self):
        for value in ['main','HEAD~1','-'+'a'*39,'a'*39,'A'*40,'a'*40+';id']:
            with self.assertRaisesRegex(r.Blocked,'immutable commit SHA'):
                r.raw_manifest(value,self.candidate)


if __name__ == '__main__':
    unittest.main()
