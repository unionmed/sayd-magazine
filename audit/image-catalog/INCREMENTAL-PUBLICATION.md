# Additive image publication — no whole-catalog rewrite

This prospective infrastructure workflow keeps existing images, TSV manifests,
article-link snapshots and taxonomy snapshots unchanged. It is not authorization
to publish any pending article, and does not bypass an upload reviewer.

## Add images

1. Obtain normal editorial/image publication authorization and retain source and
   rights evidence under the existing editorial protocol. This inventory does
   not grant rights or prove visual identity.
2. Save only new approved images at their intended local paths. Reuse an existing
   catalog path without a new row when reusing an image.
3. Create a NEW small shard using a unique `release-YYYYMMDD-topic` ID:

   ```sh
   python audit/image-catalog/incremental_catalog.py \
     --release release-YYYYMMDD-topic docs/media/uploads/YYYY/MM/new-image.jpg
   ```

   The helper validates the whole logical inventory, computes Git blob SHA/size,
   and atomically creates `manifest/release-YYYYMMDD-topic.tsv`. It never edits an
   existing TSV. Exact retries are no-ops; conflicting retries fail. Cooperating
   writers lock the directory. Manual additions still undergo duplicate checks.
   Use the `release-` prefix so new shards sort after the historic date shards.
4. Include the new image(s) and new shard in the normal reviewed content commit.
   Do not change any old manifest, annotation, or tracked catalog snapshot. Old
   date-specific publisher scripts that edit `2026-01.tsv` are historical tools,
   NOT supported templates for new publications: the append-only gate rejects
   their mutations. Adapt a future publisher to this helper before executing it.
5. Preserve every existing publication/mirror/archive/ticker/browser check. The
   inventory verifier compares the committed image tree, actual checkout bytes,
   all paths, hashes and sizes. Verify the final committed candidate, not an
   uncommitted image addition.

## Fresh search and generated reports

`search_all.py` aggregates all TSV shards deterministically. Duplicate paths are
errors even with identical hashes. Identical bytes at distinct paths remain
valid, including all historical duplicates.

`search_editorial.py` builds article associations in memory from current source
articles, without writing any file or trusting a stale snapshot. It returns
inherited editorial evidence separately, always retaining machine visual/rights
status as unverified.

Build/recheck locally or in unchanged-strength CI:

```sh
python audit/image-catalog/incremental_catalog.py --base <trusted-base-commit>
python -m unittest discover -s audit/image-catalog -p 'test_*.py' -v
python audit/image-catalog/search_all.py --audit --check-files
python audit/image-catalog/build_preliminary_taxonomy.py
python audit/image-catalog/link_historical_articles.py
python audit/image-catalog/verify_catalog.py
```

Generated full indexes live only in ignored `.catalog-build/`. The verifier
rejects stale generated inputs. CI uploads only the two concise coverage reports,
not complete image catalogs. Existing tracked JSON/Markdown outputs remain
immutable HISTORICAL SNAPSHOTS, not evidence of current completeness.

## Durable provenance

`editorial-overrides/*.json` is append-only source data, not a generated report.
The initial migration preserves the existing manually recorded visual assertion
with its original record, historical source blob/ancestor commit, article path,
image path and image blob SHA. The loader verifies this historical evidence;
changed image bytes cannot inherit the assertion. A claim on a no-longer-current
article association stays in its original override file, not in active results.

This schema specifically preserves INHERITED assertions. It does not issue new
rights grants or create new verified claims. Existing rights/source notes stay
unchanged and govern new image review. A future general annotation-authoring
schema needs separate reviewed design; never fake a historical source to add one.
Conflicting evidence keys fail closed rather than silently choosing the latest.

No historical snapshot is deleted. Its Git blob and source history remain the
provenance record. CI fetches full history; a shallow checkout unable to resolve
provenance fails rather than dropping evidence. Coverage artifacts expire after
30 days, but TSV sources/overrides and historical snapshots persist in Git.

## Migration, safeguards and rollback

No image relocation, renaming, historical TSV rewrite, catalog rewrite, site
markup or public search-index change is needed for this infrastructure migration.
All current baseline inventory records retain their contents and ordering.

The append-only check compares the complete candidate/working tree to a trusted
base, rejecting edits/deletions/renames of old TSVs, overrides and snapshots.
Branch protection/permissions are not changed. New shards use the SAME TSV
format and directory the old reader already supports: rollback of infrastructure
code can still read added images. Preserve newly created shards/overrides during
any revert. Old editorial search relied on stale snapshots, so reverting the
fresh-search integration restores that old limitation; it is not an acceptable
freshness substitute. A reviewed rollback must keep provenance and rerun checks.

Deploy via a narrow infrastructure-only protected PR; keep pending editorial
packages separate. Independent review, CI on exact commit, normal merge approval
and verification remain required. This reduces necessary uploads; it cannot
promise that platform approvals will never be requested.

The inherited-evidence adapter pins the pre-migration history anchor
`6b91310ee06b9a8059757b34d449230044f28888`. A claim fabricated in an intermediate
commit of a new publication cannot qualify as historical evidence. Changing this
trust anchor or introducing new evidence schemas requires explicit code review.

For rollback of later published articles, revert article/render/distribution
references but retain their archived image files, shards and provenance. A generic
revert deleting an already merged shard/image is intentionally rejected. Any
historical metadata correction or archive deletion requires separate explicitly
reviewed maintenance, not the ordinary additive publication path.

Existing compatibility limit: article-title associations recognize local
`docs/media/uploads/YYYY/MM/name` references. Images stored elsewhere remain in
the complete path inventory/search but may lack title associations. This change
does not broaden that parser or relocate any existing asset.
