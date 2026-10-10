#!/usr/bin/env python3
"""Search all archive paths and exact Github article associations without editing files."""
import argparse
import collections
import json
from pathlib import PurePosixPath
from urllib.parse import quote
from search_all import ROOT, records, normalize

LINKS = ROOT / "audit/image-catalog/article-image-links.json"

def search(words, section="", limit=20):
    if not LINKS.exists():
        raise SystemExit("First run link_historical_articles.py to build Github article links")
    links = json.loads(LINKS.read_text(encoding="utf-8"))
    article_by_path = collections.defaultdict(list)
    for item in links["exact"]:
        title = item["article_title"]
        article = item["article_file"]
        if (title, article) not in article_by_path[item["expected_local_path"]]:
            article_by_path[item["expected_local_path"]].append((title, article))
    keys = normalize(words).split()
    found = []
    for item in records():
        if section and normalize(section) not in [normalize(s) for s in item["sections"]]:
            continue
        path = item["path"]
        article_matches = article_by_path.get(path, [])
        corpus = normalize(path + " " + " ".join(t for t, _ in article_matches))
        if not all(word in corpus for word in keys):
            continue
        found.append({
            "image_path": path, "image_blob_sha": item["sha"],
            "section_candidates": item["sections"],
            "filename": PurePosixPath(path).name,
            "image_github_url": "https://github.com/unionmed/sayd-magazine/blob/main/" + quote(path, safe="/"),
            "articles": [
                {"title": title,
                 "github_url": "https://github.com/unionmed/sayd-magazine/blob/main/" + quote(p, safe="/")}
                for title, p in article_matches
            ],
            "visual_status": "UNVERIFIED",
            "rights_status": "NOT_VERIFIED"
        })
        if len(found) >= limit:
            break
    return {
        "query": words, "section": section,
        "returned": len(found), "results": found,
        "disclaimer": "Matches from filename, candidate section and exact Github article links only. The image must be opened and checked before use. No Wordpress sources."
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("words", nargs="?", default="")
    p.add_argument("--section", default="")
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()
    if not 1 <= args.limit <= 200:
        p.error("limit 1..200")
    print(json.dumps(search(args.words, args.section, args.limit), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
