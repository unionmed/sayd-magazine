# Gulf hunting-tourism feature — scheduled release handoff

**HOLD: do not merge, deploy, enable auto-merge or publish the Facebook post early.**

- Authorized release start: **2026-10-22 05:00 Asia/Beirut = 2026-10-22 02:00 UTC**.
- Base: `06294d8192bc22b11dd2317261140fbbee8ae8f5`, preserving the published honey-buzzard feature.
- Branch: `publish/gulf-tourism-scheduled-20261022`.
- Arabic canonical: `https://sayd-magazine.com/posts/الصيد-السياحي-في-بلدان-الخليج-العربية/`.
- English/French slug: `hunting-tourism-arab-gulf-countries` under their respective editions.
- Source: `content/features/gulf-tourism-20261022.json`.
- Source SHA256 reviewed independently: `4952d6446c828a4541e5b07d2a34c8cc1b2d3992bd95f8d161c6e188909a7a40`.

## Owner-authorized scope

The owner's 21 October instruction schedules this episode as the homepage main feature, with one investigation news item in the ticker and one attractive Facebook post. The Reel is deferred until all three episodes are published. No Reel, later episode, other social network, new category, design change or premature publication is authorized by this package.

Exact Arabic headings:

- Small: **الصيد كسياحة ومورد تنمية ١من ٣**
- Main: **الصيد السياحي في بلدان الخليج العربية**

A short three-part investigation introduction and the titles of episodes 2 and 3 are included in AR/EN/FR. These future titles are ordinary non-clickable text, without invented publication dates or unfinished URLs. All approved article paragraphs, five section headings, four approved boxes, eight approved photographs and visible source-only captions are retained. Optional 2016 Al Marzoom photo is excluded. Original approved image bytes are retained, including the WebP cover; internal source metadata is in the source JSON.

## Release operations

1. **Before release, keep the PR draft and unmerged.** Local preparation used an external preview-only clock to render and exercise the 22 October state. That helper is deliberately not in the repository. No test or production date guard is changed.
2. The unchanged ticker date guard intentionally rejects the 22 October article before Beirut midnight. After **21 October 21:00 UTC**, rerun all real, unchanged CI for the exact final PR head; do not treat preview-time results as actual release readiness.
3. Fetch current `main`. If newer than the recorded base, retain those changes, recompute only the authorized placement and rerun tests. Never reset `main` or erase intervening publications.
4. Verify all three article versions, eight images, four boxes, final headings, series introduction and two non-clickable episode titles. Confirm source hash and final reviewed head. Run the narrow Gulf exact-delta tests plus all existing required CI.
5. At or after **22 October 02:00 UTC**, and only with green required CI and no unresolved content/merge blockers, merge the exact approved head. Do not enable auto-merge in advance.
6. Wait for Pages deployment and independently verify AR/EN/FR public articles, images and canonical/hreflang, the Gulf lead, prior lead first under-main card, chronological displacement into Updates, matching ten-item ticker on homepage and inner pages, and retained honey-buzzard Science placement. Deployment may take a few minutes after the requested start time.
7. Only after the live Arabic link works and article/home/ticker are verified, publish the approved Facebook-only payload. Parent owns that payload and existing release automation; avoid duplicate scheduling or posting. Verify the external result and report its actual URL/time.

Release automation registered by parent: `6ad8935746d08191baeb28af6995325b` (05:00 Beirut). Preflight: `6ad89358970c8191b6e8cfecdb03bdbd` (00:05 Beirut). These identifiers document the handoff, not evidence of a completed future release.

## Reproducible checks (real publication date or later)

```bash
python scripts/publish_gulf_tourism_20261022.py
python scripts/test_gulf_tourism_20261022.py --base 06294d8192bc22b11dd2317261140fbbee8ae8f5
python scripts/check_publication_contract.py --base 06294d8192bc22b11dd2317261140fbbee8ae8f5
python scripts/test_homepage_doors.py
python scripts/test_shared_ticker.py
python scripts/test_hreflang_contract.py
python scripts/test_archive_media_contract.py
python scripts/test_archive_access.py
python scripts/test_combined_hunting_equestrian.py --base 06294d8192bc22b11dd2317261140fbbee8ae8f5
SAYD_BASE_COMMIT=06294d8192bc22b11dd2317261140fbbee8ae8f5 python scripts/test_header_social.py
python scripts/test_search_index.py
```

Use the current PR base instead if `main` advances, and retain all historical pinned preservation proofs. Required aggregate/browser CI is not replaced by this focused command list. Any check that remains blocked must be disclosed; never weaken a check or misdate the article to turn it green.
