# One-time native Gulf release — 22 October 2026

Owner authorized the narrow native workflow, protected merge, publication and a
redeployment of today's unchanged site on 21 October. This PR changes **only four
operational files**. It does not add an article, alter a publication validator,
change branch/environment protection, create secrets or publish social content.

## Three isolated paths

1. **Installation today:** after independent review, marking this same-repository
   `ops/gulf-native-release-20261022` PR **#273** ready triggers the token-permission test.
   The installer requires its exact event head SHA, `main` base `06294d819…`, an
   exact four-file added-only allowlist and all normal PR checks green. It first
   reruns these exact-head checks with its own token and waits for success,
   proving Actions rerun permission and automatic admission today. It uses
   the ordinary GitHub merge API with `sha`, never a direct main push or bypass.
   It then proves `docs/` unchanged from the approved base, requests a Pages
   rebuild, waits for that merged SHA and verifies the current live lead in
   Arabic, English and French including home placement, ticker and image bytes.
2. **Midnight preflight only:** 00:03/00:23 Beirut on 22 October
   (21:03/21:23 UTC on 21 October), pinned date/year/head. It has only contents
   and PR read plus Actions write; it cannot merge or request Pages. Rerun the
   exact-head ordinary checks after real Beirut midnight and verify GitHub
   reports the post-install content PR clean/mergeable. Write a readiness
   receipt, exposing strict-up-to-date/review/check blockers hours early.
3. **Publication tomorrow:** only `schedule` on `main`, fixed content PR and exact approved payload manifest,
   fixed year/date. The final candidate SHA is frozen only after exhaustive payload
   validation, then held unchanged through CI and the merge request. Start checks at 04:17, 04:37 or 04:57 Beirut (UTC+03); further
   cron entries at 05:07 and 05:17 recover a delayed/dropped trigger. A single
   concurrency group never cancels an active release. Completed checks older
   than actual Beirut midnight are rerun for this PR/head only; every discovered
   normal PR workflow must pass, including the protected Three-mirror check.
   It waits for **05:00 Beirut = 02:00 UTC** before normal protected merge.
   A late start may recover through **05:30 Beirut**, never later or on another
   day. No content commit is rewritten, and any other intervening main change
   blocks for reconciliation rather than overwriting a new publication.

## Superseding the earlier operational handoff

The frozen content package's `notes/gulf-tourism-scheduled-release-20261022.md`
records the earlier assistant release/preflight automations
`6ad8935746d08191baeb28af6995325b` and `6ad89358970c8191b6e8cfecdb03bdbd`.
Once this native route has actually passed installation and the unchanged-site
test, the parent changes those automations to observers/fallback coordination,
not competing merge/rebase/publish executors. This operational clarification
supersedes their earlier launch role without editing the frozen content payload.
The native workflow itself never publishes or schedules Facebook.

## Exact payload pin and strict up-to-date protection

Strict branch protection can require the latest `main` in a content PR. Putting
that updated content SHA literally into a new main workflow commit creates an
endless base-update loop. Instead this workflow pins:

- content PR **#274**, original immutable commit
  `3f675e6596614caa1eefbedaf79009e1afa51e36` (tree
  `fefb9517693d6496ef9e9fbbc152155901b978c8`) and base `06294d819…`;
- SHA256 `7a8ab705288cf79b39ed666bc4700c5e1cbce581b65e884406466401e6431472`
  of its **complete raw Git diff**: 1,100 paths, 192,829 bytes, with full old/new
  blob IDs, old/new modes, status and NUL-delimited exact paths;
- source JSON SHA256 `4952d644…a7a40` independently reviewed for all three languages.

After installation, the content preparer merges **only** the exact installation
main into the content branch today through the approved connector. This does
not publish the content. No rebasing away the original approved ancestor, no
new content bytes, no new secret and no protection change are allowed.

Every preflight/release proves current main equals the immutable merge commit
of installation PR273, and is an ancestor of the candidate. All four operational
files in candidate must equal main exactly. The exhaustive `main → candidate`
raw diff must byte-equal `reviewed base → original approved content` and its
embedded hash; REST file-list truncation and rename heuristics are not used.
Missing/extra paths, deletions, mode changes, changed blobs, operational edits,
a different source hash or an unreviewed main commit block. The resulting
candidate SHA is frozen before CI, and candidate/main/manifest are rechecked
before normal merge with the same expected SHA. The resulting merge must have
exactly the installation and candidate parents, and its tree must equal the
candidate tree. Duplicate runs repeat these proofs rather than trusting a
merged flag. The raw manifest is retained in run artifacts.

## Permissions and evidence

The job token has only `contents: write`, `pull-requests: write`, `pages: write`
and `actions: write`. Actions write is used only to rerun this fixed content
candidate head's normal CI and disable this exact workflow after verified success. Reads
of runs/jobs do not need an additional checks permission. No new token, secret,
admin privilege, bypass or environment approval change is introduced.

GitHub writes made with `GITHUB_TOKEN` do not automatically trigger Pages.
Therefore both paths explicitly request `POST /pages/builds`. The installer
proves actual Actions-rerun, normal-merge and Pages-request permissions today. The live verifier
requires the exact merged revision to remain `main` and checks the article,
AR/EN/FR canonical/hreflang/navigation, complete homepage placement, ten-item
shared ticker, category/Updates pages, internal links and exact image hashes.
It emits `release-receipt.json` plus `live-publication-receipt.json` as 90-day
run artifacts and a step summary. Success is not claimed at merge alone. The normal merge API
atomically pins the PR head, not its base; the Pages build API has no revision
parameter. Immediate base/main reads and post-merge parent checks bound these
races but cannot make them atomic. Do not make competing main changes during
the release. A new publication tonight requires reviewed reconciliation/repinning.

Duplicate cron runs prove the same approved payload, exact installation parent
and candidate tree again before reconciling an already merged head; require its merge
time not to predate authorization, reuse a successful exact-SHA Pages build,
and independently verify live content. No second merge occurs. After proof the
workflow disables **itself only**; a failed disable cannot undo publication and
the fixed date/year guard still prevents future publication. A denied or
ambiguous write is not blindly retried; ambiguous merge results are read back.

## Boundaries and failure handling

GitHub schedules can be delayed or dropped; redundant prestarts are mitigation,
not an exact-time guarantee. Deployment/CDN propagation starts **after** the
05:00 merge and may take minutes. Actual merge, build and live verification times
are recorded. A real CI failure, draft PR, moved frozen head/base, merge protection,
changed site, permission denial, build error or unverified CDN result fails
closed and needs diagnosis; never relax a gate or publish a different SHA.
The parent observer owns timely alerts, an authorized fallback and Facebook.
This workflow never posts, queues or reschedules Facebook or any other social.

A marker of `RELEASE_SUCCESS` and the live receipt establish publication even if
subsequent self-disable/artifact upload fails. Investigate the receipt before
retrying. If the final cron starts after 05:30, it refuses to merge: an explicitly
reviewed rescheduling decision is required. Keep no recurring assistant merge
job competing with this route.

Official references: [schedule delays](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
[Pages build request](https://docs.github.com/en/rest/pages/pages#request-a-github-pages-build),
[workflow token triggers](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow).
