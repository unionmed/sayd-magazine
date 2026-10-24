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

## Sources and generated compatibility outputs

One atomic source commit, directly on the exact current `main`, may only ADD:

* `content/publications/<release-id>.json` (`sayd-publication-v1`);
* `docs/media/publications/<release-id>/<lowercase-name>.<jpg|jpeg|png|webp>`;
* `audit/image-catalog/manifest/release-<release-id>.tsv`, exactly the new photo
  paths, Git blob hashes and byte counts, with `path\tgit_blob_sha\tsize_bytes` header.

Existing local photos can be referenced without copying them or changing their
old catalog rows. A media-only record has `articles: []`. New records and media are
immutable; corrections to already published articles remain a separately reviewed
maintenance task, not an implicit add-only update permission.

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

Each article has complete AR/EN/FR slugs, author, title, description, subtitle,
plain-text sections, sources, end-of-article photo credit and optional ticker title.
Photo order is explicit and identical across languages. Sources use credential-free
HTTPS links; metadata can retain legitimate external license references. Public
text, source wording and links still require normal editorial review.

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
