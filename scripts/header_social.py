"""Place compact social links in the green bar opposite the language switch."""
import re

LINKS = (
 ('instagram', 'إنستغرام', 'Instagram', 'https://www.instagram.com/saydmagazinetv/', '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="18" cy="6" r="1" fill="currentColor" stroke="none"/>'),
 ('facebook', 'فيسبوك', 'Facebook', 'https://www.facebook.com/SaydMagazine/', '<path d="M14 21v-8h3l.5-4H14V7c0-1 .3-2 2-2h2V2h-3c-3 0-5 2-5 5v2H7v4h3v8"/>'),
 ('youtube', 'يوتيوب', 'YouTube', 'https://www.youtube.com/@saydmagazinetv', '<rect x="2" y="5" width="20" height="14" rx="4"/><path d="m10 9 5 3-5 3z" fill="currentColor" stroke="none"/>'),
)

def apply(text, lang='ar'):
    text = re.sub(r'<div class="header-brand-row">(.*?)<nav class="header-social".*?</nav></div>', r'\1', text, flags=re.S)
    text = re.sub(r'<nav class="header-social".*?</nav>', '', text, flags=re.S)
    label = 'Follow Sayd' if lang == 'en' else 'تابعوا صيد'
    links = ''.join(f'<a class="social-{key}" href="{url}" target="_blank" rel="noopener noreferrer" aria-label="{en} — Sayd Magazine"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{icon}</svg><span>{en if lang == "en" else ar}</span></a>' for key,ar,en,url,icon in LINKS)
    nav = f'<nav class="header-social" aria-label="{label}">{links}</nav>'
    pattern = r'(<div class="container mast-top-inner">)'
    return re.sub(pattern, lambda m: m[0]+nav, text, count=1)
