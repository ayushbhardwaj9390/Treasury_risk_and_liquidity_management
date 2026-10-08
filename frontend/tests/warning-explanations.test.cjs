const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
function load(file){
  const target=path.resolve(__dirname,file);
  if(target.endsWith('.json'))return JSON.parse(fs.readFileSync(target,'utf8'));
  const exports={};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(target,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,esModuleInterop:true,target:ts.ScriptTarget.ES2020}}).outputText,{exports,require:name=>load(path.relative(__dirname,path.resolve(path.dirname(target),name+(name.endsWith('.json')?'':'.ts')))),structuredClone,Date,TextEncoder});
  return exports;
}
const {explainWarnings}=load('../lib/warning-explanations.ts'),{demoSnapshot}=load('../lib/automatic-demo.ts');
test('missing snapshot is unavailable rather than a passing assessment',()=>assert.equal(explainWarnings(null),null));
test('forecast warning cites affected week and open records without mutating positions',()=>{
  const snapshot=demoSnapshot(4),before=JSON.stringify(snapshot),warning=explainWarnings(snapshot).find(row=>row.id==='forecast');
  assert.ok(warning);assert.match(warning.title,new RegExp(`week ${snapshot.positions.forecast.firstBreach}`));
  assert.ok(warning.evidence.some(row=>row.reference==='P_EQUIPMENT'&&row.date==='2026-10-15'));
  assert.ok(warning.evidence.some(row=>row.reference==='CASH-ADJUSTMENTS'&&row.summary.includes('No credit')));
  assert.equal(JSON.stringify(snapshot),before);
});
test('currency warning cites existing contract and invoices and explains direction mismatch',()=>{
  const snapshot=demoSnapshot(4),warning=explainWarnings(snapshot).find(row=>row.id==='hedge-EUR');
  assert.match(warning.cause,/same direction/);assert.match(warning.cause,/not a predicted loss/);
  const hedge=snapshot.state.hedges.find(row=>row.currency==='EUR');
  assert.ok(warning.evidence.some(row=>row.reference===hedge.id&&row.summary.includes('No contract maturity')));
  assert.ok(warning.evidence.some(row=>row.reference==='R_EUR'));
});
test('failed market quotes expose rejected reference and missing time; recovery removes stale warning',()=>{
  const failed=demoSnapshot(6),warning=explainWarnings(failed).find(row=>row.id==='market');
  assert.ok(warning);assert.match(warning.cause,/timestamp is unavailable/);
  assert.ok(warning.evidence.some(row=>failed.history.some(event=>event.id===row.reference&&event.outcome==='QUARANTINED')));
  assert.ok(!explainWarnings(demoSnapshot(8)).some(row=>row.id==='market'));
  assert.ok(explainWarnings(demoSnapshot(8)).some(row=>row.id==='rejected'));
});
test('outside-horizon invoices get separate date review without changing open currency exposure',()=>{
  const snapshot=demoSnapshot(9),warnings=explainWarnings(snapshot),excluded=warnings.find(row=>row.id==='excluded');
  assert.ok(excluded);assert.equal(excluded.evidence.length,snapshot.positions.forecast.beyond+snapshot.positions.forecast.overdue);
  for(const row of excluded.evidence){assert.ok(row.date);assert.ok(snapshot.state.flows.some(flow=>flow.id===row.reference));}
  assert.equal(JSON.stringify(snapshot.positions.hedges),JSON.stringify(demoSnapshot(8).positions.hedges));
  assert.match(excluded.cause,/remain in open currency exposure/);
});
test('entity warning does not substitute group cash for locally available funds',()=>{
  const snapshot=demoSnapshot(4,'mnc'),warnings=explainWarnings(snapshot).filter(row=>row.id.startsWith('entity-'));
  assert.ok(warnings.length);for(const warning of warnings){assert.match(warning.cause,/not automatically available/);assert.match(warning.nextStep,/legal, tax and human approvals/);const entityId=warning.id.slice(7);assert.ok(warning.evidence.some(row=>row.reference===entityId));}
});
