# Published-article maintenance: inspection and review-only implementation

Technical inspection, 25 October 2026. Governing editorial authority remains
AGENTS.md and the owner-decision section of SOURCE-ONLY-PUBLICATION.md. This is
an implementation status report, not a new publication protocol or authorization.

## Finding

Inspected main `e0a00a7eaf867d52659796c633a15c5bf1eb8e86`, including merged
PR #321 (`e9b750043077abe947519a3493829325b77ebd4e`). The newer main also contains
the subsequently published three-bird batch. Seven immutable publication records
currently describe twelve articles; the historical archive is substantially wider.
The native source compiler supports additions and separate caption revisions,
not general body edits, withdrawal or category transitions. PR #311, the separate
Riyadh caption correction, was open at inspection; it is outside this change.

Reusable infrastructure:

- `publication_compiler.py`: exact Git snapshots, isolated builds, hashed plans,
  complete-tree candidate replay and source-parent provenance.
- `publication_request.py` and `publication_finalize.py`: source-only requests,
  independently repeated validation, review-branch creation only, existing token.
- `caption_revision.py`: immutable original source plus bounded derived corrections.
- `publication_guard.py`: trusted BASE replay; source declarations or receipts alone
  never grant a preservation exception or new distribution authority.
- `build_search_index.py`: existing public body extraction and index serialization.
- Existing protected merge, three-language, homepage, archive, catalog, SEO and
  browser checks. The branch endpoint reported main protected and the required
  `Three-mirror publication check`; this does not prove every bypass setting.

## What this PR implements

`scripts/article_maintenance.py` computes an external, deterministic review bundle.
It reads exact regular Git blobs from a clean checkout pinned to a full BASE SHA.
It accepts one closed data request for one compiler-owned article; unknown fields,
raw markup, missing translations, ambiguous text, stale base and unsupported
placements fail before output. No request in this PR targets a real article.

The three proposed operations are:

| Operation | Implemented proposal | Deliberate bounds |
| --- | --- | --- |
| Edit | Exact plain paragraph/heading replacements in six HTML/Markdown mirrors, with only the selected search bodies regenerated using the existing extractor | Three explicit translations; no title/date/image/rights/credit/source/distribution changes |
| Withdraw | Three noindex notices, removal of ordinary archive cards, selected search rows and sitemap entries; rich preview cleanup on existing redirect aliases | Refuses homepage/ticker membership, special/combined cards, contentful aliases and surviving sitemap alternates |
| Reclassify | Category badge/breadcrumb/JSON-LD, Markdown category, old/new ordinary archive cards, primary-door registry and selected search categories | Existing simple doors only; preserves original-date ordering; refuses new taxonomy, multiple search facets and homepage/ticker membership |

Original publication records, media, attribution evidence, translation identities,
publication/update dates and unrelated article bytes remain intact. A withdrawal
retains the source Markdown and Git history; removing public page content is not
erasing the original record. Static GitHub Pages notices return HTTP 200 with
noindex; the tool does not claim HTTP 410, search-engine cache erasure, private Git
history, removal of retained public media, or withdrawal from social channels.

The bundle contains every affected file's original/proposed bytes and SHA-256,
the exact BASE and decision/conflict evidence references, and a digest. Replay
recomputes the entire bundle from BASE instead of trusting supplied output paths.
The inverse is exact only if all affected files still match the proposed bytes;
later aggregate/index edits block automatic rollback and need a fresh scoped diff.
Saved JSON and its hash are integrity aids, not signatures or approval proof.

The CLI writes only a new directory outside the checkout, containing `plan.json`
and `review.json`. It does not create a source/candidate commit, stage files, move
a ref, apply a bundle, merge, deploy, or contact an external service. The `replay`
and `rollback` helpers return proposed byte mappings; neither writes them.
Do not upload the external before/after bundle as a public publication asset.

```bash
python scripts/article_maintenance.py \
  --repo /path/to/clean/sayd-magazine \
  --base FULL_CURRENT_MAIN_COMMIT \
  --request /private/reviewed-request.json \
  --output /outside-checkout/new-review-directory
```

The closed request schema is in `request()` and the synthetic example is in
`test_article_maintenance.py`. `decision_reference: private:...` and conflict
confirmation references identify evidence for independent human verification.
They do not establish that Nayef approved anything. Approval of this infrastructure
does not approve changes to a particular article.

## Production boundary: still closed

This PR is a **review-only first stage**, not a working production maintenance
route. The current native source allowlist does not accept these requests; no
maintenance exception has been added to the preservation guards. Manually
uploading the proposed derived files is not a supported workaround.

Before a real maintenance decision can execute through the native writer, finish
and review these linked changes:

1. Add a separate immutable maintenance request/decision ledger with exact
   article/operation/base/content binding. Keep independently verified owner
   decision evidence outside public article text. A conflict must be explained
   before the confirmed exception executes; the exception remains item-specific.
2. Extend trusted-BASE request validation, compilation and independent finalizer
   replay for that exact ledger format. Keep one direct-base source commit,
   immutable prior records, exact-tree/mode comparison, existing review-only ref
   restriction and current permissions. Never interpret `approved:true`, a PR
   description or this bundle as an authorization grant.
3. Teach all relevant existing guards to recognize *only* the replayed expected
   maintenance tree. Withdrawal needs an explicit tombstone state in article,
   archive, SEO/search, hreflang, image-association and responsive QA checks;
   preserve every unrelated assertion. Keep maintenance separate from new-story
   `Proof.additions` so it cannot grant distribution.
4. Make later builders/search/taxonomy/browser QA read effective maintenance
   state while retaining immutable originals, preventing withdrawn content from
   reappearing on a future build. Add ordered subsequent revisions and a fresh
   authorized restore/reverse decision, rather than deleting prior audit records.
5. Add reviewed homepage/ticker replacement/rotation and combined archive adapters;
   preserve slot counts, chronology and all three languages. Add a separate legacy
   adapter based on the actual historical rendered pages and proven identity;
   never regenerate old articles from incomplete Markdown.
6. Prove the full source request -> independent compiler/finalizer -> separate
   candidate PR sequence on exact current main, run all unchanged regression and
   three-language responsive checks, then obtain the required merge/publication
   approval for the particular article decision. Local unit tests do not prove
   that this deployed sequence has run.

These are engineering gaps, not a new editorial veto. The owner has already
authorized developing the path; no new approval is needed just to finish that
development. Production activation and any particular publication change still
require the review and approvals specified in the current task.

## Verification

Twenty synthetic offline tests pass, including the real CLI against a temporary
Git repository, unchanged repository/index/HEAD, six mirrors, search-row scope,
category chronology, withdrawal/alias metadata, exact inverse, concurrent edits,
stale/missing/wrong-language/canonical/mode inputs, ambiguous text, unsafe markup,
Unicode controls, duplicate JSON keys, special placements and tampered bundles.

```bash
python -m unittest discover -s scripts -p test_article_maintenance.py -v
```

The existing publication-contract workflow runs this test command as an additive
step. Its permissions and existing checks are unchanged. No live article was
modified, no production maintenance candidate was generated, and no publication
or merge was performed. Full repository/Actions/browser validation remains to be
observed on the draft PR; only the focused offline tests were executed locally.
