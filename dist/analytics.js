/* Basic opt-in GA4. Keep Enhanced Measurement OFF in this web stream.
 * Only fixed, allowlisted page fields are sent; never read page text or forms.
 * See ANALYTICS.md for the production and privacy verification checklist. */
(function () {
  'use strict';
  var MEASUREMENT_ID = "G-Y3LM9LKCYG";
  var HOST = "zyjock.vercel.app";
  var PAGES = {"/": "Zyjock"};
  var GROUPS = [];
  var KEY = 'site-analytics-consent:v1';
  var DISABLE = 'ga-disable-' + MEASUREMENT_ID;
  var ROOT_ID = 'site-analytics-controls';
  if (window.location.hostname !== HOST || window.location.protocol !== 'https:' ||
      !/^G-[A-Z0-9]+$/.test(MEASUREMENT_ID) || window.__siteAnalyticsReady) return;
  window.__siteAnalyticsReady = true;
  window[DISABLE] = true;
  var loaded = false;
  var lastPath = null;
  var choice = readChoice();
  var panel;
  var root;

  function readChoice() {
    try {
      var value = window.localStorage.getItem(KEY);
      return value === 'granted' || value === 'denied' ? value : null;
    } catch { return null; }
  }
  function privacySignal() {
    return navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' ||
      window.doNotTrack === '1';
  }
  function page() {
    var path = window.location.pathname.replace(/\/+$/, '') || '/';
    if (path === '/index.html') path = '/';
    if (Object.prototype.hasOwnProperty.call(PAGES, path)) return { path: path, title: PAGES[path] };
    for (var i = 0; i < GROUPS.length; i++) {
      var group = GROUPS[i];
      if (new RegExp(group.pattern).test(path)) return { path: group.path, title: group.title };
    }
    return null;
  }
  function fields(current) {
    // Deliberately omit the document referrer: it can contain personal paths too.
    return { page_location: 'https://' + HOST + current.path, page_path: current.path,
      page_title: current.title, page_referrer: '' };
  }
  function gtag() { window.dataLayer.push(arguments); }
  function configure(current) {
    if (loaded) return;
    loaded = true;
    window.dataLayer = window.dataLayer || [];
    // Basic mode: no Google script, ping, or cookie before explicit opt-in.
    gtag('consent', 'default', { analytics_storage: 'denied', ad_storage: 'denied',
      ad_user_data: 'denied', ad_personalization: 'denied' });
    gtag('set', { ads_data_redaction: true, url_passthrough: false });
    gtag('consent', 'update', { analytics_storage: 'granted' });
    gtag('js', new Date());
    gtag('config', MEASUREMENT_ID, Object.assign(fields(current), {
      send_page_view: false,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      cookie_domain: 'none', cookie_prefix: 'site_analytics',
      cookie_expires: 7776000, cookie_flags: 'SameSite=Lax;Secure'
    }));
    var script = document.createElement('script');
    script.async = true;
    script.referrerPolicy = 'no-referrer';
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + MEASUREMENT_ID;
    document.head.appendChild(script);
  }
  function track() {
    var current = page();
    var enabled = choice === 'granted' && !privacySignal() && current !== null;
    window[DISABLE] = !enabled;
    if (!enabled) { lastPath = null; return; }
    configure(current);
    // Keep automatic engagement context sanitized as well as manual pageviews.
    gtag('set', fields(current));
    if (lastPath === current.path) return;
    lastPath = current.path;
    gtag('event', 'page_view', Object.assign({ send_to: MEASUREMENT_ID }, fields(current)));
  }
  function clearCookies() {
    // Only remove this integration's host-only cookies, not application storage.
    document.cookie.split(';').forEach(function (cookie) {
      var name = cookie.split('=')[0].trim();
      if (name.indexOf('site_analytics') === 0) {
        document.cookie = name + '=; Max-Age=0; Path=/; SameSite=Lax; Secure';
      }
    });
  }
  function choose(value) {
    choice = value;
    try { window.localStorage.setItem(KEY, value); } catch { /* In-memory choice still works. */ }
    if (value !== 'granted') {
      window[DISABLE] = true;
      clearCookies();
      lastPath = null;
    }
    track();
    render(false);
    var settings = root.querySelector('[data-settings]');
    if (settings) settings.focus();
  }
  function render(open) {
    if (!root) return;
    var blocked = privacySignal();
    panel.innerHTML = '<section role="region" aria-label="Analytics privacy">' +
      '<strong>Optional analytics</strong><p>' +
      (blocked ? 'Your browser privacy signal is respected. Analytics is off.' :
        'Allow Google Analytics cookies to count visits to public pages? Only basic page and device information is collected. No typed text, answers, form details, personal plans, or shared links. Advertising features are off.') +
      '</p><div class="actions">' +
      (blocked ? '' : '<button type="button" data-allow>Allow analytics</button><button type="button" data-deny>No thanks</button>') +
      (choice !== null || blocked ? '<button type="button" data-close>Close</button>' : '') +
      '</div></section>';
    panel.hidden = !open;
    var allow = panel.querySelector('[data-allow]');
    var deny = panel.querySelector('[data-deny]');
    var close = panel.querySelector('[data-close]');
    if (allow) allow.onclick = function () { choose('granted'); };
    if (deny) deny.onclick = function () { choose('denied'); };
    if (close) close.onclick = function () { render(false); root.querySelector('[data-settings]').focus(); };
    root.querySelector('[data-settings]').setAttribute('aria-expanded', String(open));
  }
  function boot() {
    if (!document.getElementById(ROOT_ID)) {
      var host = document.createElement('div');
      host.id = ROOT_ID;
      root = host.attachShadow({ mode: 'open' });
      root.innerHTML = '<style>:host{position:fixed;left:12px;bottom:12px;z-index:10000;font:14px/1.5 system-ui,sans-serif;color:#17232b;max-width:calc(100vw - 24px)}[hidden]{display:none!important}section{box-sizing:border-box;max-width:430px;max-height:70vh;overflow:auto;padding:18px;background:#fff;border:1px solid #53616c;border-radius:8px;box-shadow:0 3px 18px #0003;margin-bottom:8px}p{margin:8px 0 12px}strong{font-size:16px}.actions{display:flex;flex-wrap:wrap;gap:8px}button{font:inherit;line-height:1.4;color:#17232b;background:#fff;border:1px solid #53616c;border-radius:4px;padding:9px 12px;cursor:pointer}button:hover{background:#edf1f3}button:focus-visible{outline:3px solid #1769aa;outline-offset:3px}[data-settings]{font-size:12px;padding:5px 9px}</style><div data-panel></div><button type="button" data-settings aria-expanded="false">Analytics settings</button>';
      document.body.appendChild(host);
      panel = root.querySelector('[data-panel]');
      root.querySelector('[data-settings]').onclick = function () {
        render(panel.hidden);
        if (!panel.hidden) { var button = panel.querySelector('button'); if (button) button.focus(); }
      };
      render(choice === null && !privacySignal() && page() !== null);
    }
    track();
  }
  window.addEventListener('site-analytics:navigation', track);
  window.addEventListener('pageshow', track);
  window.addEventListener('storage', function (event) {
    if (event.key !== KEY && event.key !== null) return;
    choice = readChoice();
    if (choice !== 'granted') clearCookies();
    track();
    render(false);
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
}());
