# One-time native Gulf release — 22 October 2026

Owner authorized the narrow native workflow, protected merge, publication and a
redeployment of today's unchanged site on 21 October. This PR changes **only four
operational files**. It does not add an article, alter a publication validator,
change branch/environment protection, create secrets or publish social content.

## Two isolated paths

1. **Installation today:** after independent review, marking this same-repository
   `ops/gulf-native-release-20261022` PR ready triggers the token-permission test.
   The installer requires its exact event head SHA, `main` base `06294d819…`, an
   exact four-file added-only allowlist and all normal PR checks green. It first
   reruns these exact-head checks with its own token and waits for success,
   proving Actions rerun permission and automatic admission today. It uses
   the ordinary GitHub merge API with `sha`, never a direct main push or bypass.
   It then proves `docs/` unchanged from the approved base, requests a Pages
   rebuild, waits for that merged SHA and verifies the current live lead in
   Arabic, English and French including home placement, ticker and image bytes.
2. **Publication tomorrow:** only `schedule` on `main`, fixed content PR/head SHA,
   fixed year/date. Start checks at 04:17, 04:37 or 04:57 Beirut (UTC+03); further
   cron entries at 05:07 and 05:17 recover a delayed/dropped trigger. A single
   concurrency group never cancels an active release. Completed checks older
   than actual Beirut midnight are rerun for this PR/head only; every discovered
   normal PR workflow must pass, including the protected Three-mirror check.
   It waits for **05:00 Beirut = 02:00 UTC** before normal protected merge.
   A late start may recover through **05:30 Beirut**, never later or on another
   day. No content commit is rewritten, and any other intervening main change
   blocks for reconciliation rather than overwriting a new publication.

## Permissions and evidence

The job token has only `contents: write`, `pull-requests: write`, `pages: write`
and `actions: write`. Actions write is used only to rerun this fixed content
head's normal CI and disable this exact workflow after verified success. Reads
of runs/jobs do not need an additional checks permission. No new token, secret,
admin privilege, bypass or environment approval change is introduced.

GitHub writes made with `GITHUB_TOKEN` do not automatically trigger Pages.
Therefore both paths explicitly request `POST /pages/builds`. The installer
proves actual Actions-rerun, normal-merge and Pages-request permissions today. The live verifier
requires the exact merged revision to remain `main` and checks the article,
AR/EN/FR canonical/hreflang/navigation, complete homepage placement, ten-item
shared ticker, category/Updates pages, internal links and exact image hashes.
It emits `release-receipt.json` plus `live-publication-receipt.json` as 90-day
run artifacts and a step summary. Success is not claimed at merge alone.

Duplicate cron runs reconcile an already merged exact head, require its merge
time not to predate authorization, reuse a successful exact-SHA Pages build,
and independently verify live content. No second merge occurs. After proof the
workflow disables **itself only**; a failed disable cannot undo publication and
the fixed date/year guard still prevents future publication. A denied or
ambiguous write is not blindly retried; ambiguous merge results are read back.

## Boundaries and failure handling

GitHub schedules can be delayed or dropped; redundant prestarts are mitigation,
not an exact-time guarantee. Deployment/CDN propagation starts **after** the
05:00 merge and may take minutes. Actual merge, build and live verification times
are recorded. A real CI failure, draft PR, moved head/base, merge protection,
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
