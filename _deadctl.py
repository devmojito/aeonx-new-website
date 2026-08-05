#!/usr/bin/env python3
"""Dead-control sweep: every element that LOOKS interactive but has nothing wired.

Renders each built page in headless Chromium (so all runtime passes -- the CTA
linkifier, _hover, the page-scoped fragments -- have run), dumps the live DOM and
reports controls that carry no destination and no handler affordance.

A control counts as WIRED if, after scripts run, it is inside an <a href> that is
not "#", or carries role=link/button, or was marked by our own passes
(data-cta / data-axcta / data-axpill), or ended up with cursor:pointer inline.

    python3 _deadctl.py            # all designed pages
    python3 _deadctl.py insights   # only paths containing "insights"
"""
import glob, os, re, subprocess, sys, html

PORT = 8809
VOCAB = re.compile(
    r'^(search\.{0,3}|filter by [a-z ]+|subscribe|submit|send( message)?|load more|view all|see all|'
    r'show more|download( [a-z ]+)?|read more|read the story|learn more|sign up( to [a-z ]+)?|apply( now)?|'
    r'watch( [a-z ]+)?|play|get started|talk to us|talk to a specialist|contact us|request a proposal|'
    r'request the trust pack|book a demo|explore( .+)?|next|previous|prev|\d{1,2}|reset form|'
    r'see the suite|meet axiom|read us|get in touch|join us|see how it works)$', re.I)

SKIP_PATH = ('node_modules', 'assets')


def pages(filt=None):
    out = []
    for f in sorted(glob.glob('**/index.html', recursive=True)):
        if any(s in f for s in SKIP_PATH):
            continue
        if re.match(r'^20\d\d/', f):          # blog posts: normal-flow prose, not designed controls
            continue
        if filt and filt not in f:
            continue
        out.append(f)
    return out


def dump(path):
    url = 'http://127.0.0.1:%d/%s' % (PORT, path.replace('index.html', ''))
    cmd = ['chromium', '--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
           '--force-device-scale-factor=1', '--window-size=1920,1100',
           '--virtual-time-budget=9000', '--dump-dom', url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.stdout
    except Exception as e:
        return ''


TAG = re.compile(r'<(?P<tag>div|span|a|button|h\d)(?P<attrs>[^>]*)>(?P<text>[^<]{1,60})</(?P=tag)>')


def scan(dom, path):
    dead = []
    # anchors are their own answer; find the enclosing tag of every short text run
    for m in TAG.finditer(dom):
        text = html.unescape(m.group('text')).strip()
        if not text or not VOCAB.match(text):
            continue
        attrs = m.group('attrs')
        tag = m.group('tag')
        # context: the 400 chars before this element carry the parent's opening tag
        ctx = dom[max(0, m.start() - 600):m.start()]
        blob = attrs + ' ' + ctx[-600:]
        wired = False
        if tag == 'a' and re.search(r'href="(?!#)[^"]+"', attrs):
            wired = True
        if re.search(r'<a [^>]*href="(?!#)[^"]+"[^>]*>\s*$', ctx):
            wired = True
        if re.search(r'role="(link|button|tab)"', blob):
            wired = True
        if re.search(r'data-(cta|axcta|axpill|axcsf|menu|cat)=', blob):
            wired = True
        if re.search(r'cursor:\s*pointer', blob):
            wired = True
        if not wired:
            dead.append(text)
    return dead


def main():
    filt = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    for p in pages(filt):
        dom = dump(p)
        if not dom:
            print('%-52s DUMP FAILED' % p)
            continue
        dead = scan(dom, p)
        # collapse duplicates, keep counts
        seen = {}
        for d in dead:
            k = d.lower()
            seen[k] = seen.get(k, 0) + 1
        if seen:
            total += len(seen)
            items = ', '.join('%s x%d' % (k, v) if v > 1 else k for k, v in sorted(seen.items()))
            print('%-52s %s' % ('/' + p.replace('index.html', ''), items[:240]))
        else:
            print('%-52s ok' % ('/' + p.replace('index.html', '')))
    print('\nDISTINCT DEAD CONTROL LABELS:', total)


if __name__ == '__main__':
    main()
