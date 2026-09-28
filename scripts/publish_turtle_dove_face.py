#!/usr/bin/env python3
"""Publish the bilingual FACE turtle-dove story with a Commons image."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
AR = "اليمام-يعبر-حدود-الصيد-مسار-أوروبي-يتعافى"
EN = "turtle-doves-cross-hunting-borders-european-flyways"
IMAGE = "european-turtle-dove-algeria-mourad-harzallah.jpg"
IMG = "media/uploads/2026/09/" + IMAGE
AT = "https://commons.wikimedia.org/wiki/File:European_turtle-dove_(Streptopelia_turtur)_in_Algeria.jpg"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
AR_TITLE = "اليمام يعبر حدود الصيد: مسار أوروبي يتعافى وآخر لا يزال تحت الضغط"
EN_TITLE = "Turtle Doves Cross Hunting Borders: One European Flyway Recovers, Another Remains Under Pressure"
AR_LEAD = "خفضت دول أوروبية صيد اليمام بنحو 90% على مساري هجرته الرئيسيين. لكن أعداد الطائر سلكت اتجاهين مختلفين: ارتفاع في الغرب، وتراجع مستمر مع بوادر استقرار في الوسط والشرق. فماذا تقول هذه الفجوة عن إدارة طائر لا تتوقف رحلته عند حدود دولة واحدة؟"
EN_LEAD = "European countries have cut Turtle Dove hunting by about 90% across the two main flyways they manage. Yet the bird's breeding population has followed different paths: growth in the west, and a continued decline with signs of stabilisation in the central and eastern flyway. What does that divergence tell us about managing a bird whose journey crosses borders?"
AR_TEXT = [
    "في تقرير أصدره الاتحاد الأوروبي للصيد والمحافظة على الطبيعة «FACE» في تموز 2026، ظهرت صورة متباينة لليمام الأوروبي (Streptopelia turtur). على مسار الهجرة الغربي، واصلت أعداد الطيور المتكاثرة في أوروبا ارتفاعها، وبلغ مؤشرها في ربيع 2025 أعلى مستوى له منذ عام 2009. أما على المسار الأوسط والشرقي، فما زال الاتجاه العام هابطًا، وإن بدا المؤشر أقرب إلى الاستقرار منذ عام 2021.",
    "المفارقة أن صيد اليمام انخفض بنحو 90% على كلا المسارين، قياسًا إلى المستويات المرجعية المستخدمة في برنامج إدارته. وفي عام 2025، أعادت دول على المسار الغربي فتح الصيد بحصص محدودة بعد وقف دام أربع سنوات، فيما بقيت الحصص على المسار الأوسط والشرقي منخفضة. وتستخدم الدول المعنية تسجيلًا إلزاميًا لما يصطاده الصيادون، مع وسائل رقمية لمتابعة الحصص في عدد منها.",
    "يرى معدّو تقرير FACE أن استمرار التراجع في الوسط والشرق، رغم الخفض الكبير للصيد، يفرض دراسة عوامل إضافية، ولا سيما حالة الموائل التي يحتاج إليها اليمام للتكاثر والتغذية. ولا تعني هذه النتيجة أن الصيد بلا تأثير؛ بل إن خفضه وحده لم يكن كافيًا حتى الآن لإظهار تعافٍ مماثل للتعافي المسجّل غربًا.",
    "## وأين تدخل البلدان العربية في القصة؟",
    "هجرة اليمام أوسع من نطاق التقرير الأوروبي. فالمسار الغربي يعبر شبه الجزيرة الإيبيرية والمغرب وموريتانيا نحو أفريقيا، فيما تمر طرق أخرى عبر إيطاليا ومالطا وتونس، أو عبر اليونان ومصر وبلدان المشرق، ومنها لبنان. ولهذا فإن ما يحدث في مناطق التكاثر الأوروبية، ومحطات العبور، ومناطق الشتاء الأفريقية، يدخل في قصة الطائر نفسه.",
    "أما بالنسبة إلى الصياد العربي، فتكمن أهمية التقرير في الإشارة إلى ضرورة معرفة كم يمامًا يمرّ في كل موسم، وكم يُصاد منه، وما الذي يتغير في الأراضي الزراعية وأماكن استراحته. التجربة الأوروبية تُظهر قيمة العدّ المنتظم، والحصص القابلة للمتابعة، وقياس أثر القرارات سنة بعد سنة. أما الإجابة عن وضع اليمام في بلداننا فتحتاج بيانات محلية وتعاونًا بين البلدان التي يعبرها.",
]
EN_TEXT = [
    "A July 2026 report from the European Federation for Hunting and Conservation (FACE) paints a mixed picture for the European Turtle Dove (Streptopelia turtur). The population breeding on the western flyway has continued to increase: its spring 2025 index was the highest since 2009. On the central and eastern flyway, the long-term trend is still downward, though the index has shown signs of stabilising since 2021.",
    "Hunting has fallen by about 90% on both flyways compared with the respective baselines used by the management programme. In 2025, western flyway countries reopened hunting under small quotas after a four-year moratorium; quotas on the central and eastern flyway remained low. Countries require hunters to report their take, with several using digital systems to track quotas.",
    "FACE argues that the continuing decline in the central and eastern flyway, despite the large reduction in hunting, warrants closer study of other pressures, especially the habitats Turtle Doves need to breed and feed. This finding does not mean hunting has no effect. It means reducing it alone has not yet produced a recovery comparable to the one observed in the west.",
    "## Where do Arab countries enter the story?",
    "The bird's migration extends beyond the European scope of the FACE report. The western route crosses the Iberian Peninsula, Morocco and Mauritania towards Africa. Other routes pass through Italy, Malta and Tunisia, or through Greece, Egypt and the Levant, including Lebanon. Breeding grounds in Europe, stopover sites and wintering grounds in Africa are therefore parts of the same story.",
    "For Arab hunters, the report points to a practical question: how many Turtle Doves pass through each season, how many are hunted, and what is changing in farmland and resting habitats? The European experience demonstrates the value of regular counts, trackable quotas and measuring the results of management decisions year by year. Assessing the species in our countries requires local data and cooperation among the countries on its routes.",
]

def body(lang):
    is_ar = lang == "ar"
    prefix = "../../" if is_ar else "../../../"
    caption = ("يمام أوروبي في الجزائر" if is_ar else "European Turtle Dove in Algeria")
    credit = ("تصوير" if is_ar else "Photo")
    lead, paragraphs = (AR_LEAD, AR_TEXT) if is_ar else (EN_LEAD, EN_TEXT)
    chunks = [f'<p><strong>{html.escape(lead)}</strong></p>',
              f'<figure><img src="{prefix}{IMG}" alt="{caption}" width="2048" height="1441" decoding="async" style="width:100%;height:auto"><figcaption>{caption}. {credit}: <a href="{AT}">Mourad Harzallah / Wikimedia Commons</a> · <a href="{LICENSE}">CC BY 4.0</a>.</figcaption></figure>']
    for p in paragraphs:
        chunks.append(f'<h2>{html.escape(p[3:])}</h2>' if p.startswith("## ") else f'<p>{html.escape(p)}</p>')
    if is_ar:
        chunks.append('<p class="sources">المصادر: <a href="https://www.face.eu/turtle_dove_report_2026/">تقرير FACE عن اليمام الأوروبي 2026</a>، <a href="https://migrationatlas.org/node/1648">أطلس هجرة الطيور</a>، <a href="https://www.cms.int/sites/default/files/document/cms_stc48_doc.18_annex2_rev.1_ssap-conservation-european-turtle-dove_e.pdf">خطة المحافظة الدولية على اليمام</a>.</p>')
    else:
        chunks.append('<p class="sources">Sources: <a href="https://www.face.eu/turtle_dove_report_2026/">FACE Turtle Dove Report 2026</a>; <a href="https://migrationatlas.org/node/1648">Bird Migration Atlas</a>; <a href="https://www.cms.int/sites/default/files/document/cms_stc48_doc.18_annex2_rev.1_ssap-conservation-european-turtle-dove_e.pdf">International Single Species Action Plan</a>.</p>')
    return "\n".join(chunks)

def article(lang):
    is_ar = lang == "ar"
    src = DOCS / ("posts/ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان/index.html" if is_ar else "en/posts/over-20000-m2-bird-nets-seized-lebanon/index.html")
    dest = DOCS / (f"posts/{AR}/index.html" if is_ar else f"en/posts/{EN}/index.html")
    page = src.read_text()
    old_title = "ضبط أكثر من 20 ألف م² شباك صيد في لبنان" if is_ar else "Over 20,000 m² of bird nets seized in Lebanon"
    page = page.replace(old_title, AR_TITLE if is_ar else EN_TITLE)
    page = page.replace("ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان", AR).replace("over-20000-m2-bird-nets-seized-lebanon", EN)
    page = page.replace("25 أيلول 2026", "28 أيلول 2026") if is_ar else page.replace("25 September 2026", "28 September 2026")
    page = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1)+html.escape(AR_LEAD if is_ar else EN_LEAD, quote=True), page, count=1)
    page, n = re.subn(r'(<article class="article-content">).*?(</article>)', lambda m: m.group(1)+"\n"+body(lang)+"\n    "+m.group(2), page, count=1, flags=re.S)
    assert n == 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)

def home(lang):
    is_ar = lang == "ar"
    path = DOCS / ("index.html" if is_ar else "en/index.html")
    page = path.read_text()
    slug, title = (AR, AR_TITLE) if is_ar else (EN, EN_TITLE)
    image = IMG if is_ar else "../"+IMG
    card = f'''<article class="card card-stack">
  <a class="thumb" href="posts/{slug}/index.html"><img src="{image}" alt="{'يمام أوروبي في الجزائر' if is_ar else 'European Turtle Dove in Algeria'}" loading="lazy"></a>
  <div class="body"><h3><a href="posts/{slug}/index.html">{title}</a></h3><div class="meta">{'28 أيلول 2026' if is_ar else '28 September 2026'}</div></div>
</article>
'''
    # Replace the lowest-priority side card; the lead and three other cards stay in place.
    start = page.index('<div class="feature-stack">')
    end = page.index('</div>', page.index('</article>', page.index('</article>', page.index('</article>', start)+10)+10)) if False else page.index('          </div>\n          </div>\n        </div>', start)
    stack = page[start:end]
    matches = list(re.finditer(r'<article class="card card-stack">.*?</article>', stack, re.S))
    assert len(matches) == 4
    stack = stack[:matches[-1].start()] + stack[matches[-1].end():]
    stack = stack.replace('<div class="feature-stack">', '<div class="feature-stack">\n'+card, 1)
    page = page[:start]+stack+page[end:]
    # The displaced oldest side card moves to Latest, with a strict ten-card cap.
    old_slug = ("منظمات-دولية-ابادة-بيئية-جنوب-لبنان" if is_ar else "south-lebanon-environmental-destruction-bird-flyway")
    old_title = ("دمار بيئي واسع في جنوب لبنان يهدد أحد أهم ممرات هجرة الطيور في العالم" if is_ar else "Widespread environmental destruction in southern Lebanon threatens one of the world’s key bird-migration flyways")
    old_img = ("media/uploads/2026/09/ecocide-south-lebanon-white-phosphorus-smoke.jpg" if is_ar else "../media/uploads/2026/09/ecocide-south-lebanon-white-phosphorus-smoke.jpg")
    old_date = ("20 أيلول 2026" if is_ar else "20 September 2026")
    item = f'''<li><a href="posts/{old_slug}/index.html"><span class="feed-thumb"><img src="{old_img}" alt="{html.escape(old_title,quote=True)}" loading="lazy"></span><span class="feed-text"><span class="feed-title">{old_title}</span><span class="feed-date">{old_date}</span></span></a></li>\n'''
    match = re.search(r'(<ul class="latest-feed">)(.*?)(</ul>)',page,re.S)
    assert match
    entries = re.findall(r'<li>.*?</li>',match.group(2),re.S)
    assert len(entries) <= 10
    if old_slug not in match.group(2):
        # The 20 September article follows the two 20 September cards.
        at = next((i for i,x in enumerate(entries) if "13 أيلول" in x or "13 September" in x),len(entries))
        entries.insert(at,item)
    entries = entries[:10]
    page = page[:match.start()] + match.group(1)+"\n"+"\n".join(entries)+"\n"+match.group(3)+page[match.end():]
    path.write_text(page)

def listing(path, row, marker='<div class="post-list">\n'):
    page=path.read_text()
    assert marker in page
    page=page.replace(marker,marker+row,1)
    path.write_text(page)

def main():
    assert (DOCS/IMG).is_file()
    article("ar"); article("en")
    home("ar"); home("en")
    ar_row=f'<article class="post-row"><a class="thumb" href="../../posts/{AR}/index.html"><img src="../../{IMG}" alt="يمام أوروبي في الجزائر" loading="lazy"></a><div class="body"><div class="meta">28 أيلول 2026</div><h2><a href="../../posts/{AR}/index.html">{AR_TITLE}</a></h2><p class="excerpt">{AR_LEAD}</p></div></article>\n'
    listing(DOCS/"category/صيد/index.html",ar_row)
    listing(DOCS/"articles/index.html",ar_row.replace("../../posts/","../posts/").replace("../../media/","../media/"))
    en_row=f'<article class="card overlay"><a class="thumb" href="../posts/{EN}/index.html"><img src="../../{IMG}" alt="European Turtle Dove in Algeria" loading="lazy"></a><div class="body"><div class="meta">28 September 2026</div><h3><a href="../posts/{EN}/index.html">{EN_TITLE}</a></h3></div></article>\n'
    listing(DOCS/"en/stories/index.html",en_row,'<div class="grid-4">\n')
    pairs=ROOT/"content/en/pairs.json"; data=json.loads(pairs.read_text()); data["pairs"][AR]=EN; pairs.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    cfg=ROOT/"content/homepage.json"; data=json.loads(cfg.read_text())
    for key in ("omit_from_latest","omit_from_ticker","omit_from_ticker_and_latest"):
        if AR not in data.setdefault(key,[]): data[key].append(AR)
        if EN not in data[key]: data[key].append(EN)
    data.setdefault("primary_door",{})[AR]="hunting"
    for slug in ("منظمات-دولية-ابادة-بيئية-جنوب-لبنان","south-lebanon-environmental-destruction-bird-flyway"):
        if slug in data.get("omit_from_latest",[]): data["omit_from_latest"].remove(slug)
    cfg.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    (ROOT/"content/posts"/(AR+".md")).write_text('---\ntitle: "'+AR_TITLE+'"\nslug: '+AR+'\ndate: 2026-09-28 23:45:00\nauthor: صيد\ncategories: [صيد]\nfeatured: ../../'+IMG+'\n---\n\n'+body("ar")+"\n")
    (ROOT/"content/en"/(EN+".md")).write_text('# '+EN_TITLE+'\n\n'+body("en")+"\n")
    import sys
    sys.path.insert(0,str(ROOT/"scripts"))
    from seo_foundation import apply
    apply(DOCS)
    print(AR,EN)

if __name__=="__main__": main()
