(function () {
  // mobile menu
  var btn = document.getElementById('menu-btn'), nav = document.getElementById('nav');
  if (btn && nav) {
    var set = function (open) {
      nav.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open ? 'hidden' : '';
    };
    btn.addEventListener('click', function () { set(!nav.classList.contains('open')); });
    var close = document.getElementById('nav-close');
    if (close) close.addEventListener('click', function () { set(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
  }

  // catalog filters toggle on mobile
  var ft = document.getElementById('filter-toggle'), fp = document.getElementById('filters');
  if (ft && fp) ft.addEventListener('click', function () {
    var o = fp.classList.toggle('open');
    ft.setAttribute('aria-expanded', o ? 'true' : 'false');
  });

  // product gallery
  var main = document.getElementById('gallery-main');
  document.querySelectorAll('[data-thumb]').forEach(function (b) {
    b.addEventListener('click', function () {
      main.src = b.dataset.thumb; main.alt = b.dataset.alt || '';
      document.querySelectorAll('[data-thumb]').forEach(function (x) { x.removeAttribute('aria-current'); });
      b.setAttribute('aria-current', 'true');
    });
  });

  // checkout: live price quote when the delivery state or payment method changes
  var form = document.getElementById('checkout-form');
  if (form) {
    var url = form.dataset.quote;
    var stateOf = function () {
      var sel = form.querySelector('input[name=address_id]:checked');
      if (sel && sel.value !== 'new') return sel.dataset.state;
      var s = form.querySelector('select[name=state_code]');
      return s ? s.value : '09';
    };
    var refresh = function () {
      var m = form.querySelector('input[name=method]:checked');
      fetch(url + '?state=' + encodeURIComponent(stateOf()) + '&method=' + encodeURIComponent(m ? m.value : ''), { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          document.getElementById('q-goods').textContent = '\u20B9' + d.goods;
          document.getElementById('q-ship').textContent = d.shipping;
          document.getElementById('q-gst').textContent = '\u20B9' + d.gst + ' (' + d.split + ')';
          document.getElementById('q-cod-row').hidden = !d.has_cod;
          document.getElementById('q-cod').textContent = '\u20B9' + d.cod;
          document.getElementById('q-total').textContent = '\u20B9' + d.total;
          var p = form.querySelector('.sticky'); if (p) { p.classList.remove('is-loading'); p.removeAttribute('aria-busy'); }
        }).catch(function () { var p = form.querySelector('.sticky'); if (p) p.classList.remove('is-loading'); });
    };
    form.addEventListener('change', function (e) {
      var n = e.target.name;
      if (n === 'address_id' || n === 'method' || n === 'state_code') {
        var nf = document.getElementById('new-address');
        var sel = form.querySelector('input[name=address_id]:checked');
        if (nf && sel) nf.hidden = sel.value !== 'new';
        refresh();
      }
    });
  }

  // review stars: keep hidden rating field in sync
  document.querySelectorAll('.star-input input').forEach(function (i) {
    i.addEventListener('change', function () {
      var h = document.getElementById('id_rating');
      if (h) h.value = i.value;
    });
  });

  // ---- form error states: mark inputs invalid and link them to their messages
  document.querySelectorAll('.field.has-error').forEach(function (f) {
    var err = f.querySelector('.errorlist'), inp = f.querySelector('input,select,textarea');
    if (inp) { inp.setAttribute('aria-invalid', 'true'); if (err && inp.id) { err.id = inp.id + '_err'; err.setAttribute('role', 'alert'); inp.setAttribute('aria-describedby', err.id); } }
  });
  var firstErr = document.querySelector('.field.has-error input,.field.has-error select,.field.has-error textarea');
  if (firstErr && !document.querySelector('[autofocus]')) firstErr.focus({ preventScroll: false });

  // ---- loading state on submit (disabled after the browser has read the form data)
  document.querySelectorAll('form').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      if (e.defaultPrevented || f.method.toLowerCase() !== 'post') return;
      var b = e.submitter || f.querySelector('button[type=submit]');
      if (!b || !b.classList.contains('btn')) return;
      setTimeout(function () { b.setAttribute('aria-busy', 'true'); b.disabled = true; }, 0);
      setTimeout(function () { b.removeAttribute('aria-busy'); b.disabled = false; }, 15000);
    });
  });
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) document.querySelectorAll('.btn[aria-busy]').forEach(function (b) { b.removeAttribute('aria-busy'); b.disabled = false; });
  });

  // ---- cookie consent + analytics (GA4 loads only after the visitor accepts)
  var KEY = 'ls_consent', gaId = document.body.dataset.ga, banner = document.getElementById('cookie-banner');
  function loadGA() {
    if (!gaId || window.__gaLoaded) return; window.__gaLoaded = true;
    var s = document.createElement('script'); s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(gaId);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || []; window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date()); gtag('config', gaId, { anonymize_ip: true });
  }
  function getConsent() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function setConsent(v) { try { localStorage.setItem(KEY, v); } catch (e) {} if (banner) banner.hidden = true; if (v === 'yes') loadGA(); }
  if (banner) {
    var c = getConsent();
    if (c === 'yes') loadGA(); else if (!c) banner.hidden = false;
    document.getElementById('cookie-accept').addEventListener('click', function () { setConsent('yes'); });
    document.getElementById('cookie-decline').addEventListener('click', function () { setConsent('no'); });
    var re = document.getElementById('cookie-reopen'); if (re) re.addEventListener('click', function () { banner.hidden = false; });
  }
  window.lsTrack = function (name, params) { if (window.gtag) gtag('event', name, params || {}); };

  // checkout quote: loading state
  if (form) form.addEventListener('change', function () { var p = form.querySelector('.sticky'); if (p) { p.classList.add('is-loading'); p.setAttribute('aria-busy', 'true'); } });
})();
