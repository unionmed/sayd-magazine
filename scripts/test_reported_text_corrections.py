#!/usr/bin/env python3
"""Regression checks for the approved 20 October 2026 textual corrections."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_arab_hunting_autumn_2026 import correct_jordan_copy
ROOT = Path(__file__).resolve().parents[1]
def read(path): return (ROOT / path).read_text()
for lang, slug, species in [('en','sayd-arab-radar-september-2026','European turtle dove'),('fr','radar-arabe-sayd-septembre-2026','tourterelle des bois')]:
    for path in [f'content/{lang}/{slug}.md', f'docs/{lang}/posts/{slug}/index.html']:
        text = read(path)
        assert species in text and '<strong>50</strong>' in text, path
        assert '50 hunters' not in text and '50 chasseurs' not in text, path
for lang, daily, continuous in [('en','752 kilometres in a day','719 kilometres in 13 hours'),('fr','752 kilomètres en une journée','719 kilomètres en 13 heures')]:
    slug = 'turtle-dove-gps-eastern-flyway-nile-red-sea'
    for path in [f'content/{lang}/{slug}.md', f'docs/{lang}/posts/{slug}/index.html']:
        text = read(path)
        assert daily in text and continuous in text, path
assert 'European turtle dove' in correct_jordan_copy('excluding the European turtle dove (Streptopelia turtur), known locally as al-hamam al-raqti, according to Jordanian reporting of the RSCN announcement on 17 September')
assert 'tourterelle des bois' in correct_jordan_copy('(tourterelle des bois exclue)')
for lang in ['en', 'fr']:
    assert '>Saudi Press Agency (SPA)</a>' in read(f'docs/{lang}/posts/where-migratory-birds-rest-mashreq-arabian-peninsula/index.html')
assert "'Saudi Press Agency (SPA)' if i==3" in read('scripts/publish_migration_refuges.py')
print('PASS: radar aggregate, Jordan species, GPS daily/continuous distinction and localized SPA attribution.')
