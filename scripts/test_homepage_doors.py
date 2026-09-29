"""Regression checks for the three mirrored homepages and fail-closed rules."""
from copy import deepcopy
from check_publication_contract import check
from refresh_homepage_doors import refresh, DOCS, config, validate_config

def test_homepages():
    check()
    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
        path=DOCS/prefix/'index.html';before=path.read_bytes()
        refresh(path,lang)
        assert path.read_bytes()==before, f'{lang}: refresh is not idempotent'
    for key in ('featured','latest'):
        bad=deepcopy(config());bad[key].append('extra-card')
        try:validate_config(bad)
        except AssertionError:pass
        else:raise AssertionError('Extra card accepted')
    # A French-only missing image must fail; restore the fixture even on failure.
    p=DOCS/'fr/index.html';original=p.read_text()
    try:
        p.write_text(original.replace('EQ-N02-interior-3x2.jpg','missing-test-image.jpg',1))
        try:check()
        except AssertionError:pass
        else:raise AssertionError('Broken mirrored image accepted')
    finally:p.write_text(original)
    print('PASS: stable renderer; excess cards and a missing mirror image rejected')
if __name__=='__main__':test_homepages()
