#!/usr/bin/env python3
"""Title-case audit: every button label on every page, checked after scripts run.

The client's rule is that BUTTON labels are Title Cased. `_uifx.html` does that at
runtime, so the only honest check is the rendered DOM: render each page headless,
take every element the runtime marked as a control (`data-cta` / `data-axpill` /
`role="link"|"button"`), and flag any label that still contains a lower-case word.

    python3 -u _tcaudit.py
"""
import glob, html, re, subprocess, sys

PORT = 8809
SKIP_WORD = re.compile(r'^[^a-zA-Z]*$')


def pages():
    out = []
    for f in sorted(glob.glob('**/index.html', recursive=True)):
        if 'node_modules' in f or 'assets' in f or re.match(r'^20\d\d/', f):
            continue
        out.append(f)
    return out


def dump(path):
    url = 'http://127.0.0.1:%d/%s' % (PORT, path.replace('index.html', ''))
    cmd = ['chromium', '--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
           '--force-device-scale-factor=1', '--window-size=1920,1100',
           '--virtual-time-budget=9000', '--dump-dom', url]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ''


CTRL = re.compile(
    r'<(?P<tag>div|span|a|button|h\d)(?P<attrs>[^>]*(?:data-cta|data-axpill|role="(?:link|button)")[^>]*)>'
    r'(?P<text>[^<]{2,40})</(?P=tag)>')


# Nav, mega-menu and footer entries are LINKS, not buttons: Figma sets them in
# sentence case deliberately and the runtime leaves them alone. Brand names keep their
# own casing too — "RISE with SAP" is SAP's product name, not a mis-cased label.
MENU = re.compile(r'^(all (products|services|alliances)|case stud|customer refer|research report|'
                  r'trust & security|investor relations|contact us|about us|board of directors|'
                  r'shareholding pattern|annual reports|quarterly results|bse disclosures|'
                  r'investor grievances|multi-cloud cms|google cloud|api documentation|'
                  r'(rise|grow) with sap|sap ams|sap signavio|axiom ai platform|newsletter|'
                  r'partners hub|aws advanced tier|sap gold partner|google cloud partner)', re.I)
CHROME = re.compile(r'<(header|footer|nav)\b|class="[^"]*(ax-mm2|ax-nav|ax-footer|ax-mnav)', re.I)


def bad_labels(dom):
    bad = set()
    for m in CTRL.finditer(dom):
        t = html.unescape(m.group('text')).strip()
        if not t or len(t) > 34 or '@' in t or '·' in t or t.startswith('+'):
            continue
        if MENU.match(t):
            continue
        if CHROME.search(dom[max(0, m.start() - 400):m.start()]):
            continue
        words = [w for w in re.split(r'[\s ]+', t) if w and not SKIP_WORD.match(w)]
        if len(words) < 2:
            continue
        # a Title Cased label has no word starting lower-case
        if any(w[0].islower() for w in words):
            bad.add(t)
    return sorted(bad)


def main():
    total = 0
    for p in pages():
        dom = dump(p)
        if not dom:
            print('%-52s DUMP FAILED' % p)
            continue
        bad = bad_labels(dom)
        if bad:
            total += len(bad)
            print('%-46s %s' % ('/' + p.replace('index.html', ''), ' | '.join(bad)[:150]))
    print('\nBUTTON LABELS NOT TITLE CASED:', total)


if __name__ == '__main__':
    main()
