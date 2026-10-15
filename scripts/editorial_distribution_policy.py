#!/usr/bin/env python3
"""Nayef-approved editorial gate: reference material never auto-enters news slots.

Do not infer 'breaking news' from a new publication date on an encyclopaedia
entry or from a contemporary explanation of an older hunting statute.
"""
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
CONFIG=ROOT/'content/homepage.json'
LINK=re.compile(r'\bhref=["\'][^"\']*posts/([^/"\'?#]+)/',re.I)
FOLDERS={'قوانين':'laws','موسوعة-الطيور':'encyclopedia','علوم-واكتشافات':'science'}
PRIMARY={'laws':'laws','birds':'encyclopedia','science':'science'}

def memberships(config=None, docs=DOCS):
    config=config or json.loads(CONFIG.read_text(encoding='utf-8'))
    lookup={}
    for folder,genre in FOLDERS.items():
        page=docs/'category'/folder/'index.html'
        if not page.is_file():
            raise ValueError('Missing editorial category listing: '+str(page))
        # Category pages repeat the global news ticker in the header. Only the
        # MAIN archive listing defines taxonomy membership; never classify a
        # ticker headline as an Encyclopaedia/Laws/Science article.
        page_html=page.read_text(encoding='utf-8')
        main=re.search(r'<main\b[^>]*>(.*?)</main>',page_html,re.S|re.I)
        if not main:
            raise ValueError('No category main content: '+str(page))
        for slug in LINK.findall(main.group(1)):
            lookup.setdefault(unquote(slug),set()).add(genre)
    for slug,door in config.get('primary_door',{}).items():
        if door in PRIMARY:
            lookup.setdefault(slug,set()).add(PRIMARY[door])
    return lookup

def eligible(slug,surface,config,lookup=None):
    if surface not in ('featured','latest','ticker'):
        raise ValueError('Unsupported news surface: '+surface)
    policy=config.get('editorial_distribution_policy')
    if not policy:
        raise ValueError('Missing explicit editorial distribution policy')
    lookup=lookup if lookup is not None else memberships(config)
    cats=lookup.get(slug,set())
    if cats.intersection(('laws','encyclopedia')):
        return False
    if 'science' in cats:
        return slug in policy['approved_science_news'].get(surface,[])
    return True

def validate_config(config,docs=DOCS):
    policy=config.get('editorial_distribution_policy')
    assert policy and policy['science_promotion_approval_required'] is True
    assert set(policy['reference_only_categories'])=={'قوانين','موسوعة-الطيور'}
    assert set(policy['approved_science_news'])=={'featured','latest','ticker'}
    lookup=memberships(config,docs)
    for surface,key in [('featured','featured'),('latest','latest'),('ticker','ticker_slugs')]:
        for slug in config[key]:
            if not eligible(slug,surface,config,lookup):
                category=', '.join(sorted(lookup.get(slug,())))
                raise AssertionError(f'{surface}: unapproved news promotion {slug} ({category})')
    assert config['latest']==config['ia_slots']['latest']
    assert config['ticker_slugs']==[e['slug'] for e in config['ticker_entries']]
    return True

if __name__=='__main__':
    validate_config(json.loads(CONFIG.read_text(encoding='utf-8')))
    print('PASS: no laws or Bird Encyclopedia in news positions; Science needs explicit approval')
