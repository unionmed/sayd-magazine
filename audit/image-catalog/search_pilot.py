#!/usr/bin/env python3
"""Read-only search for the Sayd archive image pilot. No network or writes."""
import argparse
import json
import pathlib
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = ROOT / "audit/image-catalog/pilot-2026-10-10.json"

def normalize(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold().replace("_", " ").replace("-", " ")

def search(records, query="", section="", limit=30):
    tokens = normalize(query).split()
    results = []
    for record in records:
        searchable = normalize(record.get("path", "") + " " + record.get("section_candidate", ""))
        if section and normalize(section) not in normalize(record.get("section_candidate", "")):
            continue
        if all(token in searchable for token in tokens):
            results.append(record)
    return results[:limit]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="", help="Words in filename/path, Arabic or English")
    parser.add_argument("--section", default="", help="Candidate section")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.limit <= 180:
        parser.error("--limit must be 1..180")
    with CATALOG.open(encoding="utf-8") as f:
        data = json.load(f)
    records = data["images"]
    results = search(records, args.query, args.section, args.limit)
    print(json.dumps({"catalog_count": len(records), "returned": len(results),
                      "unverified_visual": True, "results": results}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
