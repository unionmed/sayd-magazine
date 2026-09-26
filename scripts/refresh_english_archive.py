"""Keep the English archive complete and chronological across all years."""
import html
import re
from apply_site_ia import DOCS, _en_story


def main():
    path = DOCS / "en/stories/index.html"
    text = path.read_text(encoding="utf-8")
    stories = [_en_story(p.parent.name) for p in (DOCS / "en/posts").glob("*/index.html") if 'class="article-content"' in p.read_text(encoding="utf-8")]
    stories = sorted((s for s in stories if s), key=lambda s: s["stamp"], reverse=True)
    cards = []
    for story in stories:
        title = html.escape(story["title"])
        href = "../posts/" + story["slug"] + "/index.html"
        thumb = story["thumb"].replace("../../../media/", "../../media/").replace("../../posts/", "../posts/")
        cards.append(f'<article class="card overlay">{thumb}<div class="body"><div class="meta">{story["date"]}</div><h3><a href="{href}">{title}</a></h3></div></article>')
    text = text.replace("September 2026 English stories", "Archive").replace("September 2026 stories — Sayd Magazine", "Archive — Sayd Magazine").replace("English twins of Sayd Magazine’s September 2026 edition.", "Browse articles available in English, from newest to oldest.")
    start = text.index('<div class="grid-4">', text.index('<main')) + len('<div class="grid-4">')
    end = text.rfind('</article>', start, text.index('</main>')) + len('</article>')
    text = text[:start] + "\n" + "\n".join(cards) + text[end:]
    path.write_text(text, encoding="utf-8")
    print(f"English archive: {len(stories)} articles, newest to oldest")


if __name__ == "__main__":
    main()
