const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
function load(file, env = {}, fetch = () => { throw Error('No network expected'); }, custom = {}) {
  const compiled = ts.transpileModule(fs.readFileSync(path.join(__dirname, file), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: name => name.endsWith('/session') ? load('../lib/session.ts', env) : custom[name] ?? require(name), process: { env }, URL, URLSearchParams, Buffer, Date, Headers, Request, Response, TextDecoder, AbortSignal, fetch });
  return exports;
}
test('session tokens stay in server cookie headers and origin check rejects foreign writes', () => {
  const session = load('../lib/session.ts');
  assert.equal(session.authorization(new Request('https://app.test', { headers: { cookie: '__Host-treasury-session=test' } })), 'Bearer test');
  assert.equal(session.sameOrigin(new Request('https://app.test', { headers: { origin: 'https://evil.test' } })), false);
});
test('login flow rejects changed, expired and mismatched state', () => {
  const session = load('../lib/session.ts'), flow = session.newFlow('secret');
  assert.equal(session.readFlow(flow.value, flow.state, 'secret').verifier, flow.verifier);
  assert.equal(session.readFlow(flow.value, 'wrong', 'secret'), null);
  assert.equal(session.readFlow(flow.value+'x', flow.state, 'secret'), null);
  assert.equal(session.readFlow(flow.value, flow.state, 'different'), null);
  const expired = Buffer.from(JSON.stringify({ state: flow.state, verifier: flow.verifier, expires: 1 })).toString('base64url');
  const mac = require('node:crypto').createHmac('sha256','secret').update(expired).digest('base64url');
  assert.equal(session.readFlow(`${expired}.${mac}`, flow.state, 'secret'), null);
});
test('demo and incomplete or invalid identity settings cannot initiate sign-in', () => {
  assert.equal(load('../lib/session.ts', { VERCEL:'1' }).loginConfig(), null);
  assert.equal(load('../lib/session.ts', { API_BASE_URL:'https://backend', APP_URL:'invalid', OIDC_CLIENT_ID:'client', OIDC_AUTHORIZATION_URL:'https://issuer/auth', OIDC_TOKEN_URL:'https://issuer/token', SESSION_SECRET:'s'.repeat(32) }).loginConfig(), null);
});
test('recorded demo denies all writes without contacting a backend', async () => {
  const route = load('../app/api/workflow/route.ts', { VERCEL:'1' });
  assert.equal((await route.POST(new Request('https://app/api/workflow?action=create', { method:'POST' }))).status,403);
});
test('workflow denies unauthenticated and cross-origin writes', async () => {
  const route = load('../app/api/workflow/route.ts', { API_BASE_URL:'https://backend' });
  assert.equal((await route.POST(new Request('https://app/api/workflow?action=create', { method:'POST',headers:{origin:'https://evil'} }))).status,403);
  assert.equal((await route.POST(new Request('https://app/api/workflow?action=create', { method:'POST',headers:{origin:'https://app'} }))).status,401);
});
test('workflow allowlist blocks arbitrary paths and malformed release IDs', async () => {
  const route = load('../app/api/workflow/route.ts', { API_BASE_URL:'https://backend' });
  assert.equal((await route.GET(new Request('https://app/api/workflow?action=http://evil',{headers:{authorization:'Bearer test'}}))).status,400);
  assert.equal((await route.GET(new Request('https://app/api/workflow?action=status&release=../x',{headers:{authorization:'Bearer test'}}))).status,400);
});
test('valid evidence submission preserves role rejection and identity; never impersonates a demo user', async () => {
  const route = load('../app/api/workflow/route.ts', { API_BASE_URL:'https://backend' }, async (url,init) => {
    assert.equal(url,'https://backend/api/v1/production/releases/12/evidence');
    assert.equal(init.headers.Authorization,'Bearer test');
    assert.equal(init.headers['X-Treasury-User'],undefined);
    return Response.json({ detail:'Active enterprise role required' },{ status:403 });
  });
  const result = await route.POST(new Request('https://app/api/workflow?action=evidence&release=12',{method:'POST',headers:{origin:'https://app',authorization:'Bearer test','content-type':'application/json'},body:'{"kind":"SYNTHETIC"}'}));
  assert.equal(result.status,403); assert.match((await result.json()).error,/role required/);
});
test('oversized and invalid JSON records are rejected before forwarding', async () => {
  const route = load('../app/api/workflow/route.ts', { API_BASE_URL:'https://backend' });
  const request = body => new Request('https://app/api/workflow?action=create',{method:'POST',headers:{origin:'https://app',authorization:'Bearer test','content-type':'application/json'},body});
  assert.equal((await route.POST(request('x'.repeat(262145)))).status,413);
  assert.equal((await route.POST(request('{broken'))).status,400);
});

const identityEnv = { API_BASE_URL:'https://backend', APP_URL:'https://app', OIDC_CLIENT_ID:'client', OIDC_AUTHORIZATION_URL:'https://issuer/authorize', OIDC_TOKEN_URL:'https://issuer/token', SESSION_SECRET:'s'.repeat(32) };
const nextMock = { NextResponse: { json: (body, options) => decorate(Response.json(body, options)), redirect: url => decorate(new Response(null,{status:307,headers:{location:String(url)}})) } };
function decorate(response) { response.cookies = { set: (name,value,options) => response.headers.append('set-cookie',`${name}=${value}; Path=${options.path}; Max-Age=${options.maxAge}; HttpOnly; Secure; SameSite=Lax`) }; return response; }

test('company setup rejects demo writes, missing identity, foreign origin and arbitrary routes', async () => {
  const request = (action, headers = {}) => new Request(`https://app/api/company?action=${action}`, { method:'POST', headers, body:'{}' });
  assert.equal((await load('../app/api/company/route.ts', {VERCEL:'1'}).POST(request('profile'))).status,403);
  const route = load('../app/api/company/route.ts', {API_BASE_URL:'https://backend'});
  assert.equal((await route.GET(new Request('https://app/api/company?action=setup'))).status,401);
  assert.equal((await route.POST(request('profile',{origin:'https://evil',authorization:'Bearer test'}))).status,403);
  assert.equal((await route.POST(request('../production/releases',{origin:'https://app',authorization:'Bearer test'}))).status,400);
});

test('company setup forwards verified identity and preserves backend conflict', async () => {
  const route = load('../app/api/company/route.ts', {API_BASE_URL:'https://backend'}, async (url, init) => {
    assert.equal(url,'https://backend/api/v1/company/profile');
    assert.equal(init.headers.Authorization,'Bearer test');
    assert.equal(init.headers['X-Treasury-User'],undefined);
    return Response.json({detail:'Company profile changed. Reload before saving.'},{status:409});
  });
  const response = await route.POST(new Request('https://app/api/company?action=profile',{method:'POST',headers:{origin:'https://app',authorization:'Bearer test','content-type':'application/json'},body:'{}'}));
  assert.equal(response.status,409); assert.match((await response.json()).error,/Reload/);
});

test('company setup rejects oversized, malformed and non-JSON submissions', async () => {
  const route = load('../app/api/company/route.ts', {API_BASE_URL:'https://backend'});
  const request = (body, type='application/json') => new Request('https://app/api/company?action=profile',{method:'POST',headers:{origin:'https://app',authorization:'Bearer test','content-type':type},body});
  assert.equal((await route.POST(request('x'.repeat(65537)))).status,413);
  assert.equal((await route.POST(request('{bad'))).status,400);
  assert.equal((await route.POST(request('{}','text/plain'))).status,415);
});
test('login redirects only to configured provider with PKCE and secure state cookie', async () => {
  const route = load('../app/api/auth/[action]/route.ts', identityEnv, undefined, { 'next/server': nextMock });
  const response = await route.GET(new Request('https://app/api/auth/login'),{params:Promise.resolve({action:'login'})});
  const url = new URL(response.headers.get('location'));
  assert.equal(url.origin,'https://issuer'); assert.equal(url.searchParams.get('code_challenge_method'),'S256');
  assert.equal(url.searchParams.get('redirect_uri'),'https://app/api/auth/callback');
  assert.match(response.headers.get('set-cookie'),/HttpOnly; Secure; SameSite=Lax/);
});
test('callback state mismatch never exchanges a code or creates a session', async () => {
  const route = load('../app/api/auth/[action]/route.ts', identityEnv, undefined, { 'next/server': nextMock });
  const response = await route.GET(new Request('https://app/api/auth/callback?state=invalid&code=test'),{params:Promise.resolve({action:'callback'})});
  assert.equal(response.headers.get('location'),'https://app/?signin=failed');
  assert.ok(!response.headers.get('set-cookie').includes('__Host-treasury-session='));
});
test('callback requires backend account validation before setting session', async () => {
  const session = load('../lib/session.ts',identityEnv), flow=session.newFlow(identityEnv.SESSION_SECRET);
  let calls=0;
  const route = load('../app/api/auth/[action]/route.ts', identityEnv, async url => { calls++; return url==='https://issuer/token' ? Response.json({access_token:'jwt-token',expires_in:3600}) : Response.json({detail:'inactive'},{status:403}); }, { 'next/server': nextMock });
  const response = await route.GET(new Request(`https://app/api/auth/callback?state=${flow.state}&code=test`,{headers:{cookie:`__Host-treasury-flow=${flow.value}`}}),{params:Promise.resolve({action:'callback'})});
  assert.equal(calls,2); assert.equal(response.headers.get('location'),'https://app/?signin=failed');
  assert.ok(!response.headers.get('set-cookie').includes('__Host-treasury-session='));
});
test('callback verified token is stored only in secure HttpOnly session cookie', async () => {
  const session = load('../lib/session.ts',identityEnv), flow=session.newFlow(identityEnv.SESSION_SECRET);
  const route = load('../app/api/auth/[action]/route.ts', identityEnv, async url => url==='https://issuer/token' ? Response.json({access_token:'jwt-token',expires_in:900}) : Response.json({username:'reviewer',role:'RISK_MANAGER'}), { 'next/server': nextMock });
  const response = await route.GET(new Request(`https://app/api/auth/callback?state=${flow.state}&code=test`,{headers:{cookie:`__Host-treasury-flow=${flow.value}`}}),{params:Promise.resolve({action:'callback'})});
  assert.equal(response.headers.get('location'),'https://app'); assert.match(response.headers.get('set-cookie'),/__Host-treasury-session=jwt-token; Path=\/; Max-Age=900; HttpOnly; Secure/);
  assert.equal(await response.text(),'');
});
