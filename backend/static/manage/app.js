/* AeonX content admin — vanilla, no build step.
   Each page template calls one AX.<page>() initialiser at the bottom of the
   body; everything else in here is shared plumbing. */
(function (window, document) {
  'use strict';

  var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return [].slice.call((root || document).querySelectorAll(sel)); };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function toast(msg, kind) {
    var host = $('#toasts');
    if (!host) return;
    var el = document.createElement('div');
    el.className = 'toast' + (kind ? ' toast--' + kind : '');
    el.textContent = msg;
    host.appendChild(el);
    setTimeout(function () { el.remove(); }, kind === 'bad' ? 6000 : 3200);
  }

  /* Every non-2xx is surfaced, never swallowed: a silent failure in a tool that
     publishes regulatory filings is worse than a blunt error message. A 401
     means the session expired, which is recoverable only by signing in again. */
  function req(url, opts) {
    opts = opts || {};
    var headers = opts.headers || {};
    if (opts.method && opts.method !== 'GET') headers['X-CSRFToken'] = CSRF;
    return fetch(url, {
      method: opts.method || 'GET',
      headers: headers,
      body: opts.body,
      credentials: 'same-origin'
    }).then(function (r) {
      if (r.status === 401) {
        window.location.href = '/manage/login/?next=' + encodeURIComponent(location.pathname);
        throw new Error('signed out');
      }
      var ct = r.headers.get('Content-Type') || '';
      if (ct.indexOf('application/json') === -1) {
        if (!r.ok) throw new Error('Server error (' + r.status + ')');
        return r;
      }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || 'Something went wrong.');
        return data;
      });
    });
  }

  function json(url, method, obj) {
    return req(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(obj || {})
    });
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  }
  function fmtWhen(iso) {
    var d = new Date(iso), now = new Date();
    var mins = Math.round((now - d) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + ' min ago';
    if (mins < 1440) return Math.round(mins / 60) + ' hr ago';
    return fmtDate(iso);
  }

  /* debounce so typing in a search box does not fire a request per keystroke */
  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms || 260);
    };
  }

  function modal(title, bodyHTML, footHTML) {
    var el = document.createElement('div');
    el.className = 'modal';
    el.innerHTML =
      '<div class="modal__box" role="dialog" aria-modal="true">' +
        '<div class="modal__hd"><h2>' + esc(title) + '</h2>' +
          '<button class="modal__x" type="button" aria-label="Close">&times;</button></div>' +
        '<div class="modal__bd">' + bodyHTML + '</div>' +
        '<div class="modal__ft">' + (footHTML || '') + '</div>' +
      '</div>';
    document.body.appendChild(el);
    function close() { el.remove(); document.removeEventListener('keydown', onKey); }
    function onKey(e) { if (e.key === 'Escape') close(); }
    $('.modal__x', el).addEventListener('click', close);
    el.addEventListener('click', function (e) { if (e.target === el) close(); });
    document.addEventListener('keydown', onKey);
    var focusable = $('input,select,textarea,button', $('.modal__bd', el));
    if (focusable) focusable.focus();
    return { el: el, close: close };
  }

  function confirmDanger(title, message, confirmLabel) {
    return new Promise(function (resolve) {
      var m = modal(title,
        '<p style="margin:0;color:var(--body)">' + esc(message) + '</p>',
        '<button class="btn" data-no>Cancel</button>' +
        '<button class="btn btn--primary" data-yes>' + esc(confirmLabel || 'Confirm') + '</button>');
      $('[data-no]', m.el).addEventListener('click', function () { m.close(); resolve(false); });
      $('[data-yes]', m.el).addEventListener('click', function () { m.close(); resolve(true); });
    });
  }

  function pager(el, data, onGo) {
    if (!el) return;
    if (!data.total) { el.innerHTML = ''; return; }
    /* The page size differs per endpoint (documents 25, posts 20); assuming
       one of them made the other's range read wrong. */
    var size = data.page_size || 25;
    var from = (data.page - 1) * size + 1;
    var to = Math.min(data.page * size, data.total);
    el.innerHTML =
      '<span>' + from + '–' + to + ' of ' + data.total + '</span>' +
      '<button class="btn btn--sm" data-p="' + (data.page - 1) + '"' + (data.page <= 1 ? ' disabled' : '') + '>Previous</button>' +
      '<button class="btn btn--sm" data-p="' + (data.page + 1) + '"' + (data.page >= data.pages ? ' disabled' : '') + '>Next</button>';
    $$('[data-p]', el).forEach(function (b) {
      b.addEventListener('click', function () { onGo(+b.dataset.p); });
    });
  }

  function badgeNewCount(n) {
    var b = $('#nav-new');
    if (!b) return;
    if (n > 0) { b.textContent = n; b.hidden = false; } else { b.hidden = true; }
  }

  /* ------------------------------------------------------------ dashboard */
  function dashboard() {
    req('/manage/api/stats/').then(function (d) {
      badgeNewCount(d.submissions_new);
      var cards = [
        { n: d.documents, l: 'Documents', href: '/manage/documents/' },
        { n: d.published, l: 'Published', href: '/manage/documents/?status=published' },
        { n: d.unpublished, l: 'Unpublished', href: '/manage/documents/?status=unpublished' },
        { n: d.missing_file, l: 'Missing file', href: '/manage/documents/?status=missing', alert: d.missing_file > 0 },
        { n: d.submissions_new, l: 'New enquiries', href: '/manage/enquiries/', alert: d.submissions_new > 0 }
      ];
      $('#stats').innerHTML = cards.map(function (c) {
        return '<div class="stat' + (c.alert ? ' stat--alert' : '') + '"><a href="' + c.href + '">' +
          '<div class="stat__n">' + c.n + '</div><div class="stat__l">' + c.l + '</div></a></div>';
      }).join('');

      if (d.missing_file > 0) $('#missing-card').hidden = false;

      $('#recent tbody').innerHTML = d.recent.length ? d.recent.map(function (r) {
        return '<tr><td><div class="tbl__title">' + esc(r.title) + '</div>' +
          '<div class="tbl__sub">' + esc(r.section) + ' · ' + esc(r.category) + '</div></td>' +
          '<td style="white-space:nowrap;color:var(--muted)">' + fmtWhen(r.created_at) + '</td>' +
          '<td>' + (r.is_published ? '<span class="pill pill--ok">Published</span>'
                                   : '<span class="pill pill--off">Draft</span>') + '</td></tr>';
      }).join('') : '<tr><td class="empty">Nothing uploaded yet.</td></tr>';
    }).catch(function (e) { toast(e.message, 'bad'); });
  }

  /* ------------------------------------------------------------ documents */
  function documents() {
    var state = { page: 1, search: '', section: '', category: '', status: '', sort: '', selected: {} };
    var params = new URLSearchParams(location.search);
    state.status = params.get('status') || '';
    state.sort = params.get('sort') || '';
    var tax = { sections: [] };

    $('#f-status').value = state.status;

    req('/manage/api/taxonomy/').then(function (d) {
      tax = d;
      $('#f-section').innerHTML = '<option value="">All sections</option>' +
        d.sections.map(function (s) {
          return '<option value="' + esc(s.slug) + '">' + esc(s.name) + '</option>';
        }).join('');
      fillCategories();
    });

    function fillCategories() {
      var sec = tax.sections.filter(function (s) { return s.slug === state.section; });
      var cats = (state.section ? sec : tax.sections).reduce(function (acc, s) {
        return acc.concat(s.categories.map(function (c) {
          return { id: c.id, name: (state.section ? '' : s.name + ' · ') + c.name };
        }));
      }, []);
      $('#f-category').innerHTML = '<option value="">All categories</option>' +
        cats.map(function (c) { return '<option value="' + c.id + '">' + esc(c.name) + '</option>'; }).join('');
    }

    function load() {
      var q = new URLSearchParams();
      q.set('page', state.page);
      if (state.search) q.set('search', state.search);
      if (state.section) q.set('section', state.section);
      if (state.category) q.set('category', state.category);
      if (state.status) q.set('status', state.status);
      if (state.sort) q.set('sort', state.sort);
      req('/manage/api/documents/?' + q).then(render).catch(function (e) { toast(e.message, 'bad'); });
    }

    function render(d) {
      var canPub = d.can_publish;
      if (!d.results.length) {
        $('#rows').innerHTML = '<tr><td colspan="7" class="empty"><b>No documents match</b>' +
          'Try a different search or filter.</td></tr>';
        pager($('#pager'), d, function (p) { state.page = p; load(); });
        return;
      }
      $('#rows').innerHTML = d.results.map(function (r) {
        var file = r.has_file
          ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">View</a>'
          : (r.is_unavailable ? '<span class="pill pill--warn">Missing</span>'
                              : '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">External</a>');
        return '<tr data-id="' + r.id + '">' +
          '<td><input type="checkbox" class="row-check" value="' + r.id + '"' +
              (state.selected[r.id] ? ' checked' : '') + '></td>' +
          '<td><div class="tbl__title">' + esc(r.title) + '</div>' +
              '<div class="tbl__sub">' + esc(r.category) + '</div></td>' +
          '<td style="color:var(--body)">' + esc(r.section) + '</td>' +
          '<td style="white-space:nowrap;color:var(--body)">' + (r.date_label || '—') + '</td>' +
          '<td>' + file + '</td>' +
          '<td>' + (r.is_published ? '<span class="pill pill--ok">Published</span>'
                                   : '<span class="pill pill--off">Draft</span>') + '</td>' +
          '<td><div class="tbl__actions">' +
            '<button class="btn btn--sm" data-edit="' + r.id + '">Edit</button>' +
            (canPub ? '<button class="btn btn--sm" data-toggle="' + r.id + '">' +
                      (r.is_published ? 'Unpublish' : 'Publish') + '</button>' +
                      '<button class="btn btn--sm btn--danger" data-del="' + r.id + '">Delete</button>' : '') +
          '</div></td></tr>';
      }).join('');

      $$('[data-edit]').forEach(function (b) {
        b.addEventListener('click', function () {
          editDoc(d.results.filter(function (x) { return x.id === +b.dataset.edit; })[0]);
        });
      });
      $$('[data-toggle]').forEach(function (b) {
        b.addEventListener('click', function () {
          var row = d.results.filter(function (x) { return x.id === +b.dataset.toggle; })[0];
          var fd = new FormData();
          fd.append('is_published', row.is_published ? 'false' : 'true');
          b.disabled = true;
          req('/manage/api/documents/' + row.id + '/', { method: 'POST', body: fd })
            .then(function () { toast(row.is_published ? 'Unpublished.' : 'Published — live now.', 'ok'); load(); })
            .catch(function (e) { toast(e.message, 'bad'); b.disabled = false; });
        });
      });
      $$('[data-del]').forEach(function (b) {
        b.addEventListener('click', function () {
          var row = d.results.filter(function (x) { return x.id === +b.dataset.del; })[0];
          confirmDanger('Delete document',
            '“' + row.title + '” will be removed from the website and its file deleted. This cannot be undone.',
            'Delete').then(function (ok) {
            if (!ok) return;
            req('/manage/api/documents/' + row.id + '/delete/', { method: 'POST' })
              .then(function () { toast('Deleted.', 'ok'); load(); })
              .catch(function (e) { toast(e.message, 'bad'); });
          });
        });
      });
      $$('.row-check').forEach(function (c) {
        c.addEventListener('change', function () {
          if (c.checked) state.selected[c.value] = true; else delete state.selected[c.value];
          syncBulk();
        });
      });
      syncBulk();
      pager($('#pager'), d, function (p) { state.page = p; load(); });
    }

    function syncBulk() {
      var n = Object.keys(state.selected).length;
      var bar = $('#bulkbar');
      if (!bar) return;
      bar.hidden = n === 0;
      $('#bulk-n').textContent = n + ' selected';
    }

    function editDoc(row) {
      var cats = tax.sections.reduce(function (acc, s) {
        return acc.concat(s.categories.map(function (c) {
          return '<option value="' + c.id + '"' + (row && c.id === row.category_id ? ' selected' : '') + '>' +
                 esc(s.name + ' · ' + c.name) + '</option>';
        }));
      }, []).join('');
      var isNew = !row;
      var m = modal(isNew ? 'Upload document' : 'Edit document',
        '<div class="field"><label class="label">Title</label>' +
          '<input class="input" id="m-title" value="' + esc(row ? row.title : '') + '" placeholder="e.g. Board Meeting Outcome — 26 May 2026"></div>' +
        '<div class="field"><label class="label">Category</label>' +
          '<select class="select" id="m-cat">' + cats + '</select></div>' +
        '<div class="field"><label class="label">Date of filing</label>' +
          '<input class="input" id="m-date" type="date" value="' + (row && row.date ? row.date : '') + '">' +
          '<div class="hint">Shown on the website as e.g. “Jun 2026”, and used for ordering.</div></div>' +
        '<div class="field"><label class="label">' + (isNew ? 'File' : 'Replace file') + '</label>' +
          '<input class="input" id="m-file" type="file" accept=".pdf,.xlsx,.xls,.doc,.docx,.zip">' +
          '<div class="hint">' + (isNew ? 'PDF preferred.' : 'Leave empty to keep the current file.') + '</div>' +
          '<div class="progress" id="m-prog" hidden><div class="progress__bar" id="m-bar"></div></div></div>' +
        '<label style="display:flex;gap:8px;align-items:center;font-weight:600">' +
          '<input type="checkbox" id="m-pub"' + (!row || row.is_published ? ' checked' : '') + '> Publish to the website' +
        '</label>',
        '<button class="btn" data-cancel>Cancel</button>' +
        '<button class="btn btn--primary" data-save>' + (isNew ? 'Upload' : 'Save') + '</button>');

      $('[data-cancel]', m.el).addEventListener('click', m.close);
      $('[data-save]', m.el).addEventListener('click', function () {
        var btn = this;
        var fd = new FormData();
        var title = $('#m-title', m.el).value.trim();
        if (!title) { toast('Give the document a title.', 'bad'); return; }
        fd.append('title', title);
        fd.append('category_id', $('#m-cat', m.el).value);
        fd.append('date', $('#m-date', m.el).value);
        if ($('#m-pub', m.el).checked) fd.append('is_published', 'true');
        else if (!isNew) fd.append('is_published', 'false');
        var f = $('#m-file', m.el).files[0];
        if (f) fd.append('file', f);
        if (isNew && !f) { toast('Attach a file to upload.', 'bad'); return; }

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Saving';
        var url = isNew ? '/manage/api/documents/create/' : '/manage/api/documents/' + row.id + '/';
        upload(url, fd, function (pct) {
          $('#m-prog', m.el).hidden = false;
          $('#m-bar', m.el).style.width = pct + '%';
        }).then(function () {
          m.close();
          toast(isNew ? 'Uploaded.' : 'Saved.', 'ok');
          load();
        }).catch(function (e) {
          toast(e.message, 'bad');
          btn.disabled = false;
          btn.textContent = isNew ? 'Upload' : 'Save';
        });
      });
    }

    /* XHR rather than fetch purely for upload progress -- fetch cannot report it,
       and a filing can be a 20 MB scan on a slow office line. */
    function upload(url, formData, onProgress) {
      return new Promise(function (resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        xhr.setRequestHeader('X-CSRFToken', CSRF);
        xhr.upload.addEventListener('progress', function (e) {
          if (e.lengthComputable && onProgress) onProgress(Math.round(e.loaded / e.total * 100));
        });
        xhr.onload = function () {
          var data = {};
          try { data = JSON.parse(xhr.responseText); } catch (err) { /* non-JSON error page */ }
          if (xhr.status >= 200 && xhr.status < 300) resolve(data);
          else reject(new Error(data.detail || 'Upload failed (' + xhr.status + ')'));
        };
        xhr.onerror = function () { reject(new Error('Network error during upload.')); };
        xhr.send(formData);
      });
    }

    $('#add-doc').addEventListener('click', function () { editDoc(null); });
    $('#f-search').addEventListener('input', debounce(function (e) {
      state.search = e.target.value; state.page = 1; load();
    }));
    $('#f-section').addEventListener('change', function (e) {
      state.section = e.target.value; state.category = ''; state.page = 1;
      fillCategories(); load();
    });
    $('#f-category').addEventListener('change', function (e) {
      state.category = e.target.value; state.page = 1; load();
    });
    $('#f-status').addEventListener('change', function (e) {
      state.status = e.target.value; state.page = 1; load();
    });
    $('#check-all').addEventListener('change', function (e) {
      $$('.row-check').forEach(function (c) {
        c.checked = e.target.checked;
        if (c.checked) state.selected[c.value] = true; else delete state.selected[c.value];
      });
      syncBulk();
    });
    $('#bulk-clear').addEventListener('click', function () {
      state.selected = {}; $$('.row-check').forEach(function (c) { c.checked = false; });
      $('#check-all').checked = false; syncBulk();
    });
    $$('[data-bulk]').forEach(function (b) {
      b.addEventListener('click', function () {
        var ids = Object.keys(state.selected).map(Number);
        if (!ids.length) return;
        json('/manage/api/documents/bulk/', 'POST', { ids: ids, action: b.dataset.bulk })
          .then(function (d) {
            toast(d.count + ' document(s) ' + b.dataset.bulk + 'ed.', 'ok');
            state.selected = {}; load();
          }).catch(function (e) { toast(e.message, 'bad'); });
      });
    });

    req('/manage/api/stats/').then(function (d) { badgeNewCount(d.submissions_new); });
    load();
  }

  /* ---------------------------------------------------------- submissions */
  function submissions() {
    var state = { page: 1, search: '', status: 'new' };

    function load() {
      var q = new URLSearchParams();
      q.set('page', state.page);
      q.set('status', state.status);
      if (state.search) q.set('search', state.search);
      req('/manage/api/enquiries/?' + q).then(render).catch(function (e) { toast(e.message, 'bad'); });
    }

    function render(d) {
      badgeNewCount(d.new_count);
      if (!d.results.length) {
        $('#rows').innerHTML = '<tr><td colspan="6" class="empty"><b>Nothing here</b>' +
          (state.status === 'new' ? 'No new enquiries.' : 'No enquiries match.') + '</td></tr>';
        pager($('#pager'), d, function (p) { state.page = p; load(); });
        return;
      }
      $('#rows').innerHTML = d.results.map(function (r) {
        return '<tr>' +
          '<td style="white-space:nowrap;color:var(--body)">' + fmtWhen(r.created_at) + '</td>' +
          '<td><div class="tbl__title">' + esc(r.full_name) + '</div>' +
              '<div class="tbl__sub">' + esc(r.company_name) + '</div></td>' +
          '<td><span class="pill ' + (r.kind === 'talk' ? 'pill--new' : 'pill--off') + '">' + esc(r.kind_label) + '</span></td>' +
          '<td><a href="mailto:' + esc(r.email) + '">' + esc(r.email) + '</a>' +
              '<div class="tbl__sub">' + esc(r.phone) + '</div></td>' +
          '<td>' + (r.is_handled ? '<span class="pill pill--ok">Handled</span>'
                                 : '<span class="pill pill--new">New</span>') + '</td>' +
          '<td><div class="tbl__actions">' +
            '<button class="btn btn--sm" data-view="' + r.id + '">View</button>' +
            '<button class="btn btn--sm" data-handled="' + r.id + '">' +
              (r.is_handled ? 'Reopen' : 'Mark handled') + '</button>' +
          '</div></td></tr>';
      }).join('');

      $$('[data-view]').forEach(function (b) {
        b.addEventListener('click', function () {
          view(d.results.filter(function (x) { return x.id === +b.dataset.view; })[0]);
        });
      });
      $$('[data-handled]').forEach(function (b) {
        b.addEventListener('click', function () {
          var r = d.results.filter(function (x) { return x.id === +b.dataset.handled; })[0];
          json('/manage/api/enquiries/' + r.id + '/', 'POST', { is_handled: !r.is_handled })
            .then(function () { toast(r.is_handled ? 'Reopened.' : 'Marked handled.', 'ok'); load(); })
            .catch(function (e) { toast(e.message, 'bad'); });
        });
      });
      pager($('#pager'), d, function (p) { state.page = p; load(); });
    }

    function row(label, value) {
      if (!value) return '';
      return '<div class="field"><div class="label">' + esc(label) + '</div>' +
             '<div style="color:var(--body);white-space:pre-wrap">' + esc(value) + '</div></div>';
    }

    function view(r) {
      modal(r.full_name + ' · ' + r.company_name,
        row('Received', new Date(r.created_at).toLocaleString('en-IN')) +
        row('Enquiry type', r.kind_label) +
        row('Email', r.email) + row('Phone', r.phone) +
        row('Role', r.role) + row('Notes', r.additional_information) +
        row('Region', r.region) + row('Engagement', r.type_of_engagement) +
        row('Timeline', r.timeline) + row('Description', r.brief_description) +
        row('Submitted from', r.source_page) +
        (r.notify_email_sent ? '' :
          '<div class="login__err">The notification email to sales did not send. ' +
          'Follow up manually — the enquiry itself is safely recorded.</div>'),
        '<a class="btn btn--primary" href="mailto:' + esc(r.email) + '">Reply by email</a>');
    }

    $('#f-search').addEventListener('input', debounce(function (e) {
      state.search = e.target.value; state.page = 1; load();
    }));
    $('#f-status').addEventListener('change', function (e) {
      state.status = e.target.value; state.page = 1; load();
    });
    load();
  }

  /* ------------------------------------------------------------- taxonomy */
  function taxonomy() {
    function load() {
      req('/manage/api/taxonomy/').then(render).catch(function (e) { toast(e.message, 'bad'); });
      req('/manage/api/stats/').then(function (d) { badgeNewCount(d.submissions_new); });
    }

    function render(d) {
      $('#sections').innerHTML = d.sections.map(function (s) {
        return '<div class="card" style="margin-bottom:16px">' +
          '<div class="card__hd"><h2>' + esc(s.name) + '</h2>' +
            '<span class="pill pill--off">' + esc(s.slug) + '</span>' +
            '<button class="btn btn--sm btn--primary" data-add="' + s.id + '">Add category</button></div>' +
          '<div class="tbl-scroll"><table class="tbl"><tbody>' +
          (s.categories.length ? s.categories.map(function (c) {
            return '<tr><td><div class="tbl__title">' + esc(c.name) + '</div></td>' +
              '<td style="color:var(--body);white-space:nowrap">' + c.doc_count + ' document' + (c.doc_count === 1 ? '' : 's') + '</td>' +
              '<td style="width:120px"><div class="tbl__actions">' +
                '<button class="btn btn--sm" data-ren="' + c.id + '" data-name="' + esc(c.name) + '">Rename</button>' +
                (c.doc_count === 0 ? '<button class="btn btn--sm btn--danger" data-delcat="' + c.id + '">Delete</button>' : '') +
              '</div></td></tr>';
          }).join('') : '<tr><td class="empty">No categories yet.</td></tr>') +
          '</tbody></table></div></div>';
      }).join('');

      $$('[data-add]').forEach(function (b) {
        b.addEventListener('click', function () { editCat(null, +b.dataset.add); });
      });
      $$('[data-ren]').forEach(function (b) {
        b.addEventListener('click', function () { editCat({ id: +b.dataset.ren, name: b.dataset.name }); });
      });
      $$('[data-delcat]').forEach(function (b) {
        b.addEventListener('click', function () {
          confirmDanger('Delete category', 'This category is empty and will be removed.', 'Delete')
            .then(function (ok) {
              if (!ok) return;
              req('/manage/api/categories/' + b.dataset.delcat + '/', { method: 'DELETE' })
                .then(function () { toast('Category deleted.', 'ok'); load(); })
                .catch(function (e) { toast(e.message, 'bad'); });
            });
        });
      });
    }

    function editCat(cat, sectionId) {
      var m = modal(cat ? 'Rename category' : 'Add category',
        '<div class="field"><label class="label">Name</label>' +
        '<input class="input" id="c-name" value="' + esc(cat ? cat.name : '') + '" placeholder="e.g. Board Meeting"></div>',
        '<button class="btn" data-cancel>Cancel</button>' +
        '<button class="btn btn--primary" data-save>Save</button>');
      $('[data-cancel]', m.el).addEventListener('click', m.close);
      $('[data-save]', m.el).addEventListener('click', function () {
        var name = $('#c-name', m.el).value.trim();
        if (!name) { toast('Give the category a name.', 'bad'); return; }
        var p = cat
          ? json('/manage/api/categories/' + cat.id + '/', 'PATCH', { name: name })
          : json('/manage/api/categories/', 'POST', { name: name, section_id: sectionId });
        p.then(function () { m.close(); toast('Saved.', 'ok'); load(); })
         .catch(function (e) { toast(e.message, 'bad'); });
      });
    }

    load();
  }


  /* ----------------------------------------------------------------- blog */

  /* Minimal rich-text editor on contenteditable. document.execCommand is
     formally deprecated but is the only thing every browser still implements
     for this, and the alternative is a third-party library -- which this repo
     deliberately does not do. Output is plain semantic HTML, which is exactly
     what the static generator expects to receive. */
  function makeEditor(host, initialHTML, postId) {
    var BAR = [
      ['h2', 'H2', 'Heading'], ['h3', 'H3', 'Subheading'], ['p', '¶', 'Paragraph'],
      ['|'],
      ['bold', '<b>B</b>', 'Bold (Ctrl+B)'], ['italic', '<i>I</i>', 'Italic (Ctrl+I)'],
      ['|'],
      ['insertUnorderedList', '• List', 'Bulleted list'],
      ['insertOrderedList', '1. List', 'Numbered list'],
      ['blockquote', '❝', 'Quote'],
      ['|'],
      ['createLink', 'Link', 'Add link'], ['unlink', 'Unlink', 'Remove link'],
      ['image', 'Image', 'Insert image'],
      ['|'],
      ['removeFormat', 'Clear', 'Strip formatting']
    ];

    var wrap = document.createElement('div');
    wrap.className = 'editor';
    var bar = document.createElement('div');
    bar.className = 'editor__bar';
    var area = document.createElement('div');
    area.className = 'editor__area';
    area.contentEditable = 'true';
    area.setAttribute('data-placeholder', 'Write the post…');
    area.innerHTML = initialHTML || '';

    BAR.forEach(function (item) {
      if (item[0] === '|') {
        var sep = document.createElement('span');
        sep.className = 'editor__sep';
        bar.appendChild(sep);
        return;
      }
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'editor__b';
      b.innerHTML = item[1];
      b.title = item[2];
      b.dataset.cmd = item[0];
      /* mousedown, not click: click fires after the editor has already lost
         focus and the selection has collapsed, so the command would apply to
         nothing. */
      b.addEventListener('mousedown', function (e) { e.preventDefault(); exec(item[0]); });
      bar.appendChild(b);
    });

    function exec(cmd) {
      area.focus();
      if (cmd === 'h2' || cmd === 'h3' || cmd === 'p') {
        document.execCommand('formatBlock', false, cmd.toUpperCase());
      } else if (cmd === 'blockquote') {
        document.execCommand('formatBlock', false, 'BLOCKQUOTE');
      } else if (cmd === 'createLink') {
        var url = window.prompt('Link URL');
        if (url) document.execCommand('createLink', false, url);
      } else if (cmd === 'image') {
        pickImage();
      } else {
        document.execCommand(cmd, false, null);
      }
      sync();
    }

    function pickImage() {
      var input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.addEventListener('change', function () {
        var f = input.files[0];
        if (!f) return;
        var fd = new FormData();
        fd.append('image', f);
        if (postId) fd.append('post_id', postId);
        toast('Uploading image…');
        req('/manage/api/blog/image/', { method: 'POST', body: fd })
          .then(function (d) {
            area.focus();
            document.execCommand('insertHTML', false, '<img src="' + d.url + '" alt="">');
            sync();
            toast('Image inserted.', 'ok');
          })
          .catch(function (e) { toast(e.message, 'bad'); });
      });
      input.click();
    }

    function sync() {
      [].forEach.call(bar.querySelectorAll('.editor__b'), function (b) {
        var c = b.dataset.cmd;
        var on = false;
        try {
          if (c === 'bold' || c === 'italic') on = document.queryCommandState(c);
        } catch (e) { /* not all states are queryable everywhere */ }
        b.classList.toggle('is-on', !!on);
      });
    }

    area.addEventListener('keyup', sync);
    area.addEventListener('mouseup', sync);
    /* Paste as plain text by default. Pasting from Word or Google Docs drags in
       font tags, inline styles and class names that fight the site's own type
       scale -- the single most common way a CMS article ends up looking wrong. */
    area.addEventListener('paste', function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData('text/plain');
      document.execCommand('insertText', false, text);
    });

    wrap.appendChild(bar);
    wrap.appendChild(area);
    host.appendChild(wrap);
    return { getHTML: function () { return area.innerHTML; }, focus: function () { area.focus(); } };
  }

  function blog() {
    var state = { page: 1, search: '', category: '', status: '' };
    var cats = [];

    function load() {
      var q = new URLSearchParams();
      q.set('page', state.page);
      if (state.search) q.set('search', state.search);
      if (state.category) q.set('category', state.category);
      if (state.status) q.set('status', state.status);
      req('/manage/api/blog/?' + q).then(render).catch(function (e) { toast(e.message, 'bad'); });
      req('/manage/api/blog/stats/').then(function (s) {
        $('#pub-summary').textContent =
          s.total + ' posts · ' + s.published + ' published · ' + s.drafts + ' draft';
        var b = $('#nav-drafts');
        if (b) { if (s.drafts) { b.textContent = s.drafts; b.hidden = false; } else b.hidden = true; }
      });
    }

    function render(d) {
      if (!cats.length) {
        cats = d.categories;
        $('#f-category').innerHTML = '<option value="">All categories</option>' +
          cats.map(function (c) { return '<option value="' + esc(c.slug) + '">' + esc(c.name) + '</option>'; }).join('');
      }
      if (!d.results.length) {
        $('#rows').innerHTML = '<tr><td colspan="6" class="empty"><b>No posts match</b>Try a different search.</td></tr>';
        pager($('#pager'), d, function (p) { state.page = p; load(); });
        return;
      }
      $('#rows').innerHTML = d.results.map(function (r) {
        var thumb = r.cover_url
          ? '<img class="post-thumb" src="' + esc(r.cover_url) + '" alt="">'
          : '<div class="post-thumb post-thumb--ph">—</div>';
        return '<tr>' +
          '<td>' + thumb + '</td>' +
          '<td><div class="tbl__title">' + esc(r.title) + '</div>' +
              '<div class="tbl__sub">' + esc(r.path) + '</div></td>' +
          '<td style="color:var(--body)">' + esc(r.category) + '</td>' +
          '<td style="white-space:nowrap;color:var(--body)">' + fmtDate(r.published_at) + '</td>' +
          '<td>' + (r.is_published ? '<span class="pill pill--ok">Published</span>'
                                   : '<span class="pill pill--off">Draft</span>') + '</td>' +
          '<td><div class="tbl__actions">' +
            '<button class="btn btn--sm" data-edit="' + r.id + '">Edit</button>' +
            (d.can_publish ? '<button class="btn btn--sm btn--danger" data-del="' + r.id + '">Delete</button>' : '') +
          '</div></td></tr>';
      }).join('');

      $$('[data-edit]').forEach(function (b) {
        b.addEventListener('click', function () { openPost(+b.dataset.edit); });
      });
      $$('[data-del]').forEach(function (b) {
        b.addEventListener('click', function () {
          var r = d.results.filter(function (x) { return x.id === +b.dataset.del; })[0];
          confirmDanger('Delete post',
            '“' + r.title + '” and its cover image will be permanently removed. ' +
            'Its URL will 404 for anyone who has it bookmarked or found it in search.',
            'Delete').then(function (ok) {
            if (!ok) return;
            req('/manage/api/blog/' + r.id + '/delete/', { method: 'POST' })
              .then(function () { toast('Post deleted.', 'ok'); load(); })
              .catch(function (e) { toast(e.message, 'bad'); });
          });
        });
      });
      pager($('#pager'), d, function (p) { state.page = p; load(); });
    }

    function openPost(id) {
      var p = id ? req('/manage/api/blog/' + id + '/') : Promise.resolve(null);
      p.then(function (post) { editor(post); }).catch(function (e) { toast(e.message, 'bad'); });
    }

    function editor(post) {
      var isNew = !post;
      var today = new Date().toISOString().slice(0, 10);
      var m = modal(isNew ? 'New post' : 'Edit post',
        '<div class="post-grid">' +
          '<div>' +
            '<div class="field"><label class="label">Title</label>' +
              '<input class="input" id="p-title" value="' + esc(post ? post.title : '') + '" placeholder="Post title"></div>' +
            '<div class="field"><label class="label">Body</label><div id="p-editor"></div></div>' +
          '</div>' +
          '<div>' +
            '<div class="field"><label class="label">Category</label><select class="select" id="p-cat">' +
              cats.map(function (c) {
                return '<option value="' + c.id + '"' + (post && post.category_id === c.id ? ' selected' : '') + '>' + esc(c.name) + '</option>';
              }).join('') + '</select></div>' +
            '<div class="field"><label class="label">Date</label>' +
              '<input class="input" id="p-date" type="date" value="' + (post ? post.published_at : today) + '"></div>' +
            '<div class="field"><label class="label">Author</label>' +
              '<input class="input" id="p-author" value="' + esc(post ? post.author : 'admin') + '"></div>' +
            '<div class="field"><label class="label">Cover image</label>' +
              '<input class="input" id="p-cover" type="file" accept="image/*">' +
              (post && post.cover_url ? '<img class="cover-prev" src="' + esc(post.cover_url) + '" alt="">' : '') +
            '</div>' +
            '<div class="field"><label class="label">URL</label>' +
              '<input class="input" id="p-path" value="' + esc(post ? post.path : '') + '"' +
                (post ? ' readonly title="An existing post\'s URL cannot be changed here — it is indexed."' : ' placeholder="generated from the title"') + '>' +
              '<div class="hint">' + (post ? 'Fixed — changing it would break existing links and search results.'
                                           : 'Created automatically from the date and title.') + '</div></div>' +
            '<label style="display:flex;gap:8px;align-items:center;font-weight:600">' +
              '<input type="checkbox" id="p-pub"' + (!post || post.is_published ? ' checked' : '') + '> Published' +
            '</label>' +
          '</div>' +
        '</div>',
        '<button class="btn" data-cancel>Cancel</button>' +
        '<button class="btn btn--primary" data-save>' + (isNew ? 'Create post' : 'Save changes') + '</button>');

      m.el.querySelector('.modal__box').classList.add('modal__box--wide');
      var ed = makeEditor($('#p-editor', m.el), post ? post.body_html : '', post ? post.id : null);

      $('[data-cancel]', m.el).addEventListener('click', m.close);
      $('[data-save]', m.el).addEventListener('click', function () {
        var btn = this;
        var title = $('#p-title', m.el).value.trim();
        if (!title) { toast('Give the post a title.', 'bad'); return; }
        var fd = new FormData();
        fd.append('title', title);
        fd.append('category_id', $('#p-cat', m.el).value);
        fd.append('published_at', $('#p-date', m.el).value);
        fd.append('author', $('#p-author', m.el).value.trim());
        fd.append('body_html', ed.getHTML());
        fd.append('is_published', $('#p-pub', m.el).checked ? 'true' : 'false');
        var cf = $('#p-cover', m.el).files[0];
        if (cf) fd.append('cover', cf);

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Saving';
        var url = post ? '/manage/api/blog/' + post.id + '/save/' : '/manage/api/blog/create/';
        req(url, { method: 'POST', body: fd }).then(function () {
          m.close();
          toast(isNew ? 'Post created.' : 'Post saved.', 'ok');
          toast('Run the build to push it to the live site.');
          load();
        }).catch(function (e) {
          toast(e.message, 'bad');
          btn.disabled = false;
          btn.textContent = isNew ? 'Create post' : 'Save changes';
        });
      });
    }

    $('#add-post').addEventListener('click', function () { editor(null); });
    $('#f-search').addEventListener('input', debounce(function (e) {
      state.search = e.target.value; state.page = 1; load();
    }));
    $('#f-category').addEventListener('change', function (e) {
      state.category = e.target.value; state.page = 1; load();
    });
    $('#f-status').addEventListener('change', function (e) {
      state.status = e.target.value; state.page = 1; load();
    });

    req('/manage/api/stats/').then(function (d) { badgeNewCount(d.submissions_new); });
    load();
  }

  window.AX = {
    dashboard: dashboard,
    blog: blog,
    documents: documents,
    submissions: submissions,
    taxonomy: taxonomy,
    toast: toast
  };
})(window, document);
