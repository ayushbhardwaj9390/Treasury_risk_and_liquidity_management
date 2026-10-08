const {test}=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
function load(file) {
  const target=path.resolve(__dirname,file);
  if(target.endsWith('.json')) return JSON.parse(fs.readFileSync(target,'utf8'));
  const exports={};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(target,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,esModuleInterop:true,target:ts.ScriptTarget.ES2020}}).outputText,{exports,require:name=>load(path.relative(__dirname,path.resolve(path.dirname(target),name+(name.endsWith('.json')?'':'.ts')))),structuredClone,Date,TextEncoder,URL,Response});
  return exports;
}
const demo=load('../lib/automatic-demo.ts'), source=load('../lib/dummy-feed.json');
const normalized=value=>JSON.parse(JSON.stringify(value));
test('each automatic cycle matches its independently engine-checked fixture',()=>{
  for(const fixture of load('./fixtures/automatic-engine.json').cases) assert.deepEqual(normalized(demo.demoSnapshot(fixture.cycle,fixture.scope)),fixture);
});
test('matched settlements change cash once and remove open invoices without changing forecast ending cash',()=>{
  const base=demo.demoSnapshot(0),receipt=demo.demoSnapshot(1);
  assert.equal(receipt.positions.deployable,'2360000.00');
  assert.equal(receipt.positions.forecast.ending,base.positions.forecast.ending);
  assert.ok(!receipt.state.flows.some(flow=>flow.id==='R_USD'));
});
test('duplicate deliveries and reference collisions cannot double count balances or invoices',()=>{
  const four=demo.demoSnapshot(4),five=demo.demoSnapshot(5),six=demo.demoSnapshot(6),seven=demo.demoSnapshot(7);
  assert.deepEqual(normalized(four.positions),normalized(five.positions));
  assert.equal(five.history.at(-1).outcome,'DUPLICATE');
  assert.deepEqual(normalized(six.positions),normalized(seven.positions));
  assert.equal(seven.history.at(-1).outcome,'QUARANTINED');
});
test('invalid or incomplete market refresh preserves all good rates and marks them stale until recovery',()=>{
  const state=demo.demoSnapshot(3).state;
  const failed=demo.applyEvent(state,{id:'BAD',sequence:4,source:'MARKET',kind:'MARKET',title:'Bad quote',rates:{EUR:'1.20',GBP:'-1'}},4);
  assert.deepEqual(normalized(failed.state.rates),normalized(state.rates));
  assert.equal(failed.state.marketHealthy,false);
  assert.equal(demo.demoSnapshot(6).state.marketHealthy,false);
  assert.equal(demo.demoSnapshot(8).state.marketHealthy,true);
});
test('mismatched settlements and out-of-order invoices are quarantined atomically',()=>{
  const state=demo.demoSnapshot(3).state;
  const bad=demo.applyEvent(state,{...source.events[0],id:'BAD',sequence:4,amount:'401000'},4);
  assert.deepEqual(normalized(bad.state),normalized(state));
  const old=demo.applyEvent(state,{...source.events[3],id:'OLD',sequence:2},4);
  assert.equal(old.record.outcome,'QUARANTINED');
  assert.deepEqual(normalized(old.state),normalized(state));
});
test('new invoices reveal liquidity shortfall and hedge direction mismatch without changing hedge positions',()=>{
  const result=demo.demoSnapshot(4);
  assert.notEqual(result.positions.forecast.maximumShortfall,'0.00');
  assert.equal(result.positions.hedges.find(row=>row.currency==='EUR').wrongDirection,true);
  assert.deepEqual(normalized(result.state.hedges),source.hedges);
  assert.equal(result.executionEnabled,false);
});
test('delayed receipts remain in hedge exposure but leave the forecast horizon',()=>{
  const before=demo.demoSnapshot(8),after=demo.demoSnapshot(9);
  assert.deepEqual(normalized(before.positions.hedges),normalized(after.positions.hedges));
  assert.equal(after.positions.forecast.beyond,1);
  assert.notEqual(before.positions.forecast.ending,after.positions.forecast.ending);
});
test('only fixed bounded dummy cycles are accepted; arbitrary company input is rejected',async()=>{
  const route=load('../app/api/automatic-demo/route.ts');
  for(const query of ['cycle=-1','cycle=13','cycle=1.5','cycle=01','cycle=1&cycle=2','cycle=1&company=real','scope=unknown','scope=single&scope=mnc']) assert.equal((await route.GET(new Request('https://app/api/automatic-demo?'+query))).status,400);
  const response=await route.GET(new Request('https://app/api/automatic-demo?cycle=3'));
  assert.equal(response.status,200); assert.equal(response.headers.get('cache-control'),'no-store');
  assert.equal((await response.json()).mode,'SYNTHETIC_AUTOMATION');
  assert.throws(()=>demo.demoSnapshot(13)); assert.throws(()=>demo.demoSnapshot(Infinity));
});

test('single-country and MNC examples separate local entity cash from group totals',async()=>{
  const single=demo.demoSnapshot(0,'single'),mnc=demo.demoSnapshot(0,'mnc');
  assert.equal(single.positions.entities.length,1);
  assert.equal(mnc.positions.entities.length,3);
  assert.deepEqual(normalized(mnc.positions.entities.map(row=>row.country)),['US','DE','GB']);
  assert.equal(mnc.positions.deployable,single.positions.deployable);
  assert.equal(mnc.positions.buffer,'605000.00');
  assert.equal(mnc.positions.entities.find(row=>row.id==='EU').deployableLocal,'100000.00');
  const stressed=demo.demoSnapshot(4,'mnc');
  assert.ok(stressed.positions.alerts.some(text=>text.includes('cross-border')));
  assert.equal(stressed.state.flows.find(flow=>flow.currency==='EUR' && flow.amount==='600000').entity,'EU');
  const route=load('../app/api/automatic-demo/route.ts');
  const response=await route.GET(new Request('https://app/api/automatic-demo?cycle=4&scope=mnc'));
  assert.equal(response.status,200);assert.equal((await response.json()).scope,'mnc');
  assert.throws(()=>demo.demoSnapshot(0,'invalid'));
});
