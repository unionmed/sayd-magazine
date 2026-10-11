#!/usr/bin/env python3
"""Verify Github-only image archive and generate a transparent coverage report."""
import collections
import json
import os
import subprocess
from pathlib import PurePosixPath
from search_all import ROOT, EXTENSIONS, records, audit, query

HERE = ROOT / "audit/image-catalog"

def main():
    rows = list(records())
    integrity = audit(rows, check_files=True)
    problems = {field: integrity[field] for field in
                ("invalid_records", "duplicate_path_entries", "missing_local_files")
                if integrity[field]}
    # The inventory grows with authorized photographs; it is not an image cap.
    if integrity["records"] < 10184:
        problems["historical_inventory_shrank"] = integrity["records"]
    if problems:
        raise SystemExit(json.dumps(problems, ensure_ascii=False)[:4000])
    # Compare the manifest SHA to the actual Git blob at the checked-out commit.
    # Looking at files alone is not enough to prove inventory identity.
    process = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "HEAD"],
        cwd=ROOT, capture_output=True, check=True
    )
    git_images = {}
    for entry in process.stdout.split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, object_type, sha = meta.decode("ascii").split()
        name = raw_path.decode("utf-8")
        if object_type == "blob" and PurePosixPath(name).suffix.lower() in EXTENSIONS:
            git_images[name] = sha
    manifest_images = {r["path"]: r["sha"] for r in rows}
    if integrity["records"] != len(git_images):
        raise SystemExit(json.dumps({"manifest_count": integrity["records"], "git_tree_image_count": len(git_images)}, ensure_ascii=False))
    unindexed = sorted(p for p in set(git_images) - set(manifest_images) if p.startswith("docs/media/uploads/"))
    missing_in_git = sorted(set(manifest_images) - set(git_images))
    mismatched_sha = sorted(p for p in manifest_images if p in git_images and
                            manifest_images[p] != git_images[p])
    if unindexed or missing_in_git or mismatched_sha:
        raise SystemExit(json.dumps({
            "unindexed_images": unindexed[:20], "unindexed_count": len(unindexed),
            "not_in_git_tree": missing_in_git[:20], "missing_count": len(missing_in_git),
            "sha_mismatch": mismatched_sha[:20], "mismatched_count": len(mismatched_sha),
        }, ensure_ascii=False))
    taxonomy = json.loads((HERE / "preliminary-taxonomy.json").read_text(encoding="utf-8"))
    linking = json.loads((HERE / "article-image-links.json").read_text(encoding="utf-8"))
    taxrows = taxonomy["records"]
    archive = {r["path"] for r in rows}
    if len(taxrows) != len(rows) or {r["path"] for r in taxrows} != archive:
        raise SystemExit("Incomplete taxonomy or incorrect archive paths")
    if any(x["visual_status"] != "UNVERIFIED" for x in taxrows):
        raise SystemExit("Unverified images have visual-verification labels")
    all_links = linking["exact"] + linking["nonexact"]
    if len(all_links) != linking["image_references_unique_per_article"]:
        raise SystemExit("Inconsistent article link counts")
    if any(x["expected_local_path"] not in archive for x in linking["exact"]):
        raise SystemExit("Exact link points to an unindexed path")
    if any(s in x["source_reference"].lower() for x in all_links
           for s in ("wp-content", "alfalivehost", "sayd-magazine.com")):
        raise SystemExit("External or legacy image reference appeared in output")
    classified = sum(x["section_candidates"] != ["غير مصنف"] for x in taxrows)
    years = collections.Counter()
    for r in rows:
        parts = PurePosixPath(r["path"]).parts
        year = parts[3] if len(parts) >= 5 and parts[3].isdigit() else "other"
        years[year] += 1
    result = {
        "source": "Github repository unionmed/sayd-magazine only",
        "image_folder": "docs/media/uploads",
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "index_state": "all-manifest-paths-verified; visual contents unverified",
        "images_indexed": integrity["records"],
        "unique_image_paths": integrity["unique_paths"],
        "files_present_on_checkout": integrity["records"] - len(integrity["missing_local_files"]),
        "unique_blob_shas": integrity["unique_blob_shas"],
        "git_tree_images_all_repo": len(git_images),
        "unindexed_upload_images": len(unindexed),
        "manifest_sha_verified_against_git_tree": True,
        "duplicate_image_content_extra_paths": integrity["duplicate_content_extra_paths"],
        "duplicate_content_groups": integrity["duplicate_content_groups"],
        "filename_classification_candidates": classified,
        "images_not_classified_by_filename": len(rows)-classified,
        "article_files_scanned": linking["articles_scanned"],
        "articles_with_local_github_images": linking["articles_with_github_image_references"],
        "distinct_references_inside_articles": linking["image_references_unique_per_article"],
        "exact_article_image_references": linking["exact_links"],
        "distinct_images_with_exact_article": linking["catalog_images_with_exact_article_link"],
        "filename_only_unconfirmed_links": linking["unique_basename_not_verified"],
        "ambiguous_names": linking["ambiguous_basename"],
        "missing_local_paths": linking["not_found"],
        "by_year": dict(sorted(years.items())),
        "search_top_20_counts": {s: len(query(rows, s, limit=20)) for s in
                                 ("صقر", "صيد", "رماية", "horse", "duck", "falcon")},
        "limitations": "Article references to excluded external media are not treated as GitHub image links. No image contents or rights verified."
    }
    (HERE/"coverage-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    label = [
        "# تقرير فحص أرشيف صور صيد — GitHub فقط", "",
        "أُنتج هذا التقرير من الملفات الموجودة في مستودع GitHub فقط.",
        "لا يُستخدم WordPress ولا مصدر خارجي للصور.", "",
        "- الصور المفهرسة والموجودة: " + str(result["images_indexed"]),
        "- المسارات الفريدة: " + str(result["unique_image_paths"]),
        "- الصور ذات المحتويات الفريدة: " + str(result["unique_blob_shas"]),
        "- مسارات إضافية لمحتويات مكررة: " + str(result["duplicate_image_content_extra_paths"]),
        "- تصنيف أولي من اسم الملف: " + str(classified),
        "- غير مصنفة بالاسم: " + str(len(rows)-classified),
        "- ملفات المقالات المفحوصة: " + str(linking["articles_scanned"]),
        "- مقالات فيها صور محلية بالمستودع: " + str(linking["articles_with_github_image_references"]),
        "- إشارات صور محلية دقيقة: " + str(linking["exact_links"]),
        "- صور مختلفة مرتبطة مباشرة بمقالات: " + str(linking["catalog_images_with_exact_article_link"]),
        "- ترشيحات بالاسم غير مؤكدة: " + str(linking["unique_basename_not_verified"]),
        "- تطابقات مبهمة: " + str(linking["ambiguous_basename"]),
        "- مسارات محلية غير موجودة: " + str(linking["not_found"]),
        "", "## طريقة الاسترجاع",
        "python audit/image-catalog/search_editorial.py صقر --limit 10",
        "", "## حدود التحقق",
        "تصنيف أسماء الملفات أولي وليس تحققًا من محتوى الصور، ولا يثبت ملكية الحقوق.",
        "الروابط القديمة الخارجية لا تدخل أداة المطابقة، لذلك قد تكون هناك صور قابلة للاستعمال دون ربط آلي بالمقالات.",
        "يُتحقق بصريًا من الصورة ومن ملاءمتها ومصدرها قبل أي استعمال تحريري.",
        ""
    ]
    (HERE/"coverage-report.md").write_text("\n".join(label), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
