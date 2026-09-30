# Archive media repair replacing PR #97

Base: `bf1c4dbd81b2231832ca291b84908c6de148898e` (30 September 2026).

PR #97's HTML was not copied or rebased. Its restoration logic was carried forward onto current main and restricted to existing pre-2026 articles. The command `python scripts/archive_access.py --rewire-2020` restores 347 image tags in 97 historic Arabic articles from existing local uploads; a second run changes zero pages. Existing text, metadata, navigation, related cards, homepage, design and French fixes are preserved. Empty legacy alt attributes get a contextual archive label, not an invented description of the scene.

Two 2026 stories are handled separately in all three languages:

- `protecting-autumn-migratory-birds-lebanon-khatib-2017`: retain the existing lead and outdoor photograph; mirror the three approved official partner logos from current Arabic main into English and French. The two legacy logo files in #97 are superseded, and are deliberately not reintroduced alongside the newer logos.
- `autumn-migration-field-action-protect-flyways-lebanon`: restore the local photograph in Arabic, English and French before the text. Visual inspection showed two birds on a branch, not the map described by the old alt. Correct the localized alt and credit the visible photographer watermark, Fouad Itani.

The English generator and French segment data/renderer preserve these changes on regeneration; the Arabic content intermediate is aligned. The retired WXR importer was not run. No translation expansion of the historic archive is authorized or included.

## Enforcement

Changed filenames are obtained with Git's NUL separator, so Arabic paths cannot silently evade the story checks. A historical exception permits only existing pre-2026 Arabic pages with additive, accessible local upload images: exterior HTML, visible text and non-image markup must be unchanged; existing image tags and their text positions must remain intact. New files, editorial edits, current stories, removed images, missing/remote media and empty alt do not qualify and still require full publication validation. No design fingerprints or publication contract data were relaxed.

## Validation

- Publication contract against the exact base: PASS, including all changed Arabic paths.
- Homepage door/idempotence tests: PASS.
- Archive access tests and targeted media rewrite tests: PASS.
- New enforcement/generator regression tests: PASS, including quotePath true/false, text and metadata changes, new files, remote media, missing alt, and current-story rejection.
- All newly referenced image files decode successfully and are served locally as HTTP 200 image responses. All 103 changed article pages are served locally with HTTP 200.
- Archive restoration is idempotent; current EN generator retains the selected media, and both FR source segment topologies match their English source.
- Existing comprehensive `test_media_rewrite.py` fails on unchanged main as well as this branch because it requires every homepage image to be local and main currently uses `https://s1.wklcdn.com/image_253/7607894/173365487/108207649Master.jpg`. Its assertion was not removed or weakened.

## Remaining missing assets

No replacement or broken tag is fabricated for these absent files:

- `uploads/2022/11/هاني-cover.jpg`
- `uploads/2024/02/سارة-3.jpg`
- `uploads/2026/09/الدكتور-خالد-بن-إبراهيم-السليطي-—-صورة-تعريفية.jpg`
- `uploads/2026/09/مدير-معرض-سهيل-—-لقاء-تلفزيوني.jpg`
- `uploads/2026/09/ملكة-محمد-آل-شريم-—-لقاء-في-معرض-سهيل.jpg`

The archive-only command reports the first two; this does not mean the other three have been recovered. A sitewide production search/404 audit is outside this patch. This branch is review-only: no merge, main update or deployment.
