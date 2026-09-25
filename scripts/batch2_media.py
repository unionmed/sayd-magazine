#!/usr/bin/env python3
"""Batch 2: recover remaining 2022–2026 originals + named next-batch files.

Wayback CDX first, then official partner logos, then Commons only when the
title/caption names the species (document every bird fill for Mars QA).
Never overwrite Mars / Suhail / brand files. Never write WP/Wayback src
into HTML. Green «صيد» placeholders stay forbidden.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util  # noqa: E402

from homepage_thumbs import (  # noqa: E402
    BRAND_KEEP,
    HOMEPAGE_FETCH_RELS,
    HOMEPAGE_GAPS,
    HOMEPAGE_UNIQUE_THUMBS,
    MARS_OWNED,
    SUHAIL_KEEP,
    assigned_file_set,
    is_unique_binary,
    standin_hashes,
    _md5,
)
from media_rewrite import FORBIDDEN_SRC_RE  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "mirror_media", Path(__file__).resolve().parent / "mirror-media.py"
)
_mm = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mm)

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
WXR = ROOT / "exports" / "saydmagazine-.WordPress.2026-09-15.xml"
CONTENT = ROOT / "content"

PROTECTED = set(MARS_OWNED) | set(SUHAIL_KEEP) | set(BRAND_KEEP)

# Named next-batch files (some pre-2022 paths — homepage-visible only).
NEXT_BATCH_RELS = [
    "uploads/2015/06/نور-8.jpg",
    "uploads/2015/04/51.jpg",
    "uploads/2015/03/ربيع-عقل-7.jpg",
    "uploads/2015/03/محمد-حلال-4.jpg",
    "uploads/2020/10/Kark1-1.jpeg",
    "uploads/2020/10/Kark1.jpeg",
    "uploads/2020/05/رالف-2.jpg",
    "uploads/2020/05/فوائد-الرماية.jpg",
    "uploads/2020/07/رامية.jpg",
    "uploads/2015/04/16.jpg",
    "uploads/2026/09/1000468655.jpg",
    "uploads/2026/09/duck-aswan-960.jpg",
    "uploads/2026/09/narta-egret.jpg",
    "uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg",
    "uploads/2026/09/ChatGPT-Image-Sep-7-2026-01_33_30-AM-853x1024.png",
    "uploads/2026/09/saudi-hunting-season-2026.jpg",
    "uploads/2026/09/شعار-كابس-—-CABS-Bird-Guard.jpg",
    "uploads/2026/09/شعار-مركز-الشرق-الأوسط-للصيد-المستدام-ومكافحة-الصيد-الجائر-—-MECSHAP.jpg",
    "uploads/2020/04/CABS.jpg",
    "uploads/2024/09/IMG-20230102-WA0027.jpg",
    "uploads/2024/09/IMG-20230102-WA0034.jpg",
    "uploads/2024/09/Ghassan-Nassour-1-3.jpg",
    "uploads/2022/12/كلب.png",
    "uploads/2022/10/ddi.jpg",
    "uploads/2025/06/عبري-الاعماق-شهيد-الزواج.jpg",
]

# Commons fills: dest rel → (commons filenames, license note, bird?)
COMMONS_FILLS: list[dict] = [
    {
        "rel": "uploads/2026/09/narta-egret.jpg",
        "names": [
            "Narta Lagoon, Albania – Little egret.jpg",
            "Little Egret Egretta garzetta.jpg",
            "Egretta garzetta -Little Egret.jpg",
        ],
        "note": "Egretta garzetta / بلشون أبيض صغير — caption already credits Pasztilla CC BY-SA 4.0",
        "bird": True,
        "species": "Egretta garzetta (Little Egret)",
        "review": "Mars QA — body of «مع هجرة الخريف» already names this Commons file",
    },
    {
        "rel": "uploads/2026/09/duck-aswan-960.jpg",
        "names": [
            "Ferruginous Duck, Aswan.jpg",
            "Aythya nyroca Ferruginous Duck.jpg",
            "Ferruginous duck (Aythya nyroca) male.jpg",
        ],
        "note": "Aythya nyroca / البط الحديدي — caption already credits terolinjama CC0",
        "bird": True,
        "species": "Aythya nyroca (Ferruginous Duck)",
        "review": "Mars QA — body of «مع هجرة الخريف» already names this Commons file",
    },
    {
        "rel": "uploads/2026/09/pelecanus-onocrotalus-great-white-pelican.jpg",
        "names": [
            "Pelecanus onocrotalus -Great White Pelican.jpg",
            "Great White Pelican (Pelecanus onocrotalus).jpg",
            "Pelecanus onocrotalus 2.jpg",
            "Great White Pelican in flight.jpg",
        ],
        "note": "Commons species fill kept on disk only; live pages use Nayef Krayem original",
        "bird": True,
        "species": "Pelecanus onocrotalus (Great White Pelican)",
        "review": "Live hero is uploads/2026/09/great-white-pelican-nayef-krayem-matn-2026.jpg",
    },
    {
        "rel": "uploads/2026/09/africa-eurasia-flyway-map.jpg",
        "names": [
            "Bird migration routes.svg",
            "Flyways of migratory birds.svg",
            "World bird migration flyways.png",
        ],
        "note": "Open-license flyway map for autumn-migration article (not the missing ChatGPT PNG)",
        "bird": False,
        "species": "",
        "review": "Topic match for migration-map slot; not the original ChatGPT file",
    },
    {
        "rel": "uploads/2026/09/malva-sylvestris.jpg",
        "names": [
            "Malva sylvestris flowers.jpg",
            "Malva sylvestris 003.JPG",
            "Malva sylvestris 01.jpg",
        ],
        "note": "Malva sylvestris — title names الخبيزة (batch1 Commons failed)",
        "bird": False,
        "species": "",
        "review": "",
    },
]

LOGO_SOURCES = {
    "uploads/2026/09/cabs-official-logo.png": [
        "https://www.komitee.de/fileadmin/templates/komitee/Resources/Public/Images/logo.png",
        "https://www.komitee.de/fileadmin/templates/komitee/Resources/Public/Images/cabs-logo.png",
        "https://www.komitee.de/typo3conf/ext/template/Resources/Public/Images/logo.svg",
        "https://www.komitee.de/fileadmin/user_upload/logo.png",
    ],
    "uploads/2026/09/mecshap-official-logo.png": [
        "https://www.mecshap.org/favicon.ico",
    ],
    "uploads/2020/04/CABS.jpg": [],  # Wayback / WP only
}

UA = "SaydMagazineStatic/1.0 (+https://github.com/unionmed/sayd-magazine; media recovery batch2)"


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def wp_url_for(rel: str) -> str:
    path = rel[len("uploads/") :] if rel.startswith("uploads/") else rel
    return "https://sayd-magazine.com/wp-content/uploads/" + path


def encode_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (parts.scheme, parts.netloc, quote(parts.path, safe="/"), parts.query, parts.fragment)
    )


def cdx_candidates(original: str) -> list[str]:
    """Build Wayback candidate URLs: CDX hits + 0im_/im_ variants."""
    urls: list[str] = []
    variants = [original, encode_url(original)]
    www = original.replace("://sayd-magazine.com", "://www.sayd-magazine.com")
    if www != original:
        variants.append(www)
        variants.append(encode_url(www))
    jet = original.replace("://sayd-magazine.com", "://i0.wp.com/sayd-magazine.com")
    variants.append(jet)

    for v in variants:
        hit = _mm.cdx_best(v)
        if hit:
            urls.append(hit)
        urls.append(f"https://web.archive.org/web/0im_/{encode_url(v) if '://' in v else v}")
        urls.append(f"https://web.archive.org/web/im_/{encode_url(v) if '://' in v else v}")
    # Also try live WP (usually 404 after static cutover)
    urls.append(encode_url(original))
    return list(dict.fromkeys(urls))


def fetch_bytes(url: str, timeout: int = 28) -> tuple[bool, bytes, str | None]:
    status, data, ctype = _mm.fetch(url, timeout=timeout)
    if status in (200, 203) and _mm.looks_like_image(data, ctype):
        return True, data, url
    return False, b"", None


def fetch_wayback(rel: str) -> tuple[bool, bytes, str | None]:
    for url in cdx_candidates(wp_url_for(rel)):
        ok, data, src = fetch_bytes(url)
        if ok:
            return True, data, src
        time.sleep(0.12)
    return False, b"", None


def fetch_commons(names: list[str]) -> tuple[bool, bytes, str | None]:
    for name in names:
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(name)
        ok, data, src = fetch_bytes(url, timeout=45)
        if ok:
            return True, data, src
        time.sleep(0.1)
    return False, b"", None


def maybe_shrink(dest: Path) -> None:
    if not dest.is_file() or dest.stat().st_size < 1_800_000:
        return
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


def save(rel: str, data: bytes) -> Path:
    dest = MEDIA / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    maybe_shrink(dest)
    return dest


def is_protected(rel: str) -> bool:
    return rel in PROTECTED or rel in MARS_OWNED or rel in SUHAIL_KEEP


def is_standin_copy(rel: str) -> bool:
    dest = MEDIA / rel
    if not dest.is_file() or dest.stat().st_size <= 32:
        return False
    if is_protected(rel):
        return False
    stolen = standin_hashes(MEDIA)
    return md5(dest) in stolen and rel not in {
        "uploads/2022/12/بارودة.png",
        "uploads/2024/06/Bird-02.jpeg",
        "uploads/2024/09/Design.png",
        "uploads/2025/09/AP4I0956-1024x683.jpg",
        "uploads/2025/09/AP4I0032-1024x683.jpg",
        "uploads/2020/05/سينتيا.jpg",
        "uploads/2015/06/سلهب-3.jpg",
        "uploads/2024/02/ريتا-الشعار6.jpg",
        "uploads/2015/05/دينا-4.jpg",
        "uploads/2018/02/صورة-لموضوع-الخرطوش-المناسب.jpg",
    }


def year_of(rel: str) -> int:
    m = re.search(r"uploads/(\d{4})/", rel)
    return int(m.group(1)) if m else 0


UPLOAD_RE = re.compile(
    r"""(?:https?:)?(?://)?(?:web\.archive\.org/web/[^/\s\"']+/)?(?:https?:)?(?://)?
        (?:i[0-3]\.wp\.com/)?
        (?:(?:www\.)?sayd-magazine\.com|sayd\.alfalivehost\.com)
        /wp-content/uploads/(?P<rel>20\d{2}/\d{2}/[^\"'\s?#<>]+)
    """,
    re.I | re.X,
)
LOCAL_MEDIA_RE = re.compile(
    r"""(?:\.\./)*media/uploads/(?P<rel>20\d{2}/\d{2}/[^\"'\s?#<>]+)""",
    re.I,
)


def collect_rels(*texts: str) -> set[str]:
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        blob = text.replace("&amp;", "&")
        for m in UPLOAD_RE.finditer(blob):
            rel = unquote(m.group("rel")).split(";")[0]
            found.add(f"uploads/{rel}")
        for m in LOCAL_MEDIA_RE.finditer(blob):
            rel = unquote(m.group("rel")).split(";")[0]
            found.add(f"uploads/{rel}")
    return found


def collect_2022_plus() -> list[str]:
    texts: list[str] = []
    if WXR.exists():
        texts.append(WXR.read_text(encoding="utf-8", errors="ignore"))
    for md in CONTENT.rglob("*.md"):
        texts.append(md.read_text(encoding="utf-8", errors="ignore"))
    for html in DOCS.rglob("*.html"):
        texts.append(html.read_text(encoding="utf-8", errors="ignore"))
    rels = collect_rels(*texts)
    rels.update(NEXT_BATCH_RELS)
    rels.update(HOMEPAGE_FETCH_RELS)
    rels.update(HOMEPAGE_UNIQUE_THUMBS.values())
    scoped = [r for r in rels if year_of(r) >= 2022 or r in NEXT_BATCH_RELS or r in HOMEPAGE_FETCH_RELS]
    return sorted(set(scoped))


def scrape_logo_urls() -> dict[str, list[str]]:
    """Pull logo <img> URLs from official partner homepages."""
    out: dict[str, list[str]] = {"cabs": [], "mecshap": []}
    pages = {
        "cabs": [
            "https://www.komitee.de/en/",
            "https://www.komitee.de/",
        ],
        "mecshap": [
            "https://www.mecshap.org/",
            "https://www.mecshap.org/about",
        ],
    }
    img_re = re.compile(r"""(?:src|href)=["']([^"']+\.(?:png|jpe?g|svg|webp))["']""", re.I)
    for key, urls in pages.items():
        for page in urls:
            status, data, _ = _mm.fetch(page, timeout=25)
            if status != 200 or not data:
                continue
            html = data.decode("utf-8", errors="ignore")
            for src in img_re.findall(html):
                low = src.lower()
                if "logo" in low or "brand" in low or "mecshap" in low or "cabs" in low or "komitee" in low:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        parsed = urlparse(page)
                        src = f"{parsed.scheme}://{parsed.netloc}{src}"
                    out[key].append(src)
    return out


def fetch_official_logos(records: list[dict]) -> None:
    extra = scrape_logo_urls()
    # CABS
    cabs_dest = "uploads/2026/09/cabs-official-logo.png"
    cabs_wp = "uploads/2026/09/شعار-كابس-—-CABS-Bird-Guard.jpg"
    cabs_old = "uploads/2020/04/CABS.jpg"
    cabs_urls = list(LOGO_SOURCES[cabs_dest]) + extra.get("cabs", [])
    got = False
    for url in cabs_urls:
        ok, data, src = fetch_bytes(url, timeout=30)
        if ok and len(data) > 200:
            save(cabs_dest, data)
            # Also store under the WP 2026 name if that slot is a stand-in / missing
            if is_standin_copy(cabs_wp) or not (MEDIA / cabs_wp).is_file():
                save(cabs_wp, data)
            records.append(
                {
                    "rel": cabs_dest,
                    "status": "official-logo",
                    "bytes": (MEDIA / cabs_dest).stat().st_size,
                    "source": src,
                    "note": "Official CABS / komitee.de mark — partner logo, not a story thumb",
                }
            )
            got = True
            print(f"logo       CABS {src}", flush=True)
            break
        time.sleep(0.1)
    if not got:
        ok, data, src = fetch_wayback(cabs_old)
        if ok:
            save(cabs_old, data)
            save(cabs_dest, data)
            if is_standin_copy(cabs_wp) or not (MEDIA / cabs_wp).is_file():
                save(cabs_wp, data)
            records.append(
                {"rel": cabs_old, "status": "wayback-logo", "bytes": len(data), "source": src}
            )
            print(f"logo       CABS wayback {src}", flush=True)
            got = True
    if not got:
        records.append({"rel": cabs_dest, "status": "logo-failed", "bytes": 0})
        print("FAIL logo  CABS", flush=True)

    # MECSHAP
    mesh_dest = "uploads/2026/09/mecshap-official-logo.png"
    mesh_wp = "uploads/2026/09/شعار-مركز-الشرق-الأوسط-للصيد-المستدام-ومكافحة-الصيد-الجائر-—-MECSHAP.jpg"
    mesh_urls = extra.get("mecshap", []) + [
        "https://www.mecshap.org/favicon.ico",
        "https://www.mecshap.org/logo.png",
        "https://www.mecshap.org/images/logo.png",
        "https://www.mecshap.org/assets/logo.png",
    ]
    got = False
    for url in mesh_urls:
        ok, data, src = fetch_bytes(url, timeout=30)
        if ok and len(data) > 400:
            save(mesh_dest, data)
            if is_standin_copy(mesh_wp) or not (MEDIA / mesh_wp).is_file():
                save(mesh_wp, data)
            records.append(
                {
                    "rel": mesh_dest,
                    "status": "official-logo",
                    "bytes": (MEDIA / mesh_dest).stat().st_size,
                    "source": src,
                    "note": "Official MECSHAP mark — partner logo, not a story thumb",
                }
            )
            print(f"logo       MECSHAP {src}", flush=True)
            got = True
            break
        time.sleep(0.1)
    if not got:
        records.append({"rel": mesh_dest, "status": "logo-failed", "bytes": 0})
        print("FAIL logo  MECSHAP", flush=True)


def fetch_one(rel: str) -> dict:
    rec = {"rel": rel, "status": "skipped", "bytes": 0, "source": None}
    dest = MEDIA / rel
    if is_protected(rel) and dest.is_file() and dest.stat().st_size > 32:
        rec["status"] = "protected"
        rec["bytes"] = dest.stat().st_size
        return rec
    unique = dest.is_file() and dest.stat().st_size > 32 and not is_standin_copy(rel)
    if unique:
        rec["status"] = "unique-local"
        rec["bytes"] = dest.stat().st_size
        return rec
    ok, data, src = fetch_wayback(rel)
    if ok:
        save(rel, data)
        rec["status"] = "downloaded"
        rec["bytes"] = (MEDIA / rel).stat().st_size
        rec["source"] = src
        return rec
    rec["status"] = "failed"
    return rec


def wire_kaps_logos() -> None:
    """Restore partner logos on the Kaps/Makshab article using local files only."""
    page = DOCS / "posts" / "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017" / "index.html"
    if not page.is_file():
        return
    html = page.read_text(encoding="utf-8")
    cabs = None
    mesh = None
    for cand in (
        "uploads/2026/09/cabs-official-logo.png",
        "uploads/2026/09/شعار-كابس-—-CABS-Bird-Guard.jpg",
        "uploads/2020/04/CABS.jpg",
    ):
        if (MEDIA / cand).is_file() and (MEDIA / cand).stat().st_size > 200:
            cabs = cand
            break
    for cand in (
        "uploads/2026/09/mecshap-official-logo.png",
        "uploads/2026/09/شعار-مركز-الشرق-الأوسط-للصيد-المستدام-ومكافحة-الصيد-الجائر-—-MECSHAP.jpg",
    ):
        if (MEDIA / cand).is_file() and (MEDIA / cand).stat().st_size > 400:
            mesh = cand
            break
    if not cabs and not mesh:
        return
    parts = []
    if mesh:
        parts.append(
            f'<img src="../../media/{mesh}" alt="شعار مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر — MECSHAP" width="220" style="display:block;flex:0 1 220px;width:42%;max-width:220px;height:auto;object-fit:contain;">'
        )
    if cabs:
        parts.append(
            f'<img src="../../media/{cabs}" alt="شعار CABS Bird Guard" width="220" style="display:block;flex:0 1 220px;width:42%;max-width:220px;height:auto;object-fit:contain;">'
        )
    block = (
        '<div id="sayd-cabs-partner-logos" style="display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:20px;margin:18px 0 24px;">'
        + "".join(parts)
        + "</div>"
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
            "</figure>\n</div>\n<p>أعلنت منظمة",
            f"</figure>\n{block}\n</div>\n<p>أعلنت منظمة",
            1,
        )
        if block not in html:
            html = html.replace(
                "<p>أعلنت منظمة CABS",
                block + "\n<p>أعلنت منظمة CABS",
                1,
            )
    if FORBIDDEN_SRC_RE.search(html):
        raise RuntimeError("forbidden src after logo wire")
    page.write_text(html, encoding="utf-8")
    print("wired Kaps partner logos", flush=True)


def wire_pelican_fill() -> None:
    """Wire Nayef Krayem’s Matn original on the existing AR/EN pelican piece."""
    dest = MEDIA / "uploads/2026/09/great-white-pelican-nayef-krayem-matn-2026.jpg"
    if not dest.is_file():
        return
    page = DOCS / "posts" / "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك" / "index.html"
    if page.is_file():
        html = page.read_text(encoding="utf-8")
        for old in (
            "uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg",
            "uploads/2026/09/pelecanus-onocrotalus-great-white-pelican.jpg",
        ):
            html = html.replace(old, "uploads/2026/09/great-white-pelican-nayef-krayem-matn-2026.jpg")
        page.write_text(html, encoding="utf-8")
    print("wired Nayef Krayem pelican original", flush=True)


def wire_flyway_map() -> None:
    dest = MEDIA / "uploads/2026/09/africa-eurasia-flyway-map.jpg"
    if not dest.is_file():
        return
    wp = "uploads/2026/09/ChatGPT-Image-Sep-7-2026-01_33_30-AM-853x1024.png"
    if is_standin_copy(wp) or not (MEDIA / wp).is_file():
        # Keep the WP filename the article already uses, but store real map bytes.
        (MEDIA / wp).write_bytes(dest.read_bytes())
    print("wired flyway map into ChatGPT-Image slot", flush=True)


def restore_homepage_cards(mapping: dict[str, str]) -> int:
    """Insert omitted homepage cards when a unique matching file now exists."""
    home = DOCS / "index.html"
    html = home.read_text(encoding="utf-8")
    added = 0

    def card_html(slug: str, title: str, date: str, cat: str, section_cls: str) -> str:
        del cat  # Homepage cards keep the date. Door headings classify.
        rel = mapping[slug]
        return (
            f'\n<article class="card {section_cls}">\n'
            f'  <a class="thumb" href="posts/{slug}/index.html">'
            f'<img src="media/{rel}" alt="{title}" loading="lazy"></a>\n'
            f'  <div class="body">\n'
            f'    <h3><a href="posts/{slug}/index.html">{title}</a></h3>\n'
            f'    <div class="meta">{date}</div>\n'
            f"  </div>\n"
            f"</article>\n"
        )

    # Cards we can restore (article page must exist; unique thumb required).
    restore = [
        (
            "صور",
            "grid-photos",
            [
                (
                    "صور-بعدسة-الآنسة-نور-لبابيدي",
                    "صور بعدسة الآنسة نور لبابيدي",
                    "2 حزيران 2015",
                    "",
                    "card-compact overlay",
                ),
                (
                    "صور-من-رحلات-الصياد-العراقي-أحمد-زهير",
                    "صور من رحلات الصياد العراقي أحمد زهير",
                    "20 نيسان 2015",
                    "",
                    "card-compact overlay",
                ),
                (
                    "صور-للصياد-اللبناني-رجل-الاعمال-ربيع-ع",
                    "صور للصياد اللبناني رجل الأعمال ربيع عقل",
                    "14 آذار 2015",
                    "",
                    "card-compact overlay",
                ),
                (
                    "صور-بعدسة-محمد-حلّال-فرنسا",
                    "صور بعدسة محمد حلّال — فرنسا",
                    "14 آذار 2015",
                    "",
                    "card-compact overlay",
                ),
            ],
        ),
        (
            "رماية",
            "grid-4",
            [
                (
                    "لماذا-ترغب-المرأة-بتعلم-الصيد-والرماي",
                    "لماذا ترغب المرأة بتعلّم الصيد والرماية؟",
                    "20 تموز 2020",
                    "رماية",
                    "overlay",
                ),
                (
                    "سيرة-رامي-اللبناني-رالف-عراج",
                    "سيرة رامي اللبناني رالف عراج",
                    "19 أيار 2020",
                    "رماية",
                    "overlay",
                ),
                (
                    "تعرّف-على-فوائد-الرماية",
                    "تعرّف على فوائد الرماية",
                    "19 أيار 2020",
                    "رماية",
                    "overlay",
                ),
            ],
        ),
        (
            "أخبار",
            "grid-4",
            [
                (
                    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية",
                    "مع بدء هجرة الخريف.. تحرك ميداني لحماية ممرات الطيور فوق لبنان",
                    "7 أيلول 2026",
                    "أخبار",
                    "overlay",
                ),
                (
                    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
                    "مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟",
                    "8 أيلول 2026",
                    "أخبار",
                    "overlay",
                ),
            ],
        ),
    ]
    for section_title, grid_cls, cards in restore:
        for slug, title, date, cat, cls in cards:
            if slug in HOMEPAGE_GAPS and slug not in mapping:
                continue
            if slug not in mapping:
                continue
            if f"posts/{slug}/index.html" in html:
                continue
            article = DOCS / "posts" / slug / "index.html"
            if not article.is_file():
                continue
            if not is_unique_binary(MEDIA, mapping[slug], allow_source=False) and not (
                MEDIA / mapping[slug]
            ).is_file():
                continue
            # Insert after the opening grid div of this section
            pat = re.compile(
                rf'(<h2>{re.escape(section_title)}</h2>.*?<div class="{re.escape(grid_cls)}">)',
                re.S,
            )
            m = pat.search(html)
            if not m:
                continue
            html = html[: m.end()] + card_html(slug, title, date, cat, cls) + html[m.end() :]
            added += 1
            print(f"restore    homepage card {slug}", flush=True)
    if added:
        home.write_text(html, encoding="utf-8")
    return added


def main() -> int:
    records: list[dict] = []
    print("batch2 start", flush=True)

    # 1) Commons species / topic fills
    for item in COMMONS_FILLS:
        rel = item["rel"]
        rec = {
            "rel": rel,
            "status": "skipped",
            "bytes": 0,
            "note": item["note"],
            "bird": item["bird"],
            "species": item["species"],
            "review": item["review"],
        }
        if is_protected(rel):
            rec["status"] = "protected"
            records.append(rec)
            continue
        if (MEDIA / rel).is_file() and (MEDIA / rel).stat().st_size > 32 and not is_standin_copy(rel):
            rec["status"] = "unique-local"
            rec["bytes"] = (MEDIA / rel).stat().st_size
            records.append(rec)
            print(f"unique     {rel}", flush=True)
            continue
        ok, data, src = fetch_commons(item["names"])
        if ok:
            save(rel, data)
            rec["status"] = "commons"
            rec["bytes"] = (MEDIA / rel).stat().st_size
            rec["source"] = src
            print(f"commons    {rel} {rec['bytes']}", flush=True)
        else:
            rec["status"] = "commons-failed"
            print(f"FAIL commons {rel}", flush=True)
        records.append(rec)

    # 2) Official logos
    fetch_official_logos(records)

    # 3) Wayback for stand-in copies + next-batch + remaining 2022+
    queue: list[str] = []
    seen: set[str] = set()
    for rel in NEXT_BATCH_RELS + collect_2022_plus():
        if rel in seen:
            continue
        seen.add(rel)
        queue.append(rel)

    # Prioritize stand-in copies and named next-batch
    pri = [r for r in queue if r in NEXT_BATCH_RELS or is_standin_copy(r)]
    rest = [r for r in queue if r not in pri]
    ordered = pri + rest
    print(f"fetch queue priority={len(pri)} rest={len(rest)}", flush=True)

    workers = 5
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fetch_one, rel): rel for rel in ordered}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            records.append(rec)
            if rec["status"] in ("downloaded", "failed") and (
                rec["rel"] in NEXT_BATCH_RELS or rec["status"] == "downloaded"
            ):
                print(f"[{i}/{len(ordered)}] {rec['status']:12} {rec['rel']}", flush=True)

    # 4) Wire fills that replace known wrong-species stand-ins
    wire_pelican_fill()
    wire_flyway_map()
    wire_kaps_logos()

    # 5) Unique thumbs + display cleanup
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import apply_unique_thumbs as aut  # noqa: E402

    mapping = assigned_file_set(MEDIA)
    # Autumn how-world can use recovered duck if unique
    duck = "uploads/2026/09/duck-aswan-960.jpg"
    if is_unique_binary(MEDIA, duck):
        mapping.setdefault("مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو", duck)
    pelican = "uploads/2026/09/great-white-pelican-nayef-krayem-matn-2026.jpg"
    if is_unique_binary(MEDIA, pelican):
        mapping.setdefault(
            "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك", pelican
        )
    fly = "uploads/2026/09/africa-eurasia-flyway-map.jpg"
    chat = "uploads/2026/09/ChatGPT-Image-Sep-7-2026-01_33_30-AM-853x1024.png"
    if is_unique_binary(MEDIA, chat) or is_unique_binary(MEDIA, fly):
        mapping.setdefault(
            "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية",
            chat if is_unique_binary(MEDIA, chat) else fly,
        )

    total = 0
    for path in sorted(DOCS.rglob("*.html")):
        total += aut.rewrite_page(path, mapping)
    aut.fix_species_article_bodies()
    cleaned = aut.apply_display_cleanup()
    restored = restore_homepage_cards(mapping)

    cname = (DOCS / "CNAME").read_text(encoding="utf-8").strip()
    if cname != "sayd-magazine.com":
        print("ERROR CNAME", cname)
        return 3

    report = {
        "records": records,
        "mapping": mapping,
        "rewrote": total,
        "cleaned": cleaned,
        "restored_home_cards": restored,
    }
    (MEDIA / "batch2-fetch.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (ROOT / "audit" / "batch2-fetch.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    downloaded = sum(1 for r in records if r["status"] in ("downloaded", "commons", "official-logo", "wayback-logo"))
    failed = sum(1 for r in records if str(r["status"]).endswith("failed"))
    print(
        f"done downloaded={downloaded} failed={failed} restored={restored} cname={cname}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
