const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const lib={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../lib/company-preferences.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,{exports:lib});
test('single and multinational preferences validate without mutating the input',()=>{
 const single=lib.examplePreferences(),first=lib.validatePreferences(single);
 first.countries.push('IN');assert.equal(single.countries.length,1);
 const multiple=lib.validatePreferences({...single,countries:['US','IN'],currencies:['USD','INR']});
 assert.equal(multiple.currencies.length,2);assert.equal(multiple.minimum_cash_usd,'1000');
 assert.notEqual(lib.examplePreferences().countries,lib.examplePreferences().countries);
});
test('rejects unsupported, duplicate, empty, non-decimal or oversized values',()=>{
 const good=lib.examplePreferences();
 for(const change of [{countries:[]},{countries:['US','US']},{countries:['ZZ']},{currencies:['BTC']},{reviewer_roles:['ADMIN']},{minimum_cash_usd:'-1'},{minimum_cash_usd:'1.001'},{minimum_cash_usd:'1e3'},{minimum_cash_usd:'1000000000000'},{minimum_cash_usd:100}]) assert.throws(()=>lib.validatePreferences({...good,...change}));
 for(const amount of ['0','0.01','999999999999.99'])assert.equal(lib.validatePreferences({...good,minimum_cash_usd:amount}).minimum_cash_usd,amount);
});
