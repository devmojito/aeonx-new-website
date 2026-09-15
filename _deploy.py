#!/usr/bin/env python3
"""Deploy the built site to S3 behind CloudFront, uploading only the public tree.

    python3 _deploy.py            # stage, check, rsync to EC2, s3 sync --delete, invalidate
    python3 _deploy.py --dry      # stage and check only, print what would ship
    python3 _deploy.py --all      # as above, but re-upload every file so its headers are reset

What ships is decided by .vercelignore, the same file Vercel reads, so both targets
serve identical content. A hand-written rsync exclude list drifted from it once and
published backend/ (its local .env included), the generator scripts and the harvested
JSON at aeonx.digital. The stage is now built from that one file and checked for
anything that must never be public before a single byte leaves this machine.
"""
import os, re, subprocess, sys, tempfile

HOST = 'ec2-user@13.204.150.143'
KEY = os.path.expanduser('~/.ssh/aeonx-ec2.pem')
BUCKET = 's3://aeonx-website-hosting/'
DIST = 'E3OYGVP63K0FQS'
# Never public, whatever .vercelignore says. Checked against the staged tree.
FORBIDDEN = re.compile(r'(^|/)(backend/|\.env[^/]*$|_[^/]*\.(py|json|html)$|[^/]*\.pem$|CLAUDE\.md$|'
                       r'\.git/|\.claude/|node_modules/|aeonx-(node|mobile|v2|home-geo)\.json$|\.vercel/)')
EXTRA_EXCLUDES = ['.env*', '.vercel/', '.DS_Store', '__pycache__/', 'vercel.json',
                  '.vercelignore', '.gitignore', 'infra/', 'HANDOVER.md']


def rsync_filters():
    """.vercelignore is gitignore syntax; rsync takes first match, so every
    re-include (!pattern) has to come before the excludes it punches through."""
    inc, exc = [], []
    for raw in open('.vercelignore', encoding='utf-8'):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        (inc if line.startswith('!') else exc).append(line.lstrip('!'))
    exc += EXTRA_EXCLUDES
    return ['+ ' + p for p in inc] + ['- ' + p for p in exc]


def run(cmd, **kw):
    print('+', cmd if isinstance(cmd, str) else ' '.join(cmd))
    return subprocess.run(cmd, check=True, **kw)


def main():
    dry = '--dry' in sys.argv
    stage = tempfile.mkdtemp(prefix='aeonx-stage-')
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.rules') as f:
        f.write('\n'.join(rsync_filters()) + '\n')
        rules = f.name
    run(['rsync', '-a', '--delete', '--filter=merge ' + rules, './', stage + '/'])
    bad = []
    for root, dirs, files in os.walk(stage):
        for name in files + [d + '/' for d in dirs]:
            rel = os.path.relpath(os.path.join(root, name), stage)
            if name.endswith('/'):
                rel += '/'
            if FORBIDDEN.search(rel):
                bad.append(rel)
    if bad:
        sys.exit('REFUSING TO DEPLOY, private files staged:\n  ' + '\n  '.join(sorted(bad)[:40]))
    n = sum(len(fs) for _, _, fs in os.walk(stage))
    print('staged %d files in %s, none private' % (n, stage))
    if dry:
        return
    ssh = 'ssh -i %s -o StrictHostKeyChecking=no' % KEY
    run(['rsync', '-az', '--delete', '-e', ssh, stage + '/', HOST + ':~/aeonx-site/'])
    # Three groups, three Cache-Control values. Pages: browsers always revalidate,
    # the edge keeps them a day and every deploy invalidates. assets/gen: file names
    # are the Figma image hash, so a changed image is a new name and the old one can
    # be cached for a year. Everything else (SVG exports keep their node id as the
    # name and get overwritten in place): a day. `sync` only touches changed files, so
    # --all re-uploads the lot once to put headers on files that predate this.
    verb = 'cp --recursive' if '--all' in sys.argv else 'sync --delete'
    # The CLI on the instance guesses .webp as binary/octet-stream, so WebP gets its
    # own passes with the type stated. A re-upload once shipped all 385 that way.
    groups = [
        ('--exclude "*" --include "*.html" --include "*.xml" --include "*.txt"',
         'public, max-age=0, s-maxage=86400, must-revalidate', None),
        ('--exclude "*" --include "assets/gen/*" --exclude "*.webp"',
         'public, max-age=31536000, immutable', None),
        ('--exclude "*" --include "assets/gen/*.webp"',
         'public, max-age=31536000, immutable', 'image/webp'),
        ('--exclude "*" --include "*.webp" --exclude "assets/gen/*"',
         'public, max-age=86400', 'image/webp'),
        ('--exclude "*.html" --exclude "*.xml" --exclude "*.txt" --exclude "assets/gen/*" --exclude "*.webp"',
         'public, max-age=86400', None),
    ]
    passes = ' && '.join('aws s3 %s . %s %s --cache-control "%s"%s --only-show-errors'
                         % (verb, BUCKET, f, cc, (' --content-type %s' % ct) if ct else '')
                         for f, cc, ct in groups)
    if '--all' in sys.argv:          # cp never deletes, so clear stale files first
        passes = 'aws s3 sync . %s --delete --only-show-errors && %s' % (BUCKET, passes)
    remote = ('cd ~/aeonx-site && %s && echo S3_OK && '
              'aws cloudfront create-invalidation --distribution-id %s --paths "/*" '
              '--query Invalidation.Id --output text') % (passes, DIST)
    run(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, remote])


if __name__ == '__main__':
    main()
