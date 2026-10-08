const { test } = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), ts = require('typescript');
function load(file) {
  const target = path.resolve(__dirname, file);
  if (target.endsWith('.json')) return JSON.parse(fs.readFileSync(target, 'utf8'));
  const exports = {};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(target, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true, target: ts.ScriptTarget.ES2020 } }).outputText, { exports, require: name => load(path.relative(__dirname, path.resolve(path.dirname(target), name + (name.endsWith('.json') ? '' : '.ts')))), structuredClone, Date, TextEncoder });
  return exports;
}
const { demoSnapshot } = load('../lib/automatic-demo.ts');
const { buildDailySummary } = load('../lib/daily-summary.ts');
const normalize = value => JSON.parse(JSON.stringify(value));

test('summary uses checked deployable cash and separates native-currency upcoming amounts', () => {
  const snapshot = demoSnapshot(0), before = JSON.stringify(snapshot), summary = buildDailySummary(snapshot);
  assert.equal(summary.available, true);
  assert.equal(summary.cash, snapshot.positions.deployable);
  assert.equal(summary.asOf, '2026-10-08');
  assert.equal(summary.end, '2026-10-14');
  assert.equal(summary.gap, '0.00');
  assert.ok(summary.incoming.some(row => row.currency === 'USD' && row.amount === '400000.00'));
  assert.equal(JSON.stringify(snapshot), before);
});

test('date boundaries exclude overdue and later items and settlement removes receipt exactly once', () => {
  const snapshot = demoSnapshot(0);
  const base = { id: 'PAST', entity: 'DEMO', date: '2026-10-07', direction: 'INFLOW', currency: 'JPY', amount: '0.10', category: 'OTHER', probability: '1' };
  snapshot.state.flows = [base, { ...base, id: 'TODAY', date: '2026-10-08' }, { ...base, id: 'END', date: '2026-10-14', amount: '0.20' }, { ...base, id: 'LATER', date: '2026-10-15' }];
  const summary = buildDailySummary(snapshot);
  assert.deepEqual(normalize(summary.incoming), [{ currency: 'JPY', amount: '0.30', count: 2 }]);
  assert.deepEqual(normalize(summary.overdue.map(row => row.id)), ['PAST']);
  assert.equal(summary.outgoing.length, 0);
  assert.ok(!buildDailySummary(demoSnapshot(1)).incoming.some(row => row.currency === 'USD' && row.amount === '400000.00'));
});

test('missing, malformed or stale inputs are explicit and negative cash produces a gap', () => {
  assert.equal(buildDailySummary(null).available, false);
  const snapshot = demoSnapshot(0);
  snapshot.state.flows[0].date = '2026-02-30';
  assert.equal(buildDailySummary(snapshot).available, false);
  const stale = demoSnapshot(6);
  assert.equal(buildDailySummary(stale).marketHealthy, false);
  const low = demoSnapshot(0);
  low.positions.deployable = '-0.01'; low.positions.buffer = '100.00';
  assert.equal(buildDailySummary(low).gap, '100.01');
});
