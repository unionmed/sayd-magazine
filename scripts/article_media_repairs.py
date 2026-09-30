"""Scoped, repeatable media repairs for the two September 2026 migration stories."""
import re
from html import escape

PARTNERS = 'protecting-autumn-migratory-birds-lebanon-khatib-2017'
MIGRATION = 'autumn-migration-field-action-protect-flyways-lebanon'
BIRDS = 'ChatGPT-Image-Sep-7-2026-01_33_30-AM-853x1024.png'
LOGOS = ('mecshap-official-logo.png', 'cabs-official-logo.png', 'cabs-bird-guard-logo.jpg')
LOGO_ALT = {
 'ar': ('شعار مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر — MECSHAP', 'شعار CABS', 'شعار CABS Bird Guard'),
 'en': ('Middle East Center for Sustainable Hunting and Anti-Poaching — MECSHAP logo', 'CABS logo', 'CABS Bird Guard logo'),
 'fr': ('Logo du Middle East Center for Sustainable Hunting and Anti-Poaching — MECSHAP', 'Logo CABS', 'Logo CABS Bird Guard'),
}
BIRD_ALT = {
 'ar': 'طائران على غصن، أحدهما باسط جناحيه',
 'en': 'Two birds on a branch, one with its wings spread',
 'fr': 'Deux oiseaux sur une branche, dont un aux ailes déployées',
}
CREDIT = {'ar': 'تصوير: فؤاد عيتاني', 'en': 'Photo: Fouad Itani', 'fr': 'Photo : Fouad Itani'}

def logos(lang, prefix):
    tags = ''.join(f'<img src="{prefix}media/uploads/2026/09/{name}" alt="{escape(alt, quote=True)}" width="220" style="display:block;flex:0 1 220px;width:42%;max-width:220px;height:auto;object-fit:contain;">' for name,alt in zip(LOGOS,LOGO_ALT[lang]))
    return '<div id="sayd-cabs-partner-logos" style="display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:20px;margin:18px 0 24px;">'+tags+'</div>'

def birds(lang, prefix):
    return f'<figure id="sayd-autumn-birds"><img src="{prefix}media/uploads/2026/09/{BIRDS}" alt="{BIRD_ALT[lang]}" loading="lazy" width="1024" height="683"><figcaption><small class="photo-credit" style="display:block;font-size:.72em;line-height:1.4;color:#68705f;">{CREDIT[lang]}</small></figcaption></figure>'

def repair_body(slug, body, lang='en', prefix='../../../'):
    if slug == PARTNERS and 'id="sayd-cabs-partner-logos"' not in body:
        # Keep the lead photograph first, followed by the approved partner logos.
        end = body.find('</figure>')
        assert end >= 0, 'Missing approved lead photograph'
        body = body[:end+9] + '\n' + logos(lang,prefix) + body[end+9:]
    if slug == MIGRATION and BIRDS not in body:
        body = '\n' + birds(lang,prefix) + body
    return body
