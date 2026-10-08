const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const demo={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../lib/company-demo.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,{exports:demo});
const profile={company_name:' Fictional Harbor ',industry:'MANUFACTURING',country_code:'us'};
test('demo metadata stays separate from engine entities and staff roles',()=>{
 const initial=demo.emptyDemoSetup(),saved=demo.saveDemoProfile(initial,profile);
 assert.equal(initial.profile,null);assert.equal(saved.profile.company_name,'Fictional Harbor');assert.equal(saved.profile.country_code,'US');
 const domestic=demo.registerDemoEntity(saved,{name:' Harbor US ',country_code:'US',functional_currency:'usd'});
 const mnc=demo.registerDemoEntity(domestic,{name:'Harbor Germany',country_code:'de',functional_currency:'eur'});
 assert.equal(mnc.registrations.length,2);assert.equal(mnc.registrations[1].functional_currency,'EUR');assert.equal(mnc.registrations[0].status,'DEMO_DRAFT');
 assert.equal(mnc.entities.length,0);assert.equal(mnc.users.length,0);assert.equal(saved.registrations.length,0);
 assert.equal(demo.saveDemoProfile(mnc,{...profile,company_name:'Updated dummy'}).registrations.length,2);
});
test('demo setup rejects invalid inputs and case-insensitive duplicate entities',()=>{
 const initial=demo.emptyDemoSetup();
 for(const invalid of [{...profile,company_name:' '},{...profile,country_code:'USA'},{...profile,industry:'UNSUPPORTED'}])assert.throws(()=>demo.saveDemoProfile(initial,invalid));
 const entity={name:'Harbor',country_code:'US',functional_currency:'USD'};
 assert.throws(()=>demo.registerDemoEntity(initial,entity),/profile first/);
 const saved=demo.saveDemoProfile(initial,profile),added=demo.registerDemoEntity(saved,entity);
 assert.throws(()=>demo.registerDemoEntity(added,{...entity,name:' harbor '}),/already registered/);
 assert.throws(()=>demo.registerDemoEntity(saved,{...entity,functional_currency:'US'}));
 assert.throws(()=>demo.registerDemoEntity(saved,{...entity,name:' '.repeat(3)}));
 assert.equal(added.registrations.length,1);
});
test('clearing demo state returns a clean independent draft',()=>{
 const first=demo.emptyDemoSetup(),second=demo.emptyDemoSetup();first.registrations.push({name:'Test'});
 assert.equal(second.profile,null);assert.equal(second.registrations.length,0);assert.equal(second.entities.length,0);assert.equal(second.users.length,0);
});
test('quick-start examples contain only independent fictional metadata',()=>{
 const single=demo.exampleDemoSetup('single'),mnc=demo.exampleDemoSetup('multinational');
 assert.equal(single.registrations.length,1);assert.equal(mnc.registrations.length,3);
 assert.equal(mnc.registrations.map(e=>e.functional_currency).join(','),'USD,EUR,GBP');
 assert.equal(mnc.entities.length,0);assert.equal(mnc.users.length,0);
 assert.ok(mnc.profile.company_name.startsWith('Fictional'));
 mnc.registrations.pop();assert.equal(demo.exampleDemoSetup('multinational').registrations.length,3);
});
