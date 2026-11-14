"""Fail-closed browser comparison for three immutable image representations.

Encoded bytes, natural RGBA, normalized DOM and paint geometry remain exact.
Only the verified Saudi JPEG's visible interior may have a <=3 RGB raster
residual; alpha and every other screenshot pixel remain exact. This is an
explicit same-content/same-layout criterion, not bit-identical scaled pixels
or a claim about the browser's internal cause. No Playwright dependency here.
"""
import math
import re

from PIL import ImageChops
import homepage_image_sources as images

SAUDI = '-Id9SK67khA'
ENCODED = {entry[2]: entry[4] for entry in images.IMAGES}


def check_proof(proof):
    assert set(proof) == {'encoded_sha256', 'native_rgba', 'dom_sha256', 'target', 'clip', 'state', 'after_state'}, 'Unknown proof fields'
    assert proof['encoded_sha256'] == ENCODED, 'Unverified encoded image identity'
    assert set(proof['native_rgba']) == set(ENCODED), 'Missing natural image proof'
    for value in proof['native_rgba'].values():
        assert all(type(value[k]) is int and value[k] > 0 for k in ('width', 'height'))
        assert re.fullmatch('[0-9a-f]{64}', value['rgba_sha256']), 'Invalid natural RGBA digest'
    assert re.fullmatch('[0-9a-f]{64}', proof['dom_sha256']), 'Missing normalized DOM proof'
    state = proof['state']
    assert state['dpr'] == 1 and state['overflow'] <= 1
    assert set(state['selected']) == set(ENCODED), 'Missing selected image state'
    assert proof['target'] in ENCODED
    assert state['target_unobscured'] is True, 'Target image not fully visible'
    assert state['saudi_unobscured'] is True, 'Saudi visible rectangle not verified'
    for selected in state['selected'].values():
        for rectangle in (selected['rect'], selected['grid']):
            assert len(rectangle) == 4 and all(type(n) in (int, float) and math.isfinite(n) for n in rectangle)
            assert rectangle[2] > 0 and rectangle[3] > 0
    assert proof['state'] == proof['after_state'], 'Paint state changed during capture'
    clip = proof['clip']
    assert set(clip) == {'x', 'y', 'width', 'height'}
    assert all(type(n) is int and n >= 0 for n in clip.values())
    assert clip['width'] > 0 and clip['height'] > 0
    assert clip['x'] + clip['width'] <= state['viewport'][0]
    assert clip['y'] + clip['height'] <= state['viewport'][1]
    assert clip['y'] >= state['header'][1] + state['header'][3] + 24, 'Header overlaps clip'
    sx, sy, sw, sh = state['section']
    assert clip['x'] <= sx and clip['y'] <= sy
    assert clip['x'] + clip['width'] >= sx + sw
    assert clip['y'] + clip['height'] >= sy + sh
    tx, ty, tw, th = state['selected'][proof['target']]['rect']
    gx, gy, gw, gh = state['selected'][proof['target']]['grid']
    assert tx >= max(0, gx, clip['x']) and ty >= max(gy, clip['y'])
    assert tx+tw <= min(state['viewport'][0], gx+gw, clip['x']+clip['width'])
    assert ty+th <= min(state['viewport'][1], gy+gh, clip['y']+clip['height']), 'Clipped target image'


def saudi_pixels(proof):
    """Derive the allowance from verified DOM rectangles, never a caller mask."""
    state, clip = proof['state'], proof['clip']
    rect = state['selected'][SAUDI]['rect']
    grid = state['selected'][SAUDI]['grid']
    x0 = max(rect[0], grid[0], clip['x']) - clip['x']
    y0 = max(rect[1], grid[1], clip['y']) - clip['y']
    x1 = min(rect[0]+rect[2], grid[0]+grid[2], clip['x']+clip['width']) - clip['x']
    y1 = min(rect[1]+rect[3], grid[1]+grid[3], clip['y']+clip['height']) - clip['y']
    # Pixel centers must lie inside the actual image/grid/clip intersection.
    return (max(0, math.ceil(x0-.5)), max(0, math.ceil(y0-.5)),
            max(0, math.ceil(x1-.5)), max(0, math.ceil(y1-.5)))


def compare(before, after, old, new):
    """Return complete raster statistics; strict proof failures raise first."""
    check_proof(old); check_proof(new)
    assert old == new, 'Encoded/native/DOM/geometry/render-state proof differs'
    assert before.mode == after.mode == 'RGBA'
    assert before.size == after.size == (old['clip']['width'], old['clip']['height'])
    delta = ImageChops.difference(before, after)
    bands = delta.split()
    # getbbox on RGBA would use only alpha, so inspect each channel separately.
    rgb_max = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
    any_max = ImageChops.lighter(rgb_max, bands[3])
    histogram = any_max.histogram()
    changed = sum(histogram[1:])
    allowed = saudi_pixels(old)
    x0, y0, x1, y1 = allowed
    # Count every residual across the entire screenshot, then classify the
    # independently verified rectangle. No pixel is erased or ignored.
    inside = sum(any_max.crop(allowed).histogram()[1:]) if x1 > x0 and y1 > y0 else 0
    outside = changed - inside
    maximum = rgb_max.getextrema()[1]
    alpha_maximum = bands[3].getextrema()[1]
    return {'passed': outside == 0 and maximum <= 3 and alpha_maximum == 0,
            'exact_pixels': changed == 0, 'size': list(before.size),
            'mismatch_pixels': changed, 'mismatch_fraction': changed/(before.width*before.height),
            'bbox': any_max.getbbox(), 'maximum_rgb_delta': maximum,
            'maximum_alpha_delta': alpha_maximum, 'outside_saudi_pixels': outside,
            'saudi_pixel_rectangle': allowed,
            'histogram': {str(i): count for i, count in enumerate(histogram) if count}}
