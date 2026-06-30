#!/usr/bin/env python3
"""Generate an AeonX sub-page from the Figma full-canvas dump, reusing the
shared chrome (nav/mega-menu/footer/styles) extracted from index.html.

Usage: python3 _gen.py <NODE_ID> <out_path> "<Page Title>"
Body nodes are flattened to absolute vw positions, same convention as index.html.
"""
import json, sys, html, re

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
    color = solid_fill(n.get('fills')) or '#15181e'
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
    if cso and any(cso):
        def color_for(i):
            sid = cso[i] if i < len(cso) else 0
            if sid and str(sid) in sot:
                c = solid_fill(sot[str(sid)].get('fills'))
                if c:
                    return c
            return None
        parts = []
        i = 0
        while i < len(chars):
            c0 = color_for(i)
            j = i
            while j < len(chars) and color_for(j) == c0:
                j += 1
            seg = seg_html(chars[i:j])
            parts.append(f'<span style="position:static;color:{c0}">{seg}</span>' if c0 else seg)
            i = j
        body = ''.join(parts)
    else:
        body = seg_html(chars)
    style = (f"position:absolute;left:{vw(left)};top:{vw(top)};width:{vw(w)};"
             f"height:{vw(h)};font-family:'{fam}',sans-serif;font-weight:{fw};"
             f"font-size:{vw(fs)};line-height:{vw(lh)};color:{color};"
             f"text-align:{align};white-space:{ws};")
    if ls:
        style += f"letter-spacing:{vw(ls)};"
    op = n.get('opacity', 1)
    if op < 1:
        style += f"opacity:{op};"
    return f'<div class="g-t" style="{style}">{body}</div>'

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
        return ('g-img', f' data-ref="{imgref}"', style0)
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
    for e in n.get('effects', []):
        if e.get('visible', True) and e.get('type') == 'DROP_SHADOW':
            o = e.get('offset', {'x':0,'y':0}); rad = e.get('radius',0)
            style += f"box-shadow:{vw(o['x'])} {vw(o['y'])} {vw(rad)} {col(e['color'])};"
            break
    bl = blend_css(n)
    if bl:
        style += f"mix-blend-mode:{bl};"
    op = n.get('opacity', 1)
    if op < 1:
        style += f"opacity:{op};"
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

SKIP_NAMES = ('Nav Bar', 'footer', 'section.final-cta')

def walk(n, ox, oy, out, depth=0):
    if n.get('visible', True) is False:
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
    if t == 'VECTOR':
        return  # icons handled separately
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
    # (nav/mega-menu/footer/styles). index.html itself is regenerated from
    # Figma, so it must NOT be the shell source or the line offsets break.
    lines = open('_chrome.html', encoding='utf-8').read().split('\n')
    top = '\n'.join(lines[0:179])          # up to </header> (line 179)
    footer = lines[191]                     # line 192 footer
    bottom = '\n'.join(lines[192:])         # </main> + scripts + </body>
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

if __name__ == '__main__':
    main()
