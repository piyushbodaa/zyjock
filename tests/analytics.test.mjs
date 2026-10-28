import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
import vm from 'node:vm';
const loader = ['analytics.js', 'public/analytics.js', 'dist/analytics.js'].map(p => path.join(__dirname, '..', p)).find(fs.existsSync);
const source = fs.readFileSync(loader, 'utf8');
const value = name => JSON.parse(source.match(new RegExp('var ' + name + ' = (.*);'))[1]);
const id = value('MEASUREMENT_ID');
const host = value('HOST');
const pages = value('PAGES');
const groups = value('GROUPS');
const KEY = 'site-analytics-consent:v1';

function browser(options = {}) {
  class Element {
    constructor(tag) { this.tagName = tag; this.children = []; this.nodes = {}; this.hidden = false; }
    set innerHTML(html) { this.html = html; this.nodes = {}; }
    get innerHTML() { return this.html || ''; }
    appendChild(child) { this.children.push(child); return child; }
    attachShadow() { return (this.shadowRoot = new Element('shadow')); }
    setAttribute(name, val) { this[name] = val; }
    focus() { this.focused = true; }
    querySelector(selector) {
      if (this.nodes[selector]) return this.nodes[selector];
      if (selector === 'button') return this.querySelector('[data-allow]') || this.querySelector('[data-close]');
      const attribute = selector.slice(1, -1);
      if (!this.innerHTML.includes(attribute)) return null;
      return (this.nodes[selector] = new Element(attribute));
    }
  }
  const events = {};
  const saved = new Map(options.choice ? [[KEY, options.choice]] : []);
  const location = { hostname: options.host || host, protocol: options.protocol || 'https:', pathname: options.pathname || '/' };
  for (const key of ['href', 'search', 'hash']) Object.defineProperty(location, key, { get() { throw new Error('Raw URL read: ' + key); } });
  const document = { readyState: 'complete', head: new Element('head'), body: new Element('body'), cookie: 'site_analytics_ga=old; app_data=keep',
    createElement: tag => new Element(tag), getElementById: id => document.body.children.find(x => x.id === id) };
  for (const key of ['title', 'referrer']) Object.defineProperty(document, key, { get() { throw new Error('Private document field read: ' + key); } });
  const window = { location, addEventListener(name, cb) { (events[name] ||= []).push(cb); },
    localStorage: { getItem: key => { if (options.storageBlocked) throw Error('blocked'); return saved.get(key) || null; },
      setItem: (key, val) => { if (options.storageBlocked) throw Error('blocked'); saved.set(key, val); } } };
  const navigator = { doNotTrack: options.dnt ? '1' : '0', globalPrivacyControl: !!options.gpc };
  const context = vm.createContext({ window, document, navigator });
  const run = () => vm.runInContext(source, context);
  run();
  const root = () => document.body.children[0]?.shadowRoot;
  const panel = () => root()?.querySelector('[data-panel]');
  const click = selector => { const element = panel()?.querySelector(selector) || root()?.querySelector(selector); assert.ok(element, selector); element.onclick(); };
  const emit = (name, event = {}) => (events[name] || []).forEach(cb => cb(event));
  const commands = () => Array.from(window.dataLayer || [], args => Array.from(args));
  const views = () => commands().filter(args => args[0] === 'event' && args[1] === 'page_view');
  return { window, document, saved, location, run, root, panel, click, emit, commands, views };
}

test('measurement ID and production hostname are configured', () => {
  assert.match(id, /^G-[A-Z0-9]+$/); assert.match(host, /^[a-z0-9.-]+$/);
});
test('default and declined consent make no Google request or dataLayer', () => {
  const b = browser(); assert.equal(b.document.head.children.length, 0); assert.equal(b.commands().length, 0);
  b.click('[data-deny]'); assert.equal(b.document.head.children.length, 0); assert.equal(b.commands().length, 0);
  assert.equal(b.saved.get(KEY), 'denied'); assert.equal(b.window['ga-disable-' + id], true);
  const reload = browser({ choice: 'denied' }); assert.equal(reload.commands().length, 0);
});
test('accepted consent queues one sanitized view and disables ads and automatic pageviews', () => {
  const b = browser(); b.click('[data-allow]');
  assert.equal(b.document.head.children.length, 1); assert.equal(b.views().length, 1);
  assert.equal(b.document.head.children[0].referrerPolicy, 'no-referrer');
  const config = b.commands().find(x => x[0] === 'config')[2];
  assert.equal(config.send_page_view, false); assert.equal(config.allow_google_signals, false);
  assert.equal(config.allow_ad_personalization_signals, false); assert.equal(config.cookie_domain, 'none');
  assert.equal(config.page_location, 'https://' + host + '/'); assert.equal(config.page_title, pages['/']);
  assert.equal(config.page_referrer, ''); assert.equal(b.views()[0][2].send_to, id);
  assert.equal(b.commands().filter(x => x[0] === 'event').every(x => x[1] === 'page_view'), true);
  const consent = b.commands().find(x => x[0] === 'consent' && x[1] === 'default')[2];
  assert.equal(consent.ad_storage, 'denied'); assert.equal(consent.ad_user_data, 'denied'); assert.equal(consent.ad_personalization, 'denied');
});
test('duplicate loads, repeated acceptance, pageshow and query-only notifications do not duplicate views', () => {
  const b = browser({ choice: 'granted' }); b.run(); b.emit('pageshow'); b.emit('site-analytics:navigation');
  b.click('[data-settings]'); b.click('[data-allow]');
  assert.equal(b.views().length, 1); assert.equal(b.document.head.children.length, 1); assert.equal(b.document.body.children.length, 1);
});
test('preview hosts, localhost and HTTP cannot load Google even with saved consent', () => {
  for (const config of [{host:'preview.vercel.app'}, {host:'localhost'}, {protocol:'http:'}]) {
    const b = browser({ ...config, choice: 'granted' }); assert.equal(b.document.head.children.length, 0); assert.equal(b.commands().length, 0);
  }
});
test('DNT and GPC override saved permission', () => {
  for (const setting of [{dnt:true}, {gpc:true}]) {
    const b = browser({ ...setting, choice: 'granted' }); assert.equal(b.commands().length, 0); assert.equal(b.document.head.children.length, 0);
  }
});
test('unknown/private paths are excluded; returning to a public path emits once', () => {
  const initial = browser({ pathname:'/private/PRIVATE_VALUE', choice:'granted' }); assert.equal(initial.commands().length, 0);
  const b = browser({ choice:'granted' }); b.location.pathname='/private/PRIVATE_VALUE'; b.emit('site-analytics:navigation');
  assert.equal(b.views().length, 1); assert.equal(b.window['ga-disable-' + id], true);
  b.location.pathname='/'; b.emit('site-analytics:navigation'); assert.equal(b.views().length, 2);
  assert.ok(!JSON.stringify(b.commands()).includes('PRIVATE_VALUE'));
});
test('public route navigation and Back/Forward keep only fixed route fields', () => {
  const next = Object.keys(pages).find(x => x !== '/'); if (!next) return;
  const b = browser({ choice:'granted' }); b.location.pathname=next; b.emit('site-analytics:navigation');
  assert.equal(b.views().length, 2); assert.equal(b.views()[1][2].page_title, pages[next]);
  b.location.pathname='/'; b.emit('site-analytics:navigation'); assert.equal(b.views().length, 3);
});
test('dynamic routes are grouped without identifier leakage', () => {
  for (const group of groups) {
    const b = browser({ choice:'granted' });
    b.location.pathname=group.path.slice(0,group.path.lastIndexOf('/')+1)+'PRIVATE_VALUE';
    b.emit('site-analytics:navigation');
    assert.equal(b.views().at(-1)[2].page_path, group.path);
    assert.ok(!JSON.stringify(b.commands()).includes('PRIVATE_VALUE'));
  }
});
test('withdrawal stops new events and clears only analytics cookies', () => {
  const b = browser({ choice:'granted' }); b.click('[data-settings]'); b.click('[data-deny]');
  b.emit('site-analytics:navigation'); assert.equal(b.views().length, 1); assert.equal(b.window['ga-disable-' + id], true);
  assert.match(b.document.cookie, /^site_analytics_ga=; Max-Age=0/); assert.equal(b.saved.get(KEY), 'denied');
});
test('cross-tab withdrawal is applied', () => {
  const b = browser({ choice:'granted' }); b.saved.set(KEY, 'denied'); b.emit('storage', {key:KEY});
  assert.equal(b.window['ga-disable-' + id], true); assert.equal(b.views().length, 1);
});
test('unavailable storage fails closed but an explicit in-memory choice still works', () => {
  const b = browser({ storageBlocked:true }); assert.equal(b.commands().length, 0); b.click('[data-allow]'); assert.equal(b.views().length, 1);
});
