// node infra/cloudfront/viewer-request.test.js '<json [[src, dst], ...]>'
// Loads the generated function the way CloudFront would and checks every alias
// plus the routing the site depends on today.
const fs = require('fs');
const path = require('path');
const src = fs.readFileSync(path.join(__dirname, 'viewer-request.js'), 'utf8');
const handler = new Function(src + '\nreturn handler;')();

function ev(host, uri, qs) {
  const querystring = {};
  for (const [k, v] of Object.entries(qs || {})) querystring[k] = { value: v };
  return { request: { method: 'GET', uri, querystring, headers: { host: { value: host } } } };
}
let fail = 0;
function expect(label, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) { fail++; console.log('FAIL', label, '\n  got ', JSON.stringify(got), '\n  want', JSON.stringify(want)); }
}
const loc = r => (r.statusCode ? [r.statusCode, r.headers.location.value] : ['pass', r.uri]);

const cases = JSON.parse(process.argv[2] || '[]');
for (const [from, to] of cases) {
  expect('alias ' + from, loc(handler(ev('aeonx.digital', from))), [301, 'https://aeonx.digital' + to]);
  expect('alias no slash ' + from, loc(handler(ev('aeonx.digital', from.replace(/\/$/, '')))), [301, 'https://aeonx.digital' + to]);
}
expect('www', loc(handler(ev('www.aeonx.digital', '/products/quic/', { a: '1' }))), [301, 'https://aeonx.digital/products/quic/?a=1']);
expect('www root', loc(handler(ev('www.aeonx.digital', '/'))), [301, 'https://aeonx.digital/']);
expect('root', loc(handler(ev('aeonx.digital', '/'))), ['pass', '/index.html']);
expect('dir slash', loc(handler(ev('aeonx.digital', '/products/quic/'))), ['pass', '/products/quic/index.html']);
expect('dir no slash', loc(handler(ev('aeonx.digital', '/products/quic'))), ['pass', '/products/quic/index.html']);
expect('file', loc(handler(ev('aeonx.digital', '/assets/og-cover.png'))), ['pass', '/assets/og-cover.png']);
expect('sitemap', loc(handler(ev('aeonx.digital', '/sitemap.xml'))), ['pass', '/sitemap.xml']);
expect('query kept on alias', loc(handler(ev('aeonx.digital', '/about-us/', { utm_source: 'x' }))), [301, 'https://aeonx.digital/who-we-are/foundation/?utm_source=x']);
expect('api untouched', loc(handler(ev('aeonx.digital', '/api/announcement/'))), ['pass', '/api/announcement/']);
expect('manage untouched', loc(handler(ev('aeonx.digital', '/manage/'))), ['pass', '/manage/']);
expect('real post untouched', loc(handler(ev('aeonx.digital', '/2023/04/14/itd/05/25/44/240713/success-stories-sap/admin/'))), ['pass', '/2023/04/14/itd/05/25/44/240713/success-stories-sap/admin/index.html']);
console.log(fail ? fail + ' failed' : 'all ' + (cases.length * 2 + 11) + ' checks passed');
process.exit(fail ? 1 : 0);
