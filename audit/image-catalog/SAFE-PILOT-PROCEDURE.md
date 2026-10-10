# Sayd historical image catalog — safe pilot procedure

Status: INTERNAL DRAFT. Not a publishing instruction.

## Verified scope
- Existing pilot: `audit/image-catalog/pilot-2026-10-10.json` contains 180 filename/path-selected images.
- Its `section_candidate` is a **suggestion**, not an identified species, verified event, or verified photograph.
- Original files remain in `docs/media/uploads/`; keep exact paths and filenames.

## Non-negotiable protections
1. Never rename, move, delete, recompress, or overwrite historical media during cataloging.
2. Never modify `docs/`, `content/`, templates, article dates, homepage slots, redirects, canonical URLs, hreflang, robots.txt, or sitemaps for cataloging.
3. Keep indexes in `audit/image-catalog/`, outside the published GitHub Pages `docs/` root.
4. No automatic claim of photographer, species, location, capture date, license, or event from filenames.
5. Record uncertain values as null / `UNVERIFIED`; Nayef manages publication permissions.
6. Link to the original repository path; do not copy 10,000 files to ChatGPT Library.
7. A new published image must have a site-local file and a documented copy in `/Sayd picture for use`; do not claim the latter exists until confirmed.
8. Do not merge this pilot without review. Run existing SEO and publication-contract workflows before any merge.

## Catalog record fields for later versions
`path`, `git_blob_sha`, `size_bytes`, `section_candidates`, `subject_keywords_ar`, `subject_keywords_en`, `species_scientific_name`, `country`, `region`, `event_date`, `capture_date`, `source`, `photographer`, `related_article_urls`, `visual_review_status`, `rights_note`, `library_copy_status`.

## Verification steps
- Confirm candidate file path exists on the same commit as the index.
- Verify image visually before using it to illustrate an article.
- Use historical photos only as illustrative images with accurate captions, never as documentary evidence of a new event.
- Check image duplicates by hashes and visual similarity separately; identical names or sizes alone do not establish duplicates.
- Before expanding, compare the PR diff with `main` and verify only internal `audit/image-catalog/` files changed.
- Keep the draft PR open until an explicit review of search quality and safeguards.
