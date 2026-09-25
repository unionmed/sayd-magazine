"""Single cache-bust token for the shared site stylesheet.

Chrome templates, publish scripts, and committed docs HTML all read this
value so AR and EN pages stay on one query string.
"""

CSS_CACHE = "20260925-ar-nav-b"
