"""Exact episode promotion regressions; fixture approval is not publication authority."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from lxml import html
import editorial_revision as revision
import scoped_lead_revision as lead
import publication_compiler as compiler
import publication_finalize as finalizer
from test_publication_compiler import source_commit

ROOT = Path(__file__).resolve().parents[1]
PRE_PROMOTION = '7da1242fe7777cc6a6388c4f14482cb09f1fb02c'


class ScopedLeadRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-lead-tests-')
        cls.root = Path(cls.temp.name) / 'repo'
        subprocess.run(['git','clone','-q','--shared','--no-checkout',str(ROOT),str(cls.root)],check=True)
        compiler.git(cls.root,'checkout','-q','--detach',PRE_PROMOTION)
        code = {str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'scripts').glob('*.py')}
        cls.base = source_commit(cls.root,PRE_PROMOTION,code)
        compiler.git(cls.root,'checkout','-q','--detach',cls.base)
        raw=(cls.root/('content/publications/'+lead.PUBLICATION+'.json')).read_bytes()
        cls.record=json.loads(raw)
        cls.changes,cls.effective,_=lead.expected_changes(cls.root,cls.base,cls.record)
        cls.value={'schema':revision.SCHEMA,'id':lead.REVISION_ID,'expected_base':cls.base,
            'operation':lead.OPERATION,'approval_reference':'private:synthetic-test-not-owner-approval',
            'expected_source_sha256':compiler.sha256(raw),'expected_targets_sha256':compiler.sha256(compiler.canonical({p:compiler.sha256((cls.root/p).read_bytes()) for p in sorted(cls.changes)})), 'payload':{}}
        cls.path=revision.PREFIX+lead.REVISION_ID+'.json'
        cls.source=source_commit(cls.root,cls.base,{cls.path:json.dumps(cls.value).encode()})

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_exact_four_outputs_chronology_and_preservation(self):
        self.assertEqual(set(self.changes),set(lead.OUTPUTS))
        before=json.loads((self.root/'content/homepage.json').read_text());after=json.loads(self.changes['content/homepage.json'])
        episode=self.record['articles'][0]['slugs']['ar']
        self.assertEqual(after['featured'],[episode,lead.ADONIS,lead.OLD_LEAD,before['featured'][2],before['featured'][3]])
        self.assertEqual(after['latest'],[before['featured'][4]]+before['latest'][:7])
        self.assertEqual(len(after['featured']+after['latest']),len(set(after['featured']+after['latest'])))
        hunting=next(d['slugs'] for d in after['ia_door_sections'] if d['door']=='hunting')
        self.assertFalse(set(hunting)&set(after['featured']+after['latest']))
        for key in ('ticker_entries','ticker_slugs','card_image_overrides','primary_door'):
            self.assertEqual(after[key],before[key])
        for language in compiler.LANGS:
            path='docs/'+('' if language=='ar' else language+'/')+'index.html'
            tree=html.fromstring(self.changes[path]);node=tree.xpath('//article[contains(@class,"feature-lead")]')[0]
            tr=self.record['articles'][0]['translations'][language]
            self.assertEqual(node.xpath('.//h2/a')[0].text,tr['title'])
            self.assertEqual(node.xpath('.//*[contains(@class,"migration-kicker")]')[0].text,tr['kicker'])
            self.assertIn(self.record['photos'][0]['path'][5:],node.xpath('.//img')[0].get('src'))
            old=html.fromstring((self.root/path).read_bytes())
            old_lead=old.xpath('//article[contains(@class,"feature-lead")]')[0]
            self.assertEqual(node.attrib,old_lead.attrib)
            self.assertEqual([(a.tag,{k:v for k,v in a.attrib.items() if k != 'href'}) for a in node.xpath('.//a')],[(a.tag,{k:v for k,v in a.attrib.items() if k != 'href'}) for a in old_lead.xpath('.//a')])
            self.assertEqual([html.tostring(n) for n in old.xpath('//div[@class="ticker"]')],[html.tostring(n) for n in tree.xpath('//div[@class="ticker"]')])
        expected=copy.deepcopy(self.record);expected['articles'][0]['distribution']['placement']='lead'
        self.assertEqual(self.effective,expected)

    def test_empty_payload_exact_id_hashes_and_distribution(self):
        for key,value in [('payload',{'slot':'other'}),('id','other'),('operation','promote-any-lead'),('expected_base','0'*40),('expected_source_sha256','0'*64),('expected_targets_sha256','0'*64)]:
            bad=copy.deepcopy(self.value);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):revision.expected_changes(self.root,self.base,bad,self.path)
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ValueError,'distribution scope'):
            compiler.compile_publication(self.root,self.base,self.source,Path(temp)/'out',Path(temp)/'report.json',False)

    def test_request_adapter_exact_distribution_trailer(self):
        import publication_request
        tree=compiler.git(self.root,'rev-parse',self.source+'^{tree}').decode().strip()
        env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.invalid')
        message='Fixture only\n\nSayd-Publication-Request: v1\nDistribution-Review-Scope: true'
        requested=subprocess.check_output(['git','-C',str(self.root),'commit-tree',tree,'-p',self.base],input=message.encode(),env=env).decode().strip()
        self.assertTrue(publication_request.validate_source(self.root,self.base,requested))

    def test_source_mixing_rejected(self):
        for path in ('content/publications/'+lead.PUBLICATION+'.json','docs/index.html','scripts/scoped_lead_revision.py'):
            source=source_commit(self.root,self.base,{self.path:json.dumps(self.value).encode(),path:b'bad'})
            with self.subTest(path=path),self.assertRaises(ValueError):revision.source_input(self.root,self.base,source)

    def test_actual_compile_replay_finalizer_read_boundaries(self):
        # Fast unit proof; the release rehearsal MUST also run validate_stage unmocked.
        with tempfile.TemporaryDirectory() as temp,patch.object(compiler,'validate_stage'):
            out=Path(temp)/'out'
            plan=compiler.compile_publication(self.root,self.base,self.source,out,Path(temp)/'plan.json',True)
            candidate=compiler.git(out,'rev-parse','HEAD').decode().strip()
            compiler.git(self.root,'fetch','-q',str(out),candidate)
            replay=compiler.verify_candidate(self.root,self.base,candidate,Path(temp)/'replay',Path(temp)/'replay.json')
            self.assertEqual(replay,plan)
            # A valid-looking provenance message cannot authorize another page.
            files={item['path']:(out/item['path']).read_bytes() for item in plan['changes']}
            files['docs/posts/'+self.record['articles'][0]['slugs']['ar']+'/index.html']=b'unapproved body'
            raw=source_commit(self.root,self.source,files)
            tree=compiler.git(self.root,'rev-parse',raw+'^{tree}').decode().strip()
            env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.invalid')
            bad=subprocess.check_output(['git','-C',str(self.root),'commit-tree',tree,'-p',self.source],input=compiler.provenance_message(plan).encode(),env=env).decode().strip()
            with self.assertRaisesRegex(ValueError,'entire tree mismatch'):
                compiler.verify_candidate(self.root,self.base,bad,Path(temp)/'tampered-replay',Path(temp)/'tampered-plan.json')
            for item in plan['changes']:
                self.assertEqual(finalizer.read_change(out,item),(out/item['path']).read_bytes())
            with self.assertRaisesRegex(subprocess.CalledProcessError,'returned non-zero'):
                lead.expected_changes(out,candidate,self.record)


if __name__=='__main__':unittest.main()
