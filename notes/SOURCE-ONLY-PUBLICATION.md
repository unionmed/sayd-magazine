# Source-only publication: prospective, review-only workflow

## Purpose and boundary

New publications submit small immutable data records and their new local photos,
not copies of the historical translation, search, homepage, sitemap or archive
indexes. Trusted code on the exact current `main` prepares those compatibility
files on a separate review branch. **Compilation is not publication approval.**
No existing article, image inventory snapshot or editorial provenance is migrated.
Existing rendered articles and listing cards remain authoritative historical data;
Markdown is not a complete replacement for that history.

The first infrastructure PR must contain no pending article/image publication.
The existing protected merge and Pages deployment remain unchanged. Do not use
this prospective workflow to reroute a previously rejected aggregate upload.

## Owner decisions and scoped maintenance — 25 October 2026

The governing Arabic rule is the section “قرارات نايف الخاصة وحدود القواعد العامة”
in AGENTS.md. Preservation protects against unintended changes; it is not an
editorial veto over Nayef's informed, explicitly approved amendment, removal, or
reclassification of a particular publication.

Explain a concrete conflict with an existing publication rule and its consequence
to Nayef before executing an exception. Once he confirms the informed decision,
execute only that decision's scope without asking for the same approval again.
A decision about one article does not change the general rule or grant authority
over other articles; a permanent rule change requires his explicit statement.

Keep original publication records as provenance while providing separately
reviewed, bounded maintenance for their effective public text, availability, or
classification. An approved removal can remove public availability while retaining
private/audit history. The current add-only compiler and caption-only revision path
do not yet implement general body revisions, withdrawal, or reclassification.
Documentation of authority alone does not make those code paths exist or make
their checks pass: prepare the narrowly necessary implementation and normal review,
preserving unrelated content and protections. Do not claim a technical hard stop
is a separate editorial decision by Nayef, and do not silently turn a single
exception into a general guard relaxation.

## Sources and generated compatibility outputs

One atomic source commit, directly on the exact current `main`, may only ADD:

* `content/publications/<release-id>.json` (`sayd-publication-v1`);
* `docs/media/publications/<release-id>/<lowercase-name>.<jpg|jpeg|png|webp>`;
* `audit/image-catalog/manifest/release-<release-id>.tsv`, exactly the new photo
  paths, Git blob hashes and byte counts, with `path\tgit_blob_sha\tsize_bytes` header.

Existing local photos can be referenced without copying them or changing their
old catalog rows. A media-only record has `articles: []`. New records and media are
immutable; corrections to already published articles remain a separately reviewed
maintenance task, not an implicit add-only update permission. The sole bounded
caption-only exception is described below; it keeps original records immutable.

The compiler generates only the requested new article Markdown/HTML, three-language
pairs and French aliases, explicit category/archive cards, search entries,
short-link aliases/stubs, sitemap entries, local image associations and requested
homepage/ticker placement. French routes now read additive records instead of
requiring a new source-code constant for each article. The old alias map is retained.
Catalog taxonomy/association working files stay ignored under `.catalog-build`;
old `article-image-links.json`, taxonomy snapshots and old TSV shards are unchanged.

Homepage/ticker placement is **not inferred** from category or date. Manual dispatch defaults to `allow_distribution=false`; connector requests must
state `true` or `false` explicitly in their immutable trailer. `true` only permits
preparing requested broader placement for review. The JSON's `approval_reference`,
the dispatch flag and the generated commit message are not evidence that the owner
approved the article or its placement. Explicit editorial approval remains separate.

## Data contract

See `scripts/publication_schema.py` for the exact closed schema and
`scripts/test_publication_compiler.py::record` for a synthetic, non-publication
example. Unknown fields, raw HTML, executable hooks/patches, duplicate JSON keys,
unsafe URLs/paths/modes and route collisions fail closed.

Use evidence identifiers/links, not private conversation dumps or secrets.
Each record contains a release ID, exact `expected_base`, an editorial decision
reference, a photo-bank search evidence reference, photos, and zero to ten articles.
Each photo records the exact published SHA-256 and original-source SHA-256,
source/evidence reference, optional HTTPS source/license reference, explicit rights
status and evidence, and localized alt/caption text. Empty caption strings explicitly omit visible
figcaptions; descriptive alt text and end-of-article photo credit remain required. These declarations are retained
but do not prove rights, identity, bank search quality or editorial approval; a
reviewer must inspect the evidence. New/reused publication photos are fully decoded
and limited to static JPEG/PNG/WebP, 30 MB and 40 megapixels. Existing historical
media outside the new bundle are not re-encoded or newly rejected.

A distinct `user_selected_source_unresolved` photo status can accurately retain an
informed owner selection of user-supplied photos whose external rights and
photographic authenticity remain unresolved. It requires `user_supplied: true`,
`external_rights_verified: false`, `authenticity_verified: false`, and a private
bounded `private:<evidence-id>` identifier in `editorial_authorization_reference`. It cannot claim a
verified license URL, ownership, authenticity or unrestricted future reuse.
These fields are declarations, not an approval mechanism: before publication the
reviewer must independently verify the exact informed owner decision and photo
hashes. Normal licensed-image evidence and legally required attribution remain
unchanged, including when visible descriptive captions are omitted. Never relabel
this unresolved status as licensed or verified permission to make a test pass.

The one exact `dubai-carnival-20261105` release accommodates the owner's selected,
assistant-found `meydan-archive` photo without mislabeling it as user-supplied.
It requires exactly one photo and one article, the fixed local path, published and
source SHA-256, AR/EN/FR slugs and private selection-evidence identifier in the
schema. Only this bundle requires `user_supplied: false` with the existing
`user_selected_source_unresolved` status. Both verification flags remain strictly
`false`; license URLs and ownership/licence/permission statuses are rejected.
The evidence identifier is a declaration, not an approval mechanism or proof of
external rights. Independently review the informed owner decision, attribution,
source and bytes before publication. All other releases retain the original
user-supplied requirement; normal photo-integrity, compilation, review and
protected publication gates remain unchanged.

The one exact `arab-radar-october-2026` publication has a bounded schema exception:
its nine fixed photo IDs, local paths, published/source SHA-256 values, order,
trilingual slugs and section placements must match the constants in the schema.
It contains exactly one article using those nine photos, with empty captions.
For this bundle the `rights` field is omitted and rejected if present. This adds
no permission status, verification claim or reusable authorization. Every other
release retains the existing required photo fields and validation. Photo integrity,
source references, alt text, compilation review and all publication gates remain.

Each article has complete AR/EN/FR slugs, author, title, description, subtitle,
plain-text sections, sources, end-of-article photo credit and optional ticker title.
Photo order is explicit and identical across languages. Sources use credential-free
HTTPS links; metadata can retain legitimate external license references. Public
text, source wording and links still require normal editorial review.

An optional article-level `photo_placements` list places interior photographs after
specified sections, identically in all languages. Each entry contains only
`photo_id` and zero-based integer `after_section`. The first photo remains the cover
and must not appear in the list. Every remaining article photo must appear exactly
once, in article photo order, with nondecreasing section indices valid in **all**
three translations. Multiple photos may share a section, in the declared order.
An empty list is valid only for a cover-only article. No raw HTML or per-language
placement override is accepted. When absent, the existing automatic placement and
overflow behavior remains byte-identical. Empty captions still omit figcaptions;
alt text, end credit and source/rights evidence remain required.


`primary_door` and explicit `archives` are distinct from distribution. Supported
new material includes normal trilingual news, Science features with a secondary
Bird Encyclopedia listing, and multi-image Photos galleries with one institutional
end credit. Supported placements are `archive-only`, `door`, `latest`, `side`,
`lead`; ticker selection is an explicit boolean. Birds/Laws reference entries
remain archive-only, and galleries cannot enter news/ticker slots. An explicit
no-updates/no-ticker rotation can retain a feature's permanent secondary archive.
Per the explicit 24 October 2026 clarification, original publication-date order
has priority. The former lead enters the side-card pool at its chronological rank,
first only if newest; it is not pinned or guaranteed retention beyond four slots.
Its ordinary overflow follows Updates/category/archive routing with existing
no-Updates/no-ticker exclusions preserved. A batch gathers lead and side requests
before ranking, so record order cannot change the result. Equal dates preserve
existing pool order; new requested tied cards use canonical slug order. No date
is changed, and the unchanged publication contract still enforces chronology.

V1 does not reclassify existing articles, import old archives, edit protected design,
create a new taxonomy/door, register new interview collections, or publish TV/video.
Those need separately scoped reviewed maintenance. Legacy pages are never rebuilt
from incomplete Markdown. This replaces aggregate uploading for supported **new**
publication, not every historical repair process.

## Trust and permissions

* Pull-request parity runs the immutable BASE compiler, not source-PR code.
* Source input is fetched as exact Git blobs; no source branch script is run.
* Read-only compile and write-capable finalization are separate jobs. The writer
  independently rebuilds the same input without consuming an uploaded filesystem.
* Workflow-level permission is `contents: read`. Only `finalize` has the existing
  built-in `GITHUB_TOKEN` `contents: write`; no PAT, new secret, Actions-write,
  PR-write, Pages-write, environment grant or repository setting change is added.
* The token is exposed only to the final API step. Checkouts do not persist it.
  Actions are pinned to commits. There is no `pull_request_target` execution.
* The finalizer accepts only the expected repository/default-main workflow context,
  exact base/source/compiler/plan/tree hashes, and regular allowed paths. It may
  only CREATE `review/source-publication-<full-source-SHA>`; it cannot update/delete
  a ref or write `main`. This is a program restriction, not a claim that GitHub's
  contents token is itself intrinsically branch-scoped.
* Generated UTF-8 output is written through bounded Git Trees inline-content
  batches, reusing exact existing source blobs (including binary photos). Each
  batch is limited to 32 entries / 1 MiB of the exact UTF-8 JSON request; at most
  64 batches are allowed. These are internal conservative budgets, not documented
  GitHub maximum body sizes. All batches are planned before mutation, every
  intermediate tree SHA is independently verified, and main is checked before
  each batch. Unknown binary output or any oversized entry fails closed; no
  fallback upload or retry is attempted. Final tree/provenance/request checks
  still precede the sole review-ref creation. No ticker architecture changes.
* No PR is opened, approved, merged or deployed by this workflow. Existing branch
  protection is unchanged. Commit provenance fields alone are forgeable and prove
  neither actual workflow dispatch nor publication authority.

## Operation and required review

1. Finish factual, linguistic, photo-bank, source/rights and distribution review.
   Preserve explicit owner authorization for this exact publication/placement.
2. On fresh current `main`, create the single source-only commit above. Do not mix
   compiler/workflow changes or historical file edits with that commit.
3. Preferred connector route: give the source commit a `source/…` branch and end
   its message with exactly this two-trailer block (one blank line before it):
   ```text
   Sayd-Publication-Request: v1
   Distribution-Review-Scope: false
   ```
   Use `true` only when explicitly requesting preparation of broader distribution.
   These immutable trailers are request data, **not editorial authorization**.
   Open a source-only request PR to `main` using the existing connector. The
   dedicated read-only validator uses trusted BASE code. Its successful completion
   triggers the existing compiler on default-branch `workflow_run`, which re-reads
   public GitHub API run/workflow/PR identity, exact head/base and current open state.
   No upstream artifacts, caches, PR text or candidate code are consumed. The raw
   source request PR is deliberately unmergeable under candidate parity: never
   merge it. The generated branch needs its own ordinary PR in step 5.
   Manual default-branch dispatch remains available, but is not required by this
   connector route. The connector route requires no new interactive browser session or credentials;
   the existing manual path is unchanged. Neither adds credentials/permissions.
4. Inspect the actual trusted GitHub Actions run, not a self-asserted commit message:
   verify repository, workflow path/ref, event `workflow_dispatch` or validated
   `workflow_run` (including upstream request run/attempt/PR), base/compiler
   SHA, source SHA, requested scope, successful compile/finalize jobs, plan digest,
   output tree and generated commit against the run's uploaded receipt. Retain this
   evidence plus the owner's article/placement decision in the PR review record.
   If that evidence cannot be read/verified, stop before merge; do not add a PAT or
   broader workflow permission as an automatic workaround.
5. An authorized person/connector opens a **normal PR** for the generated review
   branch. A built-in-token push does not trigger ordinary push CI; require actual
   normal PR checks on the exact generated commit, not an assumed green push.
6. Review the human-readable generated diff, source rights/links/text/translations,
   ordering and responsive preview. Require unchanged contract, historical/archive,
   catalog, SEO, search, ticker, layout/browser and exact-base compiler parity checks.
   The narrow legacy dated-publication compatibility bridge verifies the actual
   candidate tree by replaying the immutable BASE compiler; it never treats a JSON
   file, `approved:true`, a receipt file or commit claim as an exemption.
7. Only then use the existing protected merge and deployment process under explicit
   publication authority. Verify deployed AR/EN/FR pages, canonical/hreflang, local
   images, category/search membership, short links and requested distribution.

## Concurrency, failure and rollback

A stale base or moved main fails; re-review/rebase into a **new** atomic source commit,
then submit its new exact SHA as a new request (or manual dispatch). No stale slot rewrite or automatic force push.
Deterministic duplicate dispatch succeeds only if the already-created review branch
has the identical tree, parent and message. A conflicting branch fails.

Any denied or uncertain API mutation stops immediately with a receipt. Do not retry
through another API/identity or assume a timed-out write failed. Read-only inspection
of exact branch/commit/run state must settle uncertainty before a separately
reviewed action. Orphaned immutable Git blobs are not a published content commit.

Before merge, abandon the review PR/branch without touching live history. To disable
future compilation, revert/disable the infrastructure workflow through normal review;
that does not alter published pages. After a publication merge, V1 intentionally has no automatic content rollback:
its immutability checks reject deletion/edit of compiled records and articles. A
withdrawal, placement correction or content correction needs separately authorized,
reviewed maintenance with a narrowly reviewed exception/path before it can pass.
Retain newly added images, manifest shards, rights/source evidence, stable links and
Git history as well as the older baseline; do not use a blanket revert to delete
catalog/provenance additions or regenerate the archive to approximate an undo.

## Verification expectations

No-content build: complete tracked tree byte-identical. Positive synthetic fixtures:
new image only, three-language category-only article, feature+secondary archive,
normal news/homepage/ticker distribution, multi-photo institutional gallery,
chronological rotation, repeat determinism and candidate parity. Negative fixtures:
stale/concurrent bases, denied distribution scope, invalid source parents, existing
aggregate/manifest edits or deletions, scripts/protected paths, symlinks/submodules/
executables, duplicate/unsafe JSON, path/case/Unicode collisions, corrupt raster,
missing hashes/shards/translations, modified outputs/provenance and conflicting refs.
Tests never publish synthetic records or pending editorial content.


## Connector trigger boundary (approved 24 October 2026)

This adapter changes reachability of the existing review-branch writer: an eligible
same-repository source PR can request review generation. It does not grant publication
or security approval. It preserves the existing `contents: write` finalizer-only
scope; it adds no credential, secret, repository permission, PR-write or auto-merge.
The public read client fails closed on network/rate-limit/incomplete responses and
never substitutes an authenticated or alternate endpoint. Default-branch workflow
identity, upstream validator path/ID/attempt, repository IDs, actual (not synthetic
merge) source SHA, source-only tree, direct current-main parent and explicit scope
are independently verified. The finalizer repeats request validation before uploads
and immediately before creating the review ref, in addition to its current-main
race guards. Conflicting existing branches and uncertain mutations stop unchanged.
Requests on arbitrary branch prefixes or non-source generated PRs are not compilation
requests. Branch filtering is only an efficiency gate, never the security proof.

Activation requires normal reviewed infrastructure merge and actual connector-only
request → validator → compiler → independent finalizer receipt evidence. Passing
local tests alone is not evidence that the deployed route has run successfully.

### Bounded caption-only revisions

An existing compiled article's visible image caption may be corrected through a
separate source-only request, **not** by editing its original publication record.
The source commit must be directly on the exact current main base and add exactly
one regular file: `content/caption-revisions/<id>.json`. It cannot mix a new story,
code, media, configuration, or other source changes.

The closed `sayd-caption-revision-v1` record contains `id`, `expected_base` (full
40-character commit), `publication_id`, `article_slug` (the original Arabic slug),
`photo_id`, and `captions`. The latter has exactly `ar`, `en`, and `fr`, each with
`old` and `new` plain-text, nonempty captions. Captions are bounded to 1,000
characters, Unicode-normalized, and cannot contain markup or control characters.
The old strings must exactly match the existing selected figure in all mirrors.
No caller-supplied output paths or source/credit/image replacements are accepted.

Only trusted base code resolves the immutable original publication, article and
photo. The native compiler substitutes six literal figcaption spans (HTML and
Markdown in three languages), plus only the optional capture-year spans described
below, preserves every other article byte, and uses the
unchanged trusted search builder to regenerate the three search indexes. Each
index must remain semantically identical except for the selected article's one
indexed caption replacement in its body. Titles, other fields, other rows,
homepage, ticker, aliases, credits, assets and original records stay unchanged.
The output is exactly those nine derived files plus the additive revision record;
existing revision records are immutable. Derived indexes are not uploaded by the
requester.

The existing read-only build/native writer produces the ordinary hashed plan and
source-parent generated candidate, with distribution scope false. Independent
trusted-base replay must match the entire candidate tree and provenance. Revisions
are separate from `Proof.additions`: they grant no new placement membership.
Responsive browser QA checks the actual revised article in all three languages
using effective captions. Normal tests, protected review/merge, Pages deployment,
and live verification still apply. This does **not** enable arbitrary article,
photo, credit, archive, or distribution edits.

A revision may additionally request `elide_photo_year` as a four-digit integer.
This is **not** an alt/credit replacement field: it only removes a corroborated
capture year from a single-photo article. The original provenance's first segment
must identify the same photo title and creator followed by a valid full calendar
date with that year; licence-review and copyright dates do not qualify. The original alt must end with the exact localized “in YEAR” phrase,
which alone is removed. The existing credit must have one delimiter-bound year
between a plain creator attribution and the localized source phrase, outside the
quoted photograph title. Copyright/rights notices, shared credits, repeated years,
and ambiguity are rejected. Only that date span is collapsed to one delimiter.

The original title, creator, source links, licence, resizing disclosure, media,
publication record, and private provenance remain unchanged. The selected search
body may additionally reflect this exact credit-year deletion; all other fields
and rows remain exact. Browser evidence uses effective caption, alt, and credit.
No arbitrary alt/credit replacement, global year removal, or other body edits are
supported, and this option does not add output files or privileges.

## Exact episode-three lead correction — 26 October 2026

The single `promote-episode-three-lead` editorial maintenance operation promotes
only the existing `hunting-tourism-egypt-iraq-jordan-20261026` article from its
ordinary homepage door card to the main lead. Its immutable revision filename is
`content/editorial-revisions/episode-three-lead-20261026.json`; its payload is empty.
It requires the exact current BASE, original publication SHA-256, and aggregate
SHA-256 of the four current target files. The owner decision remains independently
reviewed evidence, not authority conferred by these declarations.

The trusted renderer requires the Maghreb episode to be the current lead and
Adonis to be first side card. It reuses the existing chronological upper-card and
hunting-door rotation, preserves original publication dates and all current photo
overrides, and changes only `content/homepage.json` and the AR/EN/FR homepage HTML
(including lead sharing metadata). The original publication, article HTML/Markdown,
photo assets, taxonomy and ticker stay unchanged. No duplicate publication or new
Facebook post is created. Repetition, arbitrary targets, nonempty payloads, code in
the source commit, stale hashes and unrelated tree changes fail closed. This exact
correction is not a general API for editing slots. Normal replay, finalizer, PR,
contract and browser gates remain required.

## Exact two-bird life-cycle completion — 2 November 2026

The owner’s 1 November authorization to repair verified encyclopedia gaps is
implemented here only for the Sardinian Warbler and Common Redstart in
`daily-birds-20261030`. Operation `complete-two-bird-lifecycles` accepts only
revision ID `two-bird-lifecycles-20261102` and an empty payload. Trusted BASE
code contains the six fixed additions and their two institutional references;
request data cannot select text, articles or output paths. The original source
SHA-256, current BASE and aggregate target hash must match.

The output is exactly twelve existing HTML/Markdown mirrors, three search
indexes, six sitemap lastmod entries and the existing update-date registry, plus one immutable revision.
Only the selected life-cycle and final reference paragraphs change, together
with the normal 2 November update label and dateModified metadata. The original publication dates,
images, credits, taxonomy, listing cards, homepage and ticker remain exact.
Search changes must agree with the existing builder and affect only two bodies
per language. Repeat application and altered original paragraphs fail closed.

Evidence checked 2 November 2026: CSIC Vertebrados Ibéricos (incubation
12–15 days; nest departure 12–14 days; further parental care 2–3 weeks), and
BTO BirdFacts Redstart (incubation 13–14 days; fledging 16–17 days). These are
reference durations, not a borrowed European breeding calendar for Arab countries.

## Bounded November 5 bird reference presentation repair

The `text-only-nov5-bird-references` editorial operation applies only to the exact
immutable `daily-birds-20261105` publication and its ten CC0 photo identities. It
removes visible reference hyperlinks in its thirty AR/EN/FR articles while keeping
the reference names, creator credits, CC0 1.0 and plain-text iNaturalist photo IDs.
The original source/license URLs and full provenance record remain immutable.
The ten photo-specific CC0 dedications and official CC0 legal code were checked
independently on 5 November 2026: CC0 imposes no attribution or hyperlink condition.
This finding is not a guarantee of ownership or clearance of third-party rights.

The operation accepts an empty payload, exact revision ID and original source
hash, plus current-base and target hashes. Only sixty article mirrors and the
matching ten rows of each of three search indices change. No image, scientific
paragraph, date, metadata, archive, distribution, generic renderer, or other
publication changes. The ordinary source-request, trusted compile, whole-tree
parity, protected merge and live-verification process remains mandatory.
It is not a generic license/link waiver or a policy for other articles.

## Exact Qatar Updates and ticker correction — 6 November 2026

The operation `move-qatar-to-updates-nov6` accepts only revision ID
`qatar-updates-ticker-20261106`, the original `qatar-shooting-worlds-20261102`
source hash, current BASE, aggregate target hash and an empty payload. It moves
only the existing Qatar side card to Updates and refills the fourth side slot
with the existing newest Updates card, France bird flu. Both groups retain
original publication-date ordering and exactly four/eight cards, without
introducing or removing an upper-card article. Unexpected placement, exclusions,
refill identity, ticker policy or prior Qatar ticker titles fail closed. A fixed
original source hash and six fixed post-November-6 article mirror hashes require
the result update to be present first; outdated or altered mirrors are rejected.

Only the existing Qatar ticker titles change, in AR/EN/FR, to Azmy Mehelba’s
silver for Egypt, Abdulaziz Alsaad’s bronze for Kuwait and Olympic quota places
for both countries. The ten-item maximum, entry order and homepage-only scope
remain unchanged. The existing renderer generates exactly five existing targets:
`content/homepage.json`, `content/ticker.json`, and the three homepage mirrors.
Article HTML/Markdown, dates, original publication, images and all other files
remain byte-identical. No arbitrary titles, slots, targets or payload are accepted.
The source request must declare distribution scope `true`; normal trusted replay,
review, protected merge and deployment gates still apply. Approval references
are declarations, never publication authority. This code change carries no
publication record or source request; the separately reviewed operation follows
the November 6 article-only result update.


## Exact Stonechat Oman status update — 6 November 2026

The standing encyclopedia-repair authority of 1 November is implemented here
only for European Stonechat in `daily-birds-20261030`. Operation
`update-stonechat-oman-status-20261106` accepts only revision ID
`stonechat-oman-status-20261106` and an empty payload. Trusted BASE code fixes
the three country-paragraph replacements and reference label: OBRC8.0, dated
1 January2026, records `Saxicola rubicola` as `Uncommon pm & wv`, adding winter
presence to the previously attributed 2020 passage status. The original workbook
was read on6November2026; its full institutional URL is retained in the bounded
module and review evidence. Other countries and all biological text stay exact.

The original publication record remains immutable. Exact BASE, original source
hash, current derived-target hash and original paragraphs are required. Only
six selected article mirrors, three matching search bodies, three sitemap
lastmod entries and the normal update registry change, plus the new immutable
revision. The original30Octoberpublication dates, image bytes, alt, captions,
credits, taxonomy, category cards, homepage and ticker remain unchanged. The
update date is 8 November 2026. Repetition, arbitrary text/paths, stale originals
and nonempty payloads fail closed. Normal native compilation, independent
review, exact-head checks, protected merge and live verification remain required.

## Bounded v3 search storage — November 12 infrastructure repair

The separately reviewed infrastructure migration initializes language manifests
`docs/assets/search/manifest-{ar,en,fr}.json` and immutable, SHA-256-addressed
JSON shards under `docs/assets/search/shards/`. It contains only already published
content. The legacy `index-{ar,en,fr}.json` files remain byte-identical snapshots;
new v3 publications and revisions never rewrite or delete them. Existing articles,
media, provenance, dates, archive cards, taxonomy and ranking stay unchanged.
An already-open or cached old search client sees its old snapshot until reload;
the three search pages select the cache-busted v3 client. New clients do not fall
back to snapshots if any active shard fails.

The logical corpus remains the exact version-2 record model produced from full
HTML bodies. Only storage changes. Deterministic URL-hash partitions split until
each complete-record shard fits 512 KiB of the writer's exact JSON wire encoding.
One individually oversized record fails explicitly; nothing is shortened. Each
manifest carries language, categories, complete article count and closed local
shard paths with SHA-256, byte count and record count. The reader verifies all
shards, rejects duplicate keys/URLs, and reconstructs the full sorted logical
corpus before search. Four concurrent same-origin requests bound client fan-out;
queries remain entirely local. Manifests revalidate; immutable shard names keep
cached manifests internally consistent. Old shards are retained, not collected.
The manifest itself and shard count have fail-closed resource limits.

For source-only additions the compiler independently compares complete before and
after logical corpora, preserves every historical record and all metadata, and
requires exactly the deterministic changed storage outputs. Existing shard bytes
are immutable. A source request cannot initiate a format migration or alter a
legacy snapshot. A no-content build remains byte-identical. Historical bases
without manifests continue to replay the original v2 format; malformed manifests
or missing referenced shards never select that compatibility path.

Caption and fixed editorial operations retain their original article preconditions,
exact logical changes and authorization boundaries. The revision adapter maps
only their previously bounded logical search outputs to manifests/new shards,
reconstructs the result independently, and accepts only those exact generated
bytes. Existing physical target preconditions are hashed, including changed manifests;
photo-replacement payload search hashes identify the serialized complete logical
index, not the frozen snapshot. New shards must be
content-addressed and absent. This is not permission for new editorial changes,
source-controlled output paths, arbitrary new files, or deletion. Documentation
above that counts three physical search indexes describes historical v2 outputs;
v3 uses the corresponding exact manifest and shard output set instead.

The native writer retains its existing path and verification behavior: 1 MiB per
request, 32 entries, at most 64 batches,
full preflight before mutation, intermediate/final tree identity, current-base
checks and review-only ref creation all remain required. No fallback upload,
credential, permission, workflow trust change, automatic retry, merge or deployment
is introduced. The infrastructure repair must merge separately before rebuilding
any pending approved source publication on the new exact current base.


## Conservative native Trees batching — November 12 processing repair

A native Trees request received HTTP 422 with a processing-timeout message while
inside the former 4 MiB / 64-entry limits. The first predicted intermediate tree was
observed remotely; the next and final trees were absent. This is consistent with
the second request failing, but the error itself does not number the batch or
establish a GitHub service limit. That second request carried 3,497,941 bytes and 64
entries across 59 parent directories; byte volume alone does not explain the
observed outcome.

The writer's hard per-request budgets are tightened to 1 MiB and 32 entries, retaining
at most 64 batches. This deliberately lowers per-request capacity and bounds both
inline content and path fan-out. The existing 1132-output positive regression
remains required and fits 36 requests; it is not dropped or changed to a failure.
Every singleton must obey the same hard byte cap; there is no oversized exception,
soft-limit fallback, alternate upload route, binary upload, or automatic retry.

All requests and every predicted intermediate tree remain precomputed before the
first mutation. Exact source/blob reuse, current-main checks before every batch,
independent final-tree/provenance verification and review-only ref creation remain
unchanged. Failure after a successful tree POST can leave an unreachable object;
that is not a candidate ref or publication. A 422 stops before any later batch,
commit or ref. The smaller budgets are a conservative processing mitigation,
not a guarantee of GitHub acceptance; any later failure remains explicit.

## Closed Syria Jousiyeh article and ticker update — November 14

Operation `update-syria-jousiyeh-20261114` accepts only the matching immutable
revision `syria-jousiyeh-update-20261114`, empty payload, exact current base,
original Syria publication hash and aggregate target hashes. It prepends one
fixed, reviewed paragraph in each language about the ministry receiving raptors
seized at Jousiyeh on November 12 for veterinary care and rehabilitation.
Release is conditional and prospective; no count or species is inferred.
Source: Syrian Al-Ikhbariya, November 12, 2026, 22:00,
https://alikhbariah.com/تمهيداً-لإعادتها-إلى-البرية-وزارة-الإ/ .

Only the six existing article mirrors, independent update registry, corresponding
sitemap dates and three logical search bodies change, together with the existing
Syria ticker wording in the two ticker registries and the three homepage loops.
The original November 11 publication date, titles, descriptions, slugs, all old
paragraphs, photo bytes, credits and rights, card placement, ticker order and
all unrelated content remain exact. The existing CC0 stork image is retained;
no new event photograph or rights claim is introduced. V3 manifests and additive
content-addressed shards use the existing revision adapter. No snapshot deletion.

Normal separate support review, source-only request, trusted compilation,
independent review, exact-head CI, protected merge and live verification remain
mandatory. The support change does not publish the article and accepts no
arbitrary replacement text or path. Approval references do not grant permission.

## Exact same-byte homepage images — November 14 processing repair

Operation and revision ID `homepage-local-images-20261114` accept one new immutable
`content/editorial-revisions/homepage-local-images-20261114.json`, an empty payload,
the exact current base, a digest of the original channel/Adonis sources and three
fixed existing image files, and the aggregate hash of the three current homepages.
The source contains no map, path, replacement text, image or rights assertion.
Distribution review scope is false: no story/video placement or order changes.

Trusted BASE code substitutes only three `img src` spans in each AR/EN/FR homepage:
the Saudi autumn cover, Gulf autumn cover and Adonis archive portrait. Each exact
TV group/card identity is bound to its existing local path and decoded SHA-256.
Canonical inline JPEG bytes must equal the existing regular local file byte for
byte; missing files, symlinks (including parents), noncanonical paths, malformed
UTF-8/base64, mismatched hashes, duplicate/missing cards and repeat migration fail
closed. A byte-exact inverse proves that every other homepage byte is unchanged.
Relative paths are specific to the three homepages. There is no image recompression,
resize, extraction, new asset, source/license claim or generic image override.

The exact reviewed revision activates current homepage rendering and checking.
Absent markers preserve historical inline rendering; malformed markers fail rather
than select a fallback. Historical Adonis compilation and TV archive cards retain
their exact original representation. Original source JSON/data URIs, article and
category pages, photo bytes, catalogs, search, audio/video, URLs, layout and credits
remain unchanged. Subsequent homepage builds reverify the fixed image equivalence.

The support PR contains code/tests/documentation only. After its separate protected
merge, the source-only migration produces exactly three homepages plus its revision
record through the existing trusted compiler/writer and normal generated-PR review.
The finalizer adds only that exact revision path; its 1 MiB/32-entry/64-batch limits,
1132-output regression, preflight, tree identity, provenance and race guards remain
unchanged. No direct generated-output edit, alternate upload, oversized singleton,
workflow permission, retry, auto-merge or deployment route is added. Pending article
requests are rebuilt on the exact post-migration main only after protected merge.
