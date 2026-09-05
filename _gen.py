#!/usr/bin/env python3
"""Generate an AeonX sub-page from the Figma full-canvas dump, reusing the
shared chrome (nav/mega-menu/footer/styles) extracted from index.html.

Usage: python3 _gen.py <NODE_ID> <out_path> "<Page Title>"
Body nodes are flattened to absolute vw positions, same convention as index.html.
"""
import json, sys, html, re, math, os

FACTOR = 100 / 1920.0  # vw per px
IMG_EXPORTS = {}  # imageRef -> (export_node_id, method)

def load_canvas():
    d = json.load(open('aeonx-node.json'))
    return d['nodes']['4020:9394']['document']

def find(n, tid):
    if n.get('id') == tid:
        return n
    for c in n.get('children', []):
        r = find(c, tid)
        if r:
            return r
    return None


# Nodes whose art CSS cannot reproduce, replaced wholesale by Figma's own PNG render
# (assets/gen/<ref>.png, exported at scale 2). Two failure modes drove this:
#   - the "Earned where it matters." ring: a wrapper rotated +1.39deg whose badges each
#     carry -1.39deg to stand upright. emit_rotated() applies the wrapper tilt and
#     assumes child rotation ~ 0, so the counter-rotation was dropped and every badge
#     rendered tilted.
#   - its blue glow: Figma interpolates gradient stops in straight (unpremultiplied)
#     alpha, so white -> blue-with-alpha-0 shows blue mid-ramp; CSS interpolates
#     premultiplied and fades white with NO blue anywhere. The stops are faithful and
#     the result still cannot match.
# Same treatment as _saashero.bake() for filter fills. Applies to both dumps.
BAKE_NODES = {
    # Desktop bakes the disc only, same reasoning as mobile below: with the wrapper's
    # tilt flattened (FLATTEN_ROTATION) the twelve badges place by their own AABB --
    # which Figma already reports post-rotation -- so they stay real, upright elements
    # and can orbit. Only the tilted disc+shadow needs Figma's own render.
    '6564:26542': 'bake-ptdisc-desk',
    '6564:26580': 'bake-ptglow-desk',
    # Mobile bakes only the DISC. Unlike desktop, the mobile ring frame carries no
    # rotation and its badges are already upright (-0.006 rad), so the twelve logos
    # render correctly as real elements -- which is what lets them orbit while
    # staying upright. Only the tilted disc+shadow needs Figma's own render.
    '6564:26764': 'bake-ptdisc-mob',
    '5637:48966': 'bake-ptglow-mob',
}


# Nodes whose rotation (and their descendants') is dropped so the walker places every
# child by its absoluteBoundingBox, which Figma already reports post-rotation. Used for
# the desktop partner ring: its wrapper is rotated +1.39deg and each badge carries
# -1.39deg to stand upright, and emit_rotated() honours the first and drops the second.
# Flattening both leaves the badges exactly where Figma draws them, upright, as real
# elements -- the disc's tilt is not lost, it is baked into the disc's own render.
FLATTEN_ROTATION = {'6564:26541'}


def flatten_rotation(root):
    """Strip `rotation` from each FLATTEN_ROTATION node and everything under it."""
    hit = []
    for nid in FLATTEN_ROTATION:
        n = find(root, nid)
        if not n:
            continue
        stack = [n]
        while stack:
            x = stack.pop()
            if x.pop('rotation', None) is not None:
                hit.append(x['id'])
            stack.extend(x.get('children') or [])
    return hit


def bake(root):
    """Swap each BAKE_NODES subtree for a single image-fill leaf, in place.

    The box comes from whichever of bbox / renderBounds the exported PNG actually
    matches (REST exports full geometry for clipped nodes, render bounds otherwise --
    same ambiguity render_box() handles for SVG). Keeps document order, so paint
    order is untouched.
    """
    import os
    baked = []
    flatten_rotation(root)
    for nid, ref in BAKE_NODES.items():
        n = find(root, nid)
        if not n:
            continue
        path = os.path.join('assets', 'gen', ref + '.png')
        box = n.get('absoluteBoundingBox')
        rb = n.get('absoluteRenderBounds')
        try:
            from PIL import Image
            w, h = Image.open(path).size
            w, h = w / 2.0, h / 2.0          # exported at scale 2
            if rb and abs(rb['width'] - w) <= 2 and abs(rb['height'] - h) <= 2:
                box = rb
        except Exception:
            pass                              # PNG missing: keep bbox, still bake
        n['children'] = []
        n['fills'] = [{'type': 'IMAGE', 'imageRef': ref, 'scaleMode': 'FILL',
                       'blendMode': 'NORMAL'}]
        n['strokes'] = []
        n['effects'] = []
        n.pop('rotation', None)
        n.pop('cornerRadius', None)
        n.pop('rectangleCornerRadii', None)
        n['clipsContent'] = False
        n['absoluteBoundingBox'] = dict(box)
        n['absoluteRenderBounds'] = dict(box)
        baked.append(nid)
    return baked

def vw(px):
    return f"{px*FACTOR:.4f}vw"

def col(c, a=None):
    r = round(c['r']*255); g = round(c['g']*255); b = round(c['b']*255)
    op = c.get('a', 1) if a is None else a
    if op >= 0.999:
        return f"rgb({r},{g},{b})"
    return f"rgba({r},{g},{b},{op:.3f})"

def solid_fill(fills):
    for f in fills or []:
        if f.get('visible', True) is False:
            continue
        if f.get('type') == 'SOLID':
            return col(f['color'], f.get('opacity'))
    return None

def gradient_fill(fills, w=None, h_px=None):
    for f in fills or []:
        if f.get('visible', True) is False:
            continue
        t = f.get('type', '')
        if t.startswith('GRADIENT'):
            stops = f.get('gradientStops', [])
            # Figma multiplies the PAINT's own opacity into every stop. Dropping it
            # rendered a 0.1-opacity wash at full stop alpha -- the manufacturing
            # product cards came out 10x too saturated (solid teal/orange instead of
            # a near-white tint). Multiply, don't override: the stops carry alpha too.
            po = f.get('opacity')
            po = 1.0 if po is None else po
            gcol = lambda c: col(c, c.get('a', 1) * po)
            sl = ', '.join(f"{gcol(s['color'])} {s['position']*100:.1f}%" for s in stops)
            # handles are normalised to the node box: [0] = center/start,
            # [1] = end of the first axis, [2] = end of the second axis.
            h = f.get('gradientHandlePositions') or []
            if t == 'GRADIENT_ANGULAR':
                # A conic sweep. Emitting this as a linear gradient (the old
                # fallback) turned the soft swirl blobs on the industry heroes into
                # hard saturated half-moons.
                cx, cy, ang, ccw = 50.0, 50.0, 0.0, False
                if len(h) >= 2:
                    cx, cy = h[0]['x']*100, h[0]['y']*100
                    dx1, dy1 = h[1]['x']-h[0]['x'], h[1]['y']-h[0]['y']
                    ang = math.degrees(math.atan2(dx1, -dy1)) % 360
                    if len(h) >= 3:
                        dx2, dy2 = h[2]['x']-h[0]['x'], h[2]['y']-h[0]['y']
                        # handedness of the two axes says which way Figma sweeps
                        ccw = (dx1*dy2 - dy1*dx2) > 0
                # Figma closes the sweep by interpolating the last stop back to the
                # first; CSS holds the last stop instead, which floods the rest of
                # the circle. Close the loop first, THEN mirror if needed -- mirroring
                # an unclosed list puts the seam in the wrong place.
                seq = list(stops) + ([dict(stops[0], position=1.0)] if stops else [])
                if ccw:
                    # conic-gradient only sweeps clockwise; mirror the stops
                    seq = [dict(s, position=1-s['position']) for s in reversed(seq)]
                sl = ', '.join(f"{gcol(s['color'])} {s['position']*100:.1f}%" for s in seq)
                return f"conic-gradient(from {ang:.0f}deg at {cx:.1f}% {cy:.1f}%, {sl})"
            if t in ('GRADIENT_RADIAL', 'GRADIENT_DIAMOND'):
                if len(h) >= 3:
                    cx, cy = h[0]['x']*100, h[0]['y']*100
                    rx = math.hypot(h[1]['x']-h[0]['x'], h[1]['y']-h[0]['y'])*100
                    ry = math.hypot(h[2]['x']-h[0]['x'], h[2]['y']-h[0]['y'])*100
                    return (f"radial-gradient(ellipse {rx:.1f}% {ry:.1f}% "
                            f"at {cx:.1f}% {cy:.1f}%, {sl})")
                return f"radial-gradient(circle, {sl})"
            ang = 180
            if len(h) >= 2:
                dx = h[1]['x']-h[0]['x']; dy = h[1]['y']-h[0]['y']
                ang = (math.degrees(math.atan2(dx, -dy))) % 360
                # Figma's gradient line is an arbitrary segment across the node, and
                # it often runs well outside the box (handles at 2.5x). CSS instead
                # fits its line to the box, so writing the stops at their raw
                # positions squeezes the whole ramp into view -- a navy-to-pale
                # gradient that Figma shows as almost all navy comes out mid-grey.
                # Re-project the stops onto the CSS gradient line.
                if w and h_px:
                    p0 = (h[0]['x']*w, h[0]['y']*h_px)
                    p1 = (h[1]['x']*w, h[1]['y']*h_px)
                    vx, vy = p1[0]-p0[0], p1[1]-p0[1]
                    seg = math.hypot(vx, vy)
                    rad = math.radians(ang)
                    css_len = abs(w*math.sin(rad)) + abs(h_px*math.cos(rad))
                    if seg > 1e-6 and css_len > 1e-6:
                        ux, uy = vx/seg, vy/seg
                        sx = w/2.0 - css_len/2.0*ux
                        sy = h_px/2.0 - css_len/2.0*uy
                        off = ((p0[0]-sx)*ux + (p0[1]-sy)*uy) / css_len
                        span = seg / css_len
                        sl = ', '.join(
                            f"{gcol(s['color'])} {(off + s['position']*span)*100:.1f}%"
                            for s in stops)
            return f"linear-gradient({ang:.0f}deg, {sl})"
    return None

def exotic_gradient(fills):
    """True if a fill is a sweep CSS cannot reproduce (angular/diamond)."""
    return any(f.get('visible', True) and f.get('type') in ('GRADIENT_ANGULAR', 'GRADIENT_DIAMOND')
               for f in fills or [])

def image_ref(fills):
    for f in fills or []:
        if f.get('visible', True) is False:
            continue
        if f.get('type') == 'IMAGE':
            return f.get('imageRef')
    return None

BLEND_MAP = {
    'MULTIPLY': 'multiply', 'SCREEN': 'screen', 'OVERLAY': 'overlay',
    'DARKEN': 'darken', 'LIGHTEN': 'lighten', 'COLOR_DODGE': 'color-dodge',
    'COLOR_BURN': 'color-burn', 'HARD_LIGHT': 'hard-light', 'SOFT_LIGHT': 'soft-light',
    'DIFFERENCE': 'difference', 'EXCLUSION': 'exclusion', 'HUE': 'hue',
    'SATURATION': 'saturation', 'COLOR': 'color', 'LUMINOSITY': 'luminosity',
}

def blend_css(n, fill=None):
    bm = n.get('blendMode')
    css = BLEND_MAP.get(bm)
    if css:
        return css
    if fill:
        return BLEND_MAP.get(fill.get('blendMode'))
    return None

def blur_css(n, layer=True):
    """Figma blur effects -> CSS. LAYER_BLUR blurs the node itself (`filter`);
    BACKGROUND_BLUR blurs what's behind it (`backdrop-filter`). Figma's blur
    radius is ~2x the Gaussian std-dev CSS uses, so halve it. Kept in vw so the
    blur scales with the viewport like the rest of the absolute layout."""
    css = ''
    for e in n.get('effects', []):
        if e.get('visible', True) is False:
            continue
        r = e.get('radius', 0)
        if not r:
            continue
        t = e.get('type')
        if t == 'LAYER_BLUR':
            if layer:
                css += f"filter:blur({vw(r/2)});"
        elif t == 'BACKGROUND_BLUR':
            b = f"blur({vw(r/2)})"
            css += f"backdrop-filter:{b};-webkit-backdrop-filter:{b};"
    return css

def image_fill(fills):
    for f in fills or []:
        if f.get('visible', True) is False:
            continue
        if f.get('type') == 'IMAGE':
            return f
    return None

def image_sizing_css(fill, w, h):
    """CSS sizing for a Figma IMAGE fill.

    Figma's `STRETCH` is the "crop" mode from the UI: the image is not stretched to
    the box, it is positioned by `imageTransform`, a 2x3 matrix mapping box UV to
    image UV (`i = sx*u + tx`). Treating it as `cover` silently crops from the wrong
    edge -- the product screenshots in the "same architecture" cards lost their left
    sidebar. Invert the matrix into background-size + background-position instead.
    """
    if not fill:
        return "background-size:cover;background-position:center;background-repeat:no-repeat;"
    mode = fill.get('scaleMode')
    if mode == 'TILE':
        return "background-size:auto;background-repeat:repeat;"
    if mode == 'FIT':
        return "background-size:contain;background-position:center;background-repeat:no-repeat;"
    t = fill.get('imageTransform')
    if mode == 'STRETCH' and t and w and h:
        sx, tx = t[0][0], t[0][2]
        sy, ty = t[1][1], t[1][2]
        if abs(sx) > 1e-6 and abs(sy) > 1e-6:
            return (f"background-size:{vw(w/sx)} {vw(h/sy)};"
                    f"background-position:{vw(-tx/sx*w)} {vw(-ty/sy*h)};"
                    "background-repeat:no-repeat;")
    return "background-size:cover;background-position:center;background-repeat:no-repeat;"

def esc(s):
    return html.escape(s)

def emit_text(n, left, top, w, h):
    st = n.get('style', {})
    fam = st.get('fontFamily', 'Nunito Sans')
    fw = st.get('fontWeight', 400)
    fs = st.get('fontSize', 16)
    lh = st.get('lineHeightPx', fs*1.3)
    ls = st.get('letterSpacing', 0)
    align = st.get('textAlignHorizontal', 'LEFT').lower()
    solid = solid_fill(n.get('fills'))
    grad = None if solid else gradient_fill(n.get('fills'))  # gradient-filled text (e.g. stat numbers)
    color = solid or '#15181e'
    chars = n.get('characters', '')
    single = h <= lh*1.6
    ws = 'nowrap' if single else 'pre-wrap'

    def seg_html(text):
        s = esc(text)
        if not single:
            s = s.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')
        return s

    cso = n.get('characterStyleOverrides') or []
    sot = n.get('styleOverrideTable') or {}
    # If every character carries an override that agrees on size/weight, promote it
    # to the element itself. Otherwise the element keeps the (often larger) base
    # size, which shows through for any character the overrides happen to miss.
    if cso and len(cso) >= len(chars) > 0 and all(cso):
        ov = [sot.get(str(s), {}) for s in cso]
        sizes = {o.get('fontSize') for o in ov}
        weights = {o.get('fontWeight') for o in ov}
        if len(sizes) == 1 and None not in sizes:
            fs = sizes.pop()
            lh = st.get('lineHeightPx', lh)
        if len(weights) == 1 and None not in weights:
            fw = weights.pop()
    if cso and any(cso):
        # A run of characters can override colour, weight, size and family
        # (e.g. a bold, smaller emphasised phrase inside a heading). Capture
        # all of them, not just colour, or the emphasis is silently dropped.
        def ov_for(i):
            sid = cso[i] if i < len(cso) else 0
            if sid and str(sid) in sot:
                o = sot[str(sid)]
                d = {}
                col = solid_fill(o.get('fills'))
                if col:
                    d['color'] = col
                if o.get('fontWeight'):
                    d['font-weight'] = str(o['fontWeight'])
                if o.get('fontSize'):
                    d['font-size'] = vw(o['fontSize'])
                if o.get('fontFamily'):
                    d['font-family'] = f"'{o['fontFamily']}',sans-serif"
                return tuple(sorted(d.items()))
            return ()
        parts = []
        i = 0
        while i < len(chars):
            o0 = ov_for(i)
            j = i
            while j < len(chars) and ov_for(j) == o0:
                j += 1
            seg = seg_html(chars[i:j])
            if o0:
                css = ''.join(f'{k}:{v};' for k, v in o0)
                parts.append(f'<span style="position:static;{css}">{seg}</span>')
            else:
                parts.append(seg)
            i = j
        body = ''.join(parts)
    else:
        body = seg_html(chars)
    style = (f"position:absolute;left:{vw(left)};top:{vw(top)};width:{vw(w)};"
             f"height:{vw(h)};font-family:'{fam}',sans-serif;font-weight:{fw};"
             f"font-size:{vw(fs)};line-height:{vw(lh)};color:{color};"
             f"text-align:{align};white-space:{ws};")
    if grad:
        style += (f"background-image:{grad};-webkit-background-clip:text;"
                  f"background-clip:text;-webkit-text-fill-color:transparent;color:transparent;")
    if ls:
        style += f"letter-spacing:{vw(ls)};"
    op = n.get('opacity', 1)
    if op < 1:
        style += f"opacity:{op};"
    tag = heading_tag(chars, fs)
    return f'<{tag} class="g-t" style="{style}">{body}</{tag}>'

# ---- semantic headings: derive one <h1> + section <h2>s from font size ----
# Pixels are unchanged: .ax-page h1/h2 are already position:absolute and *{margin:0}
# resets UA spacing, so a heading tag renders identically to the old <div>.
HDG = {'maxfs': 0.0, 'h1_used': False}

def scan_fontsizes(n):
    if n.get('visible', True) is False:
        return
    if n.get('type') == 'TEXT':
        fs = n.get('style', {}).get('fontSize', 16)
        if fs > HDG['maxfs']:
            HDG['maxfs'] = fs
    for c in n.get('children', []):
        scan_fontsizes(c)

def heading_tag(chars, fs):
    txt = (chars or '').strip()
    words = txt.split()
    mx = HDG['maxfs'] or 1
    if (not HDG['h1_used'] and fs >= mx - 0.01 and len(words) >= 2 and len(txt) <= 90):
        HDG['h1_used'] = True
        return 'h1'
    if fs >= 0.55 * mx and len(words) >= 2 and len(txt) <= 70:
        return 'h2'
    return 'div'

def radius_css(n):
    """Figma corner radius -> CSS. Every emit path needs this, including the
    clipping-frame wrapper: a rounded frame with no fill of its own used to lose
    its radius entirely and clip its children with square corners (the product
    screenshots on the manufacturing page)."""
    if n.get('type') == 'ELLIPSE':
        return "border-radius:50%;"
    rcr = n.get('rectangleCornerRadii')
    if rcr:
        return f"border-radius:{vw(rcr[0])} {vw(rcr[1])} {vw(rcr[2])} {vw(rcr[3])};"
    cr = n.get('cornerRadius')
    return f"border-radius:{vw(cr)};" if cr else ''

def shadow_css(n):
    """DROP_SHADOW -> box-shadow, INNER_SHADOW -> inset box-shadow. The inset one is
    not decoration: the design's secondary/ghost buttons have no visible stroke and
    rely on a 2px inner shadow for their entire outline."""
    shadows = []
    for e in n.get('effects', []):
        if not e.get('visible', True):
            continue
        t = e.get('type')
        if t not in ('DROP_SHADOW', 'INNER_SHADOW'):
            continue
        o = e.get('offset', {'x': 0, 'y': 0})
        parts = f"{vw(o['x'])} {vw(o['y'])} {vw(e.get('radius', 0))}"
        if e.get('spread'):
            parts += f" {vw(e['spread'])}"
        shadows.append(('inset ' if t == 'INNER_SHADOW' else '') + parts + ' ' + col(e['color']))
    return "box-shadow:" + ','.join(shadows) + ";" if shadows else ''

def box_style(n, left, top, w, h):
    """Return (klass, extra, style) for a box/image node, or None if nothing visible."""
    fills = n.get('fills')
    imgref = image_ref(fills)
    if imgref:
        nid = n['id']
        if nid.startswith('I'):
            export_id = nid[1:].split(';')[0]; method = 'asset'
        else:
            export_id = nid; method = 'shot'
        IMG_EXPORTS[imgref] = (export_id, method)
        ifill = image_fill(fills)
        sizing = image_sizing_css(ifill, w, h)
        style0 = (f"position:absolute;left:{vw(left)};top:{vw(top)};width:{vw(w)};height:{vw(h)};"
                  f"background-image:url(/assets/gen/{imgref}.png);{sizing}")
        style0 += radius_css(n)
        style0 += shadow_css(n)
        bl = blend_css(n, ifill)
        if bl:
            style0 += f"mix-blend-mode:{bl};"
        if ifill and ifill.get('opacity') is not None and ifill['opacity'] < 1:
            style0 += f"opacity:{ifill['opacity']};"
        op = n.get('opacity', 1)
        if op < 1:
            style0 += f"opacity:{op};"
        style0 += blur_css(n)
        name = (n.get('name') or '').strip()
        low = name.lower()
        generic = (not name) or low.startswith(('rectangle', 'image', 'img', 'imgi_',
                    'ellipse', 'vector', 'frame', 'group', 'mask', 'bg', 'background',
                    'gradient', 'shape', 'union', 'subtract', 'clip'))
        a11y = ' role="presentation" aria-hidden="true"' if generic else f' role="img" aria-label="{esc(name)}"'
        return ('g-img', f' data-ref="{imgref}"{a11y}', style0)
    bg = solid_fill(fills) or gradient_fill(fills, w, h)
    style = f"position:absolute;left:{vw(left)};top:{vw(top)};width:{vw(w)};height:{vw(h)};"
    if bg:
        # any gradient must go on `background`; background-color only takes a colour
        prop = 'background' if 'gradient(' in bg else 'background-color'
        style += f"{prop}:{bg};"
    style += radius_css(n)
    strokes = n.get('strokes')
    sc = solid_fill(strokes)
    if sc:
        # Figma can stroke individual SIDES (individualStrokeWeights), and a side set
        # to 0 is not drawn at all. Reading the summary `strokeWeight` alone painted a
        # full four-sided box wherever the design has a single accent rule -- which is
        # what put a border around every card heading in "Four pillars"
        # (/services/multi-cloud-cms/) and "Data Bridge" (/services/sap-ams-axiom/).
        isw = n.get('individualStrokeWeights')
        if isw:
            sides = (('top', isw.get('top', 0)), ('right', isw.get('right', 0)),
                     ('bottom', isw.get('bottom', 0)), ('left', isw.get('left', 0)))
            drawn = [f"border-{side}:{vw(w)} solid {sc};" for side, w in sides if w]
            if drawn:
                style += 'box-sizing:border-box;' + ''.join(drawn)
        else:
            sw = n.get('strokeWeight', 1)
            style += f"box-sizing:border-box;border:{vw(sw)} solid {sc};"
    style += shadow_css(n)
    bl = blend_css(n)
    if bl:
        style += f"mix-blend-mode:{bl};"
    op = n.get('opacity', 1)
    if op < 1:
        style += f"opacity:{op};"
    style += blur_css(n)
    visible = bg or sc or [e for e in n.get('effects', []) if e.get('visible', True)]
    if not visible:
        return None
    return ('g-b', '', style)

def emit_box(n, left, top, w, h):
    r = box_style(n, left, top, w, h)
    if not r:
        return ''
    klass, extra, style = r
    return f'<div class="{klass}"{extra} style="{style}"></div>'

VEC_UID = [0]

def svg_paint(paints):
    """Return (paint_ref, defs_markup) for the first visible SOLID/GRADIENT paint."""
    for f in paints or []:
        if f.get('visible', True) is False:
            continue
        t = f.get('type')
        if t == 'SOLID':
            return col(f['color'], f.get('opacity')), ''
        if t and t.startswith('GRADIENT'):
            VEC_UID[0] += 1
            gid = f'vg{VEC_UID[0]}'
            stops = ''.join(
                f'<stop offset="{s["position"]*100:.1f}%" stop-color="{col(s["color"])}"/>'
                for s in f.get('gradientStops', []))
            h = f.get('gradientHandlePositions') or []
            if t == 'GRADIENT_RADIAL':
                defs = f'<radialGradient id="{gid}">{stops}</radialGradient>'
            else:
                if len(h) >= 2:
                    x1, y1, x2, y2 = h[0]['x'], h[0]['y'], h[1]['x'], h[1]['y']
                else:
                    x1, y1, x2, y2 = 0, 0, 1, 0
                defs = (f'<linearGradient id="{gid}" x1="{x1:.3f}" y1="{y1:.3f}" '
                        f'x2="{x2:.3f}" y2="{y2:.3f}">{stops}</linearGradient>')
            return f'url(#{gid})', defs
    return 'none', ''

def emit_vector(n, left, top, w, h):
    """Render a Figma VECTOR node as inline SVG using its fill/stroke geometry."""
    fg = n.get('fillGeometry')
    sg = n.get('strokeGeometry')
    if (not fg and not sg) or w <= 0 or h <= 0:
        return ''
    fill, fdefs = svg_paint(n.get('fills'))
    stroke, sdefs = svg_paint(n.get('strokes'))
    paths = []
    for g in fg or []:
        d = g.get('path')
        if not d:
            continue
        fr = 'evenodd' if g.get('windingRule') == 'EVENODD' else 'nonzero'
        paths.append(f'<path d="{d}" fill="{fill}" fill-rule="{fr}"/>')
    # strokeGeometry is emitted by Figma as filled outline regions
    for g in sg or []:
        d = g.get('path')
        if not d:
            continue
        paths.append(f'<path d="{d}" fill="{stroke}"/>')
    if not paths:
        return ''
    defs = fdefs + sdefs
    defs = f'<defs>{defs}</defs>' if defs else ''
    style = (f"position:absolute;left:{vw(left)};top:{vw(top)};"
             f"width:{vw(w)};height:{vw(h)};overflow:visible;")
    op = n.get('opacity', 1)
    if op < 1:
        style += f"opacity:{op};"
    bl = blend_css(n)
    if bl:
        style += f"mix-blend-mode:{bl};"
    style += blur_css(n)
    return (f'<svg class="g-vec" role="presentation" aria-hidden="true" '
            f'style="{style}" viewBox="0 0 {w:.2f} {h:.2f}" '
            f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
            f'{defs}{"".join(paths)}</svg>')

VEC_EXPORTS = set()  # figma node ids to render as SVG assets

def subtree_flags(n):
    """Scan a node's visible subtree: (has_vector, has_text, has_image)."""
    has_v = has_t = has_i = False
    stack = [n]
    while stack:
        m = stack.pop()
        if m is not n and m.get('visible', True) is False:
            continue
        mt = m.get('type')
        if mt == 'TEXT':
            has_t = True
        elif mt in ('VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'REGULAR_POLYGON', 'LINE'):
            has_v = True
        if image_ref(m.get('fills')):
            has_i = True
        if has_t and has_i:
            break
        stack.extend(m.get('children', []))
    return has_v, has_t, has_i

SVG_DIMS = {}

def svg_intrinsic(nid):
    """Intrinsic px size of this node's exported SVG, or None if not downloaded."""
    if nid not in SVG_DIMS:
        dim = None
        try:
            head = open(os.path.join('assets', 'vec', nid.replace(':', '-') + '.svg'),
                        encoding='utf-8', errors='replace').read(400)
            m = re.search(r'<svg[^>]*?width="([\d.]+)"[^>]*?height="([\d.]+)"', head)
            if m:
                dim = (float(m.group(1)), float(m.group(2)))
        except OSError:
            pass
        SVG_DIMS[nid] = dim
    return SVG_DIMS[nid]

def render_box(n, ox, oy):
    """Placement box for an exported asset. Figma normally crops SVG/PNG exports to
    the node's render bounds (post-clip/effects), so that is the default. But a node
    clipped by an ancestor still exports at FULL geometry size — dropping that into
    the clipped box squashes the entire graphic into the visible sliver (this is why
    the hero sunbursts showed a whole compressed starburst instead of a corner of a
    big one). So trust the file on disk: whichever box the SVG's own intrinsic size
    matches is the box it was exported at. The ancestor's overflow:hidden (or
    .ax-page's) then reproduces Figma's clip."""
    bb = n['absoluteBoundingBox']
    rb = n.get('absoluteRenderBounds') or bb
    dim = svg_intrinsic(n['id'])
    if dim:
        fits = lambda b: abs(dim[0]-b['width']) <= 1.5 and abs(dim[1]-b['height']) <= 1.5
        if not fits(rb) and fits(bb):
            rb = bb
        # One axis agreeing and the other not means the export was cropped on that
        # other axis by an ancestor mask, while Figma still reports the UNCROPPED
        # bound. Forcing the file into that box makes the <img> letterbox it
        # (preserveAspectRatio defaults to "meet"), which slides the art off-centre:
        # the products hero grid landed 92px right of its rail, and the sap-ams-axiom
        # hero grid pushed its first stroked line into the middle of the CTAs.
        # Derive the clipped axis from the export's own aspect instead and let the
        # ancestor's overflow:hidden do the cropping -- which is what this function
        # already does everywhere else. Affects 15 placements site-wide.
        w, h = rb['width'], rb['height']
        if dim[0] and dim[1] and w and h:
            wok = abs(dim[0]-w) <= 1.5
            hok = abs(dim[1]-h) <= 1.5
            if wok != hok:
                if wok: h = w * dim[1] / dim[0]
                else:   w = h * dim[0] / dim[1]
                return rb['x']-ox, rb['y']-oy, w, h
            # NEITHER axis agrees: Figma clipped the render bounds against the page
            # edge on two sides at once, so neither the clipped box nor the layout
            # box describes the export. Drawing it in the clipped window squashed the
            # art -- the /services/ hero put a 702x1175 DNA helix into 364x1205 (52%
            # of its width) and a 1245x1325 wireframe into 1227x1113, which is why
            # those graphics read as the wrong size and too saturated: compressed
            # strokes pile on top of each other. Place the export at its true size,
            # anchored to whichever edges were NOT clipped, and let the page's own
            # overflow:hidden reproduce Figma's crop.
            lclip = rb['x'] > bb['x'] + 0.5
            tclip = rb['y'] > bb['y'] + 0.5
            if lclip or tclip:
                x = rb['x'] + rb['width'] - dim[0] if lclip else rb['x']
                y = rb['y'] + rb['height'] - dim[1] if tclip else rb['y']
                return x-ox, y-oy, dim[0], dim[1]
    return rb['x']-ox, rb['y']-oy, rb['width'], rb['height']

def emit_vec_asset(n, left, top, w, h):
    """Render a vector node/cluster as a single exported SVG asset."""
    if w <= 0 or h <= 0:
        return ''
    nid = n['id']
    VEC_EXPORTS.add(nid)
    fn = nid.replace(':', '-')
    style = (f"position:absolute;left:{vw(left)};top:{vw(top)};"
             f"width:{vw(w)};height:{vw(h)};")
    # The REST image export renders the node's own opacity into the SVG itself (same
    # reason blur is skipped below): a cluster with opacity 0.25 exports as
    # <g opacity="0.25">...</g>, not a fully-opaque file needing 0.25 applied on top.
    # Re-adding it here squared it -- 0.25 CSS x 0.25 baked-in = 0.0625, not 0.25 --
    # which is why background line-art (e.g. the Services hero) rendered at a few
    # percent opacity, effectively invisible, instead of the quarter-strength Figma
    # actually shows.
    bl = blend_css(n)
    if bl:
        style += f"mix-blend-mode:{bl};"
    # The export already HAS the layer blur baked in as an SVG filter -- that is why
    # its render bounds are bigger than its layout box (a 557x416 ellipse exports at
    # 1009x1009 under an 800px blur). Re-applying it in CSS blurs the art twice.
    style += blur_css(n, layer=False)
    # Pages carry 60+ vector exports; deferring the off-screen ones cuts the
    # first-paint request burst without touching layout (width/height come from
    # the inline style, so nothing reflows when they arrive).
    lazy = '' if top < 60 else ' loading="lazy" decoding="async"'
    return (f'<img class="g-vec" src="/assets/vec/{fn}.svg" data-vec="{nid}"'
            f'{lazy} alt="" role="presentation" aria-hidden="true" style="{style}">')

SKIP_NAMES = ('Nav Bar', 'footer', 'section.final-cta')

try:
    # id -> {"m": [a, b, c, d], "size": [w, h]}, written by _transforms.py.
    TRANSFORMS = json.load(open('_transforms.json'))
except (OSError, ValueError):
    TRANSFORMS = {}

def solve_local_size(W, H, a, b, c, d):
    """Recover a node's own w x h from the AABB (W x H) its transform produces.
    For M = [[a,c],[b,d]] the AABB of a local w x h box is
        W = |a|w + |c|h ,  H = |b|w + |d|h
    so invert that 2x2. (Pure rotation is the special case a=d=cos, c=-b=-sin.)"""
    A, B, C, D = abs(a), abs(c), abs(b), abs(d)
    det = A * D - B * C
    if abs(det) < 1e-6:            # singular (e.g. exactly 45deg rotation)
        return W, H
    w = (W * D - H * B) / det
    h = (H * A - W * C) / det
    if w <= 0 or h <= 0:           # numeric fallback
        return W, H
    return w, h

def emit_rotated(n, ox, oy):
    """Reconstruct a transformed raster container (e.g. the tilted logo cards) as
    a CSS-transformed wrapper whose children are placed in its local frame.

    The exact 2x3 matrix comes from _transforms.json when available, and it is
    worth the extra fetch: these cards are NOT purely rotated. Their basis vectors
    are 130 deg apart (rotation + shear), so treating the AABB as a rotated box
    turns a 120x120 card into a 207x51 bar -- which is exactly how the "customer
    in this vertical" logo cards were rendering. Without the matrix we fall back
    to assuming a pure rotation, which is right for everything else.

    Children carry no transform of their own here, so they inherit the wrapper's;
    each is mapped back into local space through M^-1."""
    bb = n['absoluteBoundingBox']
    th = n['rotation']
    tr = TRANSFORMS.get(n['id'])
    if tr:
        a, b, c, d = tr['m']
        w, h = tr['size']
    else:
        a = d = math.cos(th)
        b = math.sin(th)
        c = -b
        w, h = solve_local_size(bb['width'], bb['height'], a, b, c, d)
    # Absolute position of the node's local (0,0): its AABB corner, backed off by
    # the transform's own minimum corner offset.
    corners = ((0, 0), (w, 0), (0, h), (w, h))
    orx = bb['x'] - min(a * x + c * y for x, y in corners)
    ory = bb['y'] - min(b * x + d * y for x, y in corners)
    det = a * d - b * c
    left, top = orx - ox, ory - oy
    r = box_style(n, left, top, w, h)
    if r:
        klass, extra, style = r
    else:
        klass, extra, style = 'g-b', '', (
            f"position:absolute;left:{vw(left)};top:{vw(top)};"
            f"width:{vw(w)};height:{vw(h)};")
    style += (f"transform:matrix({a:.6f},{b:.6f},{c:.6f},{d:.6f},0,0);"
              f"transform-origin:0 0;")
    if n.get('clipsContent'):
        style += "overflow:hidden;"
        if 'g-clip' not in klass:
            klass += ' g-clip'
    out = [f'<div class="{klass}"{extra} style="{style}">']

    def place(m):
        if m is not n and m.get('visible', True) is False:
            return
        if m is n:
            for ch in m.get('children', []):
                place(ch)
            return
        mt = m.get('type')
        mbb = m.get('absoluteBoundingBox')
        if mbb:
            if abs(det) < 1e-9:
                return
            dx = (mbb['x'] + mbb['width'] / 2.0) - orx
            dy = (mbb['y'] + mbb['height'] / 2.0) - ory
            lxc = (d * dx - c * dy) / det                   # M^-1 * (dx, dy)
            lyc = (-b * dx + a * dy) / det
            lw, lh = solve_local_size(mbb['width'], mbb['height'], a, b, c, d)
            ll, lt = lxc - lw / 2.0, lyc - lh / 2.0
            if mt == 'TEXT':
                out.append(emit_text(m, ll, lt, lw, lh)); return
            if mt in ('RECTANGLE', 'ELLIPSE', 'LINE'):
                out.append(emit_box(m, ll, lt, lw, lh)); return
            if mt in ('VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'REGULAR_POLYGON'):
                if m.get('fillGeometry') or m.get('strokeGeometry'):
                    out.append(emit_vector(m, ll, lt, lw, lh))
                elif m.get('absoluteRenderBounds'):
                    out.append(emit_vec_asset(m, ll, lt, lw, lh))
                return
            if mt in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
                hv, ht, hi = subtree_flags(m)
                if hv and not ht and not hi:
                    if m.get('absoluteRenderBounds'):
                        out.append(emit_vec_asset(m, ll, lt, lw, lh))
                    return
                if m.get('fills') or m.get('strokes'):
                    box = emit_box(m, ll, lt, lw, lh)
                    if box:
                        out.append(box)
        for ch in m.get('children', []):
            place(ch)

    place(n)
    out.append('</div>')
    return ''.join(out)

SKIP_NODES = {
    '5232:15038', '5246:15149',  # baked navbar + announcement in Home hero (chrome provides these)
    '5637:52052',  # Leadership/mobile: unfilled 4th executive slot ("[NEEDS INPUT: Name]",
                    # generic placeholder photo) -- shipping it added a phantom 4th carousel
                    # slide, throwing off the dot count for the 3 real executives
}

def walk(n, ox, oy, out, depth=0):
    if n.get('visible', True) is False:
        return
    if n.get('id') in SKIP_NODES:
        return
    name = n.get('name', '')
    # skip shared chrome instances/frames - we reuse our own
    if depth <= 1 and (name.startswith('Nav Bar') or name == 'footer'
                       or name == 'Footer ( AeonX)'):
        return
    t = n.get('type')
    bb = n.get('absoluteBoundingBox')
    if t == 'TEXT' and bb:
        out.append(emit_text(n, bb['x']-ox, bb['y']-oy, bb['width'], bb['height']))
        return
    if t in ('RECTANGLE', 'ELLIPSE', 'LINE') and bb:
        # An angular/diamond gradient is a sweep CSS cannot reproduce faithfully --
        # conic-gradient paints the whole disc while Figma paints only a narrow arc
        # of it (compare absoluteRenderBounds: a 1042px ellipse whose ink is
        # 521x76). Export those shapes as SVG and place them by render bounds, the
        # same way vector clusters are handled.
        if exotic_gradient(n.get('fills')) and n.get('absoluteRenderBounds'):
            l, t2, w, h = render_box(n, ox, oy)
            out.append(emit_vec_asset(n, l, t2, w, h))
            return
        h = bb['height'] if t != 'LINE' else max(bb['height'], 1)
        out.append(emit_box(n, bb['x']-ox, bb['y']-oy, bb['width'], h))
        return
    if t in ('VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'REGULAR_POLYGON') and bb:
        if n.get('fillGeometry') or n.get('strokeGeometry'):
            out.append(emit_vector(n, bb['x']-ox, bb['y']-oy, bb['width'], bb['height']))
        elif n.get('absoluteRenderBounds'):  # null render bounds => not visible
            l, t2, w, h = render_box(n, ox, oy)
            out.append(emit_vec_asset(n, l, t2, w, h))
        return
    # vector-only cluster (icon / decorative line-art): export whole node as one SVG
    if t in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT') and bb:
        hv, ht, hi = subtree_flags(n)
        if hv and not ht and not hi:
            # Null absoluteRenderBounds usually does mean "nothing is painted", and
            # that check suppresses a lot of genuinely empty clusters -- dropping it
            # outright resurrected 158 of them, 156 with no exported asset, i.e. 156
            # broken images. But it is not ALWAYS true: Figma reports null render
            # bounds for some plainly visible instances. The homepage trinity cards
            # are the case -- card 1's icon carries render bounds while cards 2 and 3
            # (identical instances, visible:true, drawn in the prototype) have null,
            # so only the first icon survived. Emit on null only when the node's SVG
            # has ALREADY been exported: that is positive evidence there is real art
            # here, and it cannot invent a broken <img> for a cluster we have no file
            # for. render_box() falls back to the layout bbox for placement.
            if n.get('absoluteRenderBounds') or svg_intrinsic(n['id']):
                l, t2, w, h = render_box(n, ox, oy)
                out.append(emit_vec_asset(n, l, t2, w, h))
            return
        # rotated raster container (tilted logo/text card): the dump drops the
        # rotation, so reconstruct it in CSS instead of drawing a flat AABB box.
        rot = n.get('rotation')
        if (t in ('FRAME', 'INSTANCE', 'COMPONENT') and rot
                and abs(rot) > 0.01 and (ht or hi)):
            out.append(emit_rotated(n, ox, oy))
            return
    # container: draw its own fill (if any) then recurse
    if t in ('FRAME', 'INSTANCE', 'COMPONENT') and bb and n.get('clipsContent'):
        # clipping frame: emit a wrapper with overflow:hidden, children relative to it
        r = box_style(n, bb['x']-ox, bb['y']-oy, bb['width'], bb['height'])
        if r:
            klass, extra, style = r
        else:
            # No paint of its own, but a rounded clip still has to round its clip.
            klass, extra, style = 'g-b', '', (
                f"position:absolute;left:{vw(bb['x']-ox)};top:{vw(bb['y']-oy)};"
                f"width:{vw(bb['width'])};height:{vw(bb['height'])};" + radius_css(n))
        out.append(f'<div class="{klass} g-clip"{extra} style="{style}overflow:hidden;">')
        walk_children(n, bb['x'], bb['y'], out, depth)
        out.append('</div>')
        return
    if t in ('FRAME', 'INSTANCE', 'GROUP', 'COMPONENT') and bb:
        if n.get('fills') or n.get('strokes'):
            b = emit_box(n, bb['x']-ox, bb['y']-oy, bb['width'], bb['height'])
            if b:
                out.append(b)
    walk_children(n, ox, oy, out, depth)

def walk_children(n, ox, oy, out, depth):
    """Emit a container's children, honouring a Figma mask.

    Figma marks a mask with isMask on the FIRST child; it masks its following
    siblings and is never painted itself. _gen.py used to draw it like any other
    shape, so a white-to-transparent gradient meant as an alpha mask got painted as
    an actual white sheet -- that is the wash that swamped the DataBridge panel.
    450 nodes across the file carry isMask.

    A rectangle/ellipse mask with a fill maps onto CSS mask-image. Group and vector
    masks (arbitrary artwork) cannot, so those are simply not painted and their
    siblings render unmasked -- still wrong, but far less wrong than painting the
    mask art on top of the content."""
    kids = n.get('children') or []
    mask = kids[0] if kids and kids[0].get('isMask') else None
    if not mask:
        for c in kids:
            walk(c, ox, oy, out, depth+1)
        return
    img = mask_image_css(mask)
    rest = kids[1:]
    mb = mask.get('absoluteBoundingBox')
    if not img or not mb:
        for c in rest:
            walk(c, ox, oy, out, depth+1)
        return
    style = (f"position:absolute;left:{vw(mb['x']-ox)};top:{vw(mb['y']-oy)};"
             f"width:{vw(mb['width'])};height:{vw(mb['height'])};"
             f"-webkit-mask-image:{img};mask-image:{img};"
             "-webkit-mask-size:100% 100%;mask-size:100% 100%;"
             "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;")
    out.append(f'<div class="g-mask" style="{style}">')
    for c in rest:
        walk(c, mb['x'], mb['y'], out, depth+1)
    out.append('</div>')

def mask_image_css(mask):
    """CSS mask-image for a Figma mask shape, or None if it can't be expressed."""
    if mask.get('type') not in ('RECTANGLE', 'ELLIPSE'):
        return None
    fills = mask.get('fills') or []
    bb = mask.get('absoluteBoundingBox') or {}
    grad = gradient_fill(fills, bb.get('width'), bb.get('height'))
    if grad:
        return grad
    if solid_fill(fills):
        # a plain shape mask: fully opaque inside its box
        return 'linear-gradient(#000,#000)'
    return None

def build_body(node):
    bb = node['absoluteBoundingBox']
    ox, oy = bb['x'], bb['y']
    HDG['maxfs'] = 0.0
    HDG['h1_used'] = False
    scan_fontsizes(node)
    out = []
    ftops = {}
    for c in node.get('children', []):
        if c.get('name') in ('footer', 'Footer ( AeonX)') and c.get('visible', True) is not False:
            fbb = c.get('absoluteBoundingBox')
            if fbb:
                ftops[c.get('name')] = (fbb['y'] - oy)
        walk(c, ox, oy, out, 0)
    # a page can carry both the old hidden-in-figma 'footer' and the redesigned
    # instance; the redesign wins when both are visible
    footer_top = ftops.get('Footer ( AeonX)', ftops.get('footer'))
    return '\n'.join(out), bb['height'], footer_top

def get_shell():
    # _chrome.html is a frozen snapshot of the hand-built homepage chrome
    # (nav/mega-menu/footer/styles). Split on structural markers so edits to
    # the head/nav (adding meta tags, etc.) never shift hard-coded line offsets.
    txt = open('_chrome.html', encoding='utf-8').read()
    hend = txt.index('</header>') + len('</header>')
    top = txt[:hend]                                    # head + header
    fstart = txt.index('<section class="ax-footer"')    # footer section
    mend = txt.index('</main>')
    footer = txt[fstart:mend].rstrip()                  # footer markup only
    bottom = txt[mend:]                                 # </main> + scripts + </body>
    # absolutize asset paths for sub-directory pages
    def absol(s):
        return s.replace('"assets/', '"/assets/').replace("url(assets/", "url(/assets/")
    return absol(top), absol(footer), absol(bottom)

def main():
    nid = sys.argv[1]
    out_path = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else 'AeonX'
    canvas = load_canvas()
    node = find(canvas, nid)
    if not node:
        print('node not found', nid); sys.exit(1)
    body, page_h_px, footer_top = build_body(node)
    top, footer, bottom = get_shell()
    # set title
    top = re.sub(r'<title>.*?</title>', f'<title>{esc(title)}</title>', top, flags=re.S)
    # per-page canonical + og:url + social titles
    BASE = 'https://aeonx.digital'
    route = '/' + out_path[:-len('index.html')] if out_path.endswith('index.html') else '/' + out_path
    # An out_path of "./index.html" yields "/./", which shipped on the homepage as
    # og:url for months: the canonical was corrected once but the og:url beside it
    # was missed, so social shares carried a URL with a "/." segment in it.
    # Collapse the artefact rather than relying on every caller passing a clean path.
    route = re.sub(r'/\./', '/', route)
    url = BASE + route
    top = top.replace('</head>', f'<link rel="canonical" href="{url}">\n<meta property="og:url" content="{url}">\n</head>', 1)
    top = re.sub(r'(<meta property="og:title" content=")[^"]*(">)', lambda m: m.group(1)+esc(title)+m.group(2), top)
    top = re.sub(r'(<meta name="twitter:title" content=")[^"]*(">)', lambda m: m.group(1)+esc(title)+m.group(2), top)
    # reposition reused footer to this page's footer offset
    if footer_top is None:
        # figma node carries no footer instance (designer omission) -- append the
        # shared footer right after the content instead of leaving the page bare
        print(f'NOTE {nid}: no footer child in figma node, appending at content end')
        footer_top = page_h_px
    if footer_top is not None:
        footer = re.sub(r'top:[\d.]+vw', f'top:{vw(footer_top)}', footer, count=1)
        # the shared footer is 850px tall; a page whose figma node still holds
        # the old 580px footer is 270px short and .ax-page{overflow:hidden}
        # would clip it -- grow the page to fit
        fh = re.search(r'height:([\d.]+)vw', footer)
        if fh:
            page_h_px = max(page_h_px, footer_top + float(fh.group(1)) * 1920 / 100)
    main_open = f'<main class="ax-page" style="height:{vw(page_h_px)}">'
    html_out = top + '\n' + main_open + '\n' + body + '\n' + footer + '\n' + bottom
    import os
    # dirname is '' for a bare filename, which makedirs rejects. Every generated page
    # used to live in a subdirectory, so this only shows up once the homepage itself
    # is generated to index.html at the repo root.
    if os.path.dirname(out_path):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(html_out)
    # report image refs needing export
    refs = set(re.findall(r'data-ref="([^"]+)"', html_out))
    print(f'wrote {out_path}  ({len(body)} bytes body, {len(refs)} unique images)')
    import os
    for ref in sorted(refs):
        exists = os.path.exists(f'assets/gen/{ref}.png')
        # refs baked into the shared chrome were emitted by an earlier run, so they
        # are not in this run's IMG_EXPORTS. They are already on disk; don't crash.
        eid, method = IMG_EXPORTS.get(ref, ('-', 'chrome'))
        print(f'EXPORT {ref} {eid} {method} {"HAVE" if exists else "NEED"}')
    for nid in sorted(VEC_EXPORTS):
        fn = nid.replace(':', '-')
        exists = os.path.exists(f'assets/vec/{fn}.svg')
        print(f'VEC {nid} {"HAVE" if exists else "NEED"}')

if __name__ == '__main__':
    main()
