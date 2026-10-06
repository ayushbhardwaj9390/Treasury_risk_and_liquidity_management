const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function handler(fetch, env = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../app/api/treasury/route.ts'), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true } }).outputText;
  const exports = {};
  const context = { exports, require: name => name.endsWith('/session') ? { authorization: request => request.headers.get('authorization') ?? (request.headers.get('cookie')?.match(/(?:^|;\s*)__Host-treasury-session=([^;]+)/)?.[1] ? `Bearer ${request.headers.get('cookie').match(/(?:^|;\s*)__Host-treasury-session=([^;]+)/)[1]}` : undefined) } : require(name.includes('demo-snapshot') ? '../lib/demo-snapshot.json' : '../lib/endpoints.json'), URL, Headers, Response, AbortSignal,
    process: { env }, fetch };
  vm.runInNewContext(compiled, context);
  return exports.GET;
}

test('unknown workspace cannot forward arbitrary requests', async () => {
  const GET = handler(() => { throw new Error('Must not fetch'); });
  assert.equal((await GET(new Request('http://preview/api/treasury?key=http://attacker'))).status, 400);
});
test('read proxy uses loopback backend and preserves user authentication without demo identity', async () => {
  const GET = handler(async (url, init) => {
    assert.equal(url, 'http://127.0.0.1:8000/api/v1/liquidity/global');
    assert.equal(init.headers.get('Authorization'), 'Bearer test-token');
    assert.equal(init.headers.get('X-Treasury-User'), null);
    assert.equal(init.method, undefined);
    assert.equal(init.cache, 'no-store');
    assert.ok(init.signal);
    return Response.json({ deployable_cash: '100' });
  });
  const response = await GET(new Request('http://preview/api/treasury?key=getLiquidity', { headers: { Authorization: 'Bearer test-token' } }));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal((await response.json()).deployable_cash, '100');
});
test('backend outage returns a recoverable message without sensitive exception detail', async () => {
  const GET = handler(async () => { throw new Error('private-host-and-secret'); });
  const response = await GET(new Request('http://preview/api/treasury?key=getLiquidity'));
  assert.equal(response.status, 502);
  assert.ok(!(await response.text()).includes('private-host-and-secret'));
});
test('unauthorized backend remains unauthorized', async () => {
  const GET = handler(async () => Response.json({ detail: 'private' }, { status: 401 }));
  const response = await GET(new Request('http://preview/api/treasury?key=getLiquidity'));
  assert.equal(response.status, 401);
});
test('production gate 503 is displayed as blocked evidence, not a transport error', async () => {
  const GET = handler(async () => Response.json({ status: 'BLOCKED' }, { status: 503 }));
  const response = await GET(new Request('http://preview/api/treasury?key=productionGate'));
  assert.equal((await response.json()).status, 'BLOCKED');
});
test('unconfigured Vercel uses labelled recorded data without contacting localhost', async () => {
  const GET = handler(() => { throw new Error('No live request allowed'); }, { VERCEL: '1' });
  const response = await GET(new Request('http://preview/api/treasury?key=getLiquidity'));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('X-Treasury-Data-Mode'), 'recorded-demo');
  assert.ok(response.headers.get('X-Treasury-Data-As-Of'));
  assert.ok((await response.json()).deployable_cash);
});
test('a configured Vercel backend never silently falls back to demo on outage', async () => {
  const GET = handler(async () => { throw new Error('Backend unavailable'); }, { VERCEL: '1', API_BASE_URL: 'https://backend.example' });
  assert.equal((await GET(new Request('http://preview/api/treasury?key=getLiquidity'))).status, 502);
});
