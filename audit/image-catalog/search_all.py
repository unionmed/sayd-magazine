#!/usr/bin/env python3
"""Read-only searchable catalog of Sayd's original GitHub image manifests.

Runs against a local checkout. Does not alter images, site pages, or SEO files.
"""
import argparse
import collections
import csv
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "audit/image-catalog/manifest"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
SECTIONS = {
    "الطيور": ["طير", "طيور", "حبارى", "سمان", "بط", "حمام", "عصفور", "bird", "quail", "duck", "eagle", "owl", "pelican"],
    "الصقارة": ["صقر", "صقور", "شاهين", "باز", "falcon", "falconry", "saker"],
    "الرماية والعتاد": ["رماية", "بندقية", "سلاح", "shooting", "rifle", "optics", "scope"],
    "الفروسية": ["حصان", "خيول", "خيل", "فروسية", "horse", "equestrian"],
    "الصيد": ["صيد", "قنص", "hunting", "hunter"],
    "الحياة البرية": ["غزال", "ذئب", "ثعلب", "wildlife", "gazelle"],
    "التخييم والبر": ["تخييم", "مخيم", "camp", "outdoor"],
    "البحر": ["سمك", "بحر", "صيد-سمك", "fishing", "sea"],
}
def normalize(s):
    s = unicodedata.normalize("NFKD", str(s or "")).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub("[إأآٱ]", "ا", s).replace("ى", "ي").replace("ـ", "")
    return re.sub(r"[_\\/\\-.]+", " ", s)

def candidate_sections(path):
    name = normalize(pathlib.PurePosixPath(path).name)
    found = [section for section, words in SECTIONS.items() if any(normalize(w) in name for w in words)]
    return found or ["غير مصنف"]

def records():
    if not MANIFEST.is_dir():
        raise FileNotFoundError("Missing manifest folder: " + str(MANIFEST))
    for manifest in sorted(MANIFEST.glob("*.tsv")):
        with manifest.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                if not row.get("path"):
                    continue
                yield {"path": row["path"], "sha": row["git_blob_sha"],
                       "size_bytes": int(row["size_bytes"]),
                       "sections": candidate_sections(row["path"]),
                       "visual_status": "UNVERIFIED",
                       "source_manifest": manifest.name}

def audit(rows, check_files=False):
    seen, hashes = set(), collections.defaultdict(list)
    missing, invalid, duplicate_paths = [], [], []
    for row in rows:
        p = row["path"]
        if p in seen:
            duplicate_paths.append(p)
        seen.add(p)
        hashes[row["sha"]].append(p)
        if not re.fullmatch(r"[0-9a-f]{40}", row["sha"]) or pathlib.PurePosixPath(p).suffix.lower() not in EXTENSIONS:
            invalid.append(p)
        if check_files and not (ROOT / p).is_file():
            missing.append(p)
    duplicates = [paths for paths in hashes.values() if len(paths) > 1]
    return {"records": len(rows), "unique_paths": len(seen), "unique_blob_shas": len(hashes),
            "duplicate_content_extra_paths": sum(len(g)-1 for g in duplicates),
            "duplicate_content_groups": len(duplicates),
            "duplicate_path_entries": duplicate_paths,
            "invalid_records": invalid,
            "missing_local_files": missing if check_files else "NOT_CHECKED",
            "sections_are_filename_candidates_only": True}

def query(rows, words="", section="", limit=30):
    tokens = normalize(words).split()
    selected = []
    for row in rows:
        if section and normalize(section) not in [normalize(x) for x in row["sections"]]:
            continue
        if not all(t in normalize(row["path"]) for t in tokens):
            continue
        selected.append({**row, "repository_url": "https://github.com/unionmed/sayd-magazine/blob/main/" + quote(row["path"], safe="/")})
        if len(selected) >= limit:
            break
    return selected

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("words", nargs="?", default="")
    p.add_argument("--section", default="")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--audit", action="store_true")
    p.add_argument("--check-files", action="store_true")
    args = p.parse_args()
    if not 1 <= args.limit <= 200:
        p.error("--limit must be 1..200")
    rows = list(records())
    out = audit(rows, args.check_files) if args.audit else {
        "total_indexed": len(rows), "results": query(rows, args.words, args.section, args.limit),
        "warning": "Filename-based suggestions only; visually verify before editorial use."}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.audit and (out["duplicate_path_entries"] or out["invalid_records"] or (args.check_files and out["missing_local_files"])):
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
