#!/usr/bin/env python3
"""Apply Batch 2 recovered binaries: unique thumbs, logos, omit wrong-species slots."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_unique_thumbs import apply_display_cleanup, fix_species_article_bodies, rewrite_page
from homepage_thumbs import assigned_file_set, is_unique_binary
from media_rewrite import FORBIDDEN_SRC_RE

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"


def wire_kaps_logos() -> None:
    page = DOCS / "posts" / "كابس-ومكشب-لحماية-طيور-الخريف-في-ل" / "index.html"
    html = page.read_text(encoding="utf-8")
    mesh = "uploads/2026/09/mecshap-official-logo.png"
    cabs = "uploads/2026/09/cabs-official-logo.png"
    guard = "uploads/2026/09/cabs-bird-guard-logo.jpg"
    if not (MEDIA / mesh).is_file() or not (MEDIA / cabs).is_file():
        return
    block = (
        '<div id="sayd-cabs-partner-logos" style="display:flex;flex-wrap:wrap;'
        'justify-content:center;align-items:center;gap:20px;margin:18px 0 24px;">'
        f'<img src="../../media/{mesh}" alt="شعار مركز الشرق الأوسط للصيد المستدام '
        'ومكافحة الصيد الجائر — مكشب MECSHAP" width="220" '
        'style="display:block;flex:0 1 220px;width:42%;max-width:220px;height:auto;object-fit:contain;">'
        f'<img src="../../media/{cabs}" alt="شعار CABS" width="220" '
        'style="display:block;flex:0 1 160px;width:28%;max-width:160px;height:auto;object-fit:contain;">'
        f'<img src="../../media/{guard}" alt="شعار CABS Bird Guard" width="220" '
        'style="display:block;flex:0 1 220px;width:42%;max-width:220px;height:auto;object-fit:contain;">'
        "</div>"
    )
    if 'id="sayd-cabs-partner-logos"' in html:
        html = re.sub(
            r'<div id="sayd-cabs-partner-logos"[^>]*>.*?</div>',
            block,
            html,
            count=1,
            flags=re.I | re.S,
        )
    else:
        html = html.replace(
            "<p>أعلنت منظمة CABS",
            block + "\n<p>أعلنت منظمة CABS",
            1,
        )
    if FORBIDDEN_SRC_RE.search(html):
        raise RuntimeError("forbidden src after logo wire")
    page.write_text(html, encoding="utf-8")
    print("wired Kaps logos")


def omit_wrong_map_slots() -> None:
    """Drop the bee-eater stand-in that was labeled as a Lebanon flyway map."""
    needle = "ChatGPT-Image-Sep-7-2026-01_33_30-AM-853x1024.png"
    for path in DOCS.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        if needle not in html:
            continue
        # Remove <img … ChatGPT-Image …>
        new = re.sub(
            rf'<img[^>]+{re.escape(needle)}[^>]*>',
            "",
            html,
            flags=re.I,
        )
        # Remove CSS background-image thumbs that used the same stand-in
        new = re.sub(
            rf'background-image:url\([^)]*{re.escape(needle)}\);',
            "background-image:none;",
            new,
        )
        if new != html:
            path.write_text(new, encoding="utf-8")
            print(f"omitted bee-eater-as-map in {path.relative_to(DOCS)}")


def restore_autumn_how_card(mapping: dict[str, str]) -> None:
    slug = "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو"
    if slug not in mapping:
        return
    home = DOCS / "index.html"
    html = home.read_text(encoding="utf-8")
    if f"posts/{slug}/index.html" in html:
        print("autumn-how card already on homepage")
        return
    rel = mapping[slug]
    card = f"""
<article class="card overlay">
  <a class="thumb" href="posts/{slug}/index.html"><img src="media/{rel}" alt="مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟" loading="lazy"></a>
  <div class="body">
    <div class="meta">8 أيلول 2026</div>
    <h3><a href="posts/{slug}/index.html">مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟</a></h3>
  </div>
</article>
"""
    html = re.sub(
        r'(<h2>أخبار</h2>.*?<div class="grid-4">)',
        r"\1" + card,
        html,
        count=1,
        flags=re.S,
    )
    home.write_text(html, encoding="utf-8")
    print("restored autumn-how homepage card")


def main() -> int:
    mapping = assigned_file_set(MEDIA)
    print(f"mapped slugs={len(mapping)}")
    total = 0
    for path in sorted(DOCS.rglob("*.html")):
        total += rewrite_page(path, mapping)
    fix_species_article_bodies()
    omit_wrong_map_slots()
    wire_kaps_logos()
    restore_autumn_how_card(mapping)
    cleaned = apply_display_cleanup()
    cname = (DOCS / "CNAME").read_text(encoding="utf-8").strip()
    if cname != "sayd-magazine.com":
        print("ERROR CNAME", cname)
        return 3
    print(f"rewrote {total}; cleaned {cleaned}; cname={cname}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
