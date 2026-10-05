# Sayd — Nayef's publication contract

These rules were explicitly requested by Nayef Krayem on 30 September 2026 (Asia/Beirut). They supersede stale bilingual or ten-card instructions in historical scripts and notes.

- Only Nayef's explicit instruction authorizes changing doors, rules, design, layout, languages, colors, social channels, or this contract. An instruction to publish a story is not permission to redesign.
- Three mirrors: Arabic, English, French. Do not publish a new story before all three complete versions exist, with the same photographs/video, category, publication date and placement decisions (lead, side, Updates, ticker, lower door and archive). Never substitute an English page for a missing French translation. Historical archive translations are a separate task; do not delete old material.
- Home: one lead, four side cards, eight Updates (desktop 4+4; mobile two visible per row with horizontal scrolling), four illustrated memory cards. Sort news newest first in every language.
- Lower doors, in order: Hunting; Shooting & Gear; Equestrian; Wildlife & Camping; Poetry & Art; Sayd TV; Photos. At most four cards per door except Sayd TV, no duplicate filler. Equestrian repeats only as explicitly recorded in homepage.json. TV has exactly six cards in two labeled groups: three recent Sayd channel videos in newest-first order unless Nayef explicitly approves an editorial order (currently Bekaa, Radar, From Sayd Memory), then three editorial selections (APU, Babtain, Arabian leopard). Channel and selections link to their respective inner-page sections; never replace selections with channel uploads. Use the original APU thumbnail with the eagle. This TV amendment was explicitly authorized by Nayef on 2 October 2026. Maintain full AR/EN/FR parity. External video removal must not silently delete the editorial record; show its unavailable status, and never copy video files without established rights.
- Preserve the approved full-width green section bands, gold desktop headings, mobile styling, shared theme, navigation and social icons/URLs. Do not hide or remove these to make a check pass.
- content/homepage.json controls story placement. content/publication-contract.json records protected design and chrome. A routine publication may update the story slots, not loosen counts or overwrite approved design fingerprints.
- Before publication: python scripts/check_publication_contract.py --base <base-commit>, then python scripts/test_homepage_doors.py. A failing check means fix the publication; never skip or weaken the check. Translation completeness still requires editorial review; automated checks cannot judge translation quality.
- Hard enforcement requires the GitHub owner to require the Three-mirror publication check, PRs and CODEOWNER approval on main, disallow direct pushes and bypass, and protect the check/contract itself. A workflow alone is not a GitHub Pages deployment gate. Do not claim bypass prevention until repository protections are actually enabled.
- Full-package and social distribution operations follow `notes/SAYD-FULL-PACKAGE-WORKFLOW.md`; that workflow complements this contract and never overrides the three-mirror publication rules or Nayef's approval authority.

## قاعدة ملزمة للكتابة والترجمة والنشر — اعتمدها نايف في 3 تشرين الأول 2026

**النص المنشور لازم يكون بصياغة صحافية، وملاحظات نقاشنا تبقى خارج المقال.**

- تُكتب كل مادة للقارئ بصوت صحافي مستقل. يُمنع إدخال الحوار مع نايف، تعليماته، أسئلة المساعد وأجوبته، إجراءات العمل والموافقة، أو ملاحظات التدقيق والتحرير الداخلية في النص المنشور.
- تأكيد معلومة أو تصحيحها أثناء النقاش هو توجيه لتحرير الوقائع، وليس نصًا يُنسخ إلى المقال أو يُحوّل تلقائيًا إلى بوكس أو تنبيه أو شرح للقرار. لا يُنشر توضيح مستمد من نقاش داخلي إلا إذا كانت له ضرورة صحافية للقارئ وصياغة مستقلة؛ والتصحيح العلني أو التوضيح الذي يطلبه نايف صراحة يُصاغ صحافيًا.
- البوكسات والاقتباسات البارزة مخصصة لمعلومة موثقة أو اقتباس أو سياق مفيد للقارئ؛ لا تُستخدم لتبرير اختيار المساعد أو شرح ما اتُّفق عليه في المحادثة.
- تُحفظ ملاحظات المصادر والتحقق والشكوك والاعتماد في السجل التحريري المنفصل. لا يُعامل سجل العمل أو تقرير التنفيذ كنص صالح للنشر.
- تُترجم النسخة الصحافية النهائية المحررة فقط إلى الإنجليزية والفرنسية، مع تطابق الوقائع والصور والتوزيع. لا تُترجم المحادثة أو التعليمات الداخلية ولا تُضاف ملاحظات من المترجم إلى المادة المنشورة.
- قبل كل نشر أو تحديث، تُراجع النسخ الثلاث وكل عناصرها الموجهة للجمهور: العنوان والمقدمة والمتن والبوكسات والتعليقات المصورة والشريط وSEO ومواد السوشيال. سؤال الفحص: «هل تخاطب هذه العبارة القارئ وتضيف قيمة صحافية، أم تنقل نقاشًا داخليًا أو تشرح عملي للمستخدم؟». تُحذف أو تُحرر أي عبارة من النوع الثاني قبل النشر. هذه مراجعة تحريرية إلزامية؛ الفحص الآلي وحده لا يثبت استيفاءها.
- تسري القاعدة على جميع المحررين والمترجمين والوكلاء العاملين على صيد. لا يعدلها إلا نايف بتوجيه صريح.

## اعتماد مصادر الصور — نايف، 5 تشرين الأول 2026

- إذا كان شعار المصدر واضحًا على الصورة، لا يكرر اسم المصدر أسفلها.
- إذا كانت صور المقال كلها من مصدر واحد، يذكر مصدر الصور مرة واحدة في نهاية المقال عند الحاجة، بدل تكراره تحت كل صورة.
- عند تعدد المصادر، توضح نسبتها من دون تكرار غير ضروري. تبقى التعليقات لوصف محتوى الصورة، وتحتفظ سجلات التحرير ببيانات المصادر والحقوق وروابط الأصل، مع مراعاة أي شرط إسناد صريح.
- تسري القاعدة على العربية والإنجليزية والفرنسية. لا تفرض القوالب تكرار اسم المصدر تحت كل صورة.

## حركة بطاقات صيد — توضيح نايف، 5 تشرين الأول 2026

- عند كل نشر يغير الرئيسي أو البطاقات الجانبية أو المستجدات، تُحدث بطاقات باب صيد الأربع بأحدث مواد الصيد المؤهلة التي لا تظهر في تلك المواضع، بترتيب تاريخ النشر من الأحدث إلى الأقدم.
- المادة التي تغادر المستجدات تدخل بابها المناسب بحسب تاريخها، وتخرج أقدم بطاقة عند امتلاء الأربع. تبقى المواد الخارجة في الباب الداخلي والأرشيف.
- لا تُثبت قائمة بطاقات صيد القديمة عند إضافة مواد جديدة. يشمل التنفيذ المصدر والمولد والمرايا الثلاث، ويحظر تكرار المواد مع المواضع العليا عند توافر مواد كافية.
- الخبر الذي استُبدل بخبر أحدث عن الحدث نفسه يبقى في الأرشيف؛ لا يعاد تدويره كأنه خبر جارٍ.
