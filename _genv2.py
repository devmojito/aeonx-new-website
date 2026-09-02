"""Run _gen.py against the Light V2 canvas instead of the production dump.

_gen.load_canvas() is hardcoded to aeonx-node.json / node 4020:9394. The V2 design
lives on a different canvas (6719:21340) in the same Figma file, so rather than
splicing it into the 88MB production dump (destructive, and _figsync's own backups
are the only way back) this points the loader at a separate file with the same
envelope. Usage is identical to _gen.py:

    python3 _genv2.py 6719:32547 index-v2.html "AeonX Digital"
"""
import json, sys
import _gen

_gen.load_canvas = lambda: json.load(open('aeonx-v2.json'))['nodes']['4020:9394']['document']

if __name__ == '__main__':
    _gen.main()
