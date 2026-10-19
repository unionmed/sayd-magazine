#!/usr/bin/env python3
"""Build isolated Mufid pilot pages and a public-only Worker corpus; no homepage rollout."""
from pathlib import Path
import json, re, shutil, html
ROOT=Path(__file__).resolve().parents[1]
COPY={
'ar':dict(title='اسأل مفيد',intro='اكتشف صيد، افهم وقارن، وجهّز نشاطك.',pilot='نسخة تجريبية للاختبار الداخلي',search='ابحث في صيد',understand='افهم وقارن',plan='جهّز نشاطك',verify='تحقّق من معلومة حديثة',suggest='اقترح موضوعًا',query='سؤالك أو موضوعك',submit='اسأل مفيد',fresh='أحتاج معلومات حديثة موثّقة',consent='أوافق على حفظ هذا الاقتراح للتحرير لمدة سبعة أيام. لا أضمّن معلومات شخصية. الإرسال لا يضمن النشر.',privacy='يُرسل السؤال والمواد المنشورة ذات الصلة إلى خدمة الذكاء الاصطناعي عند طلب إجابة. لا نحفظ المحادثات ولا نرسل نصوصها إلى أدوات الإحصاء. البحث في صيد يستخدم مواد المجلة المنشورة فقط.',settings='إعدادات الاختبار',endpoint='عنوان خدمة الاختبار',token='رمز الدخول التجريبي',save='اتصال',ready='اختر بداية واكتب سؤالك.',loading='جارٍ البحث…',error='تعذّر إكمال الطلب. حاول مجددًا.',unavailable='الخدمة غير مفعّلة. يمكن اختبار الواجهة بعد توصيل خدمة الاختبار.',none='لم أجد مواد مناسبة. جرّب اسم طائر أو موضوعًا أكثر تحديدًا.',received='وصل اقتراحك إلى قائمة المراجعة التحريرية. لا يضمن ذلك نشره.',sources='مصادر التحقق',articles='من صيد',checked='تاريخ التحقق',clear='مسح الجلسة',nojs='يتطلب مفيد تفعيل JavaScript.',consent_required='يرجى الموافقة على حفظ الاقتراح أولًا.',limit='وصلت إلى حد الاستخدام التجريبي. حاول لاحقًا.',verification_unavailable='التحقق الحديث غير متاح الآن. لا يمكن اعتماد الأرشيف لإثبات معلومة راهنة.',ai_unavailable='خدمة الإجابة غير متصلة بعد. يمكنك تجربة البحث في صيد.',verification_failed='تعذّر إتمام تحقق حديث موثّق. لم تُعرض إجابة غير متحققة.',no_sources='لم أجد مادة كافية في صيد لهذا الطلب. أعد صياغته أو اطلب تحققًا حديثًا.'),
'en':dict(title='Ask Mufid',intro='Explore Sayd, understand and compare, and prepare your activity.',pilot='Internal test version',search='Search Sayd',understand='Understand & compare',plan='Plan your activity',verify='Check current information',suggest='Suggest a topic',query='Your question or topic',submit='Ask Mufid',fresh='I need verified current information',consent='I agree to store this suggestion for editorial review for seven days. I will not include personal information. Submission does not guarantee publication.',privacy='For AI answers, your question and relevant public articles are sent to the AI service. We do not store conversations or send their text to analytics. Sayd search uses published magazine content only.',settings='Test settings',endpoint='Test service URL',token='Pilot access token',save='Connect',ready='Choose a starting point and enter your question.',loading='Searching…',error='Could not complete the request. Try again.',unavailable='The service is not activated. Connect the test service to try the interface.',none='No relevant articles found. Try a bird name or a more specific topic.',received='Your suggestion has reached the editorial review list. Publication is not guaranteed.',sources='Verification sources',articles='From Sayd',checked='Checked at',clear='Clear session',nojs='Mufid requires JavaScript.',consent_required='Please agree to storing your suggestion first.',limit='The pilot usage limit has been reached. Please try later.',verification_unavailable='Current verification is unavailable. Archives cannot establish current facts.',ai_unavailable='AI answers are not connected yet. You can try Sayd search.',verification_failed='Could not complete a sourced current check. An unverified answer was not displayed.',no_sources='No sufficient Sayd sources found. Rephrase or request current verification.'),
'fr':dict(title='Demandez à Mufid',intro='Explorez Sayd, comprenez et comparez, préparez votre activité.',pilot='Version de test interne',search='Rechercher dans Sayd',understand='Comprendre et comparer',plan='Préparer votre activité',verify='Vérifier une information récente',suggest='Proposer un sujet',query='Votre question ou sujet',submit='Demander à Mufid',fresh='Je souhaite des informations récentes vérifiées',consent='J’accepte la conservation de cette proposition pour examen éditorial pendant sept jours. Je n’inclus aucune donnée personnelle. L’envoi ne garantit pas la publication.',privacy='Pour les réponses IA, votre question et les articles publics pertinents sont transmis au service IA. Nous ne conservons pas les conversations et ne transmettons pas leur texte aux outils statistiques. La recherche Sayd utilise uniquement les articles publiés.',settings='Paramètres du test',endpoint='URL du service de test',token='Code d’accès au test',save='Connecter',ready='Choisissez une entrée et posez votre question.',loading='Recherche…',error='La demande n’a pas pu aboutir. Réessayez.',unavailable='Le service n’est pas activé. Connectez le service de test pour essayer l’interface.',none='Aucun article pertinent trouvé. Essayez un nom d’oiseau ou un sujet plus précis.',received='Votre proposition a rejoint la liste de révision éditoriale. La publication n’est pas garantie.',sources='Sources de vérification',articles='Dans Sayd',checked='Vérifié le',clear='Effacer la session',nojs='Mufid nécessite JavaScript.',consent_required='Veuillez accepter la conservation de votre proposition.',limit='La limite d’utilisation du test est atteinte. Réessayez plus tard.',verification_unavailable='La vérification récente est indisponible. Les archives ne prouvent pas les faits actuels.',ai_unavailable='Les réponses IA ne sont pas encore connectées. Essayez la recherche Sayd.',verification_failed='La vérification récente avec sources a échoué. Aucune réponse non vérifiée n’a été affichée.',no_sources='Sources Sayd insuffisantes. Reformulez ou demandez une vérification récente.')}

def build():
    rows=[]
    for lang,c in COPY.items():
        folder=ROOT/'docs'/('' if lang=='ar' else lang)
        # Search shell is already analytics-free and uses the approved edition chrome.
        page=(folder/'search/index.html').read_text()
        page=re.sub(r'<script id="search-copy".*?</script>','',page,flags=re.S)
        page=re.sub(r'<script[^>]*src="[^"]*site-search\.js[^>]*></script>','',page)
        page=re.sub(r'<link[^>]*href="[^"]*/search\.css[^>]*>','',page)
        page=re.sub(r'<title>.*?</title>',f'<title>{c["title"]} | Sayd</title>',page,flags=re.S)
        page=re.sub(r'<!-- seo:start -->.*?<!-- seo:end -->','',page,flags=re.S)
        choices=''.join(f'<button type="button" data-mode="{mode}" aria-pressed="{str(mode=="search").lower()}">{c[mode]}</button>' for mode in ('search','understand','plan'))
        main=f'''<main id="content" class="page-main mufid-page" data-mufid-language="{lang}"><div class="container mufid-shell">
<p class="mufid-pilot">{c['pilot']}</p><h1>{c['title']}</h1><p class="mufid-intro">{c['intro']}</p>
<div class="mufid-starts" role="group" aria-label="{c['title']}">{choices}</div>
<div class="mufid-tools"><button type="button" data-mode="verify" aria-pressed="false">{c['verify']}</button><button type="button" data-mode="suggest" aria-pressed="false">{c['suggest']}</button></div>
<form id="mufid-form"><label for="mufid-query">{c['query']}</label><textarea id="mufid-query" maxlength="1200" rows="4" required aria-describedby="mufid-privacy"></textarea>
<label class="mufid-check"><input type="checkbox" id="mufid-fresh">{c['fresh']}</label>
<label class="mufid-check" id="mufid-consent-row" hidden><input type="checkbox" id="mufid-consent">{c['consent']}</label>
<div class="mufid-actions"><button type="submit">{c['submit']}</button><button type="button" id="mufid-clear">{c['clear']}</button></div></form>
<p class="mufid-note" id="mufid-privacy">{c['privacy']}</p><p id="mufid-status" role="status" aria-live="polite">{c['ready']}</p>
<section id="mufid-answer" hidden aria-live="polite"></section><div id="mufid-sources"></div><div id="mufid-results"></div>
<details class="mufid-settings"><summary>{c['settings']}</summary><label for="mufid-endpoint">{c['endpoint']}</label><input id="mufid-endpoint" type="url" placeholder="https://…workers.dev" autocomplete="off" dir="ltr"><label for="mufid-token">{c['token']}</label><input id="mufid-token" type="password" autocomplete="off"><button type="button" id="mufid-connect">{c['save']}</button></details>
<noscript>{c['nojs']}</noscript></div></main>'''
        page=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:main,page,count=1,flags=re.S)
        canonical='https://sayd-magazine.com/'+('' if lang=='ar' else lang+'/')+'mufid/'
        metadata=f'<link rel="canonical" href="{canonical}"><meta property="og:title" content="{html.escape(c["title"],quote=True)}"><meta name="description" content="{html.escape(c["intro"],quote=True)}">'
        page=page.replace('</head>',metadata+'<link rel="stylesheet" href="'+('../../' if lang!='ar' else '../')+'assets/css/mufid.css?v=1">\n</head>')
        page=page.replace('</body>','<script type="application/json" id="mufid-copy">'+json.dumps(c,ensure_ascii=False).replace('<','\\u003c')+'</script><script src="'+('../../' if lang!='ar' else '../')+'assets/js/mufid.js?v=1" defer></script></body>')
        # Utility language links lead to the corresponding Mufid page.
        page=re.sub(r'<nav class="lang-switch".*?</nav>',lambda m:m[0].replace('/search/','/mufid/'),page,flags=re.S)
        target=folder/'mufid/index.html';target.parent.mkdir(parents=True,exist_ok=True)
        from build_site_search import links
        target.write_text(links(page,target))
        data=json.loads((ROOT/f'docs/assets/search/index-{lang}.json').read_text())
        for a in data['articles']:
            # An explicit article schema prevents internal files/metadata entering the bundle.
            assert re.fullmatch(r'/(?:en/|fr/)?posts/[^/]+/',a['url'])
            rows.append({k:a[k] for k in ('url','title','body','keywords','date','category','image','excerpt')} | {'lang':lang})
    for kind in ('css','js'):
        shutil.copyfile(ROOT/f'assets/{kind}/mufid.{kind}',ROOT/f'docs/assets/{kind}/mufid.{kind}')
    target=ROOT/'services/mufid/data/public-index.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'version':1,'articles':rows},ensure_ascii=False,separators=(',',':'))+'\n')
    print(f'Mufid pilot: 3 pages, {len(rows)} public language records. No live entry points changed.')
if __name__=='__main__':build()
