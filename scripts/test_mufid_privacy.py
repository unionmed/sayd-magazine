"""Mufid must remain analytics-free after shared SEO maintenance."""
from pathlib import Path
import seo_foundation as seo
ROOT=Path(__file__).resolve().parents[1]
for prefix in ('','en/','fr/'):
    rel=Path(prefix+'mufid/index.html');page=ROOT/'docs'/rel;text=page.read_text()
    assert 'data-mufid-language=' in text
    assert 'analytics:start' not in text and 'googletagmanager.com' not in text and 'gtag(' not in text
    assert 'content="noindex,follow"' in text
    assert f'<link rel="canonical" href="https://sayd-magazine.com/{prefix}mufid/">' in text
    assert seo.apply_html(text,page,ROOT/'docs',rel,{})==text
    assert (ROOT/'assets/js/mufid.js').read_bytes()==(ROOT/'docs/assets/js/mufid.js').read_bytes()
print('PASS: three pilot privacy boundaries survive SEO regeneration; canonical, noindex and synchronized assets.')
