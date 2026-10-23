#!/usr/bin/env python3
"""Generate a stable, trackable link from a published Sayd article canonical.

Does not publish, edit the article, track users or shorten URLs.
"""
import argparse
from html import unescape
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlencode, urlsplit, urlunsplit

CANONICAL = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"')
TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,95}$")
NETWORKS = {"facebook", "instagram", "tiktok", "youtube"}

def make_link(canonical, source, campaign, content):
    if source not in NETWORKS:
        raise ValueError("Unsupported network")
    if not TOKEN.fullmatch(campaign) or not TOKEN.fullmatch(content):
        raise ValueError("Campaign and content must be stable lowercase ASCII tokens")
    parsed = urlsplit(unescape(canonical))
    if parsed.scheme != "https" or parsed.netloc != "sayd-magazine.com" or parsed.query or parsed.fragment:
        raise ValueError("Must use the clean published https://sayd-magazine.com/ canonical")
    path = unquote(parsed.path)
    if not re.match(r"^/(?:en/|fr/)?posts/[^/]+/(?:index\.html)?$", path):
        raise ValueError("Not a single published article path")
    slug = path.split("/")[3 if path.startswith(("/en/", "/fr/")) else 2]
    if slug in {".", ".."} or any(x in path for x in ("\\", "\x00")):
        raise ValueError("Invalid article path")
    if path.endswith("/index.html"):
        path = path[:-len("index.html")]
    path = quote(path, safe="/-._~")
    query = urlencode({
        "utm_source": source,
        "utm_medium": "organic_social",
        "utm_campaign": campaign,
        "utm_content": content,
    })
    return urlunsplit(("https", "sayd-magazine.com", path, query, ""))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True, help="Published docs article HTML")
    parser.add_argument("--source", choices=sorted(NETWORKS), required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--content", required=True)
    args = parser.parse_args()
    raw = args.html.read_text(encoding="utf-8")
    matches = CANONICAL.findall(raw)
    if len(matches) != 1:
        parser.error("Expected exactly one canonical link in the published HTML")
    try:
        print(make_link(matches[0], args.source, args.campaign, args.content))
    except ValueError as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
