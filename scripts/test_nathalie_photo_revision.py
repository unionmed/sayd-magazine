"""Closed four-photo addition: preserve every existing editorial and chrome byte."""
import copy
import html
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from lxml import html as dom
import publication_compiler as compiler
import nathalie_photo_revision as revision
from caption_revision import article_paths

ROOT = Path(__file__).resolve().parents[1]
BASE = 'b7a596ec5d9e7ee229bbda5b57e1af32c97be68a'

class NathaliePhotoRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = compiler.tree(ROOT, BASE)
        cls.changes, cls.effective, cls.article = revision.expected_changes(ROOT, BASE, {})
        cls.original = json.loads(compiler.read_blob(ROOT, cls.before['content/publications/' + revision.PUBLICATION + '.json']))

    def test_editorial_dispatch_and_exact_revision_id(self):
        import editorial_revision as editorial
        value = {'schema':editorial.SCHEMA,'id':revision.REVISION_ID,'expected_base':BASE,
                 'operation':'add-nathalie-interview-photos','approval_reference':'private:synthetic-test',
                 'expected_source_sha256':revision.SOURCE_SHA,'payload':{},
                 'expected_targets_sha256':compiler.sha256(compiler.canonical({p:compiler.sha256(compiler.read_blob(ROOT,self.before[p])) for p in sorted(self.changes)}))}
        path=editorial.PREFIX+revision.REVISION_ID+'.json'
        changes,effective,article=editorial.expected_changes(ROOT,BASE,value,path)
        self.assertEqual(changes,self.changes)
        self.assertEqual(effective,self.effective)
        self.assertEqual(article,self.article)
        value['id']='other-interview'
        with self.assertRaises(ValueError): editorial.validate_revision(value,editorial.PREFIX+value['id']+'.json',BASE)

    def test_source_input_fixed_assets_inventory_and_extra_files(self):
        import editorial_revision as editorial
        from test_publication_compiler import source_commit
        # Synthetic bytes are confined to unreferenced test objects. Production
        # constants are never changed; this exercises source-input validation.
        fixture=b'synthetic photo fixture, never publish'
        photos=copy.deepcopy(revision.PHOTOS)
        for photo in photos: photo['sha256']=compiler.sha256(fixture)
        value={'schema':editorial.SCHEMA,'id':revision.REVISION_ID,'expected_base':BASE,
               'operation':'add-nathalie-interview-photos','approval_reference':'private:synthetic-test',
               'expected_source_sha256':revision.SOURCE_SHA,'payload':{},
               'expected_targets_sha256':compiler.sha256(compiler.canonical({p:compiler.sha256(compiler.read_blob(ROOT,self.before[p])) for p in sorted(self.changes)}))}
        path=editorial.PREFIX+revision.REVISION_ID+'.json'
        files={path:json.dumps(value).encode()}
        inventory='path\tgit_blob_sha\tsize_bytes\n'
        for photo in sorted(photos,key=lambda p:p['path']):
            files[photo['path']]=fixture
            inventory+=photo['path']+'\t'+compiler.blob_sha(fixture)+'\t'+str(len(fixture))+'\n'
        shard='audit/image-catalog/manifest/release-'+revision.REVISION_ID+'.tsv'
        files[shard]=inventory.encode()
        with patch.object(revision,'PHOTOS',photos):
            source=source_commit(ROOT,BASE,files)
            result=editorial.source_input(ROOT,BASE,source)
            self.assertEqual(len(result[2]),15)
            for edit in ('extra','wrong-image','wrong-shard','wrong-mode'):
                bad=dict(files);modes={}
                if edit=='extra':bad['docs/media/unauthorized.jpg']=fixture
                if edit=='wrong-image':bad[photos[0]['path']]=b'changed pixels'
                if edit=='wrong-shard':bad[shard]=b'wrong inventory'
                if edit=='wrong-mode':modes[photos[0]['path']]='120000'
                candidate=source_commit(ROOT,BASE,bad,modes)
                with self.subTest(edit=edit),self.assertRaises(ValueError):
                    editorial.source_input(ROOT,BASE,candidate)

    def test_exact_nine_existing_targets_and_preserved_record(self):
        self.assertEqual(len(self.changes), 9)
        expected = {p for lang in revision.LANGS for p in article_paths(self.article, lang)}
        expected.update('docs/assets/search/index-' + lang + '.json' for lang in revision.LANGS)
        self.assertEqual(set(self.changes), expected)
        e = copy.deepcopy(self.effective)
        e['photos'] = e['photos'][:1]
        e['articles'][0]['photos'] = e['articles'][0]['photos'][:1]
        for lang in revision.LANGS:
            e['articles'][0]['translations'][lang]['photo_credit'] = self.original['articles'][0]['translations'][lang]['photo_credit']
        self.assertEqual(e, self.original)

    def test_only_four_figures_and_exact_credit_are_added(self):
        for lang in revision.LANGS:
            for path in article_paths(self.article, lang):
                old = compiler.read_blob(ROOT, self.before[path]).decode()
                new = self.changes[path].decode()
                figures = re.findall(r'<figure>.*?</figure>', new, re.S)
                self.assertEqual(len(figures), 5)
                for fig in figures[1:]:
                    new = new.replace(fig, '', 1)
                new = new.replace('<p class="photo-credit">' + html.escape(revision.CREDITS[lang]) + '</p>',
                                  '<p class="photo-credit">' + html.escape(self.original['articles'][0]['translations'][lang]['photo_credit']) + '</p>', 1)
                self.assertEqual(new, old, path)
                if path.endswith('.html'):
                    self.assertIn('nathalie-interview-typography', new)

    def test_positions_order_dimensions_alt_and_five_equal_mirrors(self):
        for lang in revision.LANGS:
            page = article_paths(self.article, lang)[0]
            node = dom.fromstring(self.changes[page]).xpath('//article[@class="article-content"]')[0]
            question = 0; seen = []
            for child in node:
                if child.tag == 'h2': question += 1
                if child.tag == 'figure':
                    seen.append(question)
            self.assertEqual(seen, [0, 3, 5, 6, 7])
            images = node.xpath('./figure/img')
            for img, photo in zip(images[1:], revision.PHOTOS):
                self.assertEqual(img.get('alt'), photo['alt'][lang])
                self.assertEqual((int(img.get('width')), int(img.get('height'))), revision.DIMENSIONS[photo['id']])
                self.assertTrue(img.get('src').endswith('/' + Path(photo['path']).name))
                self.assertIn('height:auto', img.get('style'))

    def test_no_caller_markup_or_photo_override(self):
        for payload in ({'photos': []}, {'body': '<script/>'}, {'caption': 'x'}, {'path': 'docs/index.html'}):
            with self.assertRaises(ValueError): revision.expected_changes(ROOT, BASE, payload)

    def test_repeated_or_altered_original_rejected(self):
        lang='en'; page=article_paths(self.article, lang)[0]
        original=self.original['articles'][0]
        with self.assertRaises(ValueError): revision.splice(self.changes[page], page, lang, original)
        raw=compiler.read_blob(ROOT,self.before[page])
        for changed in (raw.replace(b'<h2>',b'<h3>',1),raw.replace(b'Photograph supplied by Nathalie Denolf',b'Other credit',1)):
            with self.assertRaises(ValueError): revision.splice(changed,page,lang,original)

    def test_search_changes_only_body_of_one_existing_row(self):
        for lang in revision.LANGS:
            path='docs/assets/search/index-'+lang+'.json'
            old=json.loads(compiler.read_blob(ROOT,self.before[path]));new=json.loads(self.changes[path])
            diffs=[(a,b) for a,b in zip(old['articles'],new['articles']) if a!=b]
            self.assertEqual(len(diffs),1)
            a,b=diffs[0]; b['body']=a['body']
            self.assertEqual(a,b)
            self.assertEqual(old,new)

    def test_native_search_rebuild_matches_all_three_exact_indexes(self):
        with tempfile.TemporaryDirectory(prefix='sayd-nathalie-photos-') as temporary:
            stage=Path(temporary)/'repo'
            subprocess.run(['git','clone','-q','--shared','--no-checkout',str(ROOT),str(stage)],check=True)
            compiler.git(stage,'checkout','-q','--detach',BASE)
            for path,data in self.changes.items(): (stage/path).write_bytes(data)
            subprocess.run(['python',str(ROOT/'scripts/build_search_index.py'),'--docs',str(stage/'docs')],check=True,capture_output=True)
            for lang in revision.LANGS:
                path='docs/assets/search/index-'+lang+'.json'
                self.assertEqual((stage/path).read_bytes(),self.changes[path])

if __name__=='__main__': unittest.main()
