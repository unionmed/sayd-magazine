"""Render synthetic native-maintenance candidates only, without publication."""
import argparse
import copy
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

import maintenance_native as native
import publication_compiler as compiler
from test_maintenance_native import NativeMaintenanceTests
from test_merged_section_browser import server,test_maintenance_browser


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    NativeMaintenanceTests.setUpClass()
    try:
        test=NativeMaintenanceTests()
        with sync_playwright() as runtime:
            browser=runtime.chromium.launch()
            try:
                for operation in ('edit','reclassify','withdraw'):
                    test.setUp()
                    value=copy.deepcopy(test.value);value.update(id='browser-'+operation,operation=operation)
                    if operation!='edit':value.pop('replacements')
                    if operation=='reclassify':value.update(old_door='science',new_door='wildlife')
                    if operation=='withdraw':value['notice']={l:'Synthetic withdrawal notice, never published. '+l for l in compiler.LANGS}
                    source,plan,files=test.build(value)
                    candidate=test.candidate(source,plan,files)
                    compiler.git(test.root,'checkout','--quiet','--detach',candidate)
                    transition=native.verified_transition(test.root,test.base)
                    assert transition and transition['ledger']['operation']==operation
                    proof=SimpleNamespace(site=test.root,maintenance=(transition['ledger'],))
                    http,origin=server(test.root/'docs')
                    context=browser.new_context()
                    context.route('**/*',lambda route:route.continue_() if urlsplit(route.request.url).hostname in {'127.0.0.1','localhost'} else route.abort())
                    try:
                        screens=test_maintenance_browser(context,origin,proof,args.output)
                        assert len(screens)==12,(operation,'three languages, four widths')
                    finally:
                        context.close();http.shutdown();http.server_close()
            finally:
                browser.close()
    finally:
        NativeMaintenanceTests.tearDownClass()
    print('PASS: 36 synthetic maintenance screenshots; AR/EN/FR x 4 widths x edit/reclassify/withdraw; no publication')


if __name__=='__main__':main()
