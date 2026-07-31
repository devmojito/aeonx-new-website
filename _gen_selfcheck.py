#!/usr/bin/env python3
"""Smallest thing that fails if the paint/radius emitters break. python3 _gen_selfcheck.py"""
import _gen

TEAL = {'r': 0.0196, 'g': 0.502, 'b': 0.4588, 'a': 0.6}

# A gradient paint carries its OWN opacity, which Figma multiplies into every stop.
grad = [{'type': 'GRADIENT_LINEAR', 'opacity': 0.1,
         'gradientHandlePositions': [{'x': 0, 'y': 0.5}, {'x': 1, 'y': 0.5}, {'x': 0, 'y': 1.8}],
         'gradientStops': [{'color': TEAL, 'position': 0.0},
                           {'color': dict(TEAL, a=1.0), 'position': 1.0}]}]
css = _gen.gradient_fill(grad, 451, 602)
assert '0.060' in css, css          # 0.6 stop alpha * 0.1 paint opacity
assert '0.100' in css, css          # 1.0 stop alpha * 0.1 paint opacity
assert '0.600' not in css, css      # the bug: paint opacity ignored

# Paint with no opacity key must be left alone.
plain = [{k: v for k, v in grad[0].items() if k != 'opacity'}]
assert '0.600' in _gen.gradient_fill(plain, 451, 602)

# A rounded frame keeps its radius whether or not it paints anything.
assert _gen.radius_css({'type': 'FRAME', 'cornerRadius': 16.0}) == 'border-radius:0.8333vw;'
assert _gen.radius_css({'type': 'ELLIPSE'}) == 'border-radius:50%;'
assert _gen.radius_css({'type': 'FRAME'}) == ''

# Effects reach image nodes too, not just plain boxes.
sh = _gen.shadow_css({'effects': [{'type': 'DROP_SHADOW', 'visible': True,
                                   'offset': {'x': 0, 'y': -1}, 'radius': 0, 'spread': 5,
                                   'color': {'r': 0.875, 'g': 0.247, 'b': 0.09, 'a': 0.37}}]})
assert sh.startswith('box-shadow:0.0000vw -0.0521vw 0.0000vw 0.2604vw rgba('), sh

print('ok')
