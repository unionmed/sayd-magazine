"""Regression tests: Arabic paths must be checked; historical image repair stays narrowly scoped."""
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
import check_publication_contract as contract
from article_media_repairs import repair_body, PARTNERS, MIGRATION, LOGOS, BIRDS
from build_en_edition import article_body_html, parse_draft

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])

def test_contract():
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);docs=root/'docs';page=docs/'posts/مقال-قديم/index.html';page.parent.mkdir(parents=True)
        image=docs/'media/uploads/2020/01/test.jpg';image.parent.mkdir(parents=True);image.write_bytes(b'x'*40)
        before='<html><header class="article-header"><h1>قديم</h1><div class="article-meta"><span class="meta-item">4 أيار 2020</span></div></header><article class="article-content"><p>نص قديم</p></article></html>'
        tag='<p><img src="../../media/uploads/2020/01/test.jpg" alt="صورة أرشيفية"></p>'
        after=before.replace('<p>نص قديم</p>',tag+'<p>نص قديم</p>')
        page.write_text(before);git(root,'init','-q');git(root,'add','.');git(root,'-c','user.name=Test','-c','user.email=test@example.org','commit','-qm','base')
        base=git(root,'rev-parse','HEAD').decode().strip();file=page.relative_to(root).as_posix()
        with patch.object(contract,'ROOT',root),patch.object(contract,'DOCS',docs):
            page.write_text(after)
            for value in ['true','false']:
                git(root,'config','core.quotePath',value)
                assert contract.changed_docs(base)==[file]
            assert contract.archive_image_repair(file,base)
            for broken in [after.replace('نص قديم','نص آخر'),after.replace('نص قديم','نصقديم'),after.replace('<h1>قديم','<h1>جديد'),after.replace(' alt="صورة أرشيفية"',''),after.replace('../../media/uploads/2020/01/test.jpg','https://example.org/a.jpg')]:
                page.write_text(broken);assert not contract.archive_image_repair(file,base)
            # New files and 2026 edits can never use the archive exception.
            other=docs/'posts/جديد/index.html';other.parent.mkdir();other.write_text(after)
            assert not contract.archive_image_repair(other.relative_to(root).as_posix(),base)
            page.write_text(before.replace('2020','2026'));git(root,'add',file);git(root,'-c','user.name=Test','-c','user.email=test@example.org','commit','-qm','current')
            current=git(root,'rev-parse','HEAD').decode().strip();page.write_text(after.replace('4 أيار 2020','4 أيار 2026'))
            assert not contract.archive_image_repair(file,current)

def test_current_generators():
    root=Path(__file__).resolve().parents[1]
    for slug in [PARTNERS,MIGRATION]:
        body=article_body_html(slug,parse_draft(root/'content/en'/f'{slug}.md'),'../../../')
        assert repair_body(slug,body)==body
        expected=LOGOS if slug==PARTNERS else [BIRDS]
        for name in expected:assert body.count(name)==1,(slug,name)
        for lang in ['en','fr']:
            text=(root/'docs'/lang/'posts'/slug/'index.html').read_text()
            for name in expected:assert name in text,(lang,name)

if __name__=='__main__':
    test_contract();test_current_generators()
    print('PASS: literal Arabic paths; additive archive repair only; current media survive rendering')
