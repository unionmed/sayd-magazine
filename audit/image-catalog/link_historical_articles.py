#!/usr/bin/env python3
"""Read-only cross-reference between archived media and historical post Markdown."""
import collections
import json
import pathlib
import re
from urllib.parse import unquote, urlparse
from search_all import ROOT, records

POSTS = ROOT / "content/posts"
OUT = ROOT / "audit/image-catalog/article-image-links.json"
IMAGE = re.compile(r'https?://[^\s"<>\)]+?\.(?:jpe?g|png|webp|gif|avif)(?:\?[^\s"<>]*)?', re.I)
def extract_media_path(url):
    u = urlparse(url.replace("&amp;", "&"))
    p = unquote(u.path)
    m = re.search(r"/(?:wp-content/)?uploads/(\d{4}/\d{2}/[^/]+)$", p, re.I)
    return "docs/media/uploads/" + m.group(1) if m else None

def main():
    catalog = {r["path"]: r for r in records()}
    basename_index = collections.defaultdict(list)
    for path in catalog:
        basename_index[pathlib.PurePosixPath(path).name].append(path)
    links, unresolved, articles = [], [], 0
    for post in sorted(POSTS.glob("*.md")):
        body = post.read_text(encoding="utf-8")
        title = re.search(r'^title:\s*(.*)$', body, re.M)
        title = title.group(1).strip().strip(chr(34)).strip(chr(39)) if title else post.stem
        articles += 1
        for url in sorted(set(IMAGE.findall(body))):
            expected = extract_media_path(url)
            if not expected:
                continue
            candidates = [expected] if expected in catalog else basename_index.get(pathlib.PurePosixPath(expected).name, [])
            item = {"article_file": str(post.relative_to(ROOT)), "article_title": title,
                    "source_url": url, "expected_local_path": expected,
                    "matching_paths": candidates,
                    "status": "EXACT_PATH" if expected in catalog else ("AMBIGUOUS_BASENAME" if candidates else "NOT_FOUND"),
                    "visual_status": "UNVERIFIED"}
            (links if expected in catalog else unresolved).append(item)
    result = {"schema": "sayd-article-media-crossref-v1", "articles_scanned": articles,
              "exact_links": len(links), "nonexact_links": len(unresolved),
              "warning": "Source Markdown is historical. NOT_FOUND does not prove a live broken image. No site changes.",
              "exact": links, "nonexact": unresolved}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("articles_scanned","exact_links","nonexact_links")}, ensure_ascii=False))
if __name__ == "__main__":
    main()
