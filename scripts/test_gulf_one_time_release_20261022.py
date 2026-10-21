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
        self.assertIn('workflow_dispatch: {}', raw)
        self.assertNotIn('inputs:', raw)
        self.assertNotIn('repository_dispatch', raw)
        self.assertIn('ref: ${{ github.sha }}', raw)
        self.assertIn("workflow_dispatch' && 300 || 100", raw)
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
        self.write(r.DOCS_PATH, 'original administrative note')
        self.write('delete-me.txt', 'old approved removal')
        self.write(r.ARCHIVE_TEST_PATH, 'original exact archive test')
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


class DocumentationReconciliationGuards(unittest.TestCase):
    """Real Git objects prove that the one-note exception cannot widen payload."""
    git = RealGitManifestGuards.git
    write = RealGitManifestGuards.write
    commit = RealGitManifestGuards.commit
    tearDown = RealGitManifestGuards.tearDown

    def setUp(self):
        RealGitManifestGuards.setUp(self)
        self.git('checkout','--detach',self.main)
        self.write(r.DOCS_PATH,'exact approved documentation addition')
        self.docs_head=self.commit('reviewed docs only')
        self.git('checkout','--detach',self.main)
        self.git('merge','--no-ff','--no-edit',self.docs_head)
        self.docs_base=self.git('rev-parse','HEAD')
        self.docs_blob=self.git('rev-parse',self.docs_base+':'+r.DOCS_PATH)
        for path in r.ALLOWED_INSTALL:
            self.write(path,'exact reviewed repair '+path)
        self.repair_head=self.commit('four operational repairs')
        self.git('checkout','--detach',self.docs_base)
        self.git('merge','--no-ff','--no-edit',self.repair_head)
        self.repair_main=self.git('rev-parse','HEAD')
        self.pr={'number':987,'merged':True,'merge_commit_sha':self.repair_main,
                 'base':{'ref':'main','repo':{'full_name':r.REPO}},
                 'head':{'ref':r.DOCS_REPAIR_BRANCH,'sha':self.repair_head,'repo':{'full_name':r.REPO}}}
        original_git=r.git
        patches=[patch.object(r,'DOCS_BASE',self.docs_base),patch.object(r,'DOCS_PR_HEAD',self.docs_head),
                 patch.object(r,'DOCS_BLOB',self.docs_blob),patch.object(r,'REPAIR_PR',987),
                 patch.object(r,'DOCS_REPAIR_SHA',self.repair_main),patch.object(r,'DOCS_REPAIR_HEAD',self.repair_head),
                 patch.object(r,'ORIGINAL_INSTALL_SHA',self.main),
                 patch.object(r,'original_installation_base',return_value=self.main),
                 patch.object(r,'api',side_effect=lambda path:self.pr),
                 patch.object(r,'git',side_effect=lambda *a:'' if a[0]=='fetch' else original_git(*a))]
        for item in patches:item.start();self.patches.append(item)

    def test_exact_fixed_repair_main_is_accepted(self):
        self.assertEqual(r.documentation_installation_base(),self.repair_main)

    def test_docs_blob_change_rejected(self):
        with patch.object(r,'DOCS_BLOB','0'*40):
            with self.assertRaisesRegex(r.Blocked,'documentation blob'):
                r.documentation_installation_base()

    def test_docs_parent_change_rejected(self):
        with patch.object(r,'DOCS_PR_HEAD',self.approved):
            with self.assertRaisesRegex(r.Blocked,'documentation merge parents'):
                r.documentation_installation_base()

    def test_wrong_repair_pr_branch_repo_or_head_rejected(self):
        original=deepcopy(self.pr)
        mutations=[lambda p:p.update(number=988),lambda p:p.update(merged=False),
                   lambda p:p['head'].update(ref='other'),lambda p:p['base']['repo'].update(full_name='fork/repo'),
                   lambda p:p['head'].update(sha=self.approved)]
        for mutate in mutations:
            self.pr=deepcopy(original);mutate(self.pr)
            with self.assertRaises(r.Blocked):r.documentation_installation_base()

    def test_unreviewed_main_descendant_rejected(self):
        with patch.object(r,'installation_base',return_value=self.repair_main), patch.object(r,'api',side_effect=lambda path:{'commit':{'sha':self.docs_base}} if path=='/branches/main' else self.pr):
            with self.assertRaisesRegex(r.Blocked,'not the exact reviewed installation'):
                r.candidate_snapshot()

    def test_fifth_repair_file_or_doc_edit_rejected(self):
        for path in ['notes/other.md','docs/index.html',r.DOCS_PATH]:
            self.git('checkout','--detach',self.repair_head)
            self.write(path,'unreviewed change')
            head=self.commit('invalid extra repair change')
            self.git('checkout','--detach',self.docs_base)
            self.git('merge','--no-ff','--no-edit',head)
            self.pr['head']['sha']=head;self.pr['merge_commit_sha']=self.git('rev-parse','HEAD')
            with self.assertRaises(r.Blocked):
                r.documentation_installation_base()

    def test_reviewed_docs_are_preserved_in_exact_payload_candidate(self):
        self.git('checkout','--detach',self.candidate)
        self.git('merge','--no-ff','--no-edit',self.repair_main)
        candidate=self.git('rev-parse','HEAD')
        r.verify_payload(self.repair_main,candidate)
        self.assertEqual(self.git('rev-parse',candidate+':'+r.DOCS_PATH),self.docs_blob)
        self.write(r.DOCS_PATH,'reverted or changed administrative guidance')
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.repair_main,self.commit('unauthorized note change'))


class MidnightReconciliationGuards(unittest.TestCase):
    git = RealGitManifestGuards.git
    write = RealGitManifestGuards.write
    commit = RealGitManifestGuards.commit
    tearDown = RealGitManifestGuards.tearDown

    def setUp(self):
        DocumentationReconciliationGuards.setUp(self)
        self.previous_main = self.repair_main
        for path in r.MIDNIGHT_FILES:
            self.write(path, 'exact reviewed midnight repair ' + path)
        self.midnight_head = self.commit('five fixed reviewed files')
        self.git('checkout', '--detach', self.previous_main)
        self.git('merge', '--no-ff', '--no-edit', self.midnight_head)
        self.midnight_main = self.git('rev-parse', 'HEAD')
        self.test_blob = self.git('rev-parse', self.midnight_main + ':' + r.ARCHIVE_TEST_PATH)
        self.pr = {'number':986, 'merged':True, 'merge_commit_sha':self.midnight_main,
                   'base':{'ref':'main','repo':{'full_name':r.REPO}},
                   'head':{'ref':r.MIDNIGHT_BRANCH,'sha':self.midnight_head,'repo':{'full_name':r.REPO}}}
        for item in [patch.object(r, 'documentation_installation_base', return_value=self.previous_main),
                     patch.object(r, 'MIDNIGHT_REPAIR_PR', 986),
                     patch.object(r, 'MIDNIGHT_MERGE_SHA', self.midnight_main),
                     patch.object(r, 'MIDNIGHT_HEAD_SHA', self.midnight_head), patch.object(r, 'ARCHIVE_TEST_BLOB', self.test_blob)]:
            item.start(); self.patches.append(item)

    def test_exact_five_file_chain_passes(self):
        self.assertEqual(r.archive_installation_base(), self.midnight_main)

    def test_unpinned_repair_or_test_fails_closed(self):
        for name, value in [('MIDNIGHT_REPAIR_PR',0), ('ARCHIVE_TEST_BLOB','PENDING')]:
            with patch.object(r,name,value), self.assertRaises(r.Blocked): r.archive_installation_base()

    def test_wrong_reviewed_archive_blob_rejected(self):
        with patch.object(r,'ARCHIVE_TEST_BLOB','0'*40), self.assertRaisesRegex(r.Blocked,'archive test blob'):
            r.archive_installation_base()

    def test_wrong_pr_branch_fork_parent_head_rejected(self):
        original=deepcopy(self.pr)
        for mutate in [lambda p:p.update(number=985),lambda p:p.update(merged=False),
                       lambda p:p['head'].update(ref='other'),lambda p:p['base']['repo'].update(full_name='attacker/repo'),
                       lambda p:p['head'].update(sha=self.approved)]:
            self.pr=deepcopy(original); mutate(self.pr)
            with self.assertRaises(r.Blocked): r.archive_installation_base()

    def test_extra_path_public_content_and_note_changes_rejected(self):
        for path in ['scripts/extra-test.py','docs/index.html',r.DOCS_PATH]:
            self.git('checkout','--detach',self.midnight_head)
            self.write(path,'unauthorized extra change')
            head=self.commit('invalid extra file')
            self.git('checkout','--detach',self.previous_main)
            self.git('merge','--no-ff','--no-edit',head)
            self.pr['head']['sha']=head;self.pr['merge_commit_sha']=self.git('rev-parse','HEAD')
            with self.assertRaises(r.Blocked):
                r.archive_installation_base()

    def test_archive_mode_change_rejected(self):
        self.git('checkout','--detach',self.midnight_head)
        Path(r.ARCHIVE_TEST_PATH).chmod(0o755)
        self.pr['head']['sha']=self.commit('wrong archive mode')
        self.git('checkout','--detach',self.previous_main)
        self.git('merge','--no-ff','--no-edit',self.pr['head']['sha'])
        self.pr['merge_commit_sha']=self.git('rev-parse','HEAD')
        with self.assertRaises(r.Blocked): r.archive_installation_base()

    def test_original_complete_payload_digest_survives_repair(self):
        self.git('checkout','--detach',self.candidate)
        self.git('merge','--no-ff','--no-edit',self.midnight_main)
        candidate=self.git('rev-parse','HEAD')
        r.verify_payload(self.midnight_main,candidate)
        self.assertEqual(r.raw_manifest(self.midnight_main,candidate),self.manifest)
        self.assertEqual(self.git('rev-parse',candidate+':'+r.ARCHIVE_TEST_PATH),self.test_blob)
        self.write(r.ARCHIVE_TEST_PATH,'unreviewed followup')
        with self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.verify_payload(self.midnight_main,self.commit('changed test after approval'))


class ArmingReconciliationGuards(unittest.TestCase):
    git = RealGitManifestGuards.git
    write = RealGitManifestGuards.write
    commit = RealGitManifestGuards.commit
    tearDown = RealGitManifestGuards.tearDown

    def setUp(self):
        MidnightReconciliationGuards.setUp(self)
        self.previous_main=self.midnight_main
        for path in r.ALLOWED_INSTALL:self.write(path,'reviewed arming repair '+path)
        self.arming_head=self.commit('four fixed arming files')
        self.git('checkout','--detach',self.previous_main)
        self.git('merge','--no-ff','--no-edit',self.arming_head)
        self.arming_main=self.git('rev-parse','HEAD')
        self.pr={'number':987,'merged':True,'merge_commit_sha':self.arming_main,
                 'base':{'ref':'main','repo':{'full_name':r.REPO}},
                 'head':{'ref':r.INSTALL_BRANCH,'sha':self.arming_head,'repo':{'full_name':r.REPO}}}
        for item in [patch.object(r,'archive_installation_base',return_value=self.previous_main),
                     patch.object(r,'ARMING_REPAIR_PR',987)]:
            item.start();self.patches.append(item)

    def test_exact_four_ops_chain_passes_and_archive_blob_unchanged(self):
        self.assertEqual(r.installation_base(),self.arming_main)
        self.assertEqual(self.git('rev-parse',self.arming_main+':'+r.ARCHIVE_TEST_PATH),self.test_blob)

    def test_unpinned_arming_repair_fails_closed(self):
        with patch.object(r,'ARMING_REPAIR_PR',0),self.assertRaises(r.Blocked):r.installation_base()

    def test_wrong_pr_branch_fork_parent_head_rejected(self):
        original=deepcopy(self.pr)
        for mutate in [lambda p:p.update(number=986),lambda p:p.update(merged=False),
                       lambda p:p['head'].update(ref=r.MIDNIGHT_BRANCH),
                       lambda p:p['head']['repo'].update(full_name='attacker/repo'),
                       lambda p:p['head'].update(sha=self.approved)]:
            self.pr=deepcopy(original);mutate(self.pr)
            with self.assertRaises(r.Blocked):r.installation_base()

    def test_fifth_path_including_archive_or_public_note_rejected(self):
        for path in [r.ARCHIVE_TEST_PATH,'docs/index.html',r.DOCS_PATH,'scripts/extra.py']:
            self.git('checkout','--detach',self.arming_head)
            self.write(path,'unreviewed change')
            head=self.commit('unexpected fifth change')
            self.git('checkout','--detach',self.previous_main)
            self.git('merge','--no-ff','--no-edit',head)
            self.pr['head']['sha']=head;self.pr['merge_commit_sha']=self.git('rev-parse','HEAD')
            with self.assertRaisesRegex(r.Blocked,'exactly the four'):r.installation_base()

    def test_original_payload_survives_arming_base_integration(self):
        self.git('checkout','--detach',self.candidate)
        self.git('merge','--no-ff','--no-edit',self.arming_main)
        candidate=self.git('rev-parse','HEAD')
        r.verify_payload(self.arming_main,candidate)
        self.assertEqual(r.raw_manifest(self.arming_main,candidate),self.manifest)


class HeldDispatchGuards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.old=os.getcwd(); os.chdir(self.temp.name)
        self.instant=r.DISPATCH_AFTER+timedelta(minutes=30)
        self.snapshot={'base':SHA,'head':'b'*40}
        self.event={'ref':'main','inputs':{},'repository':{'full_name':r.REPO},'sender':{'login':r.BOT}}
        self.run={'id':123,'workflow_id':r.WORKFLOW_ID,'path':r.WORKFLOW,'event':'workflow_dispatch',
                  'head_sha':SHA,'head_branch':'main','actor':{'login':r.BOT},'triggering_actor':{'login':r.BOT},
                  'created_at':self.instant.isoformat(),'status':'queued'}
        self.env={'GITHUB_REPOSITORY':r.REPO,'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main',
                  'GITHUB_ACTOR':r.BOT,'GITHUB_RUN_ID':'123','GITHUB_SHA':SHA}
        self.patches=[patch.dict(os.environ,self.env),patch.object(r,'now',return_value=self.instant),
                      patch.object(r,'installation_base',return_value=SHA),patch.object(r,'record')]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        os.chdir(self.old);self.temp.cleanup()

    def dispatch_api(self,path,*args):
        self.assertFalse(args,'context and arming must not write')
        if path=='/actions/runs/123':return self.run
        if path=='/branches/main':return {'commit':{'sha':SHA}}
        if path=='/actions/runs/1/jobs?filter=latest&per_page=100':return {'jobs':[{'name':'Three-mirror publication check','conclusion':'success'}]}
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=self.snapshot['head'];p['base']['sha']=SHA
        if path=='/pulls/'+str(r.CONTENT_PR):return p
        raise AssertionError(path)

    def test_exact_context_accepts_immutable_dispatch(self):
        with patch.object(r,'api',side_effect=self.dispatch_api):
            self.assertEqual(r.validate_dispatch_context(self.event),SHA)

    def test_context_rejects_wrong_actor_repo_ref_event(self):
        for name,value in [('GITHUB_ACTOR','unionmed'),('GITHUB_REPOSITORY','attacker/repo'),
                           ('GITHUB_REF','refs/heads/other'),('GITHUB_EVENT_NAME','pull_request')]:
            with patch.dict(os.environ,{name:value}),patch.object(r,'api') as api,self.assertRaises(r.Blocked):
                r.validate_dispatch_context(self.event)
            api.assert_not_called()

    def test_event_rejects_any_inputs_and_wrong_sender(self):
        for key,value in [('ref','other'),('inputs',{'sha':SHA}),('sender',{'login':'unionmed'}),
                          ('repository',{'full_name':'attacker/repo'})]:
            e=deepcopy(self.event);e[key]=value
            with patch.object(r,'api') as api,self.assertRaises(r.Blocked):r.validate_dispatch_context(e)
            api.assert_not_called()

    def test_date_year_and_deadline_rejected_before_api(self):
        for when in [r.DISPATCH_AFTER-timedelta(seconds=1),r.DEADLINE+timedelta(seconds=1),self.instant.replace(year=2027)]:
            with patch.object(r,'now',return_value=when),patch.object(r,'api') as api,self.assertRaises(r.Blocked):
                r.validate_dispatch_context(self.event)
            api.assert_not_called()

    def test_run_id_and_sha_are_not_arbitrary_revisions(self):
        for env in [{'GITHUB_RUN_ID':'../../other'},{'GITHUB_SHA':'b'*40}]:
            with patch.dict(os.environ,env),patch.object(r,'api') as api,self.assertRaises(r.Blocked):
                r.validate_dispatch_context(self.event)
            api.assert_not_called()

    def test_live_run_metadata_rejects_wrong_origin_and_head(self):
        original=deepcopy(self.run)
        for key,value in [('id',124),('workflow_id',1),('path','other.yml'),('event','schedule'),
                          ('head_sha','b'*40),('head_branch','other'),('actor',{'login':'unionmed'}),
                          ('triggering_actor',{'login':'unionmed'})]:
            self.run=deepcopy(original);self.run[key]=value
            with patch.object(r,'api',side_effect=self.dispatch_api),self.assertRaises(r.Blocked):
                r.validate_dispatch_context(self.event)

    def test_arm_has_no_publication_or_write_and_freezes_snapshot(self):
        check=run();check['head_sha']=self.snapshot['head']
        with patch.object(r,'api',side_effect=self.dispatch_api),patch.object(r,'candidate_snapshot',return_value=self.snapshot),\
             patch.object(r,'normal_runs',return_value={check['path']:check}),patch.object(r,'protected_merge') as merge,\
             patch.object(r,'pages_build') as pages:
            self.assertEqual(r.arm_held_release(self.event),self.snapshot)
        self.assertEqual(__import__('json').loads(Path('armed-release.json').read_text()),{'run_id':'123','snapshot':self.snapshot})
        merge.assert_not_called();pages.assert_not_called()

    def test_arm_rejects_stale_or_failed_ci(self):
        for key,value in [('conclusion','failure'),('run_started_at','2026-10-21T20:59:59Z')]:
            check=run();check[key]=value
            with patch.object(r,'api',side_effect=self.dispatch_api),patch.object(r,'candidate_snapshot',return_value=self.snapshot),\
                 patch.object(r,'normal_runs',return_value={check['path']:check}),self.assertRaises(r.Blocked):r.arm_held_release(self.event)
            self.assertFalse(Path('armed-release.json').exists())

    def test_hold_only_reads_then_revalidates_same_frozen_snapshot(self):
        Path('armed-release.json').write_text(__import__('json').dumps({'run_id':'123','snapshot':self.snapshot}))
        current=[self.instant]
        def sleep(seconds):
            self.assertGreater(seconds,0);self.assertLessEqual(seconds,300);current[0]=r.PREFLIGHT
        with patch.object(r,'now',side_effect=lambda:current[0]),patch.object(r,'api',side_effect=self.dispatch_api),\
             patch.object(r,'recheck_snapshot') as check,patch.object(r,'normal_runs',return_value={'check':run()}),\
             patch.object(r.time,'sleep',side_effect=sleep),patch.object(r,'release') as release,\
             patch.object(r,'protected_merge') as merge,patch.object(r,'pages_build') as pages:
            r.held_release(self.event)
        self.assertEqual(check.call_count,2)
        release.assert_called_once_with(expected_snapshot=self.snapshot,from_dispatch=True)
        merge.assert_not_called();pages.assert_not_called()

    def test_hold_wrong_arming_run_or_changed_snapshot_blocks(self):
        for ident in ['other','123']:
            Path('armed-release.json').write_text(__import__('json').dumps({'run_id':ident,'snapshot':self.snapshot}))
            with patch.object(r,'api',side_effect=self.dispatch_api),patch.object(r,'recheck_snapshot',side_effect=r.Blocked('changed snapshot')),\
                 patch.object(r,'release') as release,self.assertRaises(r.Blocked):r.held_release(self.event)
            release.assert_not_called()

    def launch_patches(self):
        return [patch.object(r,'RECEIPT',{'events':[{'event':'INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS','merge_sha':SHA}]}),
                patch.object(r,'recheck_snapshot')]

    def test_installer_posts_once_then_returns_queued_without_concurrency_deadlock(self):
        patches=self.launch_patches()
        for p in patches:p.start()
        try:
            with patch.object(r,'dispatch_runs',side_effect=[[],[self.run]]),\
                 patch.object(r,'api',side_effect=[{'commit':{'sha':SHA}},{}]) as api,patch.object(r.time,'sleep') as sleep:
                self.assertEqual(r.launch_held_release(SHA,self.snapshot),123)
            self.assertEqual(api.call_args_list[1].args,('/actions/workflows/gulf-one-time-release-20261022.yml/dispatches','POST',{'ref':'main'}))
            sleep.assert_not_called()
        finally:
            for p in reversed(patches):p.stop()

    def test_missing_actual_dry_run_never_dispatches(self):
        with patch.object(r,'RECEIPT',{'events':[]}),patch.object(r,'api') as api,self.assertRaises(r.Blocked):
            r.launch_held_release(SHA,self.snapshot)
        api.assert_not_called()

    def test_existing_or_multiple_dispatches_are_not_retried(self):
        patches=self.launch_patches()
        for p in patches:p.start()
        try:
            for values in [[[self.run]], [[],[self.run,self.run]]]:
                with patch.object(r,'dispatch_runs',side_effect=values),patch.object(r,'api',return_value={'commit':{'sha':SHA}}) as api,\
                     self.assertRaises(r.Blocked):r.launch_held_release(SHA,self.snapshot)
                self.assertLessEqual(sum(len(c.args)>1 and c.args[1]=='POST' for c in api.call_args_list),1)
        finally:
            for p in reversed(patches):p.stop()

    def test_ambiguous_dispatch_reads_back_without_second_post(self):
        patches=self.launch_patches()
        for p in patches:p.start()
        try:
            with patch.object(r,'dispatch_runs',side_effect=[[],[self.run]]),\
                 patch.object(r,'api',side_effect=[{'commit':{'sha':SHA}},OSError('response lost')]) as api:
                self.assertEqual(r.launch_held_release(SHA,self.snapshot),123)
            self.assertEqual(api.call_count,2)
        finally:
            for p in reversed(patches):p.stop()

    def test_denied_dispatch_is_not_retried(self):
        patches=self.launch_patches()
        for p in patches:p.start()
        try:
            with patch.object(r,'dispatch_runs',return_value=[]),\
                 patch.object(r,'api',side_effect=[{'commit':{'sha':SHA}},r.Blocked('HTTP 403')]) as api,\
                 self.assertRaisesRegex(r.Blocked,'403'):r.launch_held_release(SHA,self.snapshot)
            self.assertEqual(api.call_count,2)
        finally:
            for p in reversed(patches):p.stop()

    def test_base_update_wait_never_writes_or_accepts_changed_payload(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=r.REPAIR_CONTENT_SHA
        responses=[{'commit':{'sha':SHA}},p,{'commit':{'sha':SHA}},
                   {**p,'head':{**p['head'],'sha':'b'*40}}]
        with patch.object(r,'api',side_effect=responses) as api,patch.object(r.time,'sleep'),\
             patch.object(r,'candidate_snapshot',side_effect=r.Blocked('payload differs')),\
             patch.object(r,'protected_merge') as merge,self.assertRaisesRegex(r.Blocked,'payload differs'):
            r.wait_for_prepared_candidate(SHA)
        self.assertTrue(all(len(c.args)==1 for c in api.call_args_list));merge.assert_not_called()

    def test_base_update_wait_is_bounded(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=r.REPAIR_CONTENT_SHA
        with patch.object(r,'api',side_effect=[{'commit':{'sha':SHA}},p]),\
             patch.object(r.time,'monotonic',side_effect=[0,1801]),self.assertRaisesRegex(r.Blocked,'30 minutes'):
            r.wait_for_prepared_candidate(SHA)

    def test_all_nine_normal_workflows_are_required(self):
        self.assertEqual(len(r.CONTENT_CI),9)
        self.assertTrue({'.github/workflows/science-navigation-regression.yml',
                         '.github/workflows/team-page-qa.yml',
                         '.github/workflows/four-news-build-20261018.yml'} <= r.CONTENT_CI)

    def test_arming_rejects_missing_required_job_or_blocked_mergeability(self):
        for broken in ('required_job','mergeability'):
            def api(path,*args):
                value=self.dispatch_api(path,*args)
                if broken=='required_job' and '/jobs?' in path:value={'jobs':[]}
                if broken=='mergeability' and path.startswith('/pulls/'):
                    value['mergeable_state']='blocked'
                return value
            with patch.object(r,'api',side_effect=api),patch.object(r,'normal_runs',return_value={run()['path']:run()}),\
                 patch.object(r,'candidate_snapshot',return_value=self.snapshot),\
                 patch.object(r.time,'monotonic',side_effect=[0,121]),self.assertRaises(r.Blocked):
                r.arm_held_release(self.event)
            self.assertFalse(Path('armed-release.json').exists())

    def test_ci_admission_wait_freezes_first_exact_candidate(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=self.snapshot['head']
        with patch.object(r,'api',side_effect=[{'commit':{'sha':SHA}},p]*2) as api,\
             patch.object(r,'candidate_snapshot',return_value=self.snapshot),\
             patch.object(r,'normal_runs',side_effect=[r.Blocked('Missing normal CI workflows: test'),{}]),\
             patch.object(r,'wait_ci') as ci,patch.object(r,'recheck_snapshot') as recheck,patch.object(r.time,'sleep'):
            self.assertEqual(r.wait_for_prepared_candidate(SHA),self.snapshot)
        self.assertTrue(all(len(c.args)==1 for c in api.call_args_list))
        ci.assert_called_once();recheck.assert_called_once_with(self.snapshot)

    def test_ci_admission_wait_rejects_moved_candidate(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=self.snapshot['head']
        with patch.object(r,'api',side_effect=[{'commit':{'sha':SHA}},p]*2),\
             patch.object(r,'candidate_snapshot',side_effect=[self.snapshot,{**self.snapshot,'head':'c'*40}]),\
             patch.object(r,'normal_runs',side_effect=r.Blocked('Missing normal CI workflows: test')),\
             patch.object(r,'wait_ci') as ci,patch.object(r.time,'sleep'),\
             self.assertRaisesRegex(r.Blocked,'changed while awaiting CI'):
            r.wait_for_prepared_candidate(SHA)
        ci.assert_not_called()

    def installer_event(self):
        p=pull();p['number']=r.ARMING_REPAIR_PR;p['head']['ref']=r.INSTALL_BRANCH
        return {'action':'ready_for_review','pull_request':p}

    def test_split_installer_loads_actual_proof_before_wait_and_dispatch(self):
        saved={'repository':r.REPO,'target_time':r.START.isoformat(),
               'events':[{'event':'INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS','merge_sha':SHA}]}
        Path('release-receipt.json').write_text(__import__('json').dumps(saved))
        with patch.dict(os.environ,{'GITHUB_EVENT_NAME':'pull_request'}),patch.object(r,'RECEIPT',{}),\
             patch.object(r,'api',return_value=self.installer_event()['pull_request']),\
             patch.object(r,'wait_for_prepared_candidate',return_value=self.snapshot) as wait,\
             patch.object(r,'launch_held_release') as launch:
            r.complete_installation(self.installer_event())
        wait.assert_called_once_with(SHA);launch.assert_called_once_with(SHA,self.snapshot)

    def test_split_installer_without_actual_proof_never_waits_or_dispatches(self):
        for proof in [[],[{'event':'INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS','merge_sha':'b'*40}]]:
            Path('release-receipt.json').write_text(__import__('json').dumps(
                {'repository':r.REPO,'target_time':r.START.isoformat(),'events':proof}))
            with patch.dict(os.environ,{'GITHUB_EVENT_NAME':'pull_request'}),patch.object(r,'RECEIPT',{}),\
                 patch.object(r,'api',return_value=self.installer_event()['pull_request']),\
                 patch.object(r,'wait_for_prepared_candidate') as wait,patch.object(r,'launch_held_release') as launch,\
                 self.assertRaisesRegex(r.Blocked,'dry-run proof'):
                r.complete_installation(self.installer_event())
            wait.assert_not_called();launch.assert_not_called()

    def test_split_installer_rejects_changed_event_head(self):
        Path('release-receipt.json').write_text(__import__('json').dumps(
            {'repository':r.REPO,'target_time':r.START.isoformat(),'events':[]}))
        p=self.installer_event()['pull_request'];p['head']['sha']='c'*40
        with patch.dict(os.environ,{'GITHUB_EVENT_NAME':'pull_request'}),patch.object(r,'RECEIPT',{}),\
             patch.object(r,'api',return_value=p),patch.object(r,'wait_for_prepared_candidate') as wait,\
             self.assertRaisesRegex(r.Blocked,'event head changed'):
            r.complete_installation(self.installer_event())
        wait.assert_not_called()

    def optional_check_fixture(self):
        base={'head_sha':self.snapshot['head'],'status':'completed','conclusion':'success'}
        return {'total_count':2,'check_runs':[
            {**base,'id':1,'name':'Three-mirror publication check','app':{'id':15368,'slug':'github-actions'}},
            {**base,'id':2,'name':'Workers Builds: sayd-mufid-internal','conclusion':'failure',
             'app':{'id':85455,'slug':'cloudflare-workers-and-pages'}}]}

    def protection_fixture(self):
        return {'commit':{'sha':SHA},'protected':True,'protection':{'enabled':True,'required_status_checks':{
            'enforcement_level':'everyone','contexts':['Three-mirror publication check'],
            'checks':[{'context':'Three-mirror publication check','app_id':15368}]}}}

    def test_exact_optional_workers_failure_is_read_only(self):
        with patch.object(r,'api',side_effect=[self.protection_fixture(),self.optional_check_fixture(),
                {'sha':self.snapshot['head'],'total_count':0,'statuses':[],'state':'pending'}]) as api:
            r.exact_optional_workers_failure(self.snapshot)
        self.assertTrue(all(len(c.args)==1 for c in api.call_args_list))

    def test_optional_allowance_checks_legacy_statuses_without_trusting_empty_aggregate(self):
        for state in ['failure','pending','error']:
            status={'sha':self.snapshot['head'],'total_count':1,'statuses':[{'state':state}]}
            with patch.object(r,'api',side_effect=[self.protection_fixture(),self.optional_check_fixture(),status]),\
                 self.assertRaisesRegex(r.Blocked,'legacy commit status'):
                r.exact_optional_workers_failure(self.snapshot)
        for status in [{'sha':'c'*40,'total_count':0,'statuses':[]},
                       {'sha':self.snapshot['head'],'total_count':1,'statuses':[]},
                       {'sha':self.snapshot['head'],'total_count':100,'statuses':[{'state':'success'}]*100}]:
            with patch.object(r,'api',side_effect=[self.protection_fixture(),self.optional_check_fixture(),status]),\
                 self.assertRaisesRegex(r.Blocked,'Legacy status inspection'):
                r.exact_optional_workers_failure(self.snapshot)
        status={'sha':self.snapshot['head'],'total_count':1,'statuses':[{'state':'success'}]}
        with patch.object(r,'api',side_effect=[self.protection_fixture(),self.optional_check_fixture(),status]):
            r.exact_optional_workers_failure(self.snapshot)

    def test_optional_allowance_rejects_changed_required_protection(self):
        for mutate in [lambda b:b.update(protected=False),lambda b:b['commit'].update(sha='c'*40),
                       lambda b:b['protection'].update(enabled=False),
                       lambda b:b['protection']['required_status_checks'].update(enforcement_level='non_admins'),
                       lambda b:b['protection']['required_status_checks'].update(contexts=['other']),
                       lambda b:b['protection']['required_status_checks'].update(checks=[{'context':'Three-mirror publication check','app_id':None}])]:
            branch=self.protection_fixture();mutate(branch)
            with patch.object(r,'api',return_value=branch) as api,self.assertRaises(r.Blocked):
                r.exact_optional_workers_failure(self.snapshot)
            self.assertEqual(api.call_count,1)

    def test_optional_allowance_rejects_other_apps_names_or_nonterminal_states(self):
        for key,value in [('name','Workers Builds: another-worker'),('app',{'id':1,'slug':'cloudflare-workers-and-pages'}),
                          ('app',{'id':85455,'slug':'imposter'}),('status','in_progress'),('conclusion','cancelled'),
                          ('head_sha','c'*40)]:
            checks=self.optional_check_fixture();checks['check_runs'][1][key]=value
            with patch.object(r,'api',side_effect=[self.protection_fixture(),checks]),self.assertRaises(r.Blocked):
                r.exact_optional_workers_failure(self.snapshot)

    def test_optional_allowance_rejects_other_failed_or_pending_checks(self):
        for status,conclusion in [('completed','failure'),('queued',None),('completed','neutral')]:
            checks=self.optional_check_fixture();checks['check_runs'].append({
                'id':3,'head_sha':self.snapshot['head'],'name':'Another check','status':status,
                'conclusion':conclusion,'app':{'id':15368}});checks['total_count']=3
            with patch.object(r,'api',side_effect=[self.protection_fixture(),checks]),self.assertRaises(r.Blocked):
                r.exact_optional_workers_failure(self.snapshot)

    def test_optional_allowance_requires_exact_current_publication_check(self):
        for key,value in [('app',{'id':85455}),('conclusion','skipped'),('head_sha','c'*40),('name','Other')]:
            checks=self.optional_check_fixture();checks['check_runs'][0][key]=value
            with patch.object(r,'api',side_effect=[self.protection_fixture(),checks]),self.assertRaises(r.Blocked):
                r.exact_optional_workers_failure(self.snapshot)

    def test_optional_allowance_rejects_pagination_and_ambiguous_optional_duplicates(self):
        for kind in ['truncated','limit','duplicate','none']:
            checks=self.optional_check_fixture()
            if kind=='truncated':checks['total_count']=3
            elif kind=='limit':checks['check_runs']*=50;checks['total_count']=100
            elif kind=='duplicate':checks['check_runs'].append(deepcopy(checks['check_runs'][1]));checks['total_count']=3
            else:checks['check_runs'].pop();checks['total_count']=1
            with patch.object(r,'api',side_effect=[self.protection_fixture(),checks]),self.assertRaises(r.Blocked):
                r.exact_optional_workers_failure(self.snapshot)

    def test_unstable_arming_still_requires_all_ci_and_named_job_before_exception(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=self.snapshot['head'];p['base']['sha']=SHA;p['mergeable_state']='unstable'
        with patch.object(r,'normal_runs',return_value={run()['path']:run()}),\
             patch.object(r,'api',side_effect=[{'jobs':[{'name':'Three-mirror publication check','conclusion':'success'}]},p]),\
             patch.object(r,'exact_optional_workers_failure') as exception:
            r.readonly_merge_readiness(self.snapshot)
        exception.assert_called_once_with(self.snapshot)
        failed=run();failed['conclusion']='failure'
        with patch.object(r,'normal_runs',return_value={failed['path']:failed}),\
             patch.object(r,'exact_optional_workers_failure') as exception,self.assertRaises(r.Blocked):
            r.readonly_merge_readiness(self.snapshot)
        exception.assert_not_called()

    def test_optional_classification_rechecked_immediately_before_protected_release_merge(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=self.snapshot['head'];p['base']['sha']=SHA;p['mergeable_state']='unstable'
        merged='d'*40
        with patch.object(r,'now',return_value=r.START),patch.object(r,'api',side_effect=[p,
                {'merged':True,'sha':merged},{'parents':[{'sha':SHA},{'sha':self.snapshot['head']}]}]) as api,\
             patch.object(r,'exact_optional_workers_failure') as exception:
            self.assertEqual(r.protected_merge(r.CONTENT_PR,self.snapshot['head'],r.CONTENT_BRANCH,SHA,release=True),merged)
        exception.assert_called_once_with(self.snapshot)
        self.assertEqual(api.call_args_list[1].args[1:],('PUT', {'sha':self.snapshot['head'],'merge_method':'merge'}))

    def test_new_unknown_failed_check_before_release_blocks_without_put(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=self.snapshot['head'];p['base']['sha']=SHA;p['mergeable_state']='unstable'
        with patch.object(r,'now',return_value=r.START),patch.object(r,'api',return_value=p) as api,\
             patch.object(r,'exact_optional_workers_failure',side_effect=r.Blocked('Unrecognized failed check')),\
             self.assertRaisesRegex(r.Blocked,'Unrecognized failed'):
            r.protected_merge(r.CONTENT_PR,self.snapshot['head'],r.CONTENT_BRANCH,SHA,release=True)
        self.assertEqual(api.call_count,1)

    def test_held_release_changed_head_is_rejected_before_merge(self):
        p=pull();p['number']=r.CONTENT_PR;p['head']['sha']=SHA
        with patch.object(r,'now',return_value=r.START),patch.object(r,'api',return_value=p),\
             patch.object(r,'protected_merge') as merge,self.assertRaisesRegex(r.Blocked,'Held candidate head'):
            r.release(expected_snapshot=self.snapshot,from_dispatch=True)
        merge.assert_not_called()


if __name__ == '__main__':
    unittest.main()
