"""Synthetic maintenance proposals only; no real publication is modified."""
import base64
import copy
import html
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote

from lxml import html as dom
import article_maintenance as m
from build_search_index import MONTHS, article_body, serialize
from test_publication_compiler import record


class MemorySnapshot:
    base = 'b' * 40

    def __init__(self, files):
        self.files = files
        self.items = {p: ('100644', 'blob', 'a'*40) for p in files}

    def read(self, path):
        m.require(path in self.files and self.items[path][:2] == ('100644','blob'), 'Missing/unsafe fixture '+path)
        return self.files[path]


def fixture():
    source = record(release='maintenance-test')
    article = source['articles'][0]
    article['published'] = '2020-10-20'
    article['archives'] = ['science']
    files = {'content/publications/maintenance-test.json': m.canonical(source),
             'content/homepage.json': m.canonical({'primary_door':{article['slugs']['ar']:'science'},'unrelated':'preserved'}),
             'docs/media/publications/maintenance-test/cover.png': b'unchanged-original-media',
             'audit/image-catalog/manifest/release-maintenance-test.tsv': b'immutable rights and hashes',
             'docs/s/links.json': b'{"unchanged":"stable IDs"}'}
    paragraphs = {}
    sitemap = []
    for language in m.LANGS:
        page, markdown = m.paths(article, language)
        prefix = '' if language == 'ar' else language+'/'
        url = m.ORIGIN + quote(m.route(page),safe='/')
        paragraphs[language] = 'Original complete editorial paragraph '+language+'.'
        body = '<figure><img src="../../../media/publications/maintenance-test/cover.png" alt="Keep image"><figcaption>Keep caption</figcaption></figure><p class="excerpt">Keep subtitle</p><h2>Keep heading</h2><p>'+paragraphs[language]+'</p><p class="article-sources">Keep sources</p><p class="photo-credit">Keep rights credit</p>'
        label = m.DOORS['science'][m.LANGS.index(language)+1]
        category = '../../category/'+quote(m.DOORS['science'][0])+'/index.html'
        schema = json.dumps({'@type':'NewsArticle','datePublished':'2020-10-20','dateModified':'2020-10-21','articleSection':label},ensure_ascii=False)
        alternate = ''.join('<link rel="alternate" hreflang="'+l+'" href="'+m.ORIGIN+quote(m.route(m.paths(article,l)[0]),safe='/')+'">' for l in m.LANGS)
        data = '<!doctype html><html lang="'+language+'"><head><title>Original headline</title><link rel="canonical" href="'+url+'">'+alternate+'<meta property="og:title" content="Original headline"><meta name="description" content="Private old description"><meta property="og:image" content="old-photo"><script type="application/ld+json">'+schema+'</script></head><body><nav>Keep chrome</nav><div class="ticker">Keep ticker</div><main><div class="breadcrumb"><a href="'+category+'">'+label+'</a></div><header class="article-header"><h1>Original headline</h1><a class="badge" href="'+category+'">'+label+'</a><time>2020-10-20</time></header><article class="article-content">'+body+'</article></main><footer>Keep footer</footer></body></html>'
        files[page] = data.encode()
        files[markdown] = ('---\ncategories: '+json.dumps([m.DOORS['science'][0]],ensure_ascii=False)+'\ndate: "2020-10-20"\n---\n<article class="article-content">'+body+'</article>').encode()
        # Real Markdown wraps body directly without the article element.
        files[markdown] = files[markdown].replace(b'<article class="article-content">',b'').replace(b'</article>',b'')
        files['docs/'+prefix+'index.html'] = ('<html><main><a href="other/">Other</a></main><div class="ticker">Other ticker</div></html>').encode()
        card = '<article class="post-row"><a href="../../posts/'+article['slugs'][language]+'/index.html"><img src="../../../media/publications/maintenance-test/cover.png"></a><h2><a href="../../posts/'+article['slugs'][language]+'/index.html">Original headline</a></h2><div class="meta">20 '+MONTHS[language][9]+' 2020</div></article>'
        newer = '<article class="post-row"><a href="../../posts/unrelated-new/index.html">Newer</a><div class="meta">25 '+MONTHS[language][9]+' 2020</div></article>'
        older = '<article class="post-row"><a href="../../posts/unrelated-old/index.html">Older</a><div class="meta">10 '+MONTHS[language][9]+' 2020</div></article>'
        files['docs/'+prefix+'category/'+m.DOORS['science'][0]+'/index.html'] = ('<main>'+newer+card+older+'</main>').encode()
        files['docs/'+prefix+'category/'+m.DOORS['wildlife'][0]+'/index.html'] = ('<main>'+newer+older+'</main>').encode()
        listing = 'docs/'+prefix+('articles' if language=='ar' else 'stories')+'/index.html'
        archive_card = card.replace('../../posts/','../posts/').replace('../../../media/','../../media/')
        files[listing] = ('<main>'+archive_card+'</main>').encode()
        extracted = article_body(dom.fromstring('<article>'+body+'</article>'))[0]
        row = {'url':quote(m.route(page),safe='/@-._~'),'title':'Original headline','body':extracted,'date':'2020-10-20','category':label,'categories':[label],'excerpt':'Keep excerpt','image':'Keep image'}
        unrelated = dict(row,url='/posts/unrelated/',body='Other story never changed')
        files['docs/assets/search/index-'+language+'.json'] = serialize({'version':2,'lang':language,'categories':['Unchanged vocabulary'],'articles':[row,unrelated]})
        alias = 'docs/s/fixture-'+language+'/index.html'
        files[alias] = ('<html lang="'+language+'"><head><title>Old alias title</title><link rel="canonical" href="'+url+'"><meta property="og:description" content="Old secret excerpt"><meta http-equiv="refresh" content="0;url='+url+'"></head><body>Old alias headline</body></html>').encode()
        sitemap.append('<url><loc>'+url+'</loc></url>')
    files['docs/sitemap.xml'] = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(sitemap)+'<url><loc>'+m.ORIGIN+'/posts/unrelated/</loc></url></urlset>').encode()
    return MemorySnapshot(files), source, paragraphs


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.snapshot, self.record, self.paragraphs = fixture()
        self.article = self.record['articles'][0]
        self.value = {'schema':m.SCHEMA,'id':'test-edit','expected_base':self.snapshot.base,'publication_id':'maintenance-test',
                      'article_slug':self.article['slugs']['ar'],'operation':'edit','decision_reference':'private:test-not-owner-approval','conflicts':[],
                      'replacements':{l:[{'old':self.paragraphs[l],'new':'Revised plain paragraph & exact text '+l+'.'}] for l in m.LANGS}}

    def plan(self):
        return m.bundle(self.snapshot,self.value)

    def withdraw(self):
        self.value.pop('replacements',None)
        self.value.update(operation='withdraw',notice={l:'This item has been withdrawn. '+l for l in m.LANGS})
        return self.plan()

    def reclassify(self):
        self.value.pop('replacements',None)
        self.value.update(operation='reclassify',old_door='science',new_door='wildlife')
        return self.plan()

    def test_edit_six_mirrors_and_three_selected_search_rows(self):
        plan = self.plan()
        changes = m.replay(self.snapshot,plan)
        self.assertEqual(len(changes),9)
        for language in m.LANGS:
            for path in m.paths(self.article,language):
                expected = self.snapshot.read(path).replace(self.paragraphs[language].encode(),html.escape(self.value['replacements'][language][0]['new']).encode())
                self.assertEqual(changes[path],expected)
            path='docs/assets/search/index-'+language+'.json'
            before=json.loads(self.snapshot.read(path));after=json.loads(changes[path])
            self.assertEqual(before['articles'][1],after['articles'][1])
            old=before['articles'][0];new=after['articles'][0]
            self.assertEqual({k:v for k,v in old.items() if k!='body'},{k:v for k,v in new.items() if k!='body'})
            self.assertIn(self.value['replacements'][language][0]['new'],new['body'])

    def test_deterministic_plan_and_no_input_mutations(self):
        files=copy.deepcopy(self.snapshot.files);value=copy.deepcopy(self.value)
        self.assertEqual(self.plan(),self.plan())
        self.assertEqual(self.snapshot.files,files);self.assertEqual(self.value,value)

    def test_reverse_proposal_is_exact_and_blocks_concurrency(self):
        plan=self.plan();current=MemorySnapshot(dict(self.snapshot.files,**m.replay(self.snapshot,plan)))
        restored=m.rollback(current,plan)
        for path,data in restored.items():self.assertEqual(data,self.snapshot.read(path))
        current.files[next(iter(restored))]+=b'concurrent edit'
        with self.assertRaisesRegex(ValueError,'Concurrent'):m.rollback(current,plan)

    def test_recomputed_plan_rejects_tampered_output_or_scope(self):
        plan=self.plan();plan['changes'][0]['after_base64']=base64.b64encode(b'tampered').decode()
        with self.assertRaises(ValueError):m.replay(self.snapshot,plan)
        with self.assertRaises(ValueError):m.rollback(self.snapshot,plan)

    def test_withdrawal_notices_search_sitemap_and_cards(self):
        plan=self.withdraw();changes=m.replay(self.snapshot,plan)
        for language in m.LANGS:
            page,markdown=m.paths(self.article,language)
            node=dom.fromstring(changes[page])
            self.assertFalse(node.xpath('//article[@class="article-content"]'))
            self.assertEqual(node.xpath('//meta[@name="robots"]/@content'),['noindex,follow'])
            self.assertFalse(node.xpath('//script[@type="application/ld+json"] | //meta[@property="og:image" or @property="og:description"]'))
            self.assertEqual(len(node.xpath('//meta[@property="og:title"]')),1)
            self.assertNotIn('Original headline',node.xpath('//meta[@property="og:title"]/@content')[0])
            self.assertIn(b'Keep chrome',changes[page]);self.assertIn(b'Keep footer',changes[page]);self.assertIn(b'Keep ticker',changes[page])
            self.assertNotIn(markdown,changes)
            self.assertNotIn(self.paragraphs[language].encode(),changes[page])
            index=json.loads(changes['docs/assets/search/index-'+language+'.json'])
            self.assertEqual([r['url'] for r in index['articles']],['/posts/unrelated/'])
            alias=changes['docs/s/fixture-'+language+'/index.html']
            self.assertNotIn(b'Old secret excerpt',alias);self.assertIn(b'refresh',alias)
        self.assertNotIn(b'maintenance-test',changes['docs/sitemap.xml'])
        for path in changes:
            if '/category/' in path or '/stories/' in path or '/articles/' in path:
                self.assertNotIn(b'Original headline',changes[path])
        self.assertFalse(any(p.startswith(('content/','audit/','docs/media/')) for p in changes))

    def test_reclassification_preserves_dates_body_media_and_order(self):
        plan=self.reclassify();changes=m.replay(self.snapshot,plan)
        for language in m.LANGS:
            page,markdown=m.paths(self.article,language)
            before=self.snapshot.read(page).decode();after=changes[page].decode()
            self.assertEqual(m.body_span(before)[2],m.body_span(after)[2])
            self.assertIn('2020-10-20',after);self.assertIn('2020-10-21',after)
            self.assertIn(self.paragraphs[language],after)
            prefix='' if language=='ar' else language+'/'
            new='docs/'+prefix+'category/'+m.DOORS['wildlife'][0]+'/index.html'
            data=changes[new].decode()
            self.assertLess(data.index('Newer'),data.index('Original headline'))
            self.assertLess(data.index('Original headline'),data.index('Older'))
        config=json.loads(changes['content/homepage.json'])
        self.assertEqual(config['unrelated'],'preserved')
        self.assertEqual(config['primary_door'][self.article['slugs']['ar']],'wildlife')

    def test_reclassification_keeps_unrelated_breadcrumb_schema(self):
        for language in m.LANGS:
            page,_=m.paths(self.article,language)
            breadcrumb={'@type':'BreadcrumbList','itemListElement':[{'position':1,'name':'Unchanged home','item':m.ORIGIN+'/'}]}
            data='<script type="application/ld+json">'+json.dumps(breadcrumb)+'</script>'
            self.snapshot.files[page]=self.snapshot.files[page].replace(b'</head>',data.encode()+b'</head>')
        changes=m.replay(self.snapshot,self.reclassify())
        for language in m.LANGS:
            page,_=m.paths(self.article,language)
            self.assertIn(data.encode(),changes[page])

    def test_stale_base_unknown_fields_and_claimed_approval_rejected(self):
        for update in ({'expected_base':'c'*40},{'approved':True},{'output_paths':['AGENTS.md']},{'operation':'execute'}):
            with self.subTest(update=update):
                value=dict(self.value,**update)
                with self.assertRaises(ValueError):m.bundle(self.snapshot,value)

    def test_mixed_operation_raw_markup_controls_and_missing_translation_rejected(self):
        for update in ({'notice':{}},{'replacements':{'ar':self.value['replacements']['ar']}}):
            with self.assertRaises(ValueError):m.bundle(self.snapshot,dict(self.value,**update))
        for invalid in ('<script>bad</script>','bad\x00','bad\u202e'):
            value=copy.deepcopy(self.value);value['replacements']['ar'][0]['new']=invalid
            with self.assertRaises(ValueError):m.bundle(self.snapshot,value)

    def test_missing_or_ambiguous_old_paragraph_and_caption_edit_rejected(self):
        for old in ('absent','Keep caption','Keep rights credit','Keep subtitle'):
            value=copy.deepcopy(self.value);value['replacements']['ar'][0]['old']=old
            with self.assertRaises(ValueError):m.bundle(self.snapshot,value)
        page,_=m.paths(self.article,'ar')
        self.snapshot.files[page]=self.snapshot.files[page].replace(b'</article>',('<p>'+self.paragraphs['ar']+'</p></article>').encode())
        with self.assertRaises(ValueError):self.plan()

    def test_missing_wrong_language_canonical_or_nonregular_mirror_rejected(self):
        for kind in ('missing','language','canonical','hreflang','symlink'):
            snap,_,_=fixture();page,_=m.paths(self.article,'fr')
            if kind=='missing':snap.files.pop(page)
            if kind=='language':snap.files[page]=snap.files[page].replace(b'lang="fr"',b'lang="en"')
            if kind=='canonical':snap.files[page]=snap.files[page].replace(b'rel="canonical"',b'rel="untrusted"')
            if kind=='hreflang':snap.files[page]=snap.files[page].replace(b'hreflang="ar"',b'hreflang="de"')
            if kind=='symlink':snap.items[page]=('120000','blob','a'*40)
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):m.bundle(snap,self.value)

    def test_homepage_or_ticker_membership_blocks_removal_and_reclassification(self):
        page,_=m.paths(self.article,'ar')
        self.snapshot.files['docs/index.html']=('<div class="ticker"><a href="'+m.route(page)+'">Story</a></div>').encode()
        with self.assertRaisesRegex(ValueError,'homepage/ticker'):self.withdraw()
        self.setUp();self.snapshot.files['docs/index.html']=('<a href="'+m.route(page)+'">Story</a>').encode()
        with self.assertRaisesRegex(ValueError,'homepage/ticker'):self.reclassify()

    def test_special_placement_and_combined_archive_fail_closed(self):
        path='docs/category/special/index.html'
        self.snapshot.files[path]=('<main><script id="combined-archive-data"></script><article class="card"><a href="'+m.route(m.paths(self.article,'ar')[0])+'">Story</a></article></main>').encode()
        self.snapshot.items[path]=('100644','blob','a'*40)
        with self.assertRaises(ValueError):self.withdraw()

    def test_withdrawal_updates_combined_filters_without_changing_other_topics(self):
        path='docs/category/صيد/index.html';slug=self.article['slugs']['ar']
        filters={'equestrian':[slug,'unrelated'],'marine':['unrelated'],'landMarine':[],'countLabel':'items'}
        raw='<main><article class="post-row"><a href="'+m.route(m.paths(self.article,'ar')[0])+'">Selected</a></article><article class="post-row"><a href="/posts/unrelated/">Other</a></article><p class="archive-result-count" hidden>2 items</p><script type="application/json" id="combined-archive-data">'+json.dumps(filters)+'</script></main>'
        self.snapshot.files[path]=raw.encode();self.snapshot.items[path]=('100644','blob','a'*40)
        changed=m.replay(self.snapshot,self.withdraw())[path].decode()
        self.assertNotIn('Selected',changed);self.assertIn('Other',changed)
        self.assertIn('>1 items</p>',changed)
        node=dom.fromstring(changed);data=json.loads(node.xpath('//script[@id="combined-archive-data"]/text()')[0])
        self.assertEqual(data,dict(filters,equestrian=['unrelated']))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):m.loads('{"schema":1,"schema":2}')

    def test_legacy_punctuation_is_preserved_without_allowing_paths(self):
        value=copy.deepcopy(self.value);value.update(publication_id='legacy',article_slug='مقال،-قديم')
        self.assertEqual(m.request(value,self.snapshot.base)['article_slug'],'مقال،-قديم')
        for bad in ('../escape','a/b','%2e%2e'):
            with self.assertRaises(ValueError):m.request(dict(value,article_slug=bad),self.snapshot.base)

    def test_placement_schema_is_closed_and_action_bound(self):
        self.withdraw()
        placement={'decision_reference':'private:exact-placement','lead':'lead',
                   'side':['side-'+str(i) for i in range(4)],'latest':['latest-'+str(i) for i in range(8)],'desks':{}}
        value=dict(self.value,placement=placement)
        m.request(value,self.snapshot.base)
        for change in ({'side':['short']},{'desks':{'tv':[]}},{'output_paths':['AGENTS.md']}):
            with self.assertRaises(ValueError):m.request(dict(value,placement=dict(placement,**change)),self.snapshot.base)
        self.setUp()
        with self.assertRaises(ValueError):m.request(dict(self.value,placement=placement),self.snapshot.base)

    def test_reclassification_into_combined_door_updates_only_count_and_selected_card(self):
        for language in m.LANGS:
            prefix='' if language=='ar' else language+'/'
            existing='docs/'+prefix+'category/'+m.DOORS['wildlife'][0]+'/index.html'
            destination='docs/'+prefix+'category/'+m.DOORS['hunting'][0]+'/index.html'
            filters={'equestrian':[],'marine':[],'landMarine':[],'countLabel':'items'}
            self.snapshot.files[destination]=self.snapshot.files[existing].replace(b'</main>',('<p class="archive-result-count" hidden>2 items</p><script type="application/json" id="combined-archive-data">'+json.dumps(filters)+'</script></main>').encode())
            self.snapshot.items[destination]=('100644','blob','a'*40)
        self.value.pop('replacements');self.value.update(operation='reclassify',old_door='science',new_door='hunting')
        result=m.replay(self.snapshot,self.plan())
        for language in m.LANGS:
            prefix='' if language=='ar' else language+'/'
            path='docs/'+prefix+'category/'+m.DOORS['hunting'][0]+'/index.html'
            self.assertIn(b'>3 items</p>',result[path]);self.assertIn(b'Original headline',result[path])

    def test_source_and_media_never_enter_proposed_diff(self):
        for operation in ('edit','withdraw','reclassify'):
            self.setUp()
            plan=self.plan() if operation=='edit' else self.withdraw() if operation=='withdraw' else self.reclassify()
            forbidden=('content/publications/','audit/','docs/media/','AGENTS.md','.github/','scripts/')
            self.assertFalse(any(e['path'].startswith(forbidden) for e in plan['changes']))
            self.assertEqual(plan['status'],'REVIEW_ONLY_NOT_APPROVED_NOT_PUBLISHED')

    def test_notice_backslashes_are_literal_not_regex_references(self):
        self.withdraw()
        self.value['notice']['en']=r'Literal \1 and \g<name> in notice'
        # Angle brackets are forbidden by the plain-text schema.
        with self.assertRaises(ValueError):self.plan()
        self.value['notice']['en']=r'Literal \1 and backslash in notice'
        changes=m.replay(self.snapshot,self.plan())
        self.assertIn(br'Literal \1 and backslash',changes[m.paths(self.article,'en')[0]])

    def test_newline_paragraphs_and_multiple_simultaneous_changes(self):
        for language in m.LANGS:
            old='Line one\nLine two '+language
            for path in m.paths(self.article,language):
                self.snapshot.files[path]=self.snapshot.files[path].replace(self.paragraphs[language].encode(),old.replace('\n','<br>').encode())
            self.value['replacements'][language]=[{'old':old,'new':'Changed\nTwo lines'}, {'old':'Keep heading','new':'Changed heading'}]
        plan=self.plan()
        for language in m.LANGS:
            for path in m.paths(self.article,language):
                self.assertIn(b'<p>Changed<br>Two lines</p>',m.replay(self.snapshot,plan)[path])

    def test_missing_search_row_and_multifacet_reclassification_rejected(self):
        self.snapshot.files['docs/assets/search/index-ar.json']=serialize({'articles':[]})
        with self.assertRaisesRegex(ValueError,'search row'):self.plan()
        self.setUp()
        path='docs/assets/search/index-ar.json'
        value=json.loads(self.snapshot.files[path]);value['articles'][0]['categories'].append('Other facet')
        self.snapshot.files[path]=serialize(value)
        with self.assertRaisesRegex(ValueError,'Multiple search facets'):self.reclassify()

    def test_sitemap_surviving_alternate_and_contentful_alias_rejected(self):
        path='docs/sitemap.xml'
        self.snapshot.files[path]=self.snapshot.files[path].replace(b'</urlset>',('<url xmlns:xhtml="http://www.w3.org/1999/xhtml"><loc>'+m.ORIGIN+'/posts/other/</loc><xhtml:link href="'+m.ORIGIN+m.route(m.paths(self.article,'fr')[0])+'"/></url></urlset>').encode())
        with self.assertRaisesRegex(ValueError,'Sitemap alternate'):self.withdraw()
        self.setUp()
        path='docs/s/fixture-fr/index.html'
        self.snapshot.files[path]=self.snapshot.files[path].replace(b'http-equiv="refresh"',b'http-equiv="missing"')
        with self.assertRaisesRegex(ValueError,'Contentful alias'):self.withdraw()


class GitSnapshotTests(unittest.TestCase):
    def test_exact_clean_base_and_regular_blob_enforcement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            subprocess.run(['git','init','-q',str(root)],check=True)
            (root/'file').write_text('original')
            subprocess.run(['git','-C',str(root),'add','.'],check=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','Synthetic snapshot'],check=True)
            base=m.git(root,'rev-parse','HEAD').decode().strip()
            self.assertEqual(m.Snapshot(root,base).read('file'),b'original')
            with self.assertRaises(ValueError):m.Snapshot(root,'a'*40)
            (root/'extra').write_text('untracked')
            with self.assertRaisesRegex(ValueError,'Clean'):m.Snapshot(root,base)

    def test_cli_external_bundle_is_repeatable_and_repository_unchanged(self):
        fixture_snapshot,source,paragraphs=fixture()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'repo';root.mkdir()
            subprocess.run(['git','init','-q',str(root)],check=True)
            for path,data in fixture_snapshot.files.items():
                target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            subprocess.run(['git','-C',str(root),'add','.'],check=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','Synthetic maintenance CLI fixture'],check=True)
            base=m.git(root,'rev-parse','HEAD').decode().strip()
            value={'schema':m.SCHEMA,'id':'cli-fixture','expected_base':base,'publication_id':'maintenance-test',
                   'article_slug':source['articles'][0]['slugs']['ar'],'operation':'edit','decision_reference':'private:synthetic-not-approval','conflicts':[],
                   'replacements':{l:[{'old':paragraphs[l],'new':'New synthetic text '+l}] for l in m.LANGS}}
            request=Path(directory)/'request.json';request.write_bytes(m.canonical(value))
            output=Path(directory)/'bundle'
            args=[sys.executable,str(Path(m.__file__).resolve()),'--repo',str(root),'--base',base,'--request',str(request),'--output',str(output)]
            result=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((output/'plan.json').is_file());self.assertTrue((output/'review.json').is_file())
            plan=json.loads((output/'plan.json').read_text())
            m.replay(m.Snapshot(root,base),plan)
            self.assertEqual(m.git(root,'status','--porcelain','--untracked-files=all'),b'')
            self.assertEqual(m.git(root,'rev-parse','HEAD').decode().strip(),base)
            # Existing output and repository-local output both fail without writes.
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            args[-1]=str(root/'unsafe-output')
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertFalse((root/'unsafe-output').exists())


if __name__=='__main__':
    unittest.main()
