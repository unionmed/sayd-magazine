"""Offline exact-tree caption revision tests; fixtures are never published."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import caption_revision as revision
import publication_compiler as compiler
import publication_guard as guard
from test_publication_compiler import source_commit

ROOT = Path(__file__).resolve().parents[1]


class CaptionRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-caption-tests-')
        cls.root = Path(cls.temp.name) / 'repo'
        subprocess.run(['git', 'clone', '-q', '--shared', str(ROOT), str(cls.root)], check=True)
        original = compiler.git(cls.root, 'rev-parse', 'HEAD').decode().strip()
        code = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'scripts').glob('*.py')}
        cls.record = json.loads((cls.root / 'content/publications/riyadh-results-20261024.json').read_text())
        cls.article = cls.record['articles'][0]
        # Synthetic uncorrected fixture only: future main may already have the
        # revised caption/year elision. Restore the original three photo spans
        # and their derived search rows in this isolated clone, never in ROOT.
        import html
        effective = revision.effective_records(cls.root, cls.record, cls.article)[0]
        photo = cls.record['photos'][0];current_photo=effective['photos'][0]
        restored = {}
        for lang in ('ar','en','fr'):
            old_credit=effective['articles'][0]['translations'][lang]['photo_credit']
            original_credit=cls.article['translations'][lang]['photo_credit']
            for path in revision.article_paths(cls.article,lang):
                text=(cls.root/path).read_text()
                for old,new in [('<figcaption>'+html.escape(current_photo['caption'][lang])+'</figcaption>',
                                 '<figcaption>'+html.escape(photo['caption'][lang])+'</figcaption>'),
                                ('alt="'+html.escape(current_photo['alt'][lang])+'"',
                                 'alt="'+html.escape(photo['alt'][lang])+'"'),
                                ('<p class="photo-credit">'+html.escape(old_credit),
                                 '<p class="photo-credit">'+html.escape(original_credit))]:
                    assert text.count(old)==1
                    text=text.replace(old,new)
                restored[path]=text.encode();(cls.root/path).write_bytes(restored[path])
        subprocess.run([__import__('sys').executable,str(ROOT/'scripts/build_search_index.py'),
                        '--docs',str(cls.root/'docs')],check=True,capture_output=True)
        for lang in ('ar','en','fr'):
            path='docs/assets/search/index-'+lang+'.json';restored[path]=(cls.root/path).read_bytes()
        cls.base = source_commit(cls.root, original, dict(code,**restored))
        compiler.git(cls.root, 'checkout', '-q', '--force', '--detach', cls.base)
        current_photo = revision.effective_records(cls.root, cls.record, cls.article)[0]['photos'][0]
        cls.value = {'schema': revision.SCHEMA, 'id': 'caption-test', 'expected_base': cls.base,
                     'publication_id': cls.record['id'], 'article_slug': cls.article['slugs']['ar'],
                     'photo_id': cls.record['photos'][0]['id'],
                     'captions': {lang: {'old': current_photo['caption'][lang],
                                         'new': 'Archive photograph & illustration.'} for lang in ('ar','en','fr')}}
        cls.path = revision.PREFIX + 'caption-test.json'

    @classmethod
    def tearDownClass(cls):
        guard._proofs.clear()
        cls.temp.cleanup()

    def source(self, value=None):
        value = copy.deepcopy(value or self.value)
        return source_commit(self.root, self.base, {self.path: (json.dumps(value, ensure_ascii=False)+'\n').encode()})

    def compiled(self, value=None):
        source = self.source(value)
        with tempfile.TemporaryDirectory(prefix='sayd-caption-build-') as temp:
            output=Path(temp)/'site'
            with patch.object(compiler, 'validate_stage'):
                plan=compiler.compile_publication(self.root,self.base,source,output,Path(temp)/'plan.json')
            files={entry['path']:(output/entry['path']).read_bytes() for entry in plan['changes']}
        return source,plan,files

    def files(self):
        if not hasattr(self, '_compiled'):
            self._compiled=self.compiled()
        return dict(self._compiled[2])

    def candidate(self, files, modes=None):
        if not hasattr(self, '_compiled'): self.files()
        source,plan,_=self._compiled
        raw=source_commit(self.root,source,files,modes)
        tree=compiler.git(self.root,'rev-parse',raw+'^{tree}').decode().strip()
        import os
        env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.invalid',
                 GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.invalid')
        return subprocess.check_output(['git','-C',str(self.root),'commit-tree',tree,'-p',source],
                                       input=compiler.provenance_message(plan).encode(),env=env).decode().strip()

    def verify(self, files, modes=None):
        candidate = self.candidate(files,modes)
        with tempfile.TemporaryDirectory(prefix='sayd-caption-replay-') as temp:
            with patch.object(compiler, 'validate_stage'):
                return compiler.verify_candidate(self.root, self.base, candidate, Path(temp)/'site', Path(temp)/'plan.json')

    def test_exact_six_captions_and_new_record(self):
        plan = self.verify(self.files())
        self.assertEqual(plan['schema'], revision.PLAN_SCHEMA)
        self.assertEqual(len(plan['changes']), 10)
        for path, data in self.files().items():
            if path.endswith(('.html','.md')):
                self.assertIn(b'Archive photograph &amp; illustration.', data)
                self.assertNotIn(b'&amp;amp;', data)

    def test_unrelated_mutations_rejected(self):
        extras = {'scripts/publication_compiler.py': b'raise SystemExit(0)\n',
                  'content/homepage.json': b'{}', 'content/ticker.json': b'{}',
                  'content/publications/extra.json': b'{}',
                  'content/publications/riyadh-results-20261024.json': b'{}',
                  self.record['photos'][0]['path']: b'changed image',
                  'docs/unrelated.html': b'changed', 'docs/index.html': None}
        for path, data in extras.items():
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.verify(dict(self.files(), **{path:data}))

    def test_incomplete_stale_and_body_tamper_rejected(self):
        for mutation in ('missing','body','stale'):
            files = self.files(); path = revision.article_paths(self.article, 'en')[0]
            if mutation == 'missing': del files[path]
            if mutation == 'body': files[path] += b'<!-- extra -->'
            if mutation == 'stale':
                value = copy.deepcopy(self.value); value['expected_base'] = 'a'*40
                files[self.path] = json.dumps(value).encode()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify(files)

    def test_mode_and_symlink_rejected(self):
        for path in (self.path, revision.article_paths(self.article, 'ar')[0]):
            for mode in ('100755','120000'):
                with self.subTest(path=path, mode=mode), self.assertRaises(ValueError):
                    self.verify(self.files(), {path:mode})

    def test_closed_plain_text_schema(self):
        for field, bad in [('publication_id','../escape'), ('photo_id','../escape'),
                           ('expected_base', 'HEAD'), ('article_slug','../escape')]:
            value = copy.deepcopy(self.value); value[field]=bad
            with self.subTest(field=field), self.assertRaises((ValueError, TypeError)):
                revision.validate_revision(value,self.path,self.base)
        for bad in ('<img src=x>', 'x\n', 'x\u202e', 'x'*1001, ''):
            value=copy.deepcopy(self.value);value['captions']['ar']['new']=bad
            with self.subTest(caption=bad), self.assertRaises(ValueError): revision.validate_revision(value,self.path,self.base)
        for alteration in ('extra','missing','extra-language'):
            value=copy.deepcopy(self.value)
            if alteration=='extra': value['paths']=['docs/index.html']
            if alteration=='missing': del value['captions']['fr']
            if alteration=='extra-language': value['captions']['de']=value['captions']['en']
            with self.subTest(alteration=alteration), self.assertRaises(ValueError): revision.validate_revision(value,self.path,self.base)

    def test_guard_distinguishes_revision_from_addition(self):
        candidate=self.candidate(self.files())
        compiler.git(self.root,'checkout','-q','--detach',candidate)
        try:
            with patch.dict('os.environ', {'SAYD_PUBLICATION_HEAD':candidate}, clear=False):
                proof=guard.verified_article_evidence(self.base,self.root)
                self.assertEqual(proof.kind,'verified-caption-revision')
                self.assertEqual(proof.additions,())
                self.assertEqual(len(proof.revisions),1)
                self.assertEqual(proof.revisions[0]['photos'][0]['caption'],
                                 {lang:'Archive photograph & illustration.' for lang in ('ar','en','fr')})
                self.assertEqual(guard.tree(proof.site,'HEAD'),guard.tree(self.root,candidate))
        finally: compiler.git(self.root,'checkout','-q','--detach',self.base)

    def test_search_other_rows_and_fields_cannot_change(self):
        for mutation in ('other-row','title','delete-row'):
            files=self.files();path='docs/assets/search/index-en.json'
            value=json.loads(files[path])
            if mutation=='other-row': value['articles'][0]['body']+=' UNAPPROVED'
            if mutation=='title': value['articles'][-1]['title']+=' UNAPPROVED'
            if mutation=='delete-row': value['articles'].pop()
            files[path]=json.dumps(value).encode()
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): self.verify(files)

    def test_source_cannot_mix_code_or_publication(self):
        for path in ('scripts/caption_revision.py','content/publications/extra.json','docs/index.html'):
            source=source_commit(self.root,self.base,{self.path:json.dumps(self.value).encode(),path:b'bad'})
            with self.subTest(path=path),self.assertRaises(ValueError): revision.source_input(self.root,self.base,source)

    def test_baseline_cannot_mask_unmanifested_caption(self):
        files=self.files();path=revision.article_paths(self.article,'ar')[0]
        candidate=source_commit(self.root,self.base,{path:files[path]})
        compiler.git(self.root,'checkout','-q','--detach',candidate)
        try:
            with self.assertRaisesRegex(AssertionError,'mask historical'):
                guard.verified_publication(self.base,self.root,include_baseline=True)
        finally: compiler.git(self.root,'checkout','-q','--detach',self.base)

    def test_future_publication_preserves_revised_history(self):
        from test_publication_compiler import record, files_for
        first=self.candidate(self.files())
        compiler.git(self.root,'checkout','-q','--detach',first)
        try:
            new_record=record(first,release='after-caption-test')
            source=source_commit(self.root,first,files_for(new_record))
            with tempfile.TemporaryDirectory(prefix='sayd-after-caption-') as temp:
                output=Path(temp)/'site'
                with patch.object(compiler,'validate_stage'):
                    compiler.compile_publication(self.root,first,source,output,Path(temp)/'plan.json')
                for path,data in self.files().items():
                    if not path.startswith('docs/assets/search/'):
                        self.assertEqual((output/path).read_bytes(),data)
                for language in ('ar','en','fr'):
                    path='docs/assets/search/index-'+language+'.json'
                    old=json.loads(self.files()[path]);new=json.loads((output/path).read_bytes())
                    current={r['url']:r for r in new['articles']}
                    self.assertTrue(all(current[row['url']]==row for row in old['articles']))
        finally: compiler.git(self.root,'checkout','-q','--detach',self.base)

    def test_date_elision_exact_bytes_and_effective_evidence(self):
        value=copy.deepcopy(self.value);value['elide_photo_year']=2011
        for lang, text in {'ar':'صورة أرشيفية.','en':'Archive photograph.','fr':'Photo d’archives.'}.items():
            value['captions'][lang]['new']=text
        self._compiled=self.compiled(value)
        source,plan,files=self._compiled
        self.assertEqual(len(files),10)
        self.verify(files)
        for lang in ('ar','en','fr'):
            photo=self.record['photos'][0]
            old_alt,new_alt,old_credit,new_credit=revision.date_elision(self.article,photo,lang,2011)
            for path in revision.article_paths(self.article,lang):
                before=compiler.git(self.root,'show',self.base+':'+path).decode()
                import html
                wanted=before.replace('<figcaption>'+html.escape(value['captions'][lang]['old'])+'</figcaption>',
                                      '<figcaption>'+html.escape(value['captions'][lang]['new'])+'</figcaption>')
                wanted=wanted.replace('alt="'+html.escape(old_alt)+'"','alt="'+html.escape(new_alt)+'"')
                wanted=wanted.replace('<p class="photo-credit">'+html.escape(old_credit),
                                      '<p class="photo-credit">'+html.escape(new_credit))
                self.assertEqual(files[path],wanted.encode())
            path='docs/assets/search/index-'+lang+'.json'
            before=json.loads(compiler.git(self.root,'show',self.base+':'+path))
            after=json.loads(files[path]);old_rows={r['url']:r for r in before['articles']}
            differing=[r for r in after['articles'] if r!=old_rows[r['url']]]
            self.assertEqual(len(differing),1)
            self.assertIn('Sammy Six',differing[0]['body']);self.assertIn('CC BY 2.0',differing[0]['body'])
            self.assertNotIn(', 2011,',differing[0]['body'])
        candidate=self.candidate(files)
        with tempfile.TemporaryDirectory(prefix='sayd-effective-date-') as temp:
            stage=Path(temp)/'site'
            subprocess.run(['git','clone','-q','--shared','--no-checkout',str(self.root),str(stage)],check=True)
            compiler.git(stage,'checkout','-q','--detach',candidate)
            evidence=revision.effective_records(stage,self.record,self.article)[0]
            for lang in ('ar','en','fr'):
                self.assertNotIn('2011',evidence['photos'][0]['alt'][lang])
                self.assertNotIn('2011',evidence['articles'][0]['translations'][lang]['photo_credit'])
            original='content/publications/riyadh-results-20261024.json'
            self.assertEqual((stage/original).read_bytes(),compiler.git(self.root,'show',self.base+':'+original))
            self.assertIn('2011',evidence['photos'][0]['source_reference'])
            # Prove the fixture bootstrap still works when real main already
            # contains the short captions and date-free visible alt/credit.
            future_fixture=type('AlreadyCorrectedFixture',(CaptionRevisionTests,),{})
            with patch(__name__+'.ROOT',stage):
                future_fixture.setUpClass()
                try:
                    restored=revision.effective_records(future_fixture.root,future_fixture.record,future_fixture.article)[0]
                    self.assertEqual(restored['photos'][0]['alt'],self.record['photos'][0]['alt'])
                    self.assertEqual(restored['photos'][0]['caption'],self.record['photos'][0]['caption'])
                    for lang in ('ar','en','fr'):
                        self.assertEqual(restored['articles'][0]['translations'][lang]['photo_credit'],self.article['translations'][lang]['photo_credit'])
                finally:future_fixture.tearDownClass()

    def test_date_elision_cannot_change_protected_credit_or_body(self):
        value=copy.deepcopy(self.value);value['elide_photo_year']=2011
        self._compiled=self.compiled(value)
        path=revision.article_paths(self.article,'en')[0]
        for old,new in [('Sammy Six','Someone Else'),('Horse Club Riyadh','Different title'),
                        ('CC BY 2.0','CC0'),('https://creativecommons.org/licenses/by/2.0/','https://example.com/'),
                        ('https://www.flickr.com/photos/sammysix/6335938717/','https://example.com/'),
                        ('without cropping','with cropping'),('15 lengths','25 lengths')]:
            files=self.files();self.assertIn(old.encode(),files[path]);files[path]=files[path].replace(old.encode(),new.encode())
            with self.subTest(old=old),self.assertRaises(ValueError):self.verify(files)

    def test_date_elision_schema_and_provenance_ambiguity(self):
        for bad in (True,'2011',2011.0,999,10000,{'year':2011},None):
            value=copy.deepcopy(self.value);value['elide_photo_year']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):revision.validate_revision(value,self.path,self.base)
        for field in ('alt','photo_credit','credit_replacements'):
            value=copy.deepcopy(self.value);value['elide_photo_year']=2011;value[field]='arbitrary'
            with self.subTest(field=field),self.assertRaises(ValueError):revision.validate_revision(value,self.path,self.base)
        original_article=self.article;original_photo=self.record['photos'][0]
        path=revision.article_paths(self.article,'en')[0]
        original=compiler.git(self.root,'show',self.base+':'+path)+b'<p>Unrelated historical year 2011 stays.</p>'
        self.assertIn(b'<p>Unrelated historical year 2011 stays.</p>',
                      revision.elide_date(original,self.article,original_photo,'en',2011))
        for case in ('copyright','capture-copyright','arabic-rights','french-rights','shared-credit','title-year','creator-year','review-date-only','leading-review-date','invalid-date','nonterminal-alt','missing-year'):
            article=copy.deepcopy(original_article);photo=copy.deepcopy(original_photo)
            if case=='copyright':article['translations']['en']['photo_credit']+=' Copyright retained.'
            if case=='capture-copyright':photo['source_reference']='Copyright © Horse Club Riyadh, Sammy Six, 11 November 2011; source'
            if case=='arabic-rights':article['translations']['en']['photo_credit']+=' حقوق النشر'
            if case=='french-rights':article['translations']['en']['photo_credit']+=' Tous droits réservés.'
            if case=='shared-credit':article['photos'].append('other')
            if case=='title-year':article['translations']['en']['photo_credit']=article['translations']['en']['photo_credit'].replace('Horse Club Riyadh','Horse Club, 2011, Riyadh')
            if case=='creator-year':article['translations']['en']['photo_credit']=article['translations']['en']['photo_credit'].replace('Sammy Six','Sammy 2011 Six')
            if case=='review-date-only':photo['source_reference']='Photograph; licence confirmed 11 November 2011'
            if case=='leading-review-date':photo['source_reference']='Licence reviewed 11 November 2011; unrelated'
            if case=='invalid-date':photo['source_reference']='Photograph, 31 February 2011; source'
            if case=='nonterminal-alt':photo['alt']['en']+=' More text.'
            if case=='missing-year':photo['alt']['en']=photo['alt']['en'].replace(' in 2011','')
            with self.subTest(case=case),self.assertRaises(ValueError):revision.date_elision(article,photo,'en',2011)

    def test_historical_revision_cannot_change_or_delete(self):
        first=self.candidate(self.files())
        compiler.git(self.root,'checkout','-q','--detach',first)
        try:
            for data in (None,b'{}'):
                candidate=source_commit(self.root,first,{self.path:data})
                with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
                    compiler.verify_candidate(self.root,first,candidate,Path(temp)/'site',Path(temp)/'plan.json')
            # A stale caption-only edit without a new revision stays forbidden.
            path=revision.article_paths(self.article,'ar')[0]
            old=compiler.git(self.root,'show',self.base+':'+path)
            candidate=source_commit(self.root,first,{path:old})
            with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
                compiler.verify_candidate(self.root,first,candidate,Path(temp)/'site',Path(temp)/'plan.json')
        finally: compiler.git(self.root,'checkout','-q','--detach',self.base)


if __name__ == '__main__': unittest.main()
