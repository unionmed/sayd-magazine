#!/usr/bin/env python3
"""Publish the paired, illustrated Lebanon hiking feature in existing site chrome."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
AR = 'بين-قمم-الأرز-دليل-الهايكينغ-والتخييم-في-لبنان'
EN = 'lebanon-hiking-and-camping-among-cedars-and-valleys'
AR_TITLE = 'بين قمم الأرز وظلال الوديان: دليل الهايكينغ والتخييم في لبنان'
EN_TITLE = 'Among Cedar Peaks and Valley Shadows: Hiking and Camping in Lebanon'
AR_DESC = 'من درب الجبل اللبناني إلى قاديشا وأرز الشوف وبالوع بلعا: مسارات وصور وإرشادات عملية للمشي والتخييم المسؤول في لبنان.'
EN_DESC = 'From the Lebanon Mountain Trail to Qadisha, the cedars and Baatara: scenic hikes and practical guidance for responsible camping in Lebanon.'
HERO = 'media/uploads/2026/09/lebanon-hiking-camping-wikiloc.jpg'
HIKING = 'https://thumb.wikimedia.org/wikipedia/commons/thumb/0/07/Trekking_in_the_Lebanon_Mountains.jpg/1280px-Trekking_in_the_Lebanon_Mountains.jpg'
CANYON = 'https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8d/A_mystical_canyon_of_Qadisha_%28Holy%29_Valley_in_northern_Lebanon.jpg/1280px-A_mystical_canyon_of_Qadisha_%28Holy%29_Valley_in_northern_Lebanon.jpg'
CEDAR = 'https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e1/Lebanon_cedar_forest.jpg/1280px-Lebanon_cedar_forest.jpg'
WATERFALL = 'https://upload.wikimedia.org/wikipedia/commons/e/e2/Baatara_waterfall%2C_Lebanon_44088.JPG'

def figure(url, alt, caption, source, author, license_url, license_name):
    return (f'<figure class="feature-photo" style="margin:26px auto;max-width:800px">'
            f'<img src="{url}" alt="{html.escape(alt, quote=True)}" loading="lazy" decoding="async" '
            f'style="display:block;width:100%;height:auto;border-radius:6px">'
            f'<figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px">'
            f'{caption} — المصدر: <a href="{source}">{"Wikiloc" if "wikiloc" in source else "Wikimedia Commons"}</a>.</figcaption></figure>')

argen = '© Vyacheslav Argenberg / <a href="http://www.vascoplanet.com/">vascoplanet.com</a>'
by = 'https://creativecommons.org/licenses/by/4.0/'
by_sa = 'https://creativecommons.org/licenses/by-sa/3.0/'
hero_src = 'https://www.wikiloc.com/hiking-trails/43kms-backpacking-sannine-bakish-faqra-kfardebien-chabrouh-hrajel-qehmez-afqa-saydet-l-habes-in-aaq-173365486'
hiking_src = 'https://commons.wikimedia.org/wiki/File:Trekking_in_the_Lebanon_Mountains.jpg'
canyon_src = 'https://commons.wikimedia.org/wiki/File:A_mystical_canyon_of_Qadisha_(Holy)_Valley_in_northern_Lebanon.jpg'
cedar_src = 'https://commons.wikimedia.org/wiki/File:Lebanon_cedar_forest.jpg'
falls_src = 'https://commons.wikimedia.org/wiki/File:Baatara_waterfall,_Lebanon_44088.JPG'

AR_BODY = f'''<p>في لبنان، يتغيّر المشهد على الطريق القصير بين الساحل والجبل: من قرية معلّقة فوق وادٍ عميق إلى غابة أرز يبرد الهواء في ظلّها. ولهذا يجد محبّ المشي الطويل ومراقبة الحياة البرية والتصوير مساحة واسعة لاكتشافها، سواء اختار نهارًا على الدرب أو ليلةً في موقع تخييم مناسب.</p>
{figure(HERO, 'خيام وأمتعة تنزّه على مرتفع بين صنّين والعاقورة', 'تخييم على مسار جبلي بين صنّين والعاقورة', hero_src, '', '', '')}
<h2>درب الجبل اللبناني: رحلة يمكن تقسيمها</h2>
<p>يمتد <a href="https://lebanontrail.org/">درب الجبل اللبناني</a> نحو 470 كيلومترًا من عندقت في الشمال إلى مرجعيون في الجنوب، عبر 27 قسمًا وأكثر من 75 بلدة وقرية. لا يحتاج الزائر إلى قطع المسار كله؛ يمكن اختيار قسم يناسب الوقت واللياقة، ثم الاستعانة بخريطة محدّثة أو مرشد محلي لمعرفة نقطة البداية والعودة ومصادر المياه.</p>
<p>ما يجعل الدرب جذّابًا ليس الارتفاع وحده. فالمسار يمرّ بمناظر زراعية وقرى وممرات جبلية، ويتيح الاقتراب من تاريخ المكان ومجتمعاته من دون اختزال الرحلة في الوصول إلى قمة.</p>
{figure(HIKING, 'متنزّهون يعبرون دربًا في جبال لبنان', 'على درب الجبل اللبناني', hiking_src, '', '', '')}
<h2>قاديشا: الوادي الذي يجمع المشهد والذاكرة</h2>
<p>في وادي قاديشا، تقف المنحدرات الصخرية فوق الأديرة والمغاور القديمة. زيارة المسارات المؤدية إلى محيط قنوبين وقزحيا تمنح المشّاء مشاهد مختلفة بحسب الضوء والفصل؛ لكن بعض النزلات صعبة، لذا ينبغي اختيار طريق واضح يناسب المجموعة وتجنّب الاقتراب من الحواف.</p>
{figure(CANYON, 'المنحدرات الحادة في وادي قاديشا شمال لبنان', 'جدران وادي قاديشا الصخرية', canyon_src, argen, by, 'CC BY 4.0')}
<h2>بين الأرز والشلالات</h2>
<p>تفتح غابات أرز الشوف وتنورين وإهدن وبنتاعل أبوابًا للمشي ومراقبة الطيور والنباتات والتصوير. ولكل محمية مداخل ومسارات وتعليمات تختلف عن الأخرى؛ اسأل إدارتها عن المسار المفتوح وحالة الطقس قبل الذهاب. وفي منطقة تنورين، يضيف بالوع بلعا، المعروف أيضًا بشلال باتارا، مشهدًا جيولوجيًا لافتًا. ظهور الشلال وتدفّقه يرتبطان بالموسم والأمطار، وتحتاج الحواف المبللة والمنحدرات إلى حذر خاص.</p>
{figure(WATERFALL, 'شلال بالوع بلعا في منطقة تنورين', 'بالوع بلعا في تنورين؛ يختلف تدفّق الماء باختلاف الموسم', falls_src, 'Lodo27', by_sa, 'CC BY-SA 3.0')}
<h2>ليلة تحت النجوم: أين وكيف؟</h2>
<p>يمكن اختيار مخيم منظّم يوفر الخدمات الأساسية، أو موقع آخر يسمح مالكه أو الجهة المسؤولة بالمبيت فيه. التخييم المفتوح ليس إذنًا عامًا: تُحظر الإقامة ليلًا وإشعال النار في مواقع محمية، ومنها محمية أرز الشوف وفق قواعدها المنشورة. تحقّق من شروط الموقع والحجز وإمكان الوصول قبل الانطلاق، ولا تشعل نارًا إلا حيث تسمح التعليمات المحلية صراحةً.</p>
<p>حتى في أشهر الربيع والصيف والخريف، قد تهبط الحرارة سريعًا في الجبال أو يتغيّر الطقس. احمل ماءً كافيًا، طبقات دافئة، حذاءً مناسبًا، إضاءة وهاتفًا مشحونًا، واترك لشخص موثوق خط سيرك وموعد عودتك. اجمع كل النفايات، والتزم المسارات، واحترم الأراضي الزراعية وهدوء الحياة البرية.</p>
<p>في النهاية، أجمل صورة يعود بها المتنزّه هي التي يلتقطها من دون أن يترك أثرًا خلفه.</p>
<p><small>للتخطيط: <a href="https://lebanontrail.org/">جمعية درب الجبل اللبناني</a>، <a href="https://whc.unesco.org/en/list/850/">ملف وادي قاديشا لدى اليونسكو</a>، وإدارات المحميات قبل الزيارة.</small></p>'''

EN_BODY = f'''<p>In Lebanon, the scenery changes quickly between the coast and the mountains: a village perched above a deep valley gives way to cedar woodland and cool air. Walkers, wildlife watchers and photographers can choose a day on the trail or a night at a suitable campsite.</p>
{figure(HERO, 'Tents and hiking gear on a ridge between Sannine and Aqoura', 'Camping on a mountain route between Sannine and Aqoura', hero_src, '', '', '')}
<h2>The Lebanon Mountain Trail, one section at a time</h2>
<p>The <a href="https://lebanontrail.org/">Lebanon Mountain Trail</a> runs about 470 kilometres from Andqet in the north to Marjayoun in the south. Its 27 sections cross more than 75 towns and villages. You need not walk it end to end: choose a section that suits your time and fitness, then check an updated map or consult a local guide for the start, return route and water stops.</p>
<p>The appeal extends beyond altitude. The trail passes farms, villages and mountain paths, offering encounters with the people and history of the land as well as its peaks.</p>
{figure(HIKING, 'Hikers crossing a trail in the Lebanese mountains', 'On the Lebanon Mountain Trail', hiking_src, '', '', '')}
<h2>Qadisha, a valley of landscape and memory</h2>
<p>In the Qadisha Valley, steep cliffs rise above old monasteries and caves. Walks near Qannoubine and Qozhaya reveal different views with the season and the light. Some descents are demanding, so pick a marked route suited to your group and keep well back from exposed edges.</p>
{figure(CANYON, 'Steep cliffs in the Qadisha Valley of northern Lebanon', 'The rocky walls of the Qadisha Valley', canyon_src, argen, by, 'CC BY 4.0')}
<h2>Cedars and waterfalls</h2>
<p>The cedar landscapes of the Shouf, Tannourine, Ehden and Bentael offer walks, birdwatching and photography. Each protected area has its own trails and rules; ask its managers which routes are open and check conditions before setting out. Near Tannourine, the Baatara Gorge waterfall, also known as Balou Balaa, adds a striking geological sight. Its flow varies with rainfall and season, while wet rock and cliff edges demand care.</p>
{figure(WATERFALL, 'Baatara Gorge waterfall near Tannourine', 'Balou Balaa near Tannourine; flow changes with the season', falls_src, 'Lodo27', by_sa, 'CC BY-SA 3.0')}
<h2>A night under the stars</h2>
<p>Choose an organised campsite with basic services, or a site where the landowner or responsible authority explicitly allows overnight stays. Wild camping is not a blanket permission. Overnight stays and fires are prohibited in protected places including the Shouf Cedar Nature Reserve under its published rules. Check the site’s conditions and access before travelling, and light a fire only where local rules expressly permit one.</p>
<p>Mountain temperatures can fall quickly even in spring, summer or autumn. Carry enough water, warm layers, suitable footwear, a light and a charged phone; tell someone your route and expected return. Pack out every item of litter, stay on paths and respect farmland and wildlife.</p>
<p>The best photograph is one you can take without leaving a trace behind.</p>
<p><small>Plan with the <a href="https://lebanontrail.org/">Lebanon Mountain Trail Association</a>, <a href="https://whc.unesco.org/en/list/850/">UNESCO’s Qadisha Valley listing</a> and the relevant reserve managers.</small></p>'''

def article(lang, slug, twin, title, desc, body):
    prefix = 'en/' if lang == 'en' else ''
    template = (DOCS / prefix / 'posts' / ('the-awsaj-thornbush-reading-the-land' if prefix else 'شجيرة-العوسج-حين-تقرأ-الأرض') / 'index.html').read_text()
    old_slug = 'the-awsaj-thornbush-reading-the-land' if prefix else 'شجيرة-العوسج-حين-تقرأ-الأرض'
    old_title = 'The awsaj thornbush: reading the land, and the wild’s old pharmacy under the spines' if prefix else 'شجيرة العوسج: حين تقرأ الأرض وتعرف صيدلية البرّ في ظلّ الشوك'
    template = template.replace(old_slug, slug).replace(old_title, title)
    template = template.replace('شجيرة-العوسج-حين-تقرأ-الأرض' if prefix else 'the-awsaj-thornbush-reading-the-land', twin)
    template = template.replace('23 September 2026' if prefix else '23 أيلول 2026', '29 September 2026' if prefix else '29 أيلول 2026')
    template = re.sub(r'(<meta name="description" content=")[^"]*', lambda m:m[1] + html.escape(desc, quote=True), template, count=1)
    if lang == 'en':
        body = body.replace('— المصدر:', '— Source:')
    media_prefix = "../../../" if lang == "en" else "../../"
    body = body.replace(f'src="{HERO}"', f'src="{media_prefix}{HERO}"')
    template = re.sub(r'(<article class="article-content">).*?(</article>)', lambda m:m[1]+'\n'+body+'\n    '+m[2], template, flags=re.S, count=1)
    template = re.sub(r'<section class="related-block">.*?</section>', '', template, count=1, flags=re.S)
    out = DOCS / prefix / 'posts' / slug / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template)

def row(lang, slug, title, date, excerpt='', archive=False):
    depth = '../' if archive and lang == 'ar' else ('../../' if archive else ('../../../' if lang == 'en' else '../../'))
    link = '../posts/' if archive else '../../posts/'
    image = f'<img src="{depth}{HERO}" alt="{html.escape(title, quote=True)}" loading="lazy">'
    if archive and lang == 'en':
        return f'<article class="card overlay"><a class="thumb" href="{link}{slug}/index.html">{image}</a><div class="body"><div class="meta">{date}</div><h3><a href="{link}{slug}/index.html">{title}</a></h3></div></article>\n'
    extra = f'<p class="excerpt">{excerpt}</p>' if archive else ''
    return f'<article class="post-row"><a class="thumb" href="{link}{slug}/index.html">{image}</a><div class="body"><div class="meta">{date}</div><h2><a href="{link}{slug}/index.html">{title}</a></h2>{extra}</div></article>\n'

def prepend(path, marker, snippet, badge=None):
    text = path.read_text()
    assert marker in text, (path,marker)
    text = text.replace(marker, marker+'\n'+snippet, 1)
    if badge is not None:
        text = re.sub(r'(<span class="badge">)\d+(</span>)', lambda m:m[1]+str(badge)+m[2], text, count=1)
    path.write_text(text)

def main():
    article('ar', AR, EN, AR_TITLE, AR_DESC, AR_BODY)
    article('en', EN, AR, EN_TITLE, EN_DESC, EN_BODY)
    category = 'حياة-برية-وتخييم'
    prepend(DOCS / 'category' / category / 'index.html', '<div class="post-list">', row('ar',AR,AR_TITLE,'29 أيلول 2026'), 3)
    prepend(DOCS / 'en/category' / category / 'index.html', '<div class="post-list">', row('en',EN,EN_TITLE,'29 September 2026'), 3)
    prepend(DOCS / 'articles/index.html', '<div class="post-list">', row('ar',AR,AR_TITLE,'29 أيلول 2026',AR_DESC,True))
    prepend(DOCS / 'en/stories/index.html', '<div class="grid-4">', row('en',EN,EN_TITLE,'29 September 2026',archive=True))
    archive = DOCS / 'articles/index.html'
    archive.write_text(archive.read_text().replace('الأرشيف — كل المقالات (712)', 'الأرشيف — كل المقالات (713)', 1))
    pairs_path = ROOT / 'content/en/pairs.json'
    pairs = json.loads(pairs_path.read_text()); pairs['pairs'][AR] = EN
    pairs_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2)+'\n')
    for path, title, description, language in ((ROOT / 'content/posts' / (AR+'.md'), AR_TITLE, AR_DESC, 'ar'), (ROOT / 'content/en' / (EN+'.md'), EN_TITLE, EN_DESC, 'en')):
        path.write_text(f'# {title}\n\n**Publication date:** 29 September 2026\n**Category:** Wildlife & Camping / الحياة البرية والتخييم\n**Published URL:** https://sayd-magazine.com/{"en/" if language == "en" else ""}posts/{EN if language == "en" else AR}/\n\n{description}\n\nThe published HTML contains the complete illustrated article and image credits.\n')
    home_json = ROOT / 'content/homepage.json'
    data = json.loads(home_json.read_text())
    for name in ('omit_from_latest','omit_from_ticker'):
        data[name].extend([AR,EN])
    home_json.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(AR,EN)

if __name__ == '__main__': main()
