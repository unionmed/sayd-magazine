# Native maintenance of published articles

Technical implementation of the scoped owner-decision rule in AGENTS.md and
SOURCE-ONLY-PUBLICATION.md. This changes no editorial authority, general
publication rule, permission or merge/deployment requirement.

## Native route

The original publication compiler remains add-only. A separate closed data route
now reuses its request validator, isolated compiler, independent finalizer and
ordinary generated-candidate PR for body edits, withdrawal, ordinary category
transitions and an explicit inverse. No second writer, PAT, new secret,
PR-write permission, auto-approval, auto-merge or deployment action is added.

This infrastructure PR contains code/tests/documentation only. No request targets
a real article, and no actual article maintenance has been published.

## Source input and approval

On exact current main, add exactly one regular immutable file:
content/article-maintenance/<id>.json.

The closed sayd-article-maintenance-v1 schema is in article_maintenance.request().
It includes id, expected_base, publication_id, article_slug, one operation,
a bounded private decision_reference and a conflicts list. A disclosed conflict
records its rule reference, consequence and confirmation evidence reference.
After an article has maintenance history, previous_revision must name its exact
current revision. Unknown fields, mixed actions, executable markup, caller-chosen
output paths, duplicate JSON keys, ambiguous old text and stale inputs fail.

A private reference identifies evidence; it is not authenticated approval.
The reviewer must verify Nayef's actual decision, scope and any disclosed conflict
confirmation. Do not put private discussion text in public articles or records.
Compilation prepares review output; the existing protected merge/publication
review remains necessary.

Use the existing source/... branch, with a commit message ending in the exact
existing trailer block (preceded by one blank line):

    Sayd-Publication-Request: v1
    Distribution-Review-Scope: false

Use true instead of false only when the request includes an explicit placement
proposal, or restores a prior placement change. The validator independently
derives whether the output changes homepages/ticker and requires an exact match;
the trailer is review scope, never editorial authority.

The read-only source-request validator runs exact BASE code. The default-branch
workflow_run adapter rechecks actual repository, PR, run, source and base
identity. Compiler and independent finalizer rebuild the same request and
prepare only the existing review branch. The raw source PR is deliberately
unmergeable. Open the generated branch in a separate normal PR; inspect the
actual run/receipt and all required checks. Existing manual dispatch also works.
Neither route adds credentials or widens finalizer permissions.

## Supported decisions

| Operation | Bounded effect |
| --- | --- |
| edit | Explicit plain paragraph/internal-heading replacements in all three editions: six HTML/Markdown mirrors and selected search bodies |
| withdraw | Three stable noindex notices; ordinary archive-card/search/sitemap removal and redirect rich-preview cleanup; original Markdown retained |
| reclassify | Existing category badge, breadcrumb/structured metadata, Markdown category, dated archive cards, primary-door registry and selected search categories |
| restore | New decision naming the exact current revision; restore prior bytes/state while retaining both requests and ledgers |

Identity comes from immutable publication records. publication_id set to legacy
instead resolves existing reciprocal AR/EN/FR routes and original dates from
BASE. Six existing regular mirrors and matching canonical/alternate identities
are required. Historical pages are never regenerated from incomplete Markdown:
a requested body span absent from the source fails rather than approximating it.
No missing language is fabricated.

The category adapter covers existing Hunting & Equestrian, Gear, Land & Sea,
Science, Birds, Heritage, Laws and Photos archives. It does not invent taxonomy or convert an article into
a gallery. Original publication/update dates, media/rights, unrelated body bytes
and date ordering remain intact. Title, image/rights, credit, source and date
changes are not implicitly authorized by this route.

Without a placement proposal, existing homepage/ticker membership fails before
output. A placement object provides its own private decision_reference, the
exact lead, four side identities, eight latest identities and replacements for
affected existing desks. All proposed materials must have complete published
editions. Only the selected target may leave the news set; unrelated lead/slot
changes and same-day reordering fail. Required desk capacities, chronology,
Hunting rotation, language/image parity and every existing contract remain checked.
No new card is inferred from category/date. The ticker removes only the selected
entry, preserving other entries and the ceiling of ten rather than refilling it
without a decision. A changed lead is rebuilt from the selected existing article
card and receives the normal homepage SEO refresh.

Combined Hunting/Equestrian withdrawal and category transitions remove only the
selected identity from topic filters and update the exact card count; other
classification entries remain intact. Already reviewed marine membership uses
effective maintenance state so later combined-archive rebuilds cannot resurrect
a withdrawn/reclassified item. The shared ticker builder test compares every
source entry and enforces the existing ceiling; it does not require ten entries
after a nine-item withdrawal.

Protected TV/interview collection changes, multiple independent search facets
and unknown card shapes need a collection-specific decision/adapter. Existing
constraints that conflict with a particular future decision still require its
disclosed scoped implementation, not a blanket guard relaxation.

## Append-only history and current state

Trusted code generates content/maintenance-ledger/<id>.json; the requester cannot
supply it. It binds the request hash, exact base, language identities, original
publication date, predecessor/generation, before/after effective state and Git
blob/SHA-256 identities for every derived path. Editing/deleting previous
requests, ledgers, originals, media or rights evidence fails.

maintenance_state.py rejects broken/forked chains. Source originals remain audit
evidence; the latest ledger provides public status/classification. Search,
sitemap/SEO, classification and homepage eligibility respect this state.
SEO refuses stale article HTML on a withdrawn route. Normal candidate parity
also protects maintained legacy mirrors from unmanifested later changes.

Static Pages withdrawal is an HTTP 200 noindex notice, not HTTP 410. It does not
erase search-engine caches, public Git history, retained media, third-party
copies or social posts. Inline editorial backlinks can still lead to the notice;
text in unrelated stories is not silently changed.

A reverse is a new reviewed decision, not deletion of history or a blanket
publication revert. If any affected file has changed since the target revision,
automatic restore fails with its path; prepare a new scoped correction rather
than overwriting later work.

## Byte proof and checks

maintenance_native.source_input() accepts only one source file directly on BASE.
BASE code resolves all output paths/bytes. Code, protected files, originals,
media and rights cannot be changed by maintenance data.

The isolated candidate contains derived output plus its generated ledger, with
the original source commit as parent. Verification repeats the build from
immutable BASE and compares the entire tree, file modes, plan and provenance.
Source JSON, ledger data, an approved flag or a receipt is never a guard waiver.

The publication contract recognizes withdrawal only after non-recursive native
whole-tree recomputation, then checks the exact noindex notice and absence from
search. There is no blanket empty-article exception. The independent publication
guard also uses trusted-BASE replay. Maintenance goes into Proof.maintenance,
never new-publication Proof.additions, and grants no distribution authority.

All existing catalog, homepage, archive, ticker, hreflang, SEO, search,
related-image and navigation checks still run on the committed isolated stage.
The finalizer independently recomputes the source and retains its existing
review-ref-only restriction. A real candidate still needs actual exact-head
checks, owner-decision verification, linguistic review and publication approval.

## Synthetic verification

Focused tests cover the CLI, source validator, generated scope, stale/mixed/forged
inputs, modes/symlinks, exact replay, legacy identity, revision binding, no
resurrection and inverse decisions. Full stage checks run against synthetic
publications inside temporary full-corpus clones. Responsive QA renders
edit/reclassification/withdrawal in AR/EN/FR at 320, 390, 820 and 1440 pixels:
36 screenshots. Fixtures are never published or submitted to the native writer.

    python -m unittest discover -s scripts -p test_article_maintenance.py -v
    python -m unittest discover -s scripts -p test_maintenance_native.py -v
    python scripts/test_maintenance_browser_fixture.py --output /outside-checkout/qa

The standalone CLI continues to write an external review bundle only. It never
applies files; before/after bytes are private review material, not public assets.
Actual execution uses the native source-request/generated-candidate sequence.
Keep the infrastructure PR unmerged until review and approval. Infrastructure
approval does not select or approve a real article change.
