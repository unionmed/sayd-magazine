#!/usr/bin/env python3
"""Fetch unique featured originals for homepage + related-card gaps.

Wayback first. Open-license Commons only when the title names a species
and the WP original is missing or a stand-in copy.
Never overwrites Mars / Suhail / brand / already-unique open-license files.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util  # noqa: E402

from homepage_thumbs import BRAND_KEEP, MARS_OWNED, SUHAIL_KEEP  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "mirror_media", Path(__file__).resolve().parent / "mirror-media.py"
)
_mm = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mm)

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
PROTECTED = set(MARS_OWNED) | set(SUHAIL_KEEP) | set(BRAND_KEEP)

# Featured originals for homepage GAP cards + related placeholder slugs.
PRIORITY_RELS = [
    "uploads/2015/06/نور-8.jpg",
    "uploads/2015/04/51.jpg",
    "uploads/2015/03/ربيع-عقل-7.jpg",
    "uploads/2015/03/محمد-حلال-4.jpg",
    "uploads/2017/04/رسالة-من-كرواتي-الى-ميشال-عون.jpg",
    "uploads/2020/10/Kark1-1.jpeg",
    "uploads/2020/10/Kark1.jpeg",
    "uploads/2020/10/044aa395-6a80-4a9f-9030-775eca7f1086.jpg",
    "uploads/2020/05/رالف-2.jpg",
    "uploads/2020/05/فوائد-الرماية.jpg",
    "uploads/2020/07/رامية.jpg",
    "uploads/2020/06/خرطوش-صيد.jpg",
    "uploads/2015/03/خرطوش-صيد.jpg",
    "uploads/2015/04/16.jpg",
    "uploads/2022/10/لين-2.jpg",
    "uploads/2024/02/اللزاب.jpg",
    "uploads/2024/09/الخبيزة-00.jpeg",
    "uploads/2022/08/اماني-الحمصي-2.jpg",
    "uploads/2022/11/طازة-3.jpg",
    "uploads/2024/08/dog.jpg",
    "uploads/2022/12/كلب.png",
    "uploads/2025/06/عبري-الاعماق-شهيد-الزواج.jpg",
    "uploads/2025/09/hg.th--1024x576.jpg",
    "uploads/2025/09/الشكران.jpg",
    "uploads/2022/10/ddi.jpg",
    "uploads/2023/04/جلد-الكلب.png",
    "uploads/2024/09/IMG-20230102-WA0027.jpg",
    "uploads/2024/09/IMG-20230102-WA0034.jpg",
    "uploads/2024/09/Ghassan-Nassour-1-3.jpg",
    "uploads/2026/09/1000468655.jpg",
    "uploads/2026/09/saudi-hunting-season-2026.jpg",
    "uploads/2022/10/لين-2.jpg",
]

# Commons fills: slug → (dest rel, commons filename, license note)
COMMONS_FILLS = {
    "اللي-ما-يعرف-الصقر-يشويه": (
        "uploads/2026/09/grus-grus-common-crane.jpg",
        "Common Crane (Grus grus) 2.jpg",
        "Charles J. Sharp, CC BY-SA 4.0 — الكرك / Grus grus (article body)",
    ),
    "كرواتي-يطلب-من-عون-حماية-لقلقه-klepetan-من-نار": (
        "uploads/2026/09/ciconia-ciconia-white-stork.jpg",
        "Ciconia ciconia 01.jpg",
        "CC-licensed white stork — Klepetan is Ciconia ciconia",
    ),
    "أسرار-الأرض-عشبة-الزوفا": (
        "uploads/2026/09/hyssopus-officinalis.jpg",
        "Hyssopus officinalis 001.JPG",
        "Hyssopus officinalis — title names الزوفا",
    ),
    "أنا-الصيّاد-أعرف-عشبة-الخبيزة": (
        "uploads/2026/09/malva-sylvestris.jpg",
        "Malva sylvestris 003.JPG",
        "Malva sylvestris — title names الخبيزة",
    ),
    "أسرار-الأرض-عشبة-الشُكران-السمّ-الص": (
        "uploads/2026/09/conium-maculatum.jpg",
        "Conium maculatum 001.JPG",
        "Conium maculatum — title names الشكران",
    ),
    "الصيّاد-يعرف-شجرة-اللزاب-في-لبنان": (
        "uploads/2026/09/juniperus-excelsa.jpg",
        "Juniperus excelsa 1.jpg",
        "Juniperus excelsa — title names اللزاب",
    ),
    "الأخطبوط-عبقريّ-الأعماق-وشهيد-الزواج": (
        "uploads/2026/09/octopus-vulgaris.jpg",
        "Octopus vulgaris 2.jpg",
        "Octopus vulgaris — title names الأخطبوط",
    ),
}

STANDIN_HASHES: set[str] = set()


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_standin_hashes() -> None:
    STANDIN_HASHES.clear()
    for rel in (
        "uploads/2022/12/بارودة.png",
        "uploads/2024/06/Bird-02.jpeg",
        "uploads/2024/09/Design.png",
        "uploads/2025/09/AP4I0956-1024x683.jpg",
        "uploads/2025/09/AP4I0032-1024x683.jpg",
        "uploads/2020/05/سينتيا.jpg",
        "uploads/2015/06/سلهب-3.jpg",
        "uploads/2024/02/ريتا-الشعار6.jpg",
        "uploads/2015/05/دينا-4.jpg",
    ):
        p = MEDIA / rel
        if p.is_file():
            STANDIN_HASHES.add(md5(p))


def is_unique_on_disk(rel: str) -> bool:
    dest = MEDIA / rel
    if not dest.is_file() or dest.stat().st_size <= 32:
        return False
    if rel in PROTECTED:
        return True
    return md5(dest) not in STANDIN_HASHES


def wp_url_for(rel: str) -> str:
    path = rel[len("uploads/") :] if rel.startswith("uploads/") else rel
    return "https://sayd-magazine.com/wp-content/uploads/" + path


def fetch_image(original: str) -> tuple[bool, bytes, str | None]:
    parts = urlsplit(original)
    encoded = urlunsplit(
        (parts.scheme, parts.netloc, quote(parts.path, safe="/"), parts.query, parts.fragment)
    )
    www = encoded.replace("://sayd-magazine.com", "://www.sayd-magazine.com")
    urls = [
        f"https://web.archive.org/web/0im_/{encoded}",
        f"https://web.archive.org/web/0im_/{www}",
    ]
    for url in urls:
        status, data, ctype = _mm.fetch(url, timeout=18)
        if status in (200, 203) and _mm.looks_like_image(data, ctype):
            return True, data, url
        time.sleep(0.08)
    return False, b"", None


COMMONS_ALTS = {
    "Common Crane (Grus grus) 2.jpg": [
        "Grus grus - Common Crane 01.jpg",
        "Eurasian Crane (Grus grus).jpg",
    ],
    "Ciconia ciconia 01.jpg": [
        "White Stork (Ciconia ciconia).jpg",
        "Ciconia ciconia -white stork-8.jpg",
    ],
    "Hyssopus officinalis 001.JPG": ["Hyssopus officinalis0.jpg"],
    "Malva sylvestris 003.JPG": ["Malva sylvestris flowers.jpg"],
    "Conium maculatum 001.JPG": ["Conium maculatum 002.JPG"],
    "Juniperus excelsa 1.jpg": ["Juniperus excelsa tree.jpg"],
    "Octopus vulgaris 2.jpg": ["Octopus vulgaris Cuvier, 1797.jpg"],
}


def fetch_commons(filename: str) -> tuple[bool, bytes, str | None]:
    names = [filename] + COMMONS_ALTS.get(filename, [])
    for name in names:
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(name)
        status, data, ctype = _mm.fetch(url, timeout=40)
        if status in (200, 203) and _mm.looks_like_image(data, ctype):
            return True, data, url
    return False, b"", None


def maybe_shrink(dest: Path) -> None:
    if not dest.is_file() or dest.stat().st_size < 1_800_000:
        return
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        return
    tmp = dest.with_suffix(dest.suffix + ".tmp.jpg")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(dest),
                "-vf",
                "scale='min(1600,iw)':-1",
                "-q:v",
                "4",
                str(tmp),
            ],
            check=True,
            capture_output=True,
        )
        if tmp.is_file() and 32 < tmp.stat().st_size < dest.stat().st_size:
            tmp.replace(dest)
        elif tmp.is_file():
            tmp.unlink()
    except Exception:
        if tmp.is_file():
            tmp.unlink()


def save(rel: str, data: bytes) -> None:
    dest = MEDIA / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    maybe_shrink(dest)


def main() -> int:
    load_standin_hashes()
    records: list[dict] = []
    print("fetch start", flush=True)
    commons_ok: dict[str, str] = {}
    for slug, (rel, filename, note) in COMMONS_FILLS.items():
        rec = {"rel": rel, "slug": slug, "status": "skipped", "bytes": 0, "note": note}
        if is_unique_on_disk(rel):
            rec["status"] = "unique-local"
            rec["bytes"] = (MEDIA / rel).stat().st_size
            commons_ok[slug] = rel
            records.append(rec)
            print(f"unique     {rel}", flush=True)
            continue
        ok, data, source = fetch_commons(filename)
        if ok:
            save(rel, data)
            rec["status"] = "commons"
            rec["bytes"] = (MEDIA / rel).stat().st_size
            rec["source"] = source
            commons_ok[slug] = rel
            print(f"commons    {rel} {rec['bytes']} {slug}", flush=True)
        else:
            rec["status"] = "commons-failed"
            print(f"FAIL commons {filename}", flush=True)
        records.append(rec)

    seen: set[str] = set()
    for rel in PRIORITY_RELS:
        if rel in seen:
            continue
        seen.add(rel)
        rec = {"rel": rel, "status": "skipped", "bytes": 0, "source": None}
        if rel in PROTECTED and is_unique_on_disk(rel):
            rec["status"] = "protected"
            rec["bytes"] = (MEDIA / rel).stat().st_size
            records.append(rec)
            print(f"protected  {rel}")
            continue
        if is_unique_on_disk(rel):
            rec["status"] = "unique-local"
            rec["bytes"] = (MEDIA / rel).stat().st_size
            records.append(rec)
            print(f"unique     {rel}")
            continue
        ok, data, source = fetch_image(wp_url_for(rel))
        if ok:
            save(rel, data)
            rec["status"] = "downloaded"
            rec["bytes"] = (MEDIA / rel).stat().st_size
            rec["source"] = source
            print(f"got        {rel} {rec['bytes']}")
        else:
            rec["status"] = "failed"
            print(f"FAIL       {rel}")
        records.append(rec)

    out = MEDIA / "gap-fetch.json"
    out.write_text(
        json.dumps({"records": records, "commons": commons_ok}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
