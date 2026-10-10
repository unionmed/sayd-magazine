# Read-only search pilot

The pilot is intentionally limited to 180 image records. It does not modify the website, GitHub images, or the ChatGPT image bank.

Examples (from repository root):

```bash
python audit/image-catalog/search_pilot.py "صقر"
python audit/image-catalog/search_pilot.py "صيد" --section "الصيد" --limit 10
python audit/image-catalog/search_pilot.py "duck"
```

Search covers filenames, paths and candidate section names only. It does **not** identify image contents visually, detect species, or verify photographers, event dates, copyright or provenance.

The result field `unverified_visual: true` means all returned items require editorial visual review. A zero-result search does not mean no relevant photo exists among the other ~10,000 images.

This file is in `audit/` and is not part of the published `docs/` GitHub Pages root.
