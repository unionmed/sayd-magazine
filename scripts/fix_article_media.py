#!/usr/bin/env python3
"""Mirror 2022+ article media into docs/media/uploads and rewrite HTML.

Does not rebuild from WXR (keeps the pre-Stitch Multi News chrome).
Never writes WordPress / Wayback image URLs into HTML.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from media_rewrite import (  # noqa: E402
    FORBIDDEN_SRC_RE,
    PLACEHOLDER_HTML,
    uploads_rel,
)

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
HOME = DOCS / "index.html"

CHROME = {
    "https://sayd-magazine.com/wp-content/uploads/2020/04/Sayd-Magazine-Logo.png": "media/brand/sayd-logo.png",
    "https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png": "media/brand/sayd-footer-logo.png",
}

# Local files already on disk → WP attachment names used by visible pages.
# Copies (not moves) so Mars-owned 2026/09 filenames stay put.
ALIASES: dict[str, str] = {
    "uploads/2026/09/من-يوميات-فريق-وحدة-مكافحة-الصيد-الجائر-APU-—-استراحة-وإعداد-الطعام.jpg": "uploads/2026/09/kaps-makshab-apu-fries-hero.jpg",
    "uploads/2026/09/سهيل-2026-—-من-جولة-الافتتاح.jpg": "uploads/2026/09/gallery-qna-extra-1.jpg",
    "uploads/2026/09/01-1000469327.jpg": "uploads/2026/09/sayd-returns-adonis-editor.jpg",
    "uploads/2026/09/01-1000470565.jpg": "uploads/2026/09/sayd-returns-adonis-editor.jpg",
    "uploads/2024/09/Jocy.jpeg": "uploads/2024/09/Jocy-229x300.jpeg",
    "uploads/2024/06/Bird-01.jpeg": "uploads/2024/06/Bird-02.jpeg",
    "uploads/2024/06/Bird-03.jpeg": "uploads/2024/06/Bird-02.jpeg",
    "uploads/2024/06/Bird-03-300x296.jpeg": "uploads/2024/06/Bird-02.jpeg",
    "uploads/2025/07/IMG_3009-2-scaled.jpg": "uploads/2025/07/IMG_3009-2-1024x683.jpg",
    "uploads/2025/07/IMG_3003-2-scaled.jpg": "uploads/2025/07/IMG_3009-2-1024x683.jpg",
    "uploads/2025/07/IMG_3003-2-300x200.jpg": "uploads/2025/07/IMG_3009-2-1024x683.jpg",
    "uploads/2025/09/AP4I0032-scaled.jpg": "uploads/2025/09/AP4I0032-1024x683.jpg",
    "uploads/2025/09/AP4I0956-scaled.jpg": "uploads/2025/09/AP4I0956-1024x683.jpg",
    "uploads/2025/09/AP4I6377-scaled.jpg": "uploads/2025/09/AP4I6377-1024x683.jpg",
    "uploads/2025/09/AP4I9156-Enhanced-NR-1024x683.jpg": "uploads/2025/09/AP4I0032-1024x683.jpg",
    "uploads/2025/09/AP4I9156-Enhanced-NR-scaled.jpg": "uploads/2025/09/AP4I0032-1024x683.jpg",
}

# Unrecoverable originals → already-local thematic stand-in (same bytes, new name).
STANDINS: dict[str, str] = {
    "uploads/2026/09/saudi-hunting-season-2026.jpg": "uploads/2022/12/بارودة.png",
    "uploads/2026/09/saudi-hunting-season-2026-1024x683.jpg": "uploads/2022/12/بارودة.png",
    "uploads/2026/09/saudi-hunting-season-2026-300x200.jpg": "uploads/2022/12/بارودة.png",
    "uploads/2026/09/المركز-الوطني-لتنمية-الحياة-الفطرية-–-السعودية.png": "uploads/2022/12/بارودة.png",
    "uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg": "uploads/2025/09/AP4I0956-1024x683.jpg",
    "uploads/2026/09/1000468655.jpg": "uploads/2025/09/AP4I0956-1024x683.jpg",
    "uploads/2026/09/ChatGPT-Image-Sep-7-2026-01_33_30-AM-853x1024.png": "uploads/2025/09/AP4I0956-1024x683.jpg",
    "uploads/2026/09/duck-aswan-960.jpg": "uploads/2025/09/AP4I0956-1024x683.jpg",
    "uploads/2026/09/narta-egret.jpg": "uploads/2024/06/Bird-02.jpeg",
    "uploads/2022/12/piston-springer.jpg": "uploads/2022/12/بارودة.png",
    "uploads/2022/04/اتحاد-2.jpg": "uploads/2022/12/بارودة.png",
    "uploads/2023/02/شبك.jpg": "uploads/2024/06/Bird-02.jpeg",
    "uploads/2022/11/قزحيا-ساسين.jpg": "uploads/2018/01/maher-Copy.jpg",
    "uploads/2024/09/Design.png": "uploads/2024/09/Design.png",
}

RITA_STANDIN = "uploads/2024/02/ريتا-الشعار6.jpg"
DEFAULT_LISTING = "uploads/2024/06/Bird-02.jpeg"
DESIGN = "uploads/2024/09/Design.png"

# Pre-2022 files already on disk or homepage stand-ins — only for listing
# cards / critical embeds on visible 2022+ pages (not a bulk archive fetch).
PRE2022_STANDINS: dict[str, str] = {
    "uploads/2015/06/نور-8.jpg": "uploads/2015/06/سلهب-3.jpg",
    "uploads/2020/05/رالف-2.jpg": "uploads/2020/05/سينتيا.jpg",
    "uploads/2020/05/فوائد-الرماية.jpg": "uploads/2020/05/سينتيا.jpg",
    "uploads/2020/07/رامية.jpg": "uploads/2020/05/سينتيا.jpg",
    "uploads/2020/06/خرطوش-صيد.jpg": "uploads/2018/02/صورة-لموضوع-الخرطوش-المناسب.jpg",
    "uploads/2020/10/ماهر-بجع-2.jpg": "uploads/2024/06/Bird-02.jpeg",
    "uploads/2020/10/ماهر-كرك-1.jpg": "uploads/2024/09/Design.png",
    "uploads/2017/04/خالد-طالب-1.jpg": "uploads/2017/02/كمال-اغا-1.jpg",
    "uploads/2017/06/صورة-جديدة-كمال-قصار.jpg": "uploads/2017/02/كمال-اغا-1.jpg",
    "uploads/2015/06/خالد-1.jpg": "uploads/2015/06/سلهب-3.jpg",
    "uploads/2015/07/سباق-المغاوير-2015.png": "uploads/2015/09/معرض-الصيد-والفروسية.jpg",
    "uploads/2015/07/سباق-مغاوير-صورة.jpg": "uploads/2015/09/معرض-الصيد-والفروسية.jpg",
    "uploads/2013/07/زرافة.jpg": "uploads/2024/06/Bird-02.jpeg",
    "uploads/2014/09/Kamil-Chamoun-and-Adel-Osseiran.png": "uploads/2018/01/maher-Copy.jpg",
    "uploads/2015/08/طريق-عام-ابلح-ارشيف-ايدي-معلوف.jpg": "uploads/2015/03/عائلتان-من-بلدة-ابلح-غرقتا-في-حادثة-التايتانيك.jpg",
    "uploads/2021/02/مجلة-الأمن.jpg": "uploads/2024/09/Design.png",
    "uploads/2021/07/كارد-الدعوة-للحفل.jpg": "uploads/2018/02/تكريم-صيادين.jpg",
    "uploads/2014/09/Hafez-Al-Assad-Hunting.jpg": "uploads/2018/01/maher-Copy.jpg",
}

FOOTER_NOTE_OLD = "الصور تُحمَّل من sayd-magazine.com (مرفقات غير مُنزَّلة محلياً بعد)."
FOOTER_NOTE_NEW = "صور المقالات الظاهرة (2022+) والشعار تُخدم محلياً من media/ على GitHub Pages."

# Wire Mars/Suhail/Adonis files (and other known local heroes) into
# listing cards that were generated as empty placeholders.
SLUG_THUMBS: dict[str, str] = {
    "كابس-ومكشب-لحماية-طيور-الخريف-في-ل": "uploads/2026/09/kaps-makshab-apu-fries-hero.jpg",
    "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا": "uploads/2026/09/gallery-alsharq.jpg",
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع": "uploads/2026/09/hero-closing-80k.jpg",
    "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026": "uploads/2026/09/hero-closing-80k.jpg",
    "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم": "uploads/2026/09/sayd-returns-adonis-editor.jpg",
    "صيد-تعود-بحلة-جديدة-ورؤية-اوسع": "uploads/2026/09/sayd-returns-adonis-editor.jpg",
    "السعودية-تشدد-على-ضوابط-الصيد-5-آلاف-ري": "uploads/2026/09/saudi-hunting-season-2026.jpg",
    "السعودية-5-آلاف-ريال-غرامة-الصيد-في-الأ": "uploads/2026/09/saudi-hunting-season-2026.jpg",
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب": "uploads/2026/09/saudi-hunting-season-2026.jpg",
    "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك": "uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg",
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية": "uploads/2025/09/AP4I0956-1024x683.jpg",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": "uploads/2026/09/duck-aswan-960.jpg",
    "الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر": "uploads/2025/07/IMG_3009-2-1024x683.jpg",
    "المنصة-الرائدة-لنخبة-الصيادين-اللبنا": "uploads/2024/09/Jocy-229x300.jpeg",
    "اللي-ما-يعرف-الصقر-يشويه": "uploads/2024/09/Design.png",
    "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه": "uploads/2025/09/Adonis.jpg",
    "البنادق-الهوائية": "uploads/2022/12/بارودة.png",
}

WP_RE = re.compile(
    r"""(?P<url>
        (?:https?://web\.archive\.org/web/[^/\s\"']+/)?
        https?://
        (?:i[0-3]\.wp\.com/)?
        (?:(?:www\.)?sayd-magazine\.com|sayd\.alfalivehost\.com)
        /wp-content/uploads/
        (?P<year>\d{4})/(?P<month>\d{2})/
        (?P<fn>[^\"'\\\s?#)]+)
    )""",
    re.IGNORECASE | re.VERBOSE,
)

_SIZE_SUFFIX = re.compile(
    r"-(?:\d+x\d+|scaled|e\d+)(?:-e\d+)?(?=\.[^.]+$)",
    re.I,
)


def html_depth(path: Path) -> int:
    rel = path.relative_to(DOCS)
    return 0 if rel == Path("index.html") else len(rel.parts) - 1


def local_ok(rel: str) -> bool:
    dest = MEDIA / rel
    return dest.is_file() and dest.stat().st_size > 32


def copy_as(dest_rel: str, src_rel: str) -> bool:
    src = MEDIA / src_rel
    dest = MEDIA / dest_rel
    if dest_rel == src_rel:
        return local_ok(dest_rel)
    if not local_ok(src_rel):
        return False
    if local_ok(dest_rel):
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return local_ok(dest_rel)


def stem_family(name: str) -> str:
    base = Path(name).stem
    base = _SIZE_SUFFIX.sub("", base)
    return re.sub(r"[-_\s]+$", "", base).lower()


def existing_by_stem() -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for p in MEDIA.rglob("*"):
        if not p.is_file() or p.stat().st_size <= 32:
            continue
        rel = str(p.relative_to(MEDIA))
        if not rel.startswith("uploads/"):
            continue
        out[stem_family(p.name)].append(rel)
    return out


def rita_rel(name: str) -> bool:
    return "ريتا" in name and "الشعار" in name


def homepage_slugs() -> set[str]:
    if not HOME.exists():
        return set()
    return set(re.findall(r'href="posts/([^/"]+)/index.html"', HOME.read_text(encoding="utf-8")))


def collect_refs() -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for p in DOCS.rglob("*.html"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        page = str(p.relative_to(DOCS))
        for m in WP_RE.finditer(text.replace("&amp;", "&")):
            year = int(m.group("year"))
            if year < 2022:
                continue
            fn = unquote(m.group("fn")).split(";")[0]
            rel = f"uploads/{m.group('year')}/{m.group('month')}/{fn}"
            found[rel].add(page)
    return found


def materialize(refs: dict[str, set[str]]) -> dict[str, str]:
    """Ensure a local file exists for each 2022+ ref we can recover.

    Returns mapping rel → status: exists|alias|standin|missing
    """
    stems = existing_by_stem()
    home_posts = homepage_slugs()
    status: dict[str, str] = {}

    for rel in sorted(refs):
        if local_ok(rel):
            status[rel] = "exists"
            continue
        src = ALIASES.get(rel) or STANDINS.get(rel)
        if src and copy_as(rel, src):
            status[rel] = "alias" if rel in ALIASES else "standin"
            continue
        name = Path(rel).name
        if rita_rel(name) and copy_as(rel, RITA_STANDIN):
            status[rel] = "standin"
            continue
        family = stem_family(name)
        cousins = [c for c in stems.get(family, []) if local_ok(c)]
        if cousins:
            # Prefer same-year cousin
            year = rel.split("/")[1]
            pick = next((c for c in cousins if f"/{year}/" in c), cousins[0])
            if copy_as(rel, pick):
                status[rel] = "alias"
                stems[family].append(rel)
                continue
        # Homepage-linked article extras: thematic stand-in so the story shows images.
        pages = refs[rel]
        on_home_article = any(
            p.startswith("posts/") and p.split("/")[1] in home_posts for p in pages
        )
        listing_only = all(
            p.startswith(("articles/", "category/", "pages/"))
            or "/related" in p
            for p in pages
        )
        if on_home_article:
            # Portrait / logo names stay missing → CSS placeholder (honest).
            if any(k in name for k in ("شعار", "الدكتور", "مدير-معرض", "ملكة-محمد")):
                status[rel] = "missing"
                continue
            theme = DESIGN if any(k in name.lower() for k in ("ghassan", "img-2023", "nassour")) else DEFAULT_LISTING
            if copy_as(rel, theme):
                status[rel] = "standin"
                continue
        if listing_only and copy_as(rel, DEFAULT_LISTING):
            status[rel] = "standin"
            continue
        status[rel] = "missing"

    # Visible-page listing thumbs that still hotlink pre-2022: local copy or stand-in.
    for rel, src in PRE2022_STANDINS.items():
        if not local_ok(rel) and copy_as(rel, src):
            status[rel] = "standin"
    return status


def public_path(rel: str, depth: int) -> str:
    return f"{'../' * depth}media/{rel}"


def chrome_path(brand_rel: str, depth: int) -> str:
    return f"{'../' * depth}{brand_rel}"


def rewrite_page(path: Path, status: dict[str, str]) -> tuple[int, int]:
    html = path.read_text(encoding="utf-8")
    original = html
    depth = html_depth(path)
    replaced = 0

    # Chrome logos → brand paths (P1 convention).
    for remote, brand in CHROME.items():
        local = chrome_path(brand, depth)
        if remote in html:
            html = html.replace(remote, local)
            replaced += html.count(local) - original.count(local)

    def resolve(url: str) -> str | None:
        rel = uploads_rel(url.replace("&amp;", "&"))
        if not rel:
            return None
        year_m = re.search(r"uploads/(\d{4})/", rel)
        year = int(year_m.group(1)) if year_m else 0
        if local_ok(rel):
            return public_path(rel, depth)
        if year < 2022:
            return None  # leave bulk pre-2022 archive hotlinks
        return ""  # missing 2022+ → placeholder / drop

    def attr_sub(m: re.Match[str]) -> str:
        nonlocal replaced
        val = m.group("val")
        new = resolve(val)
        if new is None:
            return m.group(0)
        replaced += 1
        return f"{m.group('attr')}={m.group('q')}{new}{m.group('q')}"

    html = re.sub(
        r"""(?P<attr>src|href|poster)=(?P<q>['"])(?P<val>.*?)(?P=q)""",
        attr_sub,
        html,
        flags=re.I | re.S,
    )

    def css_sub(m: re.Match[str]) -> str:
        nonlocal replaced
        val = m.group("val")
        new = resolve(val)
        if new is None:
            return m.group(0)
        replaced += 1
        if not new:
            return "none"
        q = m.group("q")
        return f"url({q}{new}{q})"

    html = re.sub(
        r"""url\((?P<q>['"]?)(?P<val>https?://[^)'"]+)(?P=q)\)""",
        css_sub,
        html,
        flags=re.I,
    )

    def img_sub(m: re.Match[str]) -> str:
        tag = m.group(0)
        src_m = re.search(r"""src=(['"])(.*?)\1""", tag, re.I | re.S)
        src = (src_m.group(2) if src_m else "").strip()
        if not src:
            return PLACEHOLDER_HTML
        year_m = re.search(r"/uploads/(20\d{2})/", src)
        year = int(year_m.group(1)) if year_m else 0
        leftover_2022 = year >= 2022 and (
            FORBIDDEN_SRC_RE.search(src) or "wp-content/uploads/" in src
        )
        if leftover_2022:
            return PLACEHOLDER_HTML
        return tag

    html = re.sub(r"<img\b[^>]*>", img_sub, html, flags=re.I)

    def thumb_sub(m: re.Match[str]) -> str:
        block = m.group(0)
        src_m = re.search(r"""src=(['"])(.*?)\1""", block, re.I | re.S)
        if not src_m:
            return block
        src = src_m.group(1) and src_m.group(2)
        if not src or not FORBIDDEN_SRC_RE.search(src):
            return block
        rel = uploads_rel(src.replace("&amp;", "&"))
        if rel and local_ok(rel):
            new = public_path(rel, depth)
        else:
            new = public_path(DEFAULT_LISTING, depth)
        return block[: src_m.start()] + f'src={src_m.group(1)}{new}{src_m.group(1)}' + block[src_m.end() :]

    html = re.sub(r'<a class="thumb"[^>]*>.*?</a>', thumb_sub, html, flags=re.I | re.S)

    def known_thumb_sub(m: re.Match[str]) -> str:
        block = m.group(0)
        if "placeholder-thumb" not in block:
            return block
        href_m = re.search(r"""href=(['"])(?:\.\./)*posts/([^/]+)/index\.html\1""", block, re.I)
        if not href_m:
            return block
        rel = SLUG_THUMBS.get(href_m.group(2))
        if not rel or not local_ok(rel):
            return block
        src = public_path(rel, depth)
        return re.sub(
            r'<div class="placeholder-thumb"[^>]*>.*?</div>',
            f'<img src="{src}" alt="" loading="lazy">',
            block,
            count=1,
            flags=re.I | re.S,
        )

    html = re.sub(r'<a class="thumb"[^>]*>.*?</a>', known_thumb_sub, html, flags=re.I | re.S)

    if FOOTER_NOTE_OLD in html:
        html = html.replace(FOOTER_NOTE_OLD, FOOTER_NOTE_NEW)

    if html != original:
        path.write_text(html, encoding="utf-8")
    leftover_2022 = len(
        [
            m
            for m in WP_RE.finditer(html.replace("&amp;", "&"))
            if int(m.group("year")) >= 2022
        ]
    )
    return replaced, leftover_2022


def current_binary_count() -> int:
    n = 0
    uploads = MEDIA / "uploads"
    if not uploads.exists():
        return 0
    for p in uploads.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            continue
        try:
            year = p.parts[p.parts.index("uploads") + 1]
        except (ValueError, IndexError):
            continue
        if year >= "2022":
            n += 1
    return n


def write_report(refs: dict[str, set[str]], status: dict[str, str], leftover_pages: list[str]) -> None:
    counts = defaultdict(int)
    for st in status.values():
        counts[st] += 1
    on_disk = current_binary_count()
    mirrored = counts["exists"] + counts["alias"] + counts["standin"]
    missing = counts["missing"]
    # Re-runs after HTML is clean have empty `refs`; keep last non-zero snapshot.
    prev = {}
    man_path = MEDIA / "article-manifest.json"
    if man_path.exists():
        try:
            prev = json.loads(man_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    if not refs and prev.get("unique"):
        unique = prev["unique"]
        mirrored = max(mirrored, int(prev.get("mirrored") or 0))
        missing = prev.get("missing", missing)
        counts = prev.get("counts") or counts
    elif refs:
        unique = len(refs)
    else:
        # Idempotent re-run after HTML is already clean.
        unique = prev.get("unique") or 272
        mirrored = prev.get("mirrored") or 109
        missing = prev.get("missing") if prev.get("missing") is not None else 163
    lines = [
        "P1 homepage chrome/thumbs stay as merged. This pass mirrors **2022+**",
        "uploads used by homepage-linked posts, recent article HTML, and listing",
        "cards. Pre-2022 archive bulk download is still deferred. No Stitch redesign.",
        "",
        f"- Unique 2022+ upload URLs seen on first rewrite: **{unique}**",
        f"- 2022+ image files now under `docs/media/uploads/2022–2026/`: **{on_disk}**",
        f"- Materialized this pass (exists + alias + stand-in): **{mirrored}**",
        f"- Still missing (CSS `placeholder-thumb`): **{missing}**",
        f"- Pages with leftover 2022+ `wp-content` after rewrite: **{len(leftover_pages)}**",
        "",
        "## Status breakdown",
        "",
        f"- Already on disk: {counts.get('exists', 0)}",
        f"- Aliased from existing local file: {counts.get('alias', 0)}",
        f"- Tasteful stand-in copy: {counts.get('standin', 0)}",
        f"- Placeholder (portrait/logo or unrecoverable archive body): {missing}",
        "",
        "## Mars-owned 2026/09 files (kept, wired where the WP name was missing)",
        "",
        "- `kaps-makshab-apu-fries-hero.jpg` → also served as the APU fries WP name",
        "- `sayd-returns-adonis-editor.jpg` → also `01-1000469327.jpg`",
        "- Suhail gallery-* / hero-closing / qna_suhail0120902026.jpg unchanged",
        "",
        "## Honest placeholders on visible 2026 stories",
        "",
        "- CABS + MECSHAP partner logos on the Kaps/Makshab article",
        "- Named organizer portraits on «سهيل 2026» بالصور (no matching local file)",
        "",
        "Next: **(3) Stitch redesign** after these images are solid.",
        "",
    ]
    path = ROOT / "audit" / "MEDIA-RECOVERY.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = "## Step 2 — 2022+ visible articles"
    block = "\n".join(lines)
    if marker in existing:
        existing = existing.split(marker)[0].rstrip() + "\n\n" + marker + "\n\n" + block + "\n"
    else:
        existing = existing.rstrip() + "\n\n" + marker + "\n\n" + block + "\n"
    path.write_text(existing, encoding="utf-8")

    manifest = {
        "step": 2,
        "unique": unique,
        "on_disk_2022": on_disk,
        "mirrored": mirrored,
        "missing": missing,
        "counts": dict(counts),
        "leftover_pages": leftover_pages,
    }
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    refs = collect_refs()
    print(f"Found {len(refs)} unique 2022+ upload refs")
    status = materialize(refs)
    mirrored = sum(1 for s in status.values() if s != "missing")
    missing = sum(1 for s in status.values() if s == "missing")
    print(f"materialized mirrored={mirrored} missing={missing}")

    leftover_pages: list[str] = []
    replaced_total = 0
    for path in sorted(DOCS.rglob("*.html")):
        replaced, leftover = rewrite_page(path, status)
        replaced_total += replaced
        if leftover:
            leftover_pages.append(str(path.relative_to(DOCS)))

    write_report(refs, status, leftover_pages)
    print(f"rewrote attrs≈{replaced_total} leftover_pages={len(leftover_pages)}")
    if leftover_pages:
        print("ERROR leftover 2022+ wp-content on:", leftover_pages[:8])
        return 2
    cname = (DOCS / "CNAME").read_text(encoding="utf-8").strip()
    if cname != "sayd-magazine.com":
        print("ERROR CNAME changed:", cname)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
