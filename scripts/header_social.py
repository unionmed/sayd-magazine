"""Place compact social links in the green bar opposite the language switch."""
import re

LINKS = (
 ('instagram', 'إنستغرام', 'Instagram', 'https://www.instagram.com/saydmagazinetv/', '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="18" cy="6" r="1" fill="currentColor" stroke="none"/>'),
 ('facebook', 'فيسبوك', 'Facebook', 'https://www.facebook.com/SaydMagazine/', '<path d="M14 21v-8h3l.5-4H14V7c0-1 .3-2 2-2h2V2h-3c-3 0-5 2-5 5v2H7v4h3v8"/>'),
 ('youtube', 'يوتيوب', 'YouTube', 'https://www.youtube.com/@saydmagazinetv', '<rect x="2" y="5" width="20" height="14" rx="4"/><path d="m10 9 5 3-5 3z" fill="currentColor" stroke="none"/>'),
 ('tiktok', 'تيك توك', 'TikTok', 'https://www.tiktok.com/@saydmagazine', '<path d="M14 3v12a4 4 0 1 1-4-4v3a1 1 0 1 0 1 1V3h3c.5 3 2 4 5 4v3c-2 0-3.5-.6-5-2"/>'),
)

def apply(text, lang='ar'):
    text = re.sub(r'<div class="header-brand-row">(.*?)<nav class="header-social".*?</nav></div>', r'\1', text, flags=re.S)
    text = re.sub(r'<nav class="header-social".*?</nav>', '', text, flags=re.S)
    label = {'ar':'تابعوا صيد','en':'Follow Sayd','fr':'Suivez Sayd'}[lang]
    links = ''.join(f'<a class="social-{key}" href="{url}" target="_blank" rel="noopener noreferrer" aria-label="{en} — Sayd Magazine"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{icon}</svg><span>{ar if lang == "ar" else en}</span></a>' for key,ar,en,url,icon in LINKS)
    nav = f'<nav class="header-social" aria-label="{label}">{links}</nav>'
    pattern = r'(<div class="container mast-top-inner">)'
    return re.sub(pattern, lambda m: m[0]+nav, text, count=1)


def add_approved_tiktok(text, lang='ar'):
    """Append only the owner-approved TikTok anchor; preserve other chrome bytes."""
    key, ar, en, url, icon = next(link for link in LINKS if link[0]=='tiktok')
    label = ar if lang=='ar' else en
    link = f'<a class="social-{key}" href="{url}" target="_blank" rel="noopener noreferrer" aria-label="{en} — Sayd Magazine"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{icon}</svg><span>{label}</span></a>'
    def append(match):
        block=match[0]
        if 'class="social-tiktok"' in block:
            return block
        return block[:-6]+link+'</nav>'
    if not re.search(r'<nav class="header-social"[^>]*>',text):
        # Existing mast-top headers receive the same verified four destinations.
        # Headerless legacy pages and redirect shells remain byte-identical.
        nav_label={'ar':'تابعوا صيد','en':'Follow Sayd','fr':'Suivez Sayd'}.get(lang,'تابعوا صيد')
        anchors=''.join(f'<a class="social-{key}" href="{url}" target="_blank" rel="noopener noreferrer" aria-label="{en} — Sayd Magazine"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{icon}</svg><span>{ar if lang=="ar" else en}</span></a>' for key,ar,en,url,icon in LINKS)
        nav=f'<nav class="header-social" aria-label="{nav_label}">{anchors}</nav>'
        return re.sub(r'(<div class="container mast-top-inner">)',lambda m:m[0]+nav,text,count=1)
    return re.sub(r'<nav class="header-social"[^>]*>.*?</nav>',append,text,flags=re.S)
