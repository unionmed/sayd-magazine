#!/usr/bin/env python3
"""Create a complete preliminary taxonomy from existing manifests; no media changes."""
import collections
import json
import pathlib
from search_all import records

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "audit/image-catalog/preliminary-taxonomy.json"
def classify(row):
    path = row["path"]
    filename = pathlib.PurePosixPath(path).name
    labels = [x for x in row["sections"] if x != "غير مصنف"]
    return {
        "path": path, "sha": row["sha"], "size_bytes": row["size_bytes"],
        "section_candidates": labels or ["غير مصنف"],
        "filename": filename,
        "visual_status": "UNVERIFIED",
        "editorial_status": "REVIEW_ON_REUSE",
        "media_kind": "UNVERIFIED",
        "source": None, "photographer": None, "event_date": None,
        "country": None, "library_copy_status": "NOT_CHECKED"
    }

def main():
    items = [classify(r) for r in records()]
    counts = collections.Counter(s for r in items for s in r["section_candidates"])
    output = {"schema": "sayd-preliminary-taxonomy-v1", "classification_basis": "filename only",
              "no_visual_verification_claimed": True, "records": items,
              "summary": {"total": len(items), "categories_multi_label": dict(counts),
                          "unclassified": counts["غير مصنف"]}}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))
if __name__ == "__main__":
    main()
