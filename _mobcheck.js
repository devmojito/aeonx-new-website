/* Mobile fidelity check: the rendered .ax-mob block vs the Figma mobile frame.
 *
 * Loaded into a page at 430px. Reads _mobaudit_expected.json (written by
 * _mobaudit.py) and reports, for this route:
 *   - copy the design has that the page does not render, and vice versa
 *   - position / font-size / weight / colour deltas per text node
 *   - text the page renders at different CASE than the design (the Title Case pass)
 *   - authored-vs-live drift (a runtime pass moved an element after build)
 *   - text or boxes crossing the 430px frame edge
 *   - page height vs the Figma frame height
 *   - broken images
 *
 * Geometry is read from the element's own inline style (vw) as well as from a live
 * rect: the inline value is what the generator authored, the rect is what the user
 * sees, and the interesting failures live in the gap between them (HANDOFF 19.6).
 *
 * Result lands on window.__mobresult.
 */
(function () {
  window.__mobresult = null;
  var POS_TOL = 0.15;   // vw
  var FS_TOL = 0.05;    // vw
  var route = location.pathname.replace(/^\/|\/$/g, '') || 'index.html';

  function norm(s) { return (s || '').replace(/\s+/g, ' ').trim(); }
  function key(s) { return norm(s).toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 60); }
  function num(el, prop) {
    var m = (el.getAttribute('style') || '').match(new RegExp(prop + ':\\s*(-?[\\d.]+)vw'));
    return m ? parseFloat(m[1]) : null;
  }

  fetch('/_mobaudit_expected.json').then(function (r) { return r.json(); }).then(function (all) {
    // keys are the routes _mobile.py writes: bare paths, plus 'index.html' for home.
    // No blanket fallback -- an unmapped route must report as unmapped, not silently
    // get compared against the homepage.
    var exp = all[route] || (route === 'index.html' ? all['index.html'] : null);
    var out = { route: route, ok: !!exp };
    if (!exp) { window.__mobresult = out; return; }

    document.querySelectorAll('.ax-rv,.ax-rvo').forEach(function (e) { e.classList.add('ax-in'); });
    var s = document.createElement('style');
    s.textContent = '*{transition:none!important;animation:none!important}';
    document.head.appendChild(s);

    var mob = document.querySelector('.ax-mob');
    out.mobPresent = !!mob;
    if (!mob) { window.__mobresult = out; return; }

    var els = [].slice.call(mob.querySelectorAll('.g-t')).filter(function (e) {
      return norm(e.textContent).length > 0;
    });

    // index rendered elements by normalised text
    var byKey = {};
    els.forEach(function (e) {
      var k = key(e.textContent);
      (byKey[k] = byKey[k] || []).push(e);
    });

    var missing = [], deltas = [], caseDiffs = [], drift = [];
    var usedEls = new Set();

    exp.texts.forEach(function (x) {
      var k = key(x.text);
      var pool = (byKey[k] || []).filter(function (e) { return !usedEls.has(e); });
      if (!pool.length) {
        // try a prefix match: the design string is truncated to 80 chars
        var alt = els.filter(function (e) {
          return !usedEls.has(e) && key(e.textContent).indexOf(k.slice(0, 40)) === 0;
        });
        if (!alt.length) { missing.push(x.text.slice(0, 60)); return; }
        pool = alt;
      }
      // nearest by authored position
      pool.sort(function (a, b) {
        function d(e) {
          var l = num(e, 'left'), t = num(e, 'top');
          if (l === null || t === null) return 1e9;
          return Math.abs(l - x.left) + Math.abs(t - x.top);
        }
        return d(a) - d(b);
      });
      var el = pool[0];
      usedEls.add(el);

      var cs = getComputedStyle(el);
      var vw = innerWidth / 100;
      var al = num(el, 'left'), at = num(el, 'top');
      var r = el.getBoundingClientRect();
      var liveL = r.left / vw, liveT = (r.top + scrollY) / vw;

      var d = {};
      if (al !== null && Math.abs(al - x.left) > POS_TOL) d.left = [x.left, +al.toFixed(3)];
      if (at !== null && Math.abs(at - x.top) > POS_TOL) d.top = [x.top, +at.toFixed(3)];
      if (x.fs) {
        var fsvw = parseFloat(cs.fontSize) / vw;
        if (Math.abs(fsvw - x.fs) > FS_TOL) d.fs = [x.fs, +fsvw.toFixed(3)];
      }
      if (x.fw && String(cs.fontWeight) !== String(x.fw)) d.fw = [x.fw, cs.fontWeight];
      if (x.color && x.color !== 'GRADIENT' && cs.color !== x.color) d.color = [x.color, cs.color];
      if (Object.keys(d).length) { d.text = x.text.slice(0, 46); deltas.push(d); }

      if (norm(el.textContent) !== norm(x.text) && key(el.textContent) === k) {
        caseDiffs.push([x.text.slice(0, 46), norm(el.textContent).slice(0, 46)]);
      }
      if (al !== null && Math.abs(liveL - al) > 0.6) {
        drift.push({ text: x.text.slice(0, 34), authoredL: +al.toFixed(2), liveL: +liveL.toFixed(2) });
      }
    });

    out.expected = exp.texts.length;
    out.rendered = els.length;
    out.missing = missing;
    out.extra = els.filter(function (e) { return !usedEls.has(e); })
      .map(function (e) { return norm(e.textContent).slice(0, 46); });
    out.deltas = deltas;
    out.caseDiffs = caseDiffs;
    out.drift = drift;

    // frame-edge overflow: anything whose live rect crosses the viewport edge
    var vwpx = innerWidth;
    out.overflowRight = [].slice.call(mob.querySelectorAll('.g-t,.g-b,.g-img,.g-vec'))
      .map(function (e) { var r = e.getBoundingClientRect(); return { e: e, r: r }; })
      .filter(function (o) { return o.r.width > 0 && o.r.right > vwpx + 1 && o.r.left < vwpx; })
      .map(function (o) {
        return { t: norm(o.e.textContent).slice(0, 34) || o.e.className,
                 right: Math.round(o.r.right), over: Math.round(o.r.right - vwpx) };
      }).slice(0, 12);

    out.docScrollW = document.documentElement.scrollWidth;
    out.horizOverflow = out.docScrollW > vwpx + 1;

    var page = mob.querySelector('main.ax-page');
    out.pageH = page ? Math.round(page.getBoundingClientRect().height) : null;
    out.figmaH = Math.round(exp.frame.h * vwpx / 430);
    out.heightDeltaPx = out.pageH !== null ? out.pageH - out.figmaH : null;

    var imgs = [].slice.call(mob.querySelectorAll('img'));
    out.imgTotal = imgs.length;
    out.brokenImgs = imgs.filter(function (i) { return i.complete && i.naturalWidth === 0; })
      .map(function (i) { return i.getAttribute('src'); }).slice(0, 10);

    window.__mobresult = out;
  }).catch(function (e) { window.__mobresult = { route: route, error: String(e) }; });
})();
