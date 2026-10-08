const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const moduleExports={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../lib/forecast-review.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,{exports:moduleExports,Date});
const {reviewForecast}=moduleExports;
const points=[{week:1,date:'2026-10-10',closing:'100.00'},{week:2,date:'2026-10-17',closing:'200.00'}];
test('matches exact dates and reports error magnitude and signed bias separately',()=>{
 const result=reviewForecast(points,{'2026-10-10':'90','2026-10-17':'220'});
 assert.equal(result.meanAbsoluteError,'15.00');assert.equal(result.bias,'5.00');assert.equal(result.wapePercent,'9.68');assert.equal(result.count,2);
});
test('blank observations are unknown, zero observations are included and denominator zero is unavailable',()=>{
 const unknown=reviewForecast(points,{});assert.equal(unknown.count,0);assert.equal(unknown.meanAbsoluteError,null);
 const zero=reviewForecast(points,{'2026-10-10':'0','2026-10-17':'0'});assert.equal(zero.count,2);assert.equal(zero.meanAbsoluteError,'150.00');assert.equal(zero.wapePercent,null);
});
test('negative balances use absolute actual denominator and allow differences greater than 100 percent',()=>{
 const result=reviewForecast(points,{'2026-10-10':'-10','2026-10-17':'10'});
 assert.equal(result.wapePercent,'1500.00');assert.equal(result.bias,'-150.00');
});
test('cent arithmetic avoids binary drift and rounds negative bias symmetrically',()=>{
 const result=reviewForecast([{week:1,date:'2026-10-10',closing:'0.10'},{week:2,date:'2026-10-17',closing:'0.20'}],{'2026-10-10':'0.10','2026-10-17':'0.19'});
 assert.equal(result.meanAbsoluteError,'0.01');assert.equal(result.bias,'-0.01');
});
test('bad amounts and out-of-period actuals remain explicit and excluded',()=>{
 for(const bad of ['1e3','NaN','=1','1.234','1000000000000.01']) {
  const result=reviewForecast(points,{'2026-10-10':bad,'2026-11-01':'22'});assert.equal(result.count,0);assert.ok(result.errors['2026-10-10']);assert.ok(result.errors['2026-11-01']);
 }
 assert.equal(reviewForecast(points,{'2026-10-10':'-1000000000000'}).count,1);
});
test('invalid or ambiguous plan periods are rejected',()=>{
 assert.throws(()=>reviewForecast([points[0],points[0]],{}));
 assert.throws(()=>reviewForecast([{...points[0],date:'2026-02-30'}],{}));
 assert.throws(()=>reviewForecast([{...points[0],week:0}],{}));
 assert.throws(()=>reviewForecast(Array.from({length:53},()=>points[0]),{}));
});
