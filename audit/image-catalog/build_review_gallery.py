#!/usr/bin/env python3
"""Generate an offline, review-only HTML gallery. Output defaults outside docs/."""
import argparse
import html
import pathlib
from urllib.parse import quote
from search_all import records, query

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("words", nargs="?", default="")
    parser.add_argument("--section", default="")
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--output", default="audit/image-catalog/review-gallery.html")
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error("limit must be 1..200")
    root = pathlib.Path(__file__).resolve().parents[2]
    dest = (root / args.output).resolve()
    published = (root / "docs").resolve()
    if dest == published or published in dest.parents:
        parser.error("Refusing to write to published docs/ directory")
    selected = query(list(records()), args.words, args.section, args.limit)
    cards = []
    for row in selected:
        p = row["path"]
        local = (root / p).resolve()
        if local.is_file():
            # The HTML lives under audit/image-catalog by default.
            src = pathlib.Path(__import__("os").path.relpath(local, dest.parent)).as_posix()
        else:
            # Preview only; a GitHub-hosted image is not an archive copy.
            src = "https://raw.githubusercontent.com/unionmed/sayd-magazine/main/" + quote(p, safe="/")
        cards.append('<figure><img loading="lazy" src="'+html.escape(src,quote=True)+'" alt="Unverified archive image">'
                     '<figcaption>'+html.escape(p)+'<small>UNVERIFIED — not cleared for editorial use</small></figcaption></figure>')
    page = '''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>صيد — معاينة أرشيفية داخلية</title>
<style>body{font-family:system-ui;margin:2rem;background:#f5f5f1;color:#222}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}figure{margin:0;padding:10px;background:white;border:1px solid #ddd}img{width:100%;height:180px;object-fit:contain}figcaption{font-size:12px;overflow-wrap:anywhere}small{display:block;color:#a43;margin-top:8px}</style>
<h1>معاينة داخلية — الصور غير متحققة بصريًا</h1><p>هذه الصفحة ليست للنشر ولا تثبت مصدر الصور أو حقوقها أو تاريخها.</p><main>''' + "".join(cards) + "</main></html>"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(page,encoding="utf-8")
    print(f"Generated {len(selected)} preview cards at {dest}")

if __name__ == "__main__":
    main()
