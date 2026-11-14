/* Regression for Android mobile form AJAX encoding.
 * Executes the actual embedded dashboard JavaScript with minimal DOM stubs.
 * No npm dependencies or browser network access.
 */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('v13/mobile_dashboard.html', 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(match, 'dashboard script exists');
const js = match[1].replace('@@PREFIX@@', '/t/test');

const listeners = {};
const elem = () => ({
  textContent: '',
  value: ':bodyview',
  disabled: false,
  classList: { add() {}, remove() {}, toggle() {} },
  addEventListener(name, callback) { this.events ||= {}; this.events[name] = callback; },
  replaceChildren(...items) { this.children = items; },
  querySelector() { return elem(); },
});
const output = elem();
const notice = elem();
const chat = elem();
const form = elem();
// Chromium/Brave DOM clobbering: <input name="action"> hides form.action.
form.action = {name:'action', toString(){return '[object HTMLInputElement]';}};
form.native = false;
form.getAttribute = name => name === 'action' ? '/t/test/action' :
  name === 'data-native-submit' && form.native ? '1' : null;
form.addEventListener = (name, callback) => { listeners[name] = callback; };
const map = new Map([
  ['v13-live-output', output], ['v13-live-state', elem()],
  ['chat-running', elem()], ['ai-service-state', elem()], ['update-progress', elem()],
  ['update-result', elem()], ['pipeline-result', elem()], ['diagnostic-result', elem()], ['notice', notice],
  ['chat-compose', form], ['chat-input', chat],
  ['copy-chat', elem()], ['live-native-roles', elem()]
]);
const document = {
  hidden: true,
  getElementById(id) {
    if (!map.has(id)) throw new Error('Unknown DOM element: ' + id);
    return map.get(id);
  },
  querySelectorAll(selector) { return selector === 'form' ? [form] : []; },
  createElement() { return elem(); }
};
class FakeFormData {
  constructor() {
    this.rows = [['csrf', 'verified-token'], ['action', 'send'], ['command', ':bodyview']];
  }
  get(key) { return this.rows.find(([k]) => k === key)?.[1] ?? null; }
  [Symbol.iterator]() { return this.rows[Symbol.iterator](); }
}
const fetchCalls = [];
let refreshCallback = null;
const context = {
  document,
  window: { location: { reload() {} } },
  sessionStorage: { getItem() { return null; }, setItem() {} },
  navigator: { clipboard: null },
  FormData: FakeFormData,
  URLSearchParams,
  setInterval(fn) { refreshCallback = fn; },
  setTimeout() { return 1; },
  clearTimeout() {},
  async fetch(url, options) {
    fetchCalls.push({ url, options });
    return {
      ok: false, status: 400,
      async text() { return JSON.stringify({ ok: false, message: 'Zuerst V13 Chat starten' }); }
    };
  }
};
vm.runInNewContext(js, context, { filename: 'mobile_dashboard_inline.js' });
assert.equal(typeof listeners.submit, 'function', 'form submit callback registered');

(async () => {
  const button = { disabled: false };
  await listeners.submit({ preventDefault() {}, submitter: button });
  assert.equal(fetchCalls.length, 1, 'exactly one action HTTP request');
  const { url, options } = fetchCalls[0];
  assert.equal(url, '/t/test/action', 'MUST submit to HTML action attribute despite hidden input named action');
  assert.notEqual(url, String(form.action), 'DOM-clobbered form.action must never be used');
  assert.equal(options.method, 'POST');
  assert.ok(options.body instanceof URLSearchParams, 'MUST use urlencoded, not multipart FormData');
  assert.match(options.headers['Content-Type'], /^application\/x-www-form-urlencoded/);
  assert.equal(options.body.get('csrf'), 'verified-token');
  assert.equal(options.body.get('command'), ':bodyview');
  assert.equal(button.disabled, false, 'button becomes usable again');
  assert.match(notice.textContent, /Zuerst V13 Chat starten/, 'human-readable server error');
  assert.doesNotMatch(notice.textContent, /Unexpected end of JSON input/);
  // Native auto-update HTML form must NOT be intercepted by AJAX at all.
  form.native = true;
  let prevented = false;
  const nativeButton = { disabled: false };
  await listeners.submit({
    preventDefault() { prevented = true; }, submitter: nativeButton
  });
  assert.equal(prevented, false, 'native form POST must proceed without JS');
  assert.equal(nativeButton.disabled, false, 'native toggle button stays usable');
  assert.equal(fetchCalls.length, 1, 'no stray AJAX request for native toggle');
  form.native = false;
  assert.equal(typeof refreshCallback, 'function');
  // The real /state polling path must update four live native organs, not
  // just one static snapshot generated when the page was first rendered.
  document.hidden = false;
  context.fetch = async url => {
    assert.equal(url, '/t/test/state');
    return { ok: true, async json() { return {
      native_residency: { availability: 'AVAILABLE', readability: 'OBSERVED',
        roles: { B1_DETAIL: {processes: 1, pss_mib: 750.2},
          B2_GIST: {processes: 1, pss_mib: 702.1},
          C2_CONTROL: {processes: 1, pss_mib: 96.0},
          C3_LANGUAGE: {processes: 1, pss_mib: 224.1} } }
    }; } };
  };
  await refreshCallback();
  const nativeRoles = map.get('live-native-roles').children || [];
  assert.equal(nativeRoles.length, 4);
  assert.deepEqual(nativeRoles.map(x => x.textContent.split(':')[0]),
    ['B1 Detail','B2 Gist','C2 JEF','C3 Sprache']);
  assert.match(nativeRoles[0].textContent, /750.2 MiB PSS/);
  assert.match(nativeRoles[2].textContent, /C2 JEF: 1 laufend/);
  console.log('PASS: real dashboard JS POST + four native model live polling');
})().catch(err => { console.error(err); process.exitCode = 1; });
