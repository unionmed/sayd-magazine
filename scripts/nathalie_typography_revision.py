"""Owner-requested, exact three-page typography correction; no content editing API."""
PATHS = (
    'docs/posts/ناتالي-دينولف-ثقة-العقاب-وذكاء-الجوارح/index.html',
    'docs/en/posts/nathalie-denolf-eagle-trust-raptor-intelligence/index.html',
    'docs/fr/posts/nathalie-denolf-confiance-aigle-intelligence-rapaces/index.html',
)
STYLE = '''<style id="nathalie-interview-typography">
.article-content > h2 { font-size: 1em; font-weight: 700; line-height: 1.65; }
.article-content > blockquote.en-callout { font-size: 1.35em; font-weight: 700; line-height: 1.6; }
.article-content > blockquote.en-callout > p { font-size: inherit; font-weight: inherit; line-height: inherit; margin-bottom: 0; }
</style>
'''


def corrected(before):
    if (before.count(b'<head>\n') != 1 or before.count(b'</head>') != 1 or before.count(b'  <!-- analytics:start -->') != 1
            or before.index(b'  <!-- analytics:start -->') > before.index(b'</head>')
            or b'nathalie-interview-typography' in before):
        raise ValueError('Expected uncorrected article with exactly one head')
    return before.replace(b'<head>\n', b'<head>\n' + STYLE.encode(), 1)


def exact_revision(before, after, read):
    """Accept only all three exact style insertions; every other Git entry unchanged."""
    changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    if changed != set(PATHS):
        return False
    for path in PATHS:
        if before.get(path, ())[:2] != ('100644', 'blob') or after.get(path, ())[:2] != ('100644', 'blob'):
            return False
        try:
            expected = corrected(read(before[path]))
        except ValueError:
            return False
        if read(after[path]) != expected:
            return False
    return True
