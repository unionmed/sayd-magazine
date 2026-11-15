"""Read-only browser acceptance for the approved market affiliate presentation."""
import json
from decimal import Decimal
from playwright.sync_api import expect
from build_market_coming_soon import CATALOG, DISCLOSURES, ROUTES


def verify_market(context, origin, output):
    """Use the existing local-only context; never click or request affiliate URLs."""
    products = json.loads(CATALOG.read_text())['products']
    screenshots = []
    page = context.new_page()
    try:
        for lang, route in ROUTES.items():
            for width in (320, 390, 1440):
                page.set_viewport_size({'width': width, 'height': 1000})
                page.goto(origin+'/'+route, wait_until='networkidle')
                label = (lang, width)
                disclosure = page.locator('.market-disclosure')
                expect(disclosure).to_have_text(DISCLOSURES[lang])
                expect(disclosure).to_be_visible()
                assert disclosure.evaluate('e => !!(e.compareDocumentPosition(document.querySelector(".market-grid")) & Node.DOCUMENT_POSITION_FOLLOWING)'), label
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), label
                columns = page.locator('.market-grid').evaluate('e => getComputedStyle(e).gridTemplateColumns.split(" ").length')
                assert columns == (4 if width == 1440 else 2), label
                cards = page.locator('.market-product')
                expect(cards).to_have_count(len(products))
                for index, product in enumerate(products):
                    card = cards.nth(index)
                    for selector in ('.market-visual', '.market-buy'):
                        link = card.locator(selector)
                        expect(link).to_have_attribute('href', product['affiliate_url'])
                        expect(link).to_have_attribute('target', '_blank')
                        assert set(link.get_attribute('rel').split()) == {'noopener', 'noreferrer', 'sponsored'}, label
                    image = card.locator('.market-photo')
                    image.scroll_into_view_if_needed()
                    expect(image).to_be_visible()
                    page.wait_for_function('i => i.complete && i.naturalWidth > 0', arg=image.element_handle(), timeout=10000)
                    expect(image).to_have_attribute('src', '/'+product['image']['path'])
                    assert image.evaluate('e => getComputedStyle(e).objectFit') == 'contain', label
                    for selector in ('h2', '.market-description', '.market-price', '.market-buy'):
                        element = card.locator(selector)
                        expect(element).to_be_visible()
                        assert element.evaluate('e => e.scrollWidth <= e.clientWidth + 1 && e.scrollHeight <= e.clientHeight + 1'), (label, index, selector)
                    button = card.locator('.market-buy').bounding_box()
                    assert button['height'] >= 44 and button['width'] >= 44, label
                    expect(card.locator('.market-price')).to_have_text(f"${Decimal(product['price']['amount']):.2f} USD")
                    expect(card.locator('.market-price')).to_have_attribute('data-currency', 'USD')
                page.locator('.market-intro').scroll_into_view_if_needed()
                path = output/f'market-affiliate-{lang}-{width}.png'
                page.screenshot(path=str(path), full_page=True)
                screenshots.append(path)
    finally:
        page.close()
    print('PASS: visible market disclosures, 16 photos/prices and 32 sponsored links in AR/EN/FR at 320/390/1440px, no affiliate clicks')
    return screenshots
