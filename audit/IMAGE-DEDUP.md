# Image dedupe + species match — Batch 1 (2026-09-19)

Nayef rules applied: **one file per story**, and **bird photo must match the species name**. If unsure → **omit** the card (homepage / featured / related) or omit the body image. Never leave a green «صيد» `placeholder-thumb`. No thematic stand-in of the wrong species.

## العُوَيْسِق / AP4I0032 (Mars QA)

| | Before | After |
|--|--------|--------|
| Homepage card | `media/uploads/2025/09/AP4I0032-1024x683.jpg` | `media/uploads/2026/09/accipiter-nisus-eurasian-sparrowhawk.jpg` |
| Article lead | same AP4I0032 kestrel | same sparrowhawk path |
| Body extras | `3ouwayssek.jpg`, `AP4I0135`, `AP4I0504` (AI-bird **copies** of `Bird-02.jpeg`) | omitted (no body placeholders) |

**Visual check of AP4I0032:** male *Falco* kestrel (grey head, rufous back, yellow cere) — **not** a Palestinian sunbird, **not** *Accipiter nisus*. Same bytes as `AP4I9156-Enhanced-NR-1024x683.jpg` (the sunbird article’s old featured file).

**Nayef definition (this batch):** العُوَيْسِق = Eurasian sparrowhawk / *Accipiter nisus*.  
Note for Mars: the article English line still says “Lesser Kestrel”. Image follows Nayef’s sparrowhawk definition.

**Replacement source (open license):**

- File: `docs/media/uploads/2026/09/accipiter-nisus-eurasian-sparrowhawk.jpg`
- Species: *Accipiter nisus* (male), Castelletto Merli, Italy
- Commons: [Eurasian Sparrowhawk male - Castelletto Merli - Italy FJ0A2446 (30806289108).jpg](https://commons.wikimedia.org/wiki/File:Eurasian_Sparrowhawk_male_-_Castelletto_Merli_-_Italy_FJ0A2446_(30806289108).jpg)
- Author: Francesco Veronesi
- License: CC BY-SA 2.0
- Original Flickr: https://www.flickr.com/photos/francesco_veronesi/30806289108/

## Other open-license bird fills (title ↔ species)

| Slug | Title | Path | Why it matches | Source |
|------|-------|------|----------------|--------|
| `قتل-عقاب-نادر-اصطاد-أفعى-في-شمال-لبنان` | عقاب صرارة / Short-toed snake eagle | `uploads/2017/02/عقاب-صرارة.jpg` | Article names *Circaetus gallicus* | Zeynel Cebeci, [Yılan kartalı 01-1](https://commons.wikimedia.org/wiki/File:Circaetus_gallicus_-_Yılan_kartalı_01-1.jpg), CC BY-SA 4.0 |
| `الصياد-لا-يقنص-وروار-أزرق-الخد` | وروار أزرق الخد / *Merops persicus* | `uploads/2015/05/وروار-خد-أزرق.jpg` | Title + body = Blue-cheeked bee-eater | Charles J. Sharp, [Zimbabwe](https://commons.wikimedia.org/wiki/File:Blue-cheeked_bee-eater_(Merops_persicus_persicus)_Zimbabwe.jpg), CC BY-SA 4.0 |
| `عصفور-الشمس-الفلسطيني` | Palestine Sunbird | `uploads/2026/09/cinnyris-osea-palestine-sunbird.jpg` | Iridescent sunbird, decurved bill — not the kestrel copy | Mohammed Badarin, [Palestine_Sunbird.jpg](https://commons.wikimedia.org/wiki/File:Palestine_Sunbird.jpg), CC BY 2.0 |
| `طائر-الوروار-الأوروبي` | European Bee-eater | `uploads/2025/09/AP4I0956-1024x683.jpg` | Photo is two *Merops apiaster* (Fouad Itani) | Already local, visually verified |
| `بومة-المخازن` | Barn Owl | `uploads/2025/09/AP4I6377-1024x683.jpg` | *Tyto alba* | Already local, visually verified |
| `الشهرمان-الشائع` | Common Shelduck | `uploads/2025/07/IMG_3009-2-1024x683.jpg` | *Tadorna tadorna* | Already local, visually verified |
| `لا-تصدق-وجود-هذا-الطائر` | AI-designed bird | `uploads/2024/06/Bird-02.jpeg` | Article is about an AI bird; this **is** that file | WXR featured |
| `اللي-ما-يعرف-الصقر-يشويه` | الكرك / Common Crane | `uploads/2026/09/grus-grus-common-crane.jpg` | Title is a proverb; **body is Hula cranes (*Grus grus*)** | Charles J. Sharp, CC BY-SA 4.0 |

Copies of `Bird-02.jpeg` (AI bird) were **not** used as stand-ins for any other species.

## Homepage cards — before → after

| Slug | Title (short) | Before | After | Why |
|------|---------------|--------|-------|-----|
| كابس-ومكشب-… | كابس / مكشب | `kaps-makshab-apu-fries-hero.jpg` | **unchanged** | Mars-owned; APU field photo |
| 80-ألف-زائر-… | سهيل 80 ألف | `hero-closing-80k.jpg` | **unchanged** | Suhail closer |
| السعودية-تطلق-… | موسم السعودية | `ncw-wildlife-card.jpg` | **unchanged** | Unique NCW desert card |
| من-ذاكرة-صيد-… | ذاكرة صيد | `ريتا-الشعار6.jpg` (Rita’s photo) | **GAP** | Shared Rita file; no unique Memory original |
| صيد-تعود-… | صيد تعود | `sayd-returns-adonis-editor.jpg` | **unchanged** | Mars-owned |
| بالفيديو-مقناص-… | بابطين | placeholder | `babtain-maqnas-afghanistan-yt.jpg` | YouTube thumb for that video |
| لا-تصدق-وجود-هذا-الطائر | AI bird | `Bird-02.jpeg` | **unchanged** | Correct featured |
| من-هم-الصيادين-المسوؤلين | تكريم | `تكريم-صيادين.jpg` | **unchanged** | Unique, matches |
| كرواتي-يطلب-من-عون | Klepetan | `كمال-اغا-1.jpg` (other story) | **GAP** | Wrong person’s photo |
| قتل-عقاب-نادر | عقاب صرارة | `Bird-02.jpeg` (AI bird) | `عقاب-صرارة.jpg` | Open *Circaetus gallicus* |
| بالصور-والفيديو-صياد-مسؤول | إنقاذ لقلق | `كمال-اغا-1.jpg` | **unchanged** | WXR featured for this slug |
| صور-بعدسة-الآنسة-نور | نور | `سلهب-3.jpg` | **GAP** | Shared Elias Salhab file; `نور-8.jpg` was a copy |
| صور-الصياد-اللبناني-الياس-سلهب | سلهب | `سلهب-3.jpg` | **unchanged** | Correct featured |
| صور-من-رحلات-…أحمد-زهير | زهير | `سلهب-3.jpg` | **GAP** | Shared; `51.jpg` was a copy |
| صور-للصياد-…ربيع-ع | ربيع عقل | `سلهب-3.jpg` | **GAP** | Shared |
| بعدسة-التاريخ-…أبلح | أبلح | `عائلتان-…التايتانيك.jpg` | **unchanged** | Unique, matches |
| صور-بعدسة-محمد-حلّال | حلال | `سلهب-3.jpg` | **GAP** | Shared |
| مع-بدء-هجرة-الخريف | هجرة الخريف | `AP4I0956` (European bee-eater) | **GAP** | Wrong species for a news card |
| تنظيم-الصيد-يحمي | تنظيم الصيد | `Adonis.jpg` | **unchanged** | Adonis speaking; matches |
| الشهرمان-الشائع | شهرمان | `IMG_3009-2-1024x683.jpg` | **unchanged** | Shelduck verified |
| المنصة-الرائدة | منصة صيد | `Jocy-229x300.jpeg` | **unchanged** | WXR featured |
| اللي-ما-يعرف-الصقر-يشويه | الصقر | `Design.png` (world-map art) | **GAP** | Not a falcon; `Kark1-1.jpeg` missing |
| ما-هي-مناطق-الصيد-المسؤول | مناطق | `maher-Copy.jpg` | **unchanged** | Unique |
| المعرض-الدولي-للصيد-…أبو-ظ | أبوظبي | `معرض-الصيد-والفروسية.jpg` | **unchanged** | Unique |
| الصياد-لا-يقنص-وروار-أزرق-الخد | وروار أزرق الخد | `AP4I0032` (kestrel) | `وروار-خد-أزرق.jpg` | Open *Merops persicus* |
| لماذا-ترغب-المرأة-…رماي | رماية نساء | `سينتيا.jpg` | **GAP** | Shared Cynthia file |
| سيرة-رامي-اللبناني-رالف | رالف | `سينتيا.jpg` | **GAP** | Shared |
| تعرّف-على-فوائد-الرماية | فوائد | `سينتيا.jpg` | **GAP** | Shared |
| هذا-ما-علمتني-أيّاه-الرماية | سينتيا | `سينتيا.jpg` | **unchanged** | WXR featured for this slug |
| البنادق-الهوائية | بنادق هوائية | `بارودة.png` | **unchanged** | WXR featured |
| بعد-غلاء-الاسعار-…خرطوش | غلاء خرطوش | `خرطوش-المناسب.jpg` (other article) | **GAP** | Shared cartridge file |
| تعرّف-على-شخصيّتك | شخصية السلاح | `تعرف-على-شخصيتك.jpg` | **unchanged** | Unique |
| خرطوش-الصيد-لكل-طريدة | خرطوش | `خرطوش-المناسب.jpg` | **unchanged** | Correct featured |
| رئيس-نادي-xdc-سليم | سليم مجاعص | `salim-5.jpg` | **unchanged** | Unique |
| المغامرة-الأردنية-دينا | دينا | `دينا-4.jpg` | **unchanged** | Unique |
| عبدالله-بني-سعيد | عبدالله | `دينا-4.jpg` | **GAP** | Dina’s photo, wrong story |
| رولا-ايمانويل | رولا | `رولا-1.jpg` | **unchanged** | Unique |
| الصيد-بين-الفوضى-…-3 | مغترب 3 | `Design.png` | **GAP** | Shared series graphic; hunter binaries were copies |
| الصيد-بين-الفوضى-…-2 | مغترب 2 | `Design.png` | **GAP** | Shared |
| الصيد-بين-الفوضى-والنظام-تجارب-الصي | مغترب 1 | `Design.png` | **unchanged** | Series graphic; one slug only |
| الصيادة-ريتا-حبيب-الشعار | ريتا | `ريتا-الشعار6.jpg` | **unchanged** | Correct featured |
| العُوَيْسِق | عويسق | `AP4I0032` kestrel | sparrowhawk open file | Nayef = *Accipiter nisus* |
| طائر-الوروار-الأوروبي | وروار أوروبي | `AP4I0956` | **unchanged** | Verified *Merops apiaster* |
| بومة-المخازن | بومة | `AP4I6377` | **unchanged** | Verified barn owl |

Latest-feed is text-only (no thumbs) — no shared src there.

## Nayef display rule (same PR)

Green «صيد» `placeholder-thumb` is gone from **homepage cards, article featured, related «ذات صلة», and article bodies**. Mars is stripping body placeholders — we omit them, never reinsert.

| Surface | Rule |
|---------|------|
| Homepage card | Unique matching image, or **remove the card** |
| Article featured | Unique matching image, or **omit the featured block** |
| Related card | Unique matching image for that related story, or **remove the card** |
| Article body | Real local image, or **omit** (no green square) |
| Listing row | Unique matching thumb, or text row without a thumb |

## Homepage cards — this pass

| Slug | After | Why |
|------|-------|-----|
| كرواتي-يطلب-من-عون-…klepetan | `uploads/2017/04/رسالة-من-كرواتي-الى-ميشال-عون.jpg` | Unique letter photo (WP featured) |
| اللي-ما-يعرف-الصقر-يشويه | `uploads/2026/09/grus-grus-common-crane.jpg` | Body is about **الكرك / Grus grus**, not a falcon. Charles J. Sharp, [Common Crane (Grus grus) 2](https://commons.wikimedia.org/wiki/File:Common_Crane_(Grus_grus)_2.jpg), CC BY-SA 4.0 |
| بعد-غلاء-الاسعار-… | `uploads/2015/03/خرطوش-صيد.jpg` | Unique cartridge still (not the shared `خرطوش-المناسب` copy) |
| من-ذاكرة-صيد-… | **card removed** | Only unused unique hero would be Rita’s photo — already assigned to Rita |
| صور نور / زهير / ربيع / حلال | **cards removed** | Featured files were `سلهب-3` copies; Wayback 0im_ had no distinct original |
| مع-بدء-هجرة-الخريف | **card removed** | `1000468655.jpg` is a bee-eater stand-in; no unique original |
| رماية نساء / رالف / فوائد | **cards removed** | Featured files were `سينتيا.jpg` copies |
| عبدالله-بني-سعيد | **card removed** | `16.jpg` not archived |
| الفوضى 2 / 3 | **cards removed** | Series graphic already used by part 1; hunter JPEGs not archived |

## Related-card fills (species / topic match)

| Slug | Path | Why |
|------|------|-----|
| أسرار-الأرض-عشبة-الزوفا | `uploads/2025/09/hg.th--1024x576.jpg` | WP featured recovered (زوفا) |
| أنا-الصيّاد-أعرف-عشبة-الخبيزة | `uploads/2024/09/الخبيزة-00.jpeg` | WP featured recovered |
| أسرار-الأرض-عشبة-الشُكران | `uploads/2025/09/الشكران.jpg` | WP featured recovered |
| الصيّاد-يعرف-شجرة-اللزاب | `uploads/2024/02/اللزاب.jpg` | WP featured recovered |
| الأخطبوط-… | `uploads/2026/09/octopus-vulgaris.jpg` | Title names الأخطبوط; Commons *Octopus vulgaris* |
| لين-عراجي-بطلة-فروسية | `uploads/2022/10/لين-2.jpg` | WP featured recovered |
| الصيّادة-السورية-أماني | `uploads/2022/08/اماني-الحمصي-2.jpg` | WP featured recovered |
| جورج-تازة-… | `uploads/2022/11/طازة-3.jpg` | WP featured recovered |
| كيف-تحمي-كلبك-… | `uploads/2024/08/dog.jpg` | WP featured recovered |
| مشاكل-جلد-الكلاب | `uploads/2023/04/جلد-الكلب.png` | WP featured recovered |

Related cards that still had no unique matching file were **deleted**, not left as green squares. Shared stand-in thumbs (e.g. `saudi-hunting-season-2026.jpg` = `بارودة.png`) were treated as missing and the card removed.

## Counts

| | |
|--|--:|
| Duplicate homepage cases found | 12 |
| Fixed (unique matching file or open-license species fill) | 13 |
| Homepage cards omitted (no unique original) | 12 |
| Related cards remaining (all real unique thumbs) | 1152 |
| Green «صيد» placeholders left sitewide | **0** |
| Still blocked pending original fetch | see MEDIA-RECOVERY next-batch |

## Next-batch (remaining 2022–2026 + homepage gaps)

Fetch **real** originals (Wayback), not stand-in copies, for:

- Gallery featured: `نور-8.jpg`, `51.jpg`, `ربيع-عقل-7.jpg`, `محمد-حلال-4.jpg`
- `رسالة-من-كرواتي-الى-ميشال-عون.jpg`, `Kark1-1.jpeg`, `رالف-2.jpg`, `فوائد-الرماية.jpg`, `رامية.jpg`, `خرطوش-صيد.jpg`, `16.jpg`
- Memory of Sayd unique hero
- 2026 originals still stand-in copies: `1000468655.jpg`, `duck-aswan-960.jpg`, `saudi-hunting-season-2026.jpg`, CABS/MECSHAP logos, Suhail organizer portraits
- Body galleries 2022–2025 still missing (~160 names)

---

## Batch 2 — bird / logo fills for Mars QA (do not mark done)

These are **new** assignments. Species matches the caption/title. They are **not** the missing WP camera originals.

| Slug / surface | File | Species / mark | Why | Credit | Mars action |
|----------------|------|----------------|-----|--------|-------------|
| `مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو` body + homepage card | `narta-egret.jpg` | *Egretta garzetta* (Little Egret) | Replaced AP4I0956 bee-eater stand-in. Caption already named this Commons file. | Pasztilla (Attila Terbócs), [Narta Lagoon, Albania – Little egret](https://commons.wikimedia.org/wiki/File:Narta_Lagoon,_Albania_%E2%80%93_Little_egret.jpg), CC BY-SA 4.0 | Confirm it is an egret (not a flamingo; article is about Narta flamingo protests — image is the site ID already in the caption) |
| same article body + homepage thumb | `duck-aswan-960.jpg` | *Aythya nyroca* (Ferruginous Duck / البط الحديدي) | Title/body name البط الحديدي. Replaced bee-eater stand-in. | terolinjama / iNaturalist, [Ferruginous Duck, Aswan](https://commons.wikimedia.org/wiki/File:Ferruginous_Duck,_Aswan.jpg), CC0 | Confirm ferruginous duck (chestnut, white undertail) |
| `البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك` | `pelecanus-onocrotalus-great-white-pelican.jpg` | *Pelecanus onocrotalus* | **Not** Nayef Kareem’s 2026 Matn flight photo. Caption says so. | Wikimedia Commons Great White Pelican | Replace with Nayef original when available; do not credit نايف on this file |
| Kaps/Makshab partner row | `cabs-official-logo.png` + `cabs-bird-guard-logo.jpg` + `mecshap-official-logo.png` | CABS + MECSHAP official marks | WP 2026 logo binaries were never archived | komitee.de + mecshap.org | Confirm these are the marks Sayd wants next to APU fries |

**Not assigned (honest omit):** `1000468655.jpg`, ChatGPT flyway PNG, gallery portraits (`نور-8` …), shooting portraits, Suhail organizer faces, Memory hero.
