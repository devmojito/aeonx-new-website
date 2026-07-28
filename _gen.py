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

def gradient_fill(fills):
    for f in fills or []:
        if f.get('visible', True) is False:
            continue
        t = f.get('type', '')
        if t.startswith('GRADIENT'):
            stops = f.get('gradientStops', [])
            sl = ', '.join(f"{col(s['color'])} {s['position']*100:.1f}%" for s in stops)
            if t == 'GRADIENT_RADIAL':
                return f"radial-gradient(circle, {sl})"
            # approximate linear angle from handles
            h = f.get('gradientHandlePositions')
            ang = 180
            if h and len(h) >= 2:
                import math
                dx = h[1]['x']-h[0]['x']; dy = h[1]['y']-h[0]['y']
                ang = (math.degrees(math.atan2(dx, -dy))) % 360
            return f"linear-gradient({ang:.0f}deg, {sl})"
    return None

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

def blur_css(n):
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
        if ifill and ifill.get('scaleMode') == 'TILE':
            sizing = "background-size:auto;background-repeat:repeat;"
        else:
            sizing = "background-size:cover;background-position:center;background-repeat:no-repeat;"
        style0 = (f"position:absolute;left:{vw(left)};top:{vw(top)};width:{vw(w)};height:{vw(h)};"
                  f"background-image:url(/assets/gen/{imgref}.png);{sizing}")
        cr = n.get('cornerRadius')
        if n.get('type') == 'ELLIPSE':
            style0 += "border-radius:50%;"
        elif cr:
            style0 += f"border-radius:{vw(cr)};"
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
    bg = solid_fill(fills) or gradient_fill(fills)
    style = f"position:absolute;left:{vw(left)};top:{vw(top)};width:{vw(w)};height:{vw(h)};"
    if bg:
        prop = 'background' if (bg.startswith('linear') or bg.startswith('radial')) else 'background-color'
        style += f"{prop}:{bg};"
    if n.get('type') == 'ELLIPSE':
        style += "border-radius:50%;"
    else:
        rcr = n.get('rectangleCornerRadii')
        cr = n.get('cornerRadius')
        if rcr:
            style += f"border-radius:{vw(rcr[0])} {vw(rcr[1])} {vw(rcr[2])} {vw(rcr[3])};"
        elif cr:
            style += f"border-radius:{vw(cr)};"
    strokes = n.get('strokes')
    sc = solid_fill(strokes)
    if sc:
        sw = n.get('strokeWeight', 1)
        style += f"box-sizing:border-box;border:{vw(sw)} solid {sc};"
    # DROP_SHADOW -> box-shadow, INNER_SHADOW -> inset box-shadow. The inset one is
    # not decoration: the design's secondary/ghost buttons have no visible stroke and
    # rely on a 2px inner shadow for their entire outline.
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
    if shadows:
        style += "box-shadow:" + ','.join(shadows) + ";"
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
    op = n.get('opacity', 1)
    if op < 1:
        style += f"opacity:{op};"
    bl = blend_css(n)
    if bl:
        style += f"mix-blend-mode:{bl};"
    style += blur_css(n)
    return (f'<img class="g-vec" src="/assets/vec/{fn}.svg" data-vec="{nid}" '
            f'alt="" role="presentation" aria-hidden="true" style="{style}">')

SKIP_NAMES = ('Nav Bar', 'footer', 'section.final-cta')

def solve_true_size(W, H, th):
    """Given a node's axis-aligned bounding box (W x H) and its rotation `th`
    (radians), recover the node's true pre-rotation width/height. Figma's dump
    lacks relativeTransform/size, so we invert AABB = R(th)*(w,h):
        W = w*cos + h*sin ,  H = w*sin + h*cos
    """
    c, s = abs(math.cos(th)), abs(math.sin(th))
    det = c * c - s * s
    if abs(det) < 1e-4:            # ~45deg: singular, no clean inverse
        return W, H
    w = (W * c - H * s) / det
    h = (H * c - W * s) / det
    if w <= 0 or h <= 0:           # numeric fallback
        return W, H
    return w, h

def emit_rotated(n, ox, oy):
    """Reconstruct a rotated raster container (e.g. the tilted logo cards) as a
    CSS-rotated wrapper whose children are placed in its local (unrotated) frame.
    Rotation preserves the node's center, so the true-size box is centered on the
    AABB center; children are inverse-rotated into local coordinates and inherit
    the wrapper's rotation via CSS (so no per-child transform is needed while the
    child's own rotation is ~0, which holds for these cards)."""
    bb = n['absoluteBoundingBox']
    th = n['rotation']
    cx = bb['x'] + bb['width'] / 2.0
    cy = bb['y'] + bb['height'] / 2.0
    w, h = solve_true_size(bb['width'], bb['height'], th)
    deg = math.degrees(th)
    c, s = math.cos(th), math.sin(th)   # R(-th) = [[c, s], [-s, c]]
    left, top = cx - w / 2.0 - ox, cy - h / 2.0 - oy
    r = box_style(n, left, top, w, h)
    if r:
        klass, extra, style = r
    else:
        klass, extra, style = 'g-b', '', (
            f"position:absolute;left:{vw(left)};top:{vw(top)};"
            f"width:{vw(w)};height:{vw(h)};")
    style += f"transform:rotate({deg:.4f}deg);transform-origin:center center;"
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
            dx = (mbb['x'] + mbb['width'] / 2.0) - cx
            dy = (mbb['y'] + mbb['height'] / 2.0) - cy
            lxc, lyc = c * dx + s * dy, -s * dx + c * dy    # inverse-rotate
            lw, lh = solve_true_size(mbb['width'], mbb['height'], th)
            ll, lt = w / 2.0 + lxc - lw / 2.0, h / 2.0 + lyc - lh / 2.0
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
                    b = emit_box(m, ll, lt, lw, lh)
                    if b:
                        out.append(b)
        for ch in m.get('children', []):
            place(ch)

    place(n)
    out.append('</div>')
    return ''.join(out)

SKIP_NODES = {'5232:15038', '5246:15149'}  # baked navbar + announcement in Home hero (chrome provides these)

def walk(n, ox, oy, out, depth=0):
    if n.get('visible', True) is False:
        return
    if n.get('id') in SKIP_NODES:
        return
    name = n.get('name', '')
    # skip shared chrome instances/frames - we reuse our own
    if depth <= 1 and (name.startswith('Nav Bar') or name == 'footer'):
        return
    t = n.get('type')
    bb = n.get('absoluteBoundingBox')
    if t == 'TEXT' and bb:
        out.append(emit_text(n, bb['x']-ox, bb['y']-oy, bb['width'], bb['height']))
        return
    if t in ('RECTANGLE', 'ELLIPSE', 'LINE') and bb:
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
            if n.get('absoluteRenderBounds'):
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
            klass, extra, style = 'g-b', '', (
                f"position:absolute;left:{vw(bb['x']-ox)};top:{vw(bb['y']-oy)};"
                f"width:{vw(bb['width'])};height:{vw(bb['height'])};")
        out.append(f'<div class="{klass} g-clip"{extra} style="{style}overflow:hidden;">')
        for c in n.get('children', []):
            walk(c, bb['x'], bb['y'], out, depth+1)
        out.append('</div>')
        return
    if t in ('FRAME', 'INSTANCE', 'GROUP', 'COMPONENT') and bb:
        if n.get('fills') or n.get('strokes'):
            b = emit_box(n, bb['x']-ox, bb['y']-oy, bb['width'], bb['height'])
            if b:
                out.append(b)
    for c in n.get('children', []):
        walk(c, ox, oy, out, depth+1)

def build_body(node):
    bb = node['absoluteBoundingBox']
    ox, oy = bb['x'], bb['y']
    HDG['maxfs'] = 0.0
    HDG['h1_used'] = False
    scan_fontsizes(node)
    out = []
    footer_top = None
    for c in node.get('children', []):
        if c.get('name') == 'footer' and c.get('visible', True) is not False:
            fbb = c.get('absoluteBoundingBox')
            if fbb:
                footer_top = (fbb['y'] - oy)
        walk(c, ox, oy, out, 0)
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
    url = BASE + route
    top = top.replace('</head>', f'<link rel="canonical" href="{url}">\n<meta property="og:url" content="{url}">\n</head>', 1)
    top = re.sub(r'(<meta property="og:title" content=")[^"]*(">)', lambda m: m.group(1)+esc(title)+m.group(2), top)
    top = re.sub(r'(<meta name="twitter:title" content=")[^"]*(">)', lambda m: m.group(1)+esc(title)+m.group(2), top)
    # reposition reused footer to this page's footer offset
    if footer_top is not None:
        footer = re.sub(r'top:[\d.]+vw', f'top:{vw(footer_top)}', footer, count=1)
    main_open = f'<main class="ax-page" style="height:{vw(page_h_px)}">'
    html_out = top + '\n' + main_open + '\n' + body + '\n' + footer + '\n' + bottom
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(html_out)
    # report image refs needing export
    refs = set(re.findall(r'data-ref="([^"]+)"', html_out))
    print(f'wrote {out_path}  ({len(body)} bytes body, {len(refs)} unique images)')
    import os
    for ref in sorted(refs):
        exists = os.path.exists(f'assets/gen/{ref}.png')
        eid, method = IMG_EXPORTS[ref]
        print(f'EXPORT {ref} {eid} {method} {"HAVE" if exists else "NEED"}')
    for nid in sorted(VEC_EXPORTS):
        fn = nid.replace(':', '-')
        exists = os.path.exists(f'assets/vec/{fn}.svg')
        print(f'VEC {nid} {"HAVE" if exists else "NEED"}')

if __name__ == '__main__':
    main()
