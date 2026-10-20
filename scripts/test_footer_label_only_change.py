import subprocess
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from footer_label_only_change import exact_footer_label_change, footer_label_only_repair, OLD, NEW, ROOT

BEFORE = b'''<!doctype html><html lang="en"><head><title>Title</title><meta name="description" content="old"><style>a{color:red}</style></head><body><main><article><p>Body</p><img src="photo.jpg"><a href="source">Credit</a><time>2026-10-20</time></article></main><footer class="site-footer"><div class="footer-main"><div class="container footer-grid"><div class="footer-col"><h3>Doors</h3><ul><li><a href="section">Science</a></li></ul></div></div></div></footer></body></html>'''
AFTER = BEFORE.replace(OLD, NEW)

class FooterLabelOnlyTests(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(exact_footer_label_change(BEFORE, AFTER))

    def test_other_bytes_always_rejected(self):
        for old, new in [(b'Body',b'Changed'),(b'photo.jpg',b'new.jpg'),(b'href="source"',b'href="other"'),(b'Credit',b'Other credit'),(b'color:red',b'color:blue'),(b'2026-10-20',b'2026-10-21'),(b'<title>Title',b'<title>New'),(b'content="old"',b'content="new"'),(b'href="section"',b'href="bad"')]:
            with self.subTest(old=old):self.assertFalse(exact_footer_label_change(BEFORE,AFTER.replace(old,new)))
        self.assertFalse(exact_footer_label_change(BEFORE,AFTER+b'\n'))
        self.assertFalse(exact_footer_label_change(BEFORE,BEFORE))

    def test_ambiguous_or_unlocated_heading_rejected(self):
        variants=[BEFORE.replace(b'</footer>',b'<div class="footer-col"><h3>D&#111;ors</h3></div></footer>'), BEFORE.replace(b'<div class="footer-col">',b'<article class="article-content"><div class="footer-col">').replace(b'</footer>',b'</article></footer>'), BEFORE.replace(b'<footer', b'<article><footer').replace(b'</footer>',b'</footer></article>'), BEFORE.replace(OLD,b'<!--'+OLD+b'--><h3>D&#111;ors</h3>'), BEFORE.replace(b'<p>Body</p>',OLD), BEFORE.replace(OLD,b'<!--'+OLD+b'-->'), BEFORE.replace(b'<main>',b'<main>'+OLD).replace(b'<div class="footer-col">'+OLD,b'<div class="footer-col">'), BEFORE.replace(b'class="site-footer"',b'class="other"'),BEFORE.replace(b'class="footer-col"',b'class="other"'),BEFORE.replace(b'lang="en"',b'lang="fr"'),BEFORE.replace(b'</body>',b'<footer></footer></body>'),BEFORE.replace(b'</footer>',b''),BEFORE.replace(b'<h3>Doors</h3>',b'<h3> Doors </h3>')]
        for value in variants:
            with self.subTest(value=value):self.assertFalse(exact_footer_label_change(value,value.replace(OLD,NEW)))

    def test_git_sources_and_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
            def write(name, data):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            file = 'docs/en/posts/example/index.html'
            source = 'content/en/example.md'
            git('init');git('config','user.name','Test');git('config','user.email','test@example.invalid')
            write(file, BEFORE);write(source,b'Original source')
            git('add','.');git('commit','-m','fixture')
            base = git('rev-parse','HEAD')
            write(file,AFTER)
            with patch('footer_label_only_change.ROOT',root):
                self.assertTrue(footer_label_only_repair(file,base))
                for other in ['docs/fr/posts/example/index.html','docs/en/index.html','docs/en/posts/../index.html','docs/en/posts/missing/index.html']:
                    self.assertFalse(footer_label_only_repair(other,base))
                self.assertFalse(footer_label_only_repair(file,None))
                self.assertFalse(footer_label_only_repair(file,'missing-base'))
                write(source,b'Edited source');self.assertFalse(footer_label_only_repair(file,base))
                (root/source).unlink();self.assertFalse(footer_label_only_repair(file,base))
                write(source,b'Original source')
                newfile='docs/en/posts/new-page/index.html';write(newfile,AFTER)
                self.assertFalse(footer_label_only_repair(newfile,base))

    def test_legacy_missing_en_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL).decode().strip()
            def write(name,data):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            file='docs/en/posts/legacy/index.html'
            mapping='content/en/pairs.json';ar='content/posts/legacy-ar.md'
            mapdata=json.dumps({'pairs':{'legacy-ar':'legacy'}}).encode()
            git('init');git('config','user.name','Test');git('config','user.email','test@example.invalid')
            write(file,BEFORE);write(mapping,mapdata);write(ar,b'Arabic source')
            git('add','.');git('commit','-m','legacy fixture');base=git('rev-parse','HEAD')
            write(file,AFTER)
            with patch('footer_label_only_change.ROOT',root):
                self.assertTrue(footer_label_only_repair(file,base))
                write('content/en/legacy.md',b'New source');self.assertFalse(footer_label_only_repair(file,base))
                (root/'content/en/legacy.md').unlink()
                (root/'content/en/legacy.md').symlink_to(root/'nonexistent')
                self.assertFalse(footer_label_only_repair(file,base))
                (root/'content/en/legacy.md').unlink()
                write(ar,b'Changed');self.assertFalse(footer_label_only_repair(file,base));write(ar,b'Arabic source')
                write(mapping,b'{"pairs":{}}');self.assertFalse(footer_label_only_repair(file,base));write(mapping,mapdata)
                (root/ar).unlink();self.assertFalse(footer_label_only_repair(file,base))

    def test_separate_raw_and_dom_headings_rejected(self):
        value=BEFORE.replace(OLD,b'<h3>D&#111;ors</h3>').replace(b'<footer class="site-footer">',b'<footer class="site-footer"><article><div class="footer-col">'+OLD+b'</div></article>')
        self.assertFalse(exact_footer_label_change(value,value.replace(OLD,NEW)))

if __name__ == '__main__':unittest.main()
