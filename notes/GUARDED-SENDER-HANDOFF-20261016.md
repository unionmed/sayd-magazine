# Issue 36 — sender handoff inspection, 16 October 2026

Status: PARTIAL_IMPLEMENTATION / EXTERNAL_BINDING_BLOCKED. Do not resume the old task.

## Current evidence

- Read issue 36 and its sole comment, merged PR212 and PR37, current main gate and workflow, and the original incident report. The current gate remains a verifier/release producer, never a provider sender.
- ChatGPT task `6acb8fedc00c81919d10bd5270028e7d` remains disabled; last run 12 October, last update 12 October 21:05:06 UTC. Its prompt still instructs direct Metricool/provider calls. Peek does not expose the full trigger set. No task configuration was changed.
- Metricool read succeeded for Sayd brand 7119579, Facebook page 459225740767624. The planner query for 12 October–16 November returned both historical published items and drafts, despite its documented scheduled-only scope; classification used returned draft/provider fields, not the endpoint name.
- The old returned queue entries remain drafts. A separate growth post, ID 397259788, is non-draft, autoPublish=true, Facebook PENDING, timestamp 16 October 12:30 Asia/Beirut. Thus pausing the old task does not imply every external sender/queue is gated. No claim is made that this post passed the gate or that it has been published.
- No public test post was sent. Historical European/Bekaa links and cancelled drafts were not reactivated.

## Reused implementation and tests

`scripts/guarded_social_sender.py` calls the existing PR212 `publication_gate.verify` immediately before the transport callback. Its production entry fetches origin/main and uses the existing GitSource ancestry validation. It does not accept a previously generated receipt as authority. The transport receives the exact detached payload just checked, not a second unchecked provider request.

The existing canonical/short-link inventory, live short redirect, AR/EN/FR articles, titles, OG images, image bytes, placements, categories, latest and shared tickers remain checked by PR212. No new gate or weakened publication contract was introduced. Identity is the Arabic canonical; translations do not create independent deliveries. Current gate allows the Arabic canonical or its published short link for social reading links; English/French reading links are not separately supported payload identities.

The integration seam is Facebook-only. Instagram photo/carousel sends are blocked. Reels/Shorts require a separately validated video transport and are NOT silently treated as a photo send. This seam does not implement that transport.

A durable exclusive-create receipt prevents concurrent/repeated article+platform attempts, including a changed caption. PENDING is recorded as PENDING, never PUBLISHED. PUBLISHED requires a provider ID and public HTTPS URL. Timeout/malformed result leaves UNKNOWN_REQUIRES_RECONCILIATION and blocks retries. A trusted provider reader must reconcile ambiguous/pending outcomes; no automatic deletion/retry path is supplied. An ATTEMPTING record after crash also remains blocked.

Local verification: existing 21 gate tests plus 10 sender integration tests passed. Positive tests used fixture HTML and a fake transport; draft, missing French and wrong short redirect made zero transport calls. The unmerged production-entry case made zero transport calls. These are controlled integration tests, NOT a fresh live-site proof or a real Metricool end-to-end test. No independent reviewer was invoked in this run.

## Exact remaining blocker

The connected Metricool capability is a ChatGPT tool, not an importable transport available to repository Python. No authenticated Metricool transport, provider credential, deployed restricted worker, or durable delivery/reconciliation service has been supplied/verified. The tools exposed here do not let this code intercept or revoke direct ChatGPT Metricool/UI sends. Writing a prompt saying 'check first' would not enforce the boundary.

Completion requires a deployed sender whose sole provider-write path invokes `send`, a trusted fixed-brand/page adapter mapping the validated payload, durable shared ledger with reconciliation of actual provider statuses, and routing the existing task to that sender while removing its direct-send bypass. Preserve its complete original event subscriptions, exclusions and no-duplicate history. The current automation peek omits subscriptions, so they must be obtained through a capability exposing them before any prompt/trigger update. Do not guess/recreate them or create a competing automation.

Do not merge or re-enable as a claim of full production protection: this PR makes the independent code seam concrete and testable, but issue 36 remains open until the actual deployment and provider binding have been verified without public test posts.
