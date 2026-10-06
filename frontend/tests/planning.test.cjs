const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const exportsObject={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../lib/planning.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,{exports:exportsObject,TextEncoder,Date});
const {parseCsv,validateRows,simulate,decimal,dollars}=exportsObject;
const mapping={id:'id',date:'date',amount:'amount',currency:'currency',direction:'direction',category:'category',probability:'probability',entity:'entity'};
const parse = text => validateRows(parseCsv(text).rows,mapping);
test('CSV reader handles BOM, quoted separators, escaped quotes and CRLF',()=>{
  const csv=parseCsv('\uFEFFid,entity,date,amount\r\nA,"Trading, \"\"UK\"\"",2026-10-03,1\r\n');
  assert.equal(csv.rows[0].entity,'Trading, "UK"'); assert.equal(csv.rows.length,1);
});
test('malformed files, duplicate headers and oversized input are rejected',()=>{
  for(const text of ['id,id\n1,2','id,date\nA','id,date\n"unfinished']) assert.throws(()=>parseCsv(text));
  assert.throws(()=>parseCsv('x'.repeat(524289))); assert.throws(()=>parseCsv('id\n'+Array.from({length:501},(_,i)=>i).join('\n')));
});
test('validation reports duplicates, impossible dates, currency, amount and category mistakes',()=>{
  const result=parse('id,date,amount,currency,direction,category\nA,2026-02-30,10,USD,INFLOW,OTHER\nB,2026-10-03,10,ZZZ,INFLOW,OTHER\nC,2026-10-03,1e9,USD,INFLOW,OTHER\nD,2026-10-03,10,USD,INFLOW,CRUDE_PURCHASE\nE,2026-10-03,10,USD,INFLOW,OTHER\nE,2026-10-03,10,USD,INFLOW,OTHER');
  assert.equal(result.errors.length,5); assert.equal(result.flows.length,1);
});
test('signed bank amounts infer directions without treating a debit as a receipt',()=>{
  const result=parse('id,date,amount\nDEBIT,2026-10-03,-12.50\nCREDIT,2026-10-03,10');
  assert.equal(result.errors.length,0); assert.equal(result.flows[0].direction,'OUTFLOW'); assert.equal(result.flows[0].amount,'12.50');
});
test('payments cannot be probability discounted and spreadsheet formula references are rejected',()=>{
  assert.equal(parse('id,date,amount,direction,probability\nA,2026-10-03,10,OUTFLOW,0.5').errors.length,1);
  assert.equal(parse('id,date,amount\n=SUM(1),2026-10-03,10').errors.length,1);
});
test('fixed point arithmetic rounds decimal cents consistently without binary float drift',()=>{
  assert.equal(dollars(decimal('0.1')+decimal('0.2')),'0.30'); assert.equal(dollars(-decimal('1.005')),'-1.01');
});
const fixtures=require('./fixtures/planning-engine.json');
for(const fixture of fixtures.cases) test(`browser matches Python engine: ${fixture.case}`,()=>{
  const result=simulate(fixture.flows,fixture.assumptions);
  for(const key of ['ending','headroom','maximumShortfall','firstBreach']) assert.equal(result[key],fixture.expected[key]);
  for(const [i,point] of result.points.entries()) for(const key of ['week','closing','inflows','outflows','shortfall']) assert.equal(point[key],fixture.expected.points[i][key]);
});
test('missing FX assumptions fail; delayed receipts beyond horizon stay visible',()=>{
  const fixture=fixtures.cases[0]; assert.throws(()=>simulate(fixture.flows,{...fixture.assumptions,rates:{}}),/exchange rate/);
  const result=simulate(fixture.flows,{...fixture.assumptions,delay:90}); assert.equal(result.beyond,1); assert.equal(result.ending,'12200000.00');
});
test('invalid horizon and infinite scenario changes are rejected',()=>{
  const fixture=fixtures.cases[0]; assert.throws(()=>simulate(fixture.flows,{...fixture.assumptions,weeks:0})); assert.throws(()=>simulate(fixture.flows,{...fixture.assumptions,oil:Infinity}));
});
test('decimal percentage steps accept ordinary input without binary float rejection',()=>{
  const fixture=fixtures.cases[0];
  assert.doesNotThrow(()=>simulate(fixture.flows,{...fixture.assumptions,oil:0.7}));
  assert.throws(()=>simulate(fixture.flows,{...fixture.assumptions,oil:0.75}));
  assert.throws(()=>simulate(fixture.flows,{...fixture.assumptions,start:'0000-01-01'}));
});
