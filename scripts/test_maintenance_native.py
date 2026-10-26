"""Native maintenance and inverse decisions in isolated synthetic publication history."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import article_maintenance as maintenance
import maintenance_native as native
import maintenance_state as state
import publication_compiler as compiler
import publication_finalize as finalizer
import publication_guard as guard
import publication_request as requests
from test_publication_compiler import record,files_for,source_commit

ROOT=Path(__file__).resolve().parents[1]


class NativeMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='sayd-native-maintenance-tests-')
        cls.root=Path(cls.temp.name)/'repo'
        subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','-q','--shared',str(ROOT),str(cls.root)],check=True)
        first=compiler.git(cls.root,'rev-parse','HEAD').decode().strip()
        cls.record=record(first,'native-maintenance-fixture')
        cls.record['articles'][0]['archives']=['science']
        source=source_commit(cls.root,first,files_for(cls.record))
        output=Path(cls.temp.name)/'initial-synthetic-publication'
        plan=Path(cls.temp.name)/'initial-plan.json'
        # Fixture publication only. The four maintenance operations below run
        # the real unchanged-strength stage checks against this full corpus.
        script="""import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'scripts')
import publication_compiler as c
with patch.object(c,'validate_stage'):
    c.compile_publication(Path.cwd(),sys.argv[1],sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]))
"""
        result=subprocess.run([sys.executable,'-c',script,first,source,str(output),str(plan)],cwd=cls.root,capture_output=True,text=True)
        if result.returncode:
            raise AssertionError(result.stdout[-3000:]+'\n'+result.stderr[-5000:])
        generated=compiler.git(output,'rev-parse','HEAD').decode().strip()
        compiler.git(cls.root,'fetch','--quiet',str(output),generated)
        compiler.git(cls.root,'checkout','--quiet','--detach',generated)
        cls.base=generated
        cls.article=cls.record['articles'][0]

    @classmethod
    def tearDownClass(cls):
        guard._proofs.clear()
        cls.temp.cleanup()

    def setUp(self):
        compiler.git(self.root,'checkout','--quiet','--force','--detach',self.base)
        self.value={'schema':maintenance.SCHEMA,'id':'native-test-edit','expected_base':self.base,
                    'publication_id':self.record['id'],'article_slug':self.article['slugs']['ar'],
                    'operation':'edit','decision_reference':'private:synthetic-not-editorial-approval','conflicts':[],
                    'replacements':{l:[{'old':self.article['translations'][l]['sections'][0]['paragraphs'][0],
                                         'new':'A corrected synthetic paragraph in '+l+'; never a publication instruction.'}] for l in compiler.LANGS}}
        self.path=state.REQUEST_PREFIX+self.value['id']+'.json'

    def source(self,value=None,extra=None,modes=None):
        value=copy.deepcopy(value or self.value)
        path=state.REQUEST_PREFIX+value['id']+'.json'
        files={path:maintenance.canonical(value)}
        files.update(extra or {})
        source=source_commit(self.root,value['expected_base'],files,modes)
        # Existing immutable trailers, still request data rather than approval.
        tree=compiler.git(self.root,'rev-parse',source+'^{tree}').decode().strip()
        env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.invalid')
        scope=bool(value.get('placement'))
        if value['operation']=='restore':
            previous=state.current(self.root)[value['article_slug']]
            scope=native.review_scope({e['path']:None for e in previous['changes']})
        message='Synthetic maintenance request\n\nSayd-Publication-Request: v1\nDistribution-Review-Scope: '+str(scope).lower()+'\n'
        return subprocess.check_output(['git','-C',str(self.root),'commit-tree',tree,'-p',value['expected_base']],input=message.encode(),env=env).decode().strip()

    def build(self,value=None,full=False):
        value=copy.deepcopy(value or self.value)
        source=self.source(value)
        scope=requests.request_scope(compiler.git(self.root,'show','-s','--format=%B',source).decode())
        with tempfile.TemporaryDirectory(prefix='sayd-native-maintenance-build-') as directory:
            output=Path(directory)/'site';report=Path(directory)/'plan.json'
            if full:
                plan=compiler.compile_publication(self.root,value['expected_base'],source,output,report,scope)
            else:
                with patch.object(compiler,'validate_stage'):
                    plan=compiler.compile_publication(self.root,value['expected_base'],source,output,report,scope)
            files={e['path']:(output/e['path']).read_bytes() for e in plan['changes']}
        return source,plan,files

    def candidate(self,source,plan,files,modes=None):
        provisional=source_commit(self.root,source,files,modes)
        tree=compiler.git(self.root,'rev-parse',provisional+'^{tree}').decode().strip()
        env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.invalid')
        return subprocess.check_output(['git','-C',str(self.root),'commit-tree',tree,'-p',source],input=compiler.provenance_message(plan).encode(),env=env).decode().strip()

    def test_source_validator_and_exact_generated_scope(self):
        source,plan,files=self.build()
        self.assertFalse(requests.validate_source(self.root,self.base,source))
        self.assertEqual(len(plan['changes']),11)
        self.assertIn(self.path,files)
        ledger=json.loads(files[state.PREFIX+self.value['id']+'.json'])
        self.assertEqual(ledger['generation'],1);self.assertIsNone(ledger['previous'])
        self.assertEqual(ledger['after_state']['status'],'active')
        self.assertEqual(len(ledger['changes']),9)
        for path in files:finalizer.safe_output_path(path)
        candidate=self.candidate(source,plan,files)
        with tempfile.TemporaryDirectory() as directory,patch.object(compiler,'validate_stage'):
            compiler.verify_candidate(self.root,self.base,candidate,Path(directory)/'site',Path(directory)/'plan.json')

    def test_candidate_tree_mode_source_and_provenance_tamper_rejected(self):
        source,plan,files=self.build()
        variants=[dict(files,**{'scripts/publication_compiler.py':b'raise SystemExit(0)\n'}),
                  dict(files,**{'content/homepage.json':b'{}'}),
                  dict(files,**{state.PREFIX+self.value['id']+'.json':b'{}'})]
        for modified in variants:
            candidate=self.candidate(source,plan,modified)
            compiler.git(self.root,'checkout','-q','--force','--detach',candidate)
            with self.assertRaises((ValueError,subprocess.CalledProcessError)):
                native.verified_transition(self.root,self.base)
        for path in (self.path,maintenance.paths(self.article,'fr')[0]):
            candidate=self.candidate(source,plan,files,{path:'120000'})
            compiler.git(self.root,'checkout','-q','--force','--detach',self.base)
            with tempfile.TemporaryDirectory() as directory,patch.object(compiler,'validate_stage'),self.assertRaises(ValueError):
                compiler.verify_candidate(self.root,self.base,candidate,Path(directory)/'site',Path(directory)/'plan.json')

    def test_mixed_sources_stale_predecessor_and_forged_ledger_rejected(self):
        for extra in ({'docs/unrelated.html':b'tampered'}, {'content/maintenance-ledger/forged.json':b'{}'},
                      {'content/publications/new.json':b'{}'}, {'content/caption-revisions/mixed.json':b'{}'}):
            with self.subTest(extra=list(extra)):
                with self.assertRaises(ValueError):native.source_input(self.root,self.base,self.source(extra=extra))
        value=copy.deepcopy(self.value);value['previous_revision']='unrelated'
        with self.assertRaises(ValueError):native.source_input(self.root,self.base,self.source(value))

    def test_raw_request_cannot_masquerade_as_candidate(self):
        source=self.source()
        compiler.git(self.root,'checkout','-q','--detach',source)
        with self.assertRaises(ValueError):native.verified_transition(self.root,self.base)

    def test_external_trusted_guard_keeps_maintenance_out_of_additions(self):
        source,plan,files=self.build()
        candidate=self.candidate(source,plan,files)
        compiler.git(self.root,'checkout','-q','--detach',candidate)
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false','SAYD_PUBLICATION_HEAD':candidate}):
            proof=guard.verified_publication(self.base,self.root)
            self.assertEqual(proof.kind,'verified-article-maintenance')
            self.assertEqual(proof.additions,())
            self.assertEqual(proof.revisions,())
            self.assertEqual(len(proof.maintenance),1)
            self.assertEqual(proof.maintenance[0]['article_slug'],self.article['slugs']['ar'])
            self.assertEqual(compiler.git(proof.site,'rev-parse','HEAD^{tree}'),compiler.git(self.root,'rev-parse','HEAD^{tree}'))
        guard._proofs.clear()

    def test_full_edit_reclassify_withdraw_and_restore_checks(self):
        # Each operation starts from the same synthetic baseline; no real article
        # or fixture is published. Every native stage check runs, without mocks.
        for operation in getattr(self,'operations',('edit','reclassify','withdraw')):
            compiler.git(self.root,'checkout','-q','--force','--detach',self.base)
            value=copy.deepcopy(self.value);value['id']='full-'+operation;value['operation']=operation
            if operation!='edit':value.pop('replacements')
            if operation=='reclassify':value.update(old_door='science',new_door='wildlife')
            if operation=='withdraw':value['notice']={l:'Synthetic withdrawal notice, never published. '+l for l in compiler.LANGS}
            with self.subTest(operation=operation):
                source,plan,files=self.build(value,full=True)
                candidate=self.candidate(source,plan,files)
                compiler.git(self.root,'checkout','-q','--detach',candidate)
                self.assertEqual(native.verified_transition(self.root,self.base)['ledger']['operation'],operation)
                state.assert_effective(self.root)
                if operation=='withdraw':
                    # A fresh, specifically authorized reverse request preserves
                    # the complete old ledger and restores only exact prior bytes.
                    restore={k:copy.deepcopy(v) for k,v in value.items() if k!='notice'}
                    restore.update(id='full-restore',operation='restore',expected_base=candidate,
                                   previous_revision=value['id'],restore_revision=value['id'])
                    inverse_source,inverse_plan,inverse_files=self.build(restore,full=True)
                    inverse=self.candidate(inverse_source,inverse_plan,inverse_files)
                    compiler.git(self.root,'checkout','-q','--detach',inverse)
                    self.assertEqual(native.verified_transition(self.root,candidate)['ledger']['after_state']['status'],'active')
                    state.assert_effective(self.root)
                    self.assertTrue((self.root/state.PREFIX/(value['id']+'.json')).is_file())
                    for language in compiler.LANGS:
                        path=maintenance.paths(self.article,language)[0]
                        self.assertEqual((self.root/path).read_bytes(),compiler.git(self.root,'show',self.base+':'+path))

    def test_no_resurrection_and_sequential_edits_need_current_revision(self):
        value=copy.deepcopy(self.value);value.pop('replacements');value.update(id='withdraw-state',operation='withdraw',notice={l:'Withdrawn synthetic fixture.' for l in compiler.LANGS})
        source,plan,files=self.build(value);candidate=self.candidate(source,plan,files)
        compiler.git(self.root,'checkout','-q','--detach',candidate)
        import seo_foundation as seo
        import build_search_index as search
        import refresh_homepage_doors as home
        for language in compiler.LANGS:
            path=maintenance.paths(self.article,language)[0]
            relative=Path(path).relative_to('docs')
            original=compiler.git(self.root,'show',self.base+':'+path).decode()
            self.assertFalse(seo.in_sitemap(relative,self.root/'docs'))
            with self.assertRaisesRegex(ValueError,'stale content'):seo.apply_html(original,self.root/path,self.root/'docs',relative,{})
            (self.root/path).write_text(original)
            self.assertIsNone(search.extract_article(self.root/path,self.root/'docs',language))
        with patch.object(home,'ROOT',self.root),patch.object(home,'DOCS',self.root/'docs'):
            with self.assertRaisesRegex(ValueError,'Withdrawn'):home.source_article_category(self.article['slugs']['ar'])
        with self.assertRaises(ValueError):state.assert_effective(self.root)

    def test_legacy_identity_uses_existing_routes_and_never_rebuilds_markdown(self):
        value=copy.deepcopy(self.value);value['publication_id']='legacy'
        source,plan,files=self.build(value)
        self.assertEqual(len(plan['changes']),11)
        self.assertNotIn('content/publications/'+self.record['id']+'.json',files)
        # Legacy support does not infer a French version from English.
        page=maintenance.paths(self.article,'ar')[0]
        changed=compiler.git(self.root,'show',self.base+':'+page).replace(b'hreflang="fr"',b'hreflang="de"')
        altered=source_commit(self.root,self.base,{page:changed})
        compiler.git(self.root,'checkout','-q','--detach',altered)
        value['expected_base']=altered
        with self.assertRaises(ValueError):self.build(value)

    def test_full_selected_lead_withdrawal_and_shared_ticker(self):
        original_base=self.base
        value=record(original_base,'native-upper-maintenance-fixture',placement='lead',ticker=True)
        value['articles'][0]['archives']=['science']
        replacement=copy.deepcopy(value['articles'][0])
        replacement['slugs']={l:'native-upper-replacement-'+l for l in compiler.LANGS}
        replacement['distribution']={'placement':'archive-only','ticker':False}
        for language in compiler.LANGS:
            replacement['translations'][language]['title']='Replacement synthetic fixture '+language
        value['articles'].append(replacement)
        source=source_commit(self.root,original_base,files_for(value))
        with tempfile.TemporaryDirectory(prefix='sayd-upper-bootstrap-') as directory:
            output=Path(directory)/'site'
            script="""import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'scripts')
import publication_compiler as c
with patch.object(c,'validate_stage'):
    c.compile_publication(Path.cwd(),sys.argv[1],sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]),True)
"""
            result=subprocess.run([sys.executable,'-c',script,original_base,source,str(output),str(Path(directory)/'plan.json')],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout[-1500:]+result.stderr[-5000:])
            base=compiler.git(output,'rev-parse','HEAD').decode().strip()
            compiler.git(self.root,'fetch','--quiet',str(output),base)
            compiler.git(self.root,'checkout','--quiet','--detach',base)
        home=json.loads((self.root/'content/homepage.json').read_text())
        target=value['articles'][0]['slugs']['ar']
        self.assertEqual(home['ia_slots']['main'],target)
        request={'schema':maintenance.SCHEMA,'id':'withdraw-selected-lead','expected_base':base,
                 'publication_id':value['id'],'article_slug':target,'operation':'withdraw',
                 'decision_reference':'private:synthetic-owner-decision','conflicts':[],
                 'notice':{l:'Synthetic withdrawn lead notice. '+l for l in compiler.LANGS},
                 'placement':{'decision_reference':'private:synthetic-explicit-replacement',
                              'lead':replacement['slugs']['ar'],'side':home['ia_slots']['important'],
                              'latest':home['latest'],'desks':{}}}
        source,plan,files=self.build(request,full=True)
        self.assertEqual(plan['policy'],{'allow_distribution':True})
        self.assertTrue(requests.validate_source(self.root,base,source))
        candidate=self.candidate(source,plan,files)
        compiler.git(self.root,'checkout','--quiet','--detach',candidate)
        transition=native.verified_transition(self.root,base)
        self.assertEqual(transition['ledger']['after_state']['status'],'withdrawn')
        changed_home=json.loads((self.root/'content/homepage.json').read_text())
        self.assertEqual(changed_home['ia_slots']['main'],replacement['slugs']['ar'])
        self.assertNotIn(target,changed_home['ticker_slugs'])
        self.assertEqual(changed_home['ia_slots']['important'],home['ia_slots']['important'])
        self.assertEqual(changed_home['latest'],home['latest'])
        from lxml import html
        for language,prefix in (('ar',''),('en','en'),('fr','fr')):
            node=html.fromstring((self.root/'docs'/prefix/'index.html').read_bytes())
            href=node.xpath('//article[contains(@class,"feature-lead")]//h2/a/@href')
            self.assertEqual(href,['posts/'+replacement['slugs'][language]+'/index.html'])
        restore={k:copy.deepcopy(v) for k,v in request.items() if k not in {'notice','placement'}}
        restore.update(id='restore-selected-lead',operation='restore',expected_base=candidate,
                       previous_revision=request['id'],restore_revision=request['id'])
        inverse_source,inverse_plan,inverse_files=self.build(restore,full=True)
        self.assertEqual(inverse_plan['policy'],{'allow_distribution':True})
        self.assertTrue(requests.validate_source(self.root,candidate,inverse_source))
        for change in transition['ledger']['changes']:
            self.assertEqual(inverse_files[change['path']],compiler.git(self.root,'show',base+':'+change['path']))
        inverse=self.candidate(inverse_source,inverse_plan,inverse_files)
        compiler.git(self.root,'checkout','--quiet','--detach',inverse)
        self.assertEqual(native.verified_transition(self.root,candidate)['ledger']['after_state']['status'],'active')
        state.assert_effective(self.root)
        self.assertTrue((self.root/state.PREFIX/(request['id']+'.json')).is_file())


if __name__=='__main__':
    unittest.main()
