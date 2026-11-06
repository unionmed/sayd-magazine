"""One Saluki publication retires its superseded homepage card, not its archive.

Implements the existing same-event supersession rule. No schema field, general
exclusion API, publication approval, or historical-content edit is introduced.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import html
from publication_schema import require

RELEASE = 'arabian-saluki-championship-20261106'
SLUGS = {
    'ar': 'بطولة-السلوقي-العربي-العين-الظفرة-2026-2027',
    'en': 'arabian-saluki-championship-al-ain-al-dhafra-2026-2027',
    'fr': 'championnat-saluki-arabe-al-ain-al-dhafra-2026-2027',
}
OLD_AR = 'بطولة-السلوقي-العربي-نوفمبر-2026-أبريل-2027'
OLD_EN = 'arabian-saluki-championship-november-2026-april-2027'
OLD_FILES = {
    'content/features/approved-three-20261020.json': 'b9922a74e30bbc3262cd97e5f4459951d913ed25b9643bc1bf4173fedef52b42',
    f'docs/posts/{OLD_AR}/index.html': 'e7594d81a271ce26e022f5dcd23b76c9c5608adf903624fba82f7f01fadf863f',
    f'docs/en/posts/{OLD_EN}/index.html': '439aa88d788edd14cf7c5d630c2d409853385e09862a819b4c6c56ce8efb136f',
    f'docs/fr/posts/{OLD_EN}/index.html': '3b65ec43aaeb15ea2bbb0f301d42ab3a70780d505dc68763e1a150300e70251e',
}


def apply(stage, records, home, allow_distribution):
    """Validate before the sole mutation; ordinary publications remain unchanged."""
    matches = [record for record in records if record['id'] == RELEASE]
    if not matches:
        return False
    require(len(records) == 1 and len(matches[0]['articles']) == 1,
            'Saluki supersession requires its single exact publication')
    article = matches[0]['articles'][0]
    require(article['slugs'] == SLUGS and article['published'] == '2026-11-06'
            and article['primary_door'] == 'hunting' and article['archives'] == ['hunting']
            and article['kind'] == 'article' and 'format' not in article,
            'Saluki supersession publication identity changed')
    require(allow_distribution is True
            and article['distribution'] == {'placement': 'door', 'ticker': False},
            'Saluki supersession requires Hunting-only distribution review')
    stage = Path(stage)
    for relative, expected in OLD_FILES.items():
        path = stage / relative
        require(path.is_file() and not path.is_symlink(),
                'Missing regular Saluki predecessor: ' + relative)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                'Saluki predecessor source/page changed: ' + relative)
    pairs = json.loads((stage / 'content/en/pairs.json').read_text())['pairs']
    require(pairs.get(OLD_AR) == OLD_EN and home['primary_door'].get(OLD_AR) == 'hunting',
            'Saluki predecessor mapping/category changed')
    upper = set(home['featured'] + home['latest'] + home['ticker_slugs'])
    upper.update(entry['slug'] for entry in home['ticker_entries'])
    upper.update([home['ia_slots']['main'], *home['ia_slots']['important'], *home['ia_slots']['latest']])
    require(OLD_AR not in upper, 'Saluki supersession cannot change upper slots/ticker')
    for prefix, slug in (('', OLD_AR), ('en/', OLD_EN), ('fr/', OLD_EN)):
        for listing in ('category/صيد', 'stories' if prefix else 'articles'):
            path = stage / f'docs/{prefix}{listing}/index.html'
            require(path.is_file() and not path.is_symlink(), 'Missing Saluki archive')
            cards = html.fromstring(path.read_bytes()).xpath('//article')
            matches = [card for card in cards if any(
                '/posts/' + slug + '/' in unquote(urlsplit(href).path)
                for href in card.xpath('.//a/@href'))]
            require(len(matches) == 1, 'Saluki predecessor must remain in each archive')
    # The existing selector refreshes all three Hunting sections at capacity.
    # Do not modify dates, routes, archives, upper placements, or other exclusions.
    if OLD_AR not in home['omit_from_home_desks']:
        home['omit_from_home_desks'].append(OLD_AR)
    return True
