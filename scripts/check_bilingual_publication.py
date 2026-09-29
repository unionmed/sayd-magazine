#!/usr/bin/env python3
"""Compatibility entry point: publications now require all three languages."""
import sys,json
from check_publication_contract import check,check_new_stories,ROOT
if __name__=='__main__':
    check()
    if len(sys.argv)>1:
        pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
        check_new_stories(['docs/posts/'+sys.argv[1]+'/index.html'],pairs)
