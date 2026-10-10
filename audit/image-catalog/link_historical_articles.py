#!/usr/bin/env python3
"""Read-only cross-reference of GitHub articles and GitHub archive images.

Accepted references are repository-local docs/media/uploads/ paths and URLs
pointing directly to the unionmed/sayd-magazine GitHub repository. External
image services and legacy content hosts are deliberately ignored.
"""
import collections
import html
import json
import pathlib
import re
from urllib.parse import unquote, urlsplit
from search_all import ROOT, records

POSTS = ROOT / "content/posts"
OUT = ROOT / "audit/image-catalog/article-image-links.json"
CANDIDATE = re.compile(
    r"""https?://[^\s"'<>]+|(?<![\w/])(?:\.\./)*(?:docs/)?media/uploads/[^\s"'<>]+""",
    re.I,
)
SUFFIX = re.compile(r"\.(?:jpe?g|png|webp|gif|avif)$", re.I)
LOCAL = re.compile(
    r"(?:\.\./)*(?:docs/)?media/uploads/(\d{4}/\d{2}/[^/]+)$", re.I
)
GITHUB = re.compile(
    r"/unionmed/sayd-magazine/(?:blob|raw)/[^/]+/docs/media/uploads/(\d{4}/\d{2}/[^/]+)$",
    re.I,
)
GITHUB_RAW = re.compile(
    r"/unionmed/sayd-magazine/[^/]+/docs/media/uploads/(\d{4}/\d{2}/[^/]+)$",
    re.I,
)

def extract_media_path(reference):
    """Canonicalize only locally stored GitHub media references."""
    reference = html.unescape(reference).strip().rstrip(",;)")
    u = urlsplit(reference)
    m = None
    if u.scheme or u.netloc:
        if u.scheme not in ("http", "https"):
            return None
        if u.netloc.lower() == "github.com":
            m = GITHUB.fullmatch(u.path)
        elif u.netloc.lower() == "raw.githubusercontent.com":
            m = GITHUB_RAW.fullmatch(u.path)
        else:
            return None
    else:
        m = LOCAL.fullmatch(u.path)
    if not m:
        return None
    relative = unquote(m.group(1))
    if not SUFFIX.search(relative):
        return None
    if relative in (".", "..") or "/../" in relative or "/./" in relative:
        return None
    return "docs/media/uploads/" + relative

def image_references(body):
    found = {}
    for match in CANDIDATE.finditer(body):
        raw = match.group(0).rstrip(",;)")
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
        "schema": "sayd-github-article-media-crossref-v3",
        "source": "unionmed/sayd-magazine repository only",
        "articles_scanned": articles_scanned,
        "articles_with_github_image_references": articles_with_images,
        "image_references_unique_per_article": len(results),
        "exact_links": len(exact),
        "unique_basename_not_verified": counts["UNIQUE_BASENAME"],
        "ambiguous_basename": counts["AMBIGUOUS_BASENAME"],
        "not_found": counts["NOT_FOUND"],
        "catalog_images_with_exact_article_link": len({r["expected_local_path"] for r in exact}),
        "warning": "Only local and GitHub repository image references counted. Missing links do not prove an image is missing. No website changes.",
        "exact": exact,
        "nonexact": nonexact
    }

def main():
    result = build_links()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("exact", "nonexact")}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
