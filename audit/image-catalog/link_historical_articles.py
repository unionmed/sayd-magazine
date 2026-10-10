#!/usr/bin/env python3
"""Read-only cross-reference: archived image manifests vs historical post Markdown.

Indexes featured image metadata, HTML image attributes, linked originals, and
relative upload references. No site files or images are changed.
"""
import collections
import html
import json
import pathlib
import re
from urllib.parse import unquote, urlparse
from search_all import ROOT, records

POSTS = ROOT / "content/posts"
OUT = ROOT / "audit/image-catalog/article-image-links.json"
# Sources include old WordPress URLs and newer relative ../../media/uploads/.
# Scan all upload references, then discard tokens not ending in an image suffix.
CANDIDATE = re.compile(
    r"""(?:https?:)?//[^\s"'<>]+|(?:\.\./)*(?:docs/)?media/uploads/[^\s"'<>]+|"""
    r"""(?:/)?(?:wp-content/)?uploads/[^\s"'<>]+""", re.I
)
SUFFIX = re.compile(r"\.(?:jpe?g|png|webp|gif|avif)$", re.I)

def extract_media_path(reference):
    reference = html.unescape(reference).strip().rstrip(",;)")
    u = urlparse(reference)
    p = unquote(u.path).replace("\\", "/")
    m = re.search(r"(?:^|/)(?:(?:wp-content|media)/)?uploads/(\d{4}/\d{2}/[^/]+)$", p, re.I)
    if not m or not SUFFIX.search(m.group(1)):
        return None
    return "docs/media/uploads/" + m.group(1)

def image_references(body):
    found = {}
    for match in CANDIDATE.finditer(body):
        raw = match.group(0).rstrip(",;)")
        # URL fragments or query strings should not alter the local lookup path.
        local = extract_media_path(raw)
        if local:
            found.setdefault(local, raw)
    return found

def title_from_post(text, fallback):
    m = re.search(r"^title:\s*(.*)$", text, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else fallback

def build_links():
    catalog = {r["path"]: r for r in records()}
    basename_index = collections.defaultdict(list)
    for path in catalog:
        basename_index[pathlib.PurePosixPath(path).name].append(path)
    results = []
    articles_scanned = 0
    articles_with_images = 0
    for post in sorted(POSTS.glob("*.md")):
        body = post.read_text(encoding="utf-8")
        references = image_references(body)
        articles_scanned += 1
        if references:
            articles_with_images += 1
        for expected, raw in sorted(references.items()):
            candidates = [expected] if expected in catalog else basename_index.get(pathlib.PurePosixPath(expected).name, [])
            status = ("EXACT_PATH" if expected in catalog else
                      "UNIQUE_BASENAME" if len(candidates) == 1 else
                      "AMBIGUOUS_BASENAME" if candidates else "NOT_FOUND")
            results.append({
                "article_file": str(post.relative_to(ROOT)),
                "article_title": title_from_post(body, post.stem),
                "source_reference": raw, "expected_local_path": expected,
                "matching_paths": candidates, "status": status,
                "visual_status": "UNVERIFIED"
            })
    counts = collections.Counter(r["status"] for r in results)
    exact = [r for r in results if r["status"] == "EXACT_PATH"]
    nonexact = [r for r in results if r["status"] != "EXACT_PATH"]
    return {
        "schema": "sayd-article-media-crossref-v2",
        "articles_scanned": articles_scanned,
        "articles_with_image_references": articles_with_images,
        "image_references_unique_per_article": len(results),
        "exact_links": len(exact),
        "unique_basename_not_verified": counts["UNIQUE_BASENAME"],
        "ambiguous_basename": counts["AMBIGUOUS_BASENAME"],
        "not_found": counts["NOT_FOUND"],
        "catalog_images_with_exact_article_link": len({r["expected_local_path"] for r in exact}),
        "warning": "Historical source references only. Non-exact matches require checking; NOT_FOUND is not proof of a broken live image. No website changes.",
        "exact": exact,
        "nonexact": nonexact
    }

def main():
    result = build_links()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("exact", "nonexact")}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
