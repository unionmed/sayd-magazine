# Bee-eater profile and contextual reading paths

## Scope

Correct the existing Arabic and English European bee-eater profile and provide its complete French mirror, required by the unchanged publication gate for edited stories. Preserve the original 17 September 2025 publication date, photo, slug, category, homepage placement and shared tickers. Record the editorial update separately as 12 October 2026. Add the French item at the older end of its existing archive/category listings.

The three BirdLife photo captions now link to the corresponding profile. Two short next-reading links lead from the profile to existing BirdLife and migratory-resting-place articles in the same language. No new hub, homepage promotion, social publication or commercial content.

## Evidence and editorial decisions

- Farinós-Celdrán et al. (2016), *Consumption of honey bees by Merops apiaster … in Mediterranean semiarid landscapes: a threat to beekeeping?* DOI: https://doi.org/10.1080/00218839.2016.1195630 . Author institution record: https://portalinvestigacion.um.es/documentos/63b0d7390f8bcd1826cfbc2d . The abstract reports spatial and seasonal variation in honey-bee consumption in Murcia. It does not substantiate selective predation on weak individuals strengthening hives. Remove the universal benefit and universally-small-diet-share claims. Publisher full-text access was unavailable; no claim to full-text review.
- Galeotti and Inglisa (2001), study in five Sardinian areas: https://iris.unipv.it/handle/11571/8675 . This is contextual evidence about predation pressure, not evidence of healthier colonies.
- White, Bartholomew and Kinney (1978), *Physiological and Ecological Correlates of Tunnel Nesting in the European Bee-Eater*, https://doi.org/10.1086/physzool.51.2.30157862 . The abstract describes nest chambers and absence of nest sanitation. Remove the unsupported separate waste chamber/clean nest claim; retain only tunnel ending in nesting chamber.
- Visually inspected the actual existing AP4I0956-1024x683.jpg: two European bee-eaters on a thorny branch, one spreading its wings. Alt text describes that scene in all three languages without inventing place/date. Existing photo and visible Fouad Itani watermark retained; no new image or rights claim.
- Retain the original Lebanon summer-observation/breeding-possibility qualification, without turning it into a confirmed nesting record. Remove the English-only blanket description of harm to bees as a false claim.

## Reproduction and checks

Reviewed content source: `content/features/bee-eater-reader-paths.json`. The Arabic/English editorial drafts are aligned. Apply the narrowly scoped overlay after legacy WXR/edition generation:

```
python scripts/update_bee_eater_reader_paths.py
python scripts/test_bee_eater_reader_paths.py
```

The overlay updates only this profile, the three contextual BirdLife captions, the French archive/category entry, and affected sitemap entries. It does not run general regeneration or modify the publication checks, ticker sources, homepage sources, CSS or distribution rules.

Run the unchanged publication contract against the branch base and the existing homepage, shared ticker, SEO, hreflang, archive access/media, French-listing, article-navigation and GA4 checks. A passing automated check does not substitute for independent Arabic/English/French editorial and visual review before merge.
