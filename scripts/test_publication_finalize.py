#!/usr/bin/env python3
"""Offline security tests: no request in this suite reaches GitHub."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import publication_finalize as f


def run(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


def sign(plan):
    plan["plan_sha256"] = hashlib.sha256(f.canonical_plan(plan)).hexdigest()
    return plan


class FakeAPI:
    def __init__(self, case, existing=None, fail_ref=False, stale_at=None):
        self.case = case
        self.calls = []
        self.existing = existing
        self.fail_ref = fail_ref
        self.stale_at = stale_at
        self.main_reads = 0
        self.commit = None

    def request(self, method, endpoint, payload=None, missing=False):
        self.calls.append((method, endpoint, payload))
        if method == "GET" and endpoint == "/git/ref/heads/main":
            self.main_reads += 1
            return {"object": {"sha": "a" * 40 if self.stale_at == self.main_reads else self.case.base}}
        if method == "GET" and endpoint == "/git/commits/" + self.case.source:
            return {"tree": {"sha": run(self.case.repo, "rev-parse", self.case.source + "^{tree}")}}
        if method == "GET" and endpoint.startswith("/git/ref/heads/review/"):
            return None if self.existing is None else {"object": {"sha": self.existing[0]}}
        if method == "GET" and endpoint.startswith("/git/commits/"):
            return self.existing[1] if self.existing and endpoint.endswith(self.existing[0]) else self.commit
        if method == "POST" and endpoint == "/git/blobs":
            import base64
            return {"sha": f.blob_sha(base64.b64decode(payload["content"]))}
        if method == "POST" and endpoint == "/git/trees":
            entries = f.tree_entries(self.case.repo, self.case.source)
            for entry in payload["tree"]:
                entries[entry["path"]] = (entry["mode"], entry["sha"])
            return {"sha": f.tree_sha(entries)}
        if method == "POST" and endpoint == "/git/commits":
            self.commit = {"tree": {"sha": payload["tree"]}, "message": payload["message"],
                           "parents": [{"sha": sha} for sha in payload["parents"]]}
            return {"sha": "c" * 40}
        if method == "POST" and endpoint == "/git/refs":
            if self.fail_ref:
                raise f.UncertainMutation("Synthetic timeout after ref create; no retry")
            self.existing = (payload["sha"], self.commit)
            return {"ref": payload["ref"], "object": {"sha": payload["sha"]}}
        raise AssertionError((method, endpoint))


class FinalizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.site = Path(self.tmp.name) / "site"
        self.repo.mkdir(); self.site.mkdir()
        run(self.repo, "init", "-q")
        run(self.repo, "config", "user.name", "Test")
        run(self.repo, "config", "user.email", "test@example.invalid")
        self.write(self.repo, "README.md", b"Keep historical baseline\n")
        self.write(self.repo, "content/homepage.json", b'{"old":true}\n')
        self.write(self.repo, "docs/posts/old/index.html", b"<p>Keep historic body</p>\n")
        run(self.repo, "add", "."); run(self.repo, "commit", "-qm", "baseline")
        self.base = run(self.repo, "rev-parse", "HEAD")
        self.write(self.repo, "content/publications/new.json", b'{"source":"data only"}\n')
        run(self.repo, "add", "."); run(self.repo, "commit", "-qm", "source data")
        self.source = run(self.repo, "rev-parse", "HEAD")
        values = {"content/homepage.json": b'{"old":true,"new":true}\n',
                  "content/publications/new.json": b'{"source":"data only"}\n',
                  "docs/posts/new/index.html": b"<p>New article</p>\n"}
        changes = []
        base_entries = f.tree_entries(self.repo, self.base)
        for path, data in sorted(values.items()):
            self.write(self.site, path, data)
            old = base_entries.get(path)
            changes.append({"path": path, "mode": "100644", "status": "M" if old else "A",
                            "old_blob": old[1] if old else None, "new_blob": f.blob_sha(data),
                            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        self.plan = sign({"schema": "sayd-publication-plan-v1", "base_commit": self.base,
                          "source_commit": self.source, "compiler_commit": self.base,
                          "policy": {"allow_distribution": False}, "changes": changes})

    def write(self, root, path, data):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def finalize(self, api=None, plan=None, validator=lambda *args: None, **kwargs):
        plan = self.plan if plan is None else plan
        return f.finalize(self.repo, self.site, plan, self.base, self.source, self.base,
                          plan["plan_sha256"], api or FakeAPI(self), validator, **kwargs)

    def test_expected_tree_digest_matches_real_git(self):
        self.assertEqual(f.tree_sha(f.tree_entries(self.repo, self.source)),
                         run(self.repo, "rev-parse", self.source + "^{tree}"))
        self.write(self.repo, "x.y", b"file")
        self.write(self.repo, "x/a", b"nested")
        self.write(self.repo, "عربي/مقال.html", b"unicode")
        os.symlink("README.md", self.repo / "link")
        run(self.repo, "add", "."); run(self.repo, "commit", "-qm", "tree edge cases")
        head = run(self.repo, "rev-parse", "HEAD")
        self.assertEqual(f.tree_sha(f.tree_entries(self.repo, head)), run(self.repo, "rev-parse", head + "^{tree}"))

    def test_creates_only_fixed_review_branch_and_preserves_source_parent(self):
        api = FakeAPI(self)
        receipt = self.finalize(api)
        self.assertEqual(receipt["status"], "CREATED_REVIEW_ONLY")
        self.assertFalse(receipt["published"])
        self.assertFalse(receipt["merged"])
        refs = [call for call in api.calls if call[:2] == ("POST", "/git/refs")]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0][2]["ref"], "refs/heads/" + f.BRANCH_PREFIX + self.source)
        self.assertTrue(all(call[0] in ("GET", "POST") for call in api.calls))
        self.assertEqual(api.commit["parents"], [{"sha": self.source}])

    def test_identical_existing_branch_is_read_only_idempotent(self):
        first = FakeAPI(self)
        self.finalize(first)
        second = FakeAPI(self, existing=first.existing)
        receipt = self.finalize(second)
        self.assertEqual(receipt["status"], "ALREADY_EXISTS")
        self.assertFalse(any(c[0] == "POST" for c in second.calls))

    def test_conflicting_existing_branch_never_updates(self):
        api = FakeAPI(self, existing=("e" * 40, {"tree": {"sha": "f" * 40}, "parents": [], "message": "other"}))
        with self.assertRaisesRegex(f.Blocked, "conflicts"):
            self.finalize(api)
        self.assertFalse(any(c[0] == "POST" for c in api.calls))

    def test_stale_main_before_upload_has_no_mutation(self):
        api = FakeAPI(self, stale_at=1)
        with self.assertRaisesRegex(f.Blocked, "Main changed"):
            self.finalize(api)
        self.assertFalse(any(c[0] == "POST" for c in api.calls))

    def test_main_race_before_ref_creation_creates_no_ref(self):
        api = FakeAPI(self, stale_at=3)
        with self.assertRaisesRegex(f.Blocked, "Main changed"):
            self.finalize(api)
        self.assertFalse(any(c[:2] == ("POST", "/git/refs") for c in api.calls))

    def test_uncertain_ref_write_stops_without_retry(self):
        api = FakeAPI(self, fail_ref=True)
        with self.assertRaises(f.UncertainMutation):
            self.finalize(api)
        self.assertEqual(sum(c[:2] == ("POST", "/git/refs") for c in api.calls), 1)

    def test_no_content_plan_performs_no_api_call(self):
        plan = copy.deepcopy(self.plan); plan["changes"] = []; sign(plan)
        api = FakeAPI(self)
        receipt = self.finalize(api, plan)
        self.assertEqual(receipt["status"], "NO_CHANGES")
        self.assertEqual(api.calls, [])

    def test_compiler_scope_validator_runs_before_all_remote_operations(self):
        def blocked(*args):
            raise f.Blocked("Unrelated historical mutation")
        api = FakeAPI(self)
        with self.assertRaisesRegex(f.Blocked, "Unrelated"):
            self.finalize(api, validator=blocked)
        self.assertEqual(api.calls, [])

    def test_tampered_output_fails_before_api(self):
        (self.site / "docs/posts/new/index.html").write_text("tampered")
        api = FakeAPI(self)
        with self.assertRaisesRegex(f.Blocked, "Output bytes changed"):
            self.finalize(api)
        self.assertEqual(api.calls, [])

    def test_plan_digest_tampering_is_blocked(self):
        plan = copy.deepcopy(self.plan); plan["changes"][0]["bytes"] += 1
        with self.assertRaisesRegex(f.Blocked, "digest mismatch"):
            self.finalize(plan=plan)

    def test_read_only_build_digest_must_match_independent_build(self):
        with self.assertRaisesRegex(f.Blocked, "digest mismatch"):
            f.validate_plan(self.site, self.plan, self.base, self.source, self.base, "0" * 64)

    def test_distribution_cannot_be_self_authorized_by_plan(self):
        plan = copy.deepcopy(self.plan); plan["policy"]["allow_distribution"] = True; sign(plan)
        api = FakeAPI(self)
        with self.assertRaisesRegex(f.Blocked, "trusted dispatch"):
            self.finalize(api, plan)
        self.assertEqual(api.calls, [])
        self.assertEqual(self.finalize(plan=plan, allow_distribution=True)["status"], "CREATED_REVIEW_ONLY")

    def test_distribution_flag_integrates_with_real_compiler_validator(self):
        from publication_compiler import validate_report
        plan = copy.deepcopy(self.plan); plan["policy"]["allow_distribution"] = True; sign(plan)
        result = self.finalize(plan=plan, allow_distribution=True, validator=validate_report)
        self.assertEqual(result["status"], "CREATED_REVIEW_ONLY")

    def test_deleted_or_executable_file_is_blocked(self):
        for field, value in [("status", "D"), ("mode", "100755"), ("mode", "120000")]:
            plan = copy.deepcopy(self.plan); plan["changes"][0][field] = value; sign(plan)
            with self.subTest(field=field, value=value), self.assertRaises(f.Blocked):
                self.finalize(plan=plan)

    def test_old_blob_cannot_be_forged(self):
        plan = copy.deepcopy(self.plan); plan["changes"][0]["old_blob"] = "0" * 40; sign(plan)
        with self.assertRaisesRegex(f.Blocked, "trusted base"):
            self.finalize(plan=plan)

    def test_output_symlink_is_blocked(self):
        file = self.site / "docs/posts/new/index.html"
        file.unlink(); file.symlink_to(self.repo / "README.md")
        with self.assertRaisesRegex(f.Blocked, "Symlink"):
            self.finalize()

    def test_duplicate_paths_are_blocked(self):
        plan = copy.deepcopy(self.plan); plan["changes"].append(plan["changes"][0]); sign(plan)
        with self.assertRaisesRegex(f.Blocked, "Duplicate"):
            self.finalize(plan=plan)

    def test_safe_path_blocks_code_and_protected_inputs(self):
        for path in ["../docs/index.html", "/docs/index.html", "docs//index.html", "docs/./index.html",
                     "docs/../README.md", "docs\\index.html", "docs/.git/config", "scripts/publish.py",
                     ".github/workflows/evil.yml", "content/publication-contract.json", "assets/css/site.css",
                     "docs/assets/js/evil.js", "docs/assets/css/site.css", "audit/image-catalog/manifest/2026-01.tsv"]:
            with self.subTest(path=path), self.assertRaises(f.Blocked):
                f.safe_output_path(path)

    def test_dispatch_context_is_exact_and_default_branch_only(self):
        env = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
               "GITHUB_REPOSITORY": f.REPOSITORY, "GITHUB_REF": "refs/heads/main",
               "GITHUB_SHA": self.base, "GITHUB_WORKFLOW_REF": f.WORKFLOW,
               "GITHUB_WORKFLOW_SHA": self.base, "GITHUB_JOB": "finalize", "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2"}
        f.validate_context(env, self.base, self.source, self.base)
        receipt = f.workflow_receipt_context(env, self.base, self.source, self.base, True)
        self.assertEqual(receipt['run_id'], '123')
        self.assertEqual(receipt['run_attempt'], '2')
        self.assertEqual(receipt['workflow_sha'], self.base)
        self.assertEqual(receipt['workflow_ref'], f.WORKFLOW)
        self.assertEqual(receipt['event_name'], 'workflow_dispatch')
        self.assertEqual(receipt['policy'], {'allow_distribution': True})
        self.assertTrue(receipt['run_url'].endswith('/actions/runs/123/attempts/2'))
        for key in env:
            bad = dict(env); bad[key] = "untrusted"
            with self.subTest(key=key), self.assertRaises(f.Blocked):
                f.validate_context(bad, self.base, self.source, self.base)
        with self.assertRaises(f.Blocked):
            f.validate_context(env, self.base, "main", self.base)

    def test_api_never_supports_ref_update_or_credential_redirect(self):
        api = f.GitHub("synthetic-not-a-token")
        for method in ["PATCH", "PUT", "DELETE"]:
            with self.subTest(method=method), self.assertRaises(f.Blocked):
                api.request(method, "/git/refs/heads/main")
        with self.assertRaises(f.Blocked):
            f.NoRedirect().redirect_request(None, None, 301, "redirect", {}, "https://untrusted.invalid")


if __name__ == "__main__":
    unittest.main()
