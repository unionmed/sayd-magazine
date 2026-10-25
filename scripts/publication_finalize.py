#!/usr/bin/env python3
"""Create one review-only branch from a twice-built, trusted publication plan.

This program never updates a ref, creates/approves a PR, merges, or deploys.
It runs only in the validated default-branch dispatch/request workflow. The compiler
must be trusted main code; source commits are data, never executable checkouts.
An uncertain API mutation is reported and STOPPED, never automatically retried.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "unionmed/sayd-magazine"
WORKFLOW = f"{REPOSITORY}/.github/workflows/source-publication.yml@refs/heads/main"
BRANCH_PREFIX = "review/source-publication-"
SHA = re.compile(r"[0-9a-f]{40}\Z")
# Conservative internal request budgets, not claimed GitHub API maxima.
TREE_BATCH_BYTES = 4 * 1024 * 1024
TREE_BATCH_ENTRIES = 64
TREE_BATCH_COUNT = 64
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class Blocked(ValueError):
    pass


class UncertainMutation(Blocked):
    """An API operation may have happened; inspect remotely before any retry."""


def require(condition, message):
    if not condition:
        raise Blocked(message)


def full_sha(value):
    require(isinstance(value, str) and SHA.fullmatch(value), "Expected an exact commit/blob SHA")
    return value


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def canonical_plan(plan):
    return json.dumps({k: v for k, v in plan.items() if k != "plan_sha256"},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_context(env, base, source, compiler):
    for value in (base, source, compiler):
        full_sha(value)
    require(base == compiler, "Dispatch must use the exact current-main compiler/base")
    require(env.get("GITHUB_EVENT_NAME") in ("workflow_dispatch", "workflow_run"), "Untrusted workflow event")
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REF": "refs/heads/main",
        "GITHUB_SHA": compiler, "GITHUB_WORKFLOW_REF": WORKFLOW,
        "GITHUB_WORKFLOW_SHA": compiler, "GITHUB_JOB": "finalize",
    }
    for key, value in expected.items():
        require(env.get(key) == value, f"Untrusted workflow context: {key}")
    require(re.fullmatch(r"[0-9]+", env.get("GITHUB_RUN_ID", "")), "Missing trusted run ID")
    require(re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ATTEMPT", "")), "Missing trusted run attempt")


def workflow_receipt_context(env, base, source, compiler, allow_distribution):
    """Actual validated runner context, never copied from submitted source data.

    These are audit pointers, not a signature. Reviewers must retrieve the
    artifact from this real GitHub run and verify owner publication authority.
    """
    validate_context(env, base, source, compiler)
    return {"run_id": env["GITHUB_RUN_ID"], "run_attempt": env["GITHUB_RUN_ATTEMPT"],
            "workflow_ref": env["GITHUB_WORKFLOW_REF"], "workflow_sha": env["GITHUB_WORKFLOW_SHA"],
            "event_name": env["GITHUB_EVENT_NAME"], "job": env["GITHUB_JOB"], "ref": env["GITHUB_REF"],
            "policy": {"allow_distribution": bool(allow_distribution)},
            "run_url": f'https://github.com/{REPOSITORY}/actions/runs/{env["GITHUB_RUN_ID"]}/attempts/{env["GITHUB_RUN_ATTEMPT"]}'}


def safe_output_path(value):
    require(isinstance(value, str) and value and "\\" not in value and "\x00" not in value,
            "Unsafe output path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value
            and all(part not in ("", ".", "..", ".git") for part in path.parts),
            "Unsafe/noncanonical output path")
    require(not any(ord(c) < 32 or ord(c) == 127 for c in value), "Control character in output path")
    # Defense in depth, in addition to the compiler's exact bundle-derived scope.
    # No source or generated executable, workflow, policy, CSS, JS, or contract.
    allowed = (
        value in {"content/en/pairs.json", "content/fr/edition-2026.json",
                  "content/homepage.json", "content/ticker.json", "content/article-updates.json",
                  "content/interviews.json", "content/marine-fishing.json"}
        or (value.startswith("content/publications/") and len(path.parts) == 3 and path.suffix == ".json")
        or (value.startswith("content/caption-revisions/") and len(path.parts) == 3 and path.suffix == ".json")
        or (path.parts[:2] in {("content", "article-maintenance"), ("content", "maintenance-ledger")}
            and len(path.parts) == 3 and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}\.json',path.name))
        or (path.parts[:2] in {("content", "posts"), ("content", "en"), ("content", "fr")}
            and len(path.parts) == 3 and path.suffix == ".md")
        or (value.startswith("audit/image-catalog/manifest/release-")
            and len(path.parts) == 4 and path.suffix == ".tsv")
        or (path.parts[0] == "docs" and path.suffix in {".html", ".json", ".xml"}
            and not value.startswith(("docs/assets/css/", "docs/assets/js/")))
        or (value.startswith("docs/media/publications/")
            and len(path.parts) == 5 and path.suffix in {".jpg", ".jpeg", ".png", ".webp"})
    )
    require(allowed, f"Finalizer forbids this output path: {value}")
    return path


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def read_change(site, item):
    path = safe_output_path(item.get("path"))
    require(item.get("mode") == "100644", "Only regular non-executable output files are accepted")
    require(item.get("status") in ("A", "M"), "Deletions/renames are forbidden")
    full_sha(item.get("new_blob"))
    if item.get("old_blob") is not None:
        full_sha(item["old_blob"])
    require(isinstance(item.get("sha256"), str) and SHA256.fullmatch(item["sha256"]), "Invalid output digest")
    require(type(item.get("bytes")) is int and item["bytes"] >= 0, "Invalid output size")
    target = site.joinpath(*path.parts)
    require(not site.is_symlink(), "Symlinked output root")
    cursor = site
    for component in path.parts:
        cursor = cursor / component
        require(not cursor.is_symlink(), "Symlinked output component")
    require(target.is_file(), f"Missing output file: {path}")
    data = target.read_bytes()
    require(len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
            and blob_sha(data) == item["new_blob"], f"Output bytes changed: {path}")
    return data


def validate_plan(site, plan, base, source, compiler, expected_plan):
    require(isinstance(plan, dict) and plan.get("schema") == "sayd-publication-plan-v1", "Unknown plan schema")
    for field, value in (("base_commit", base), ("source_commit", source), ("compiler_commit", compiler)):
        require(plan.get(field) == full_sha(value), f"Plan {field} mismatch")
    require(isinstance(expected_plan, str) and SHA256.fullmatch(expected_plan), "Invalid read-only build digest")
    actual = hashlib.sha256(canonical_plan(plan)).hexdigest()
    require(plan.get("plan_sha256") == actual == expected_plan, "Independent build/plan digest mismatch")
    changes = plan.get("changes")
    require(isinstance(changes, list), "Missing changes list")
    paths = [item.get("path") for item in changes if isinstance(item, dict)]
    require(len(paths) == len(changes) and all(isinstance(p, str) for p in paths), "Invalid changes")
    require(paths == sorted(set(paths)), "Duplicate or unordered change paths")
    return [(item, read_change(site, item)) for item in changes]


def tree_entries(root, commit):
    entries = {}
    for row in git(root, "ls-tree", "-rz", "--full-tree", full_sha(commit)).split(b"\0"):
        if not row:
            continue
        meta, path = row.split(b"\t", 1)
        mode, kind, sha = meta.decode("ascii").split(" ")
        require(kind in ("blob", "commit"), "Unexpected source tree object")
        entries[path.decode("utf-8")] = (mode, sha)
    return entries


def tree_sha(entries):
    """Compute Git tree IDs without writing or trusting a generated .git folder."""
    root = {}
    for path, value in entries.items():
        node = root
        parts = path.split("/")
        for component in parts[:-1]:
            require(component not in node or isinstance(node[component], dict), "Tree path collision")
            node = node.setdefault(component, {})
        require(parts[-1] not in node, "Duplicate tree path")
        node[parts[-1]] = value

    def digest(node):
        rows = []
        for name, value in node.items():
            directory = isinstance(value, dict)
            mode, sha = ("40000", digest(value)) if directory else value
            rows.append(((name + ("/" if directory else "")).encode("utf-8"),
                         mode.encode() + b" " + name.encode("utf-8") + b"\0" + bytes.fromhex(sha)))
        data = b"".join(row for _, row in sorted(rows))
        return hashlib.sha1(b"tree " + str(len(data)).encode() + b"\0" + data).hexdigest()
    return digest(root)


def api_json(payload):
    """One exact UTF-8 wire encoding for request sizing and transmission."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def prepare_tree_batches(changes, source_entries, original_tree):
    """Prevalidate all bytes and bound every mutation before the first POST.

    Source/base objects are already present remotely. Reuse those exact SHAs;
    novel generated text is written inline by GitHub's documented Trees API.
    Unknown binary output fails closed instead of adding a second upload path.
    """
    known_blobs = {sha for mode, sha in source_entries.values() if mode == "100644"}
    entries = []
    for item, data in changes:
        path, sha = item["path"], item["new_blob"]
        if source_entries.get(path) == ("100644", sha):
            continue
        entry = {"path": path, "mode": "100644", "type": "blob"}
        if sha in known_blobs:
            entry["sha"] = sha
        else:
            try:
                text = data.decode("utf-8", errors="strict")
            except UnicodeDecodeError as error:
                raise Blocked("Binary output is not an existing validated source blob: " + path) from error
            require(text.encode("utf-8") == data and blob_sha(data) == sha,
                    "Inline content differs from validated bytes")
            entry["content"] = text
        entries.append((entry, sha))
    batches, pending = [], []
    current = dict(source_entries)
    parent_tree = original_tree
    def finish():
        nonlocal pending, parent_tree
        if not pending:
            return
        payload = {"base_tree": parent_tree, "tree": [entry for entry, _ in pending]}
        require(len(api_json(payload)) <= TREE_BATCH_BYTES, "Tree request exceeds bounded byte budget")
        for entry, sha in pending:
            current[entry["path"]] = ("100644", sha)
        expected = tree_sha(current)
        batches.append((payload, expected))
        require(len(batches) <= TREE_BATCH_COUNT, "Publication exceeds bounded tree request budget")
        parent_tree, pending = expected, []
    for entry, sha in entries:
        trial = {"base_tree": parent_tree, "tree": [e for e, _ in pending] + [entry]}
        if pending and (len(pending) >= TREE_BATCH_ENTRIES or len(api_json(trial)) > TREE_BATCH_BYTES):
            finish()
        pending.append((entry, sha))
        require(len(api_json({"base_tree": parent_tree, "tree": [e for e, _ in pending]}))
                <= TREE_BATCH_BYTES, "Single tree entry exceeds bounded byte budget")
    finish()
    return batches, parent_tree


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Blocked("GitHub API redirect refused; token is never forwarded")


class GitHub:
    def __init__(self, token):
        require(bool(token), "Missing final-step GitHub token")
        self.token = token
        self.opener = build_opener(NoRedirect())

    def request(self, method, endpoint, payload=None, missing=False):
        require(method in ("GET", "POST") and endpoint.startswith("/git/"), "Unsupported API operation")
        # This client cannot PATCH/PUT/DELETE refs, change permissions or merge.
        url = f"https://api.github.com/repos/{REPOSITORY}{endpoint}"
        body = None if payload is None else api_json(payload)
        req = Request(url, data=body, method=method, headers={
            "Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Sayd-Source-Publication/1",
            "Content-Type": "application/json",
        })
        try:
            with self.opener.open(req, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            if method == "GET" and missing and error.code == 404:
                return None
            try:
                detail = str(json.loads(error.read()).get("message", ""))
                detail = " ".join(detail.split())[:500]
            except (ValueError, AttributeError, OSError):
                detail = ""
            if method != "GET" and error.code >= 500:
                raise UncertainMutation(f"Uncertain {method} {endpoint}: HTTP {error.code} {detail}; stop and inspect, do not retry") from error
            raise Blocked(f"GitHub rejected {method} {endpoint}: HTTP {error.code} {detail}; no retry") from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            kind = UncertainMutation if method != "GET" else Blocked
            raise kind(f"{'Uncertain mutation' if method != 'GET' else 'Read failed'} {method} {endpoint}; stop and inspect, do not retry") from error


def check_main(api, base):
    current = api.request("GET", "/git/ref/heads/main")
    require(current.get("object", {}).get("sha") == base, "Main changed: rebuild/review against the new base; no ref written")


def verify_commit(commit, expected_tree, source, message):
    require(commit.get("tree", {}).get("sha") == expected_tree, "Review branch tree conflicts with the verified output")
    require([p.get("sha") for p in commit.get("parents", [])] == [source], "Review branch parent conflicts")
    require(commit.get("message") == message, "Review branch provenance conflicts")


def finalize(root, site, plan, base, source, compiler, expected_plan, api, compiler_validator,
             allow_distribution=False, pre_write_check=None):
    """All validation precedes API mutations. api is injectable for offline tests."""
    require(isinstance(plan, dict), "Invalid plan object")
    require(plan.get("policy") == {"allow_distribution": bool(allow_distribution)},
            "Plan distribution scope differs from the trusted dispatch choice")
    changes = validate_plan(site, plan, base, source, compiler, expected_plan)
    compiler_validator(site, plan, base, source, compiler, allow_distribution)
    source_entries = tree_entries(root, source)
    original_tree = git(root, "rev-parse", source + "^{tree}").decode().strip()
    require(tree_sha(source_entries) == original_tree, "Source tree digest mismatch")
    batches, batched_tree = prepare_tree_batches(changes, source_entries, original_tree)
    base_entries = tree_entries(root, base)
    for item, _ in changes:
        old = base_entries.get(item["path"])
        require(item["old_blob"] == (old[1] if old else None), "Old output blob differs from trusted base")
        require(item["status"] == ("M" if old else "A"), "Output change type differs from base")
        require(not old or old[0] == "100644", "Cannot replace nonregular historical file")
        source_entries[item["path"]] = ("100644", item["new_blob"])
    expected_tree = tree_sha(source_entries)
    require(batched_tree == expected_tree, "Batched tree differs from independently validated final tree")
    branch = BRANCH_PREFIX + full_sha(source)
    receipt = {"schema": "sayd-review-branch-receipt-v1", "repository": REPOSITORY,
               "base_commit": base, "source_commit": source, "compiler_commit": compiler,
               "plan_sha256": expected_plan, "branch": branch, "tree": expected_tree,
               "published": False, "merged": False, "required_next_step": "Open a normal PR and run checks on the exact generated commit; no publication authorized here"}
    if not changes:
        return dict(receipt, status="NO_CHANGES", branch=None)
    check_main(api, base)
    source_remote = api.request("GET", "/git/commits/" + source)
    require(source_remote.get("tree", {}).get("sha") == original_tree, "Remote source differs from local source")
    message = (f"Generate source-only publication review candidate {source}\n\n"
               f"Source-Publication-Plan: {expected_plan}\nCompiler-Commit: {compiler}\nBase-Commit: {base}\n"
               f"Distribution-Review-Scope: {str(bool(allow_distribution)).lower()}")
    endpoint = "/git/ref/heads/" + branch
    existing = api.request("GET", endpoint, missing=True)
    if existing is not None:
        sha = full_sha(existing.get("object", {}).get("sha"))
        verify_commit(api.request("GET", "/git/commits/" + sha), expected_tree, source, message)
        check_main(api, base)
        return dict(receipt, status="ALREADY_EXISTS", commit=sha)
    if pre_write_check:
        pre_write_check()
    for payload, expected_batch_tree in batches:
        check_main(api, base)
        tree = api.request("POST", "/git/trees", payload)
        require(tree.get("sha") == expected_batch_tree, "Generated remote tree differs; no ref created")
    check_main(api, base)
    commit = api.request("POST", "/git/commits", {"message": message, "tree": expected_tree, "parents": [source]})
    sha = full_sha(commit.get("sha"))
    verify_commit(api.request("GET", "/git/commits/" + sha), expected_tree, source, message)
    # The only ref mutation is an atomic CREATE of a derived review branch.
    # A race (422), timeout, or ambiguous response stops; it never updates/retries.
    check_main(api, base)
    if pre_write_check:
        pre_write_check()
    created = api.request("POST", "/git/refs", {"ref": "refs/heads/" + branch, "sha": sha})
    if created.get("ref") != "refs/heads/" + branch or created.get("object", {}).get("sha") != sha:
        raise UncertainMutation("Uncertain POST /git/refs response for " + branch + "; inspect, do not retry")
    try:
        observed = api.request("GET", endpoint)
        require(observed.get("object", {}).get("sha") == sha, "Review branch readback mismatch")
    except Blocked as error:
        raise UncertainMutation("Review branch creation was acknowledged but readback failed for "
                                + branch + "; inspect, do not retry") from error
    return dict(receipt, status="CREATED_REVIEW_ONLY", commit=sha)


def request_binding_check(root, env, base, source, allow_distribution):
    """Return a fresh-read check; workflow_run cannot fall back to dispatch."""
    if env.get('GITHUB_EVENT_NAME') != 'workflow_run':
        return None
    from publication_request import resolve_local
    event = json.loads(Path(env['GITHUB_EVENT_PATH']).read_text())
    def check():
        verified = resolve_local(root, event, env, fetch=False)
        require(verified['base'] == base and verified['source'] == source
                and verified['allow_distribution'] == allow_distribution, 'Request binding changed')
        return verified
    return check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("site", "report", "base", "source", "compiler", "expected-plan", "receipt"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allow-distribution", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    provenance = workflow_receipt_context(os.environ, args.base, args.source, args.compiler, args.allow_distribution)
    require(git(root, "rev-parse", "HEAD").decode().strip() == args.compiler, "Compiler checkout differs from trusted workflow SHA")
    require(not git(root, "status", "--porcelain", "--untracked-files=all").strip(), "Trusted compiler worktree is not clean")
    request_check = request_binding_check(root, os.environ, args.base, args.source, args.allow_distribution)
    if request_check:
        provenance['request'] = request_check()
    from publication_compiler import validate_report
    plan = json.loads(Path(args.report).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(Blocked("Nonfinite JSON")))
    try:
        receipt = finalize(root, Path(args.site), plan, args.base, args.source, args.compiler,
                           args.expected_plan, GitHub(os.environ.get("GITHUB_TOKEN")), validate_report,
                           allow_distribution=args.allow_distribution, pre_write_check=request_check)
    except (ValueError, subprocess.CalledProcessError) as error:
        receipt = {"schema": "sayd-review-branch-receipt-v1", "repository": REPOSITORY,
                   "base_commit": args.base, "source_commit": args.source, "compiler_commit": args.compiler,
                   "plan_sha256": args.expected_plan, "branch": BRANCH_PREFIX + args.source,
                   "status": "UNCERTAIN_STOPPED" if isinstance(error, UncertainMutation) else "BLOCKED",
                   "reason": str(error), "published": False, "merged": False,
                   "automatic_retry_allowed": False}
        receipt.update(provenance)
        Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        raise
    receipt.update(provenance)
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"PUBLICATION FINALIZER BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(1)
