"""Closed same-byte migration and adversarial runtime/whole-tree regressions."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from lxml import html
import homepage_image_sources as images
import editorial_revision as revision
import publication_compiler as compiler
import publication_finalize as finalize
import adonis_tv_publication as adonis

ROOT = Path(__file__).resolve().parents[1]
# Stable pre-migration baseline, not the current publishing queue.
ORIGINAL = 'abd3687229ea0322a22e8d63097dacb5ee4f1e5b'


class HomepageImageSourcesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_publication_compiler import source_commit
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-home-image-test-')
        cls.root = Path(cls.temp.name) / 'repo'
        subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(cls.root)], check=True)
        code = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'scripts').glob('*.py')}
        cls.base = source_commit(cls.root, ORIGINAL, code)
        compiler.git(cls.root, 'checkout', '-q', '--detach', cls.base)
        cls.blobs = images.migration_inputs(cls.root, cls.base)
        cls.sources = images.source_images(cls.blobs.__getitem__)
        cls.expected, _, _ = images.migration_changes(cls.root, cls.base, images.source_digest(cls.blobs))
        cls.value = {'schema': revision.SCHEMA, 'id': images.ID, 'expected_base': cls.base,
                     'operation': images.OPERATION, 'approval_reference': 'private:synthetic-test-not-approval',
                     'expected_source_sha256': images.source_digest(cls.blobs),
                     'expected_targets_sha256': compiler.sha256(compiler.canonical({p: compiler.sha256(cls.blobs[p]) for p in sorted(cls.expected)})),
                     'payload': {}}
        cls.marker = (json.dumps(cls.value, ensure_ascii=False, indent=2) + '\n').encode()
        cls.source = source_commit(cls.root, cls.base, {images.MARKER: cls.marker})
        cls.stage = Path(cls.temp.name) / 'stage'
        with patch.object(compiler, 'validate_stage'):
            cls.plan = compiler.compile_publication(cls.root, cls.base, cls.source, cls.stage, Path(cls.temp.name)/'plan.json', False)
        cls.candidate = compiler.git(cls.stage, 'rev-parse', 'HEAD').decode().strip()
        compiler.git(cls.root, 'fetch', '-q', str(cls.stage), cls.candidate)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_nine_src_spans_and_every_other_byte(self):
        self.assertEqual(set(self.expected), set(images.HOMES.values()))
        self.assertEqual({e['path'] for e in self.plan['changes']}, {*self.expected, images.MARKER})
        for lang, path in images.HOMES.items():
            old, new = self.blobs[path], self.expected[path]
            old_tree, new_tree = html.fromstring(old), html.fromstring(new)
            before, after = old_tree.xpath('//img/@src'), new_tree.xpath('//img/@src')
            self.assertEqual(sum(a != b for a, b in zip(before, after)), 3)
            self.assertEqual(len(before), len(after))
            self.assertEqual(sum(s.startswith(images.PREFIX) for s in after), 6)
            restored = new
            for entry in images.IMAGES:
                source = self.sources[entry[2]]
                local = images.local_src(lang, entry)
                self.assertEqual(new.count(('src="'+local+'"').encode()), 1)
                restored = restored.replace(('src="'+local+'"').encode(), ('src="'+source+'"').encode(), 1)
                self.assertEqual(base64.b64decode(source.split(',', 1)[1]), self.blobs[entry[3]])
                self.assertEqual(compiler.sha256(self.blobs[entry[3]]), entry[4])
            self.assertEqual(restored, old)
        old, new = compiler.tree(self.root, self.base), compiler.tree(self.stage, self.candidate)
        self.assertEqual({p for p in old.keys() | new.keys() if old.get(p) != new.get(p)}, {*self.expected, images.MARKER})

    def test_writer_preflight_same_hard_caps_no_oversized_singleton(self):
        changes = finalize.validate_plan(self.stage, self.plan, self.base, self.source, self.base, self.plan['plan_sha256'])
        batches, tree = finalize.prepare_tree_batches(changes, finalize.tree_entries(self.root, self.source),
            compiler.git(self.root, 'rev-parse', self.source+'^{tree}').decode().strip())
        self.assertEqual((finalize.TREE_BATCH_BYTES, finalize.TREE_BATCH_ENTRIES, finalize.TREE_BATCH_COUNT), (1048576, 32, 64))
        self.assertEqual(len(batches), 3)
        self.assertEqual(tree, compiler.git(self.stage, 'rev-parse', 'HEAD^{tree}').decode().strip())
        for payload, _ in batches:
            self.assertLessEqual(len(finalize.api_json(payload)), 1048576)
        finalize.safe_output_path(images.MARKER)
        with self.assertRaises(finalize.Blocked):
            finalize.safe_output_path('content/editorial-revisions/homepage-local-images-other.json')

    def test_marker_absent_exact_legacy_and_active_exact_local(self):
        self.assertFalse(images.active(self.root))
        self.assertTrue(images.active(self.stage))
        for lang, home in images.HOMES.items():
            for entry in images.IMAGES:
                source = self.sources[entry[2]]
                self.assertEqual(images.image_src(self.root, lang, self.root/home, *entry[:3], source), source)
                self.assertEqual(images.image_src(self.stage, lang, self.stage/home, *entry[:3], source), images.local_src(lang, entry))
        source = 'data:image/jpeg;base64,untouched'
        self.assertEqual(images.image_src(self.stage, 'ar', self.stage/'docs/index.html', 'sayd-channel', 'data-video-id', 'other', source), source)

    def test_context_bad_source_unsafe_paths_missing_and_hash_fail_closed(self):
        entry = images.IMAGES[0]; source = self.sources[entry[2]]
        for lang, home, group, attribute, identity, data in (
                ('xx', 'docs/index.html', *entry[:3], source),
                ('ar', 'docs/posts/other/index.html', *entry[:3], source),
                ('ar', 'docs/../docs/index.html', *entry[:3], source),
                ('ar', 'docs/index.html', 'sayd-selections', entry[1], entry[2], source),
                ('ar', 'docs/index.html', entry[0], 'data-external-selection', entry[2], source),
                ('ar', 'docs/index.html', *entry[:3], source+'\n'),
                ('ar', 'docs/index.html', *entry[:3], 'https://example.com/image.jpg'),
                ('ar', 'docs/index.html', *entry[:3], images.PREFIX+'not-base64'),
                ('ar', 'docs/index.html', *entry[:3], self.sources[images.IMAGES[1][2]])):
            with self.subTest(context=(lang, home, group, data[:30])), self.assertRaises(ValueError):
                images.image_src(self.stage, lang, self.stage/home, group, attribute, identity, data)
        for path in ('../outside.jpg', '/tmp/outside.jpg', 'docs/../outside.jpg', 'docs/%2e%2e/x', 'docs\\x', 'https://example.com/x', 'docs/./x', 'docs//x', 'docs/x?y', 'docs/\x00'):
            with self.subTest(path=path), self.assertRaises(ValueError): images.read_regular(self.stage, path)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root/images.MARKER; marker.parent.mkdir(parents=True); marker.write_bytes(self.marker)
            target = root/entry[3]; target.parent.mkdir(parents=True)
            for kind in ('missing', 'wrong-bytes', 'leaf-symlink', 'directory'):
                if kind == 'wrong-bytes': target.write_bytes(b'wrong')
                elif kind == 'leaf-symlink': target.symlink_to(self.stage/entry[3])
                elif kind == 'directory': target.mkdir()
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    images.image_src(root, 'ar', root/'docs/index.html', *entry[:3], source)
                if target.is_symlink() or target.is_file(): target.unlink()
                elif target.is_dir(): target.rmdir()
            target.parent.rmdir(); target.parent.symlink_to((self.stage/entry[3]).parent)
            with self.assertRaises(ValueError): images.image_src(root, 'ar', root/'docs/index.html', *entry[:3], source)

    def test_malformed_duplicate_symlink_and_unknown_marker_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); marker = root/images.MARKER; marker.parent.mkdir(parents=True)
            for raw in (b'\xff', b'null', b'{}', b'{"id":"one","id":"two"}', self.marker.replace(images.OPERATION.encode(), b'arbitrary-operation'), self.marker.replace(b'"payload": {}', b'"payload": {"map": []}')):
                marker.write_bytes(raw)
                with self.subTest(raw=raw[:50]), self.assertRaises(ValueError): images.active(root)
            marker.unlink(); marker.symlink_to(self.stage/images.MARKER)
            with self.assertRaises(ValueError): images.active(root)
            marker.unlink(); marker.parent.rmdir(); marker.parent.symlink_to((self.stage/images.MARKER).parent)
            with self.assertRaises(ValueError): images.active(root)

    def test_exact_card_span_missing_duplicate_wrong_group_and_forged_map(self):
        raw = self.blobs['docs/index.html']; entry = images.IMAGES[0]
        needle = ('data-video-id="'+entry[2]+'"').encode()
        import re
        card = re.search(rb'<article class="card" '+needle+rb'>.*?</article>', raw, re.S)[0]
        noncanonical = card.replace(b'<article class="card" ', b'<article  class="card" ', 1)
        for bad in (raw.replace(needle, b'data-video-id="missing"', 1), raw.replace(card, card+card, 1),
                    raw.replace(b'data-tv-group="sayd-channel"', b'data-tv-group="wrong"', 1),
                    raw.replace(card, b'<!--'+card+b'-->'+noncanonical, 1),
                    raw.replace(card, card.replace(b'<img ', b'<img src="another" ', 1), 1),
                    b'\xff'+raw, raw+b'\x00'):
            with self.subTest(prefix=bad[:25]), self.assertRaises(ValueError): images.replace_home(bad, 'ar', self.sources)
        for source_map in (dict(self.sources, extra='x'), dict(self.sources, **{entry[2]: self.sources[images.IMAGES[1][2]]})):
            with self.assertRaises(ValueError): images.replace_home(raw, 'ar', source_map)
        with self.assertRaises(ValueError): images.replace_home(self.expected['docs/index.html'], 'ar', self.sources)

    def test_closed_revision_source_preconditions_and_repeat(self):
        from test_publication_compiler import source_commit
        for key, value in (('id', 'other'), ('operation', 'other'), ('expected_base', '0'*40),
                           ('expected_source_sha256', '0'*64), ('expected_targets_sha256', '0'*64),
                           ('payload', {'path': 'docs/other.html'})):
            bad = dict(self.value, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError): revision.expected_changes(self.root, self.base, bad, images.MARKER)
        for path in (images.CHANNEL, images.ADONIS, images.IMAGES[0][3], 'docs/index.html', 'scripts/injected.py'):
            source = source_commit(self.root, self.base, {images.MARKER: self.marker, path: b'tampered'})
            with self.subTest(path=path), self.assertRaises(ValueError): revision.source_input(self.root, self.base, source)
        for mode in ('100755', '120000'):
            source = source_commit(self.root, self.base, {images.MARKER: self.marker}, {images.MARKER: mode})
            with self.assertRaises(ValueError): revision.source_input(self.root, self.base, source)
        with self.assertRaises(ValueError): images.migration_inputs(self.stage, self.candidate)
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
            compiler.compile_publication(self.root, self.base, self.source, Path(temp)/'bad', Path(temp)/'plan.json', True)

    def test_historical_adonis_replay_unchanged_with_active_marker(self):
        # The source root has the same history, with/without a runtime marker.
        legacy = '55cff6194bbcd9a62461c83f483cd74783c36559'
        value = json.loads(self.blobs[images.ADONIS]); value['expected_base'] = legacy
        value['expected_channel_sha256'] = compiler.sha256(compiler.git(self.root, 'show', legacy+':'+images.CHANNEL))
        poster = self.blobs[adonis.POSTER]
        self.assertEqual(adonis.expected_changes(self.root, legacy, value, poster), adonis.expected_changes(self.stage, legacy, value, poster))
        adonis.check_published(self.root); adonis.check_published(self.stage)
        for lang in images.LANGS:
            self.assertNotEqual(adonis.homepage_card(self.root, lang), adonis.homepage_card(self.stage, lang))
            category = 'docs/'+('' if lang == 'ar' else lang+'/')+adonis.TV_PATH
            self.assertEqual((self.root/category).read_bytes(), (self.stage/category).read_bytes())

    def test_actual_contract_rejects_arbitrary_local_remote_inline_or_missing_src(self):
        # Execute the real checker, including the existing Adonis full-card check.
        command = ['python', '-c', 'import sys;sys.path.insert(0,"scripts");from check_publication_contract import check;check()']
        baseline = subprocess.run(command, cwd=self.stage, capture_output=True)
        self.assertEqual(baseline.returncode, 0, baseline.stderr.decode()[-3000:])
        for lang, path in images.HOMES.items():
            target = self.stage/path; original = target.read_bytes()
            for entry in images.IMAGES:
                needle = ('src="'+images.local_src(lang, entry)+'"').encode()
                for bad in ('media/missing.jpg', 'https://example.com/image.jpg', self.sources[entry[2]], images.local_src(lang, images.IMAGES[(images.IMAGES.index(entry)+1)%3])):
                    try:
                        target.write_bytes(original.replace(needle, ('src="'+bad+'"').encode(), 1))
                        result = subprocess.run(command, cwd=self.stage, capture_output=True)
                        self.assertNotEqual(result.returncode, 0, (lang, entry[2], bad[:60]))
                    finally: target.write_bytes(original)

    def test_relative_homepage_refresh_is_byte_identical(self):
        # The trusted desk-replay guard invokes refresh with a relative path.
        # Both pre-migration and activated trees must preserve every byte.
        command = ['python', '-c', 'import sys; from pathlib import Path; sys.path.insert(0,"scripts"); import refresh_homepage_doors as home; [home.refresh(Path(path),lang) for lang,path in [("ar","docs/index.html"),("en","docs/en/index.html"),("fr","docs/fr/index.html")]]']
        for root in (self.root, self.stage):
            before = {path: (root/path).read_bytes() for path in images.HOMES.values()}
            subprocess.run(command, cwd=root, check=True)
            self.assertEqual(before, {path: (root/path).read_bytes() for path in images.HOMES.values()})
            self.assertFalse(compiler.git(root, 'status', '--porcelain').strip())

    def test_full_validation_replay_and_refresh_idempotence(self):
        # Unmocked protected stage checks, then a trusted whole-tree replay.
        compiler.validate_stage(self.stage, self.base, True)
        with tempfile.TemporaryDirectory() as temp:
            plan = compiler.verify_candidate(self.root, self.base, self.candidate, Path(temp)/'replay', Path(temp)/'plan.json')
            self.assertEqual(plan, self.plan)
        subprocess.run(['python', 'scripts/test_homepage_doors.py'], cwd=self.stage, check=True)
        self.assertFalse(compiler.git(self.stage, 'status', '--porcelain').strip())


if __name__ == '__main__': unittest.main()
