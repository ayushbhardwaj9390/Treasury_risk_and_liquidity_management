// Export deterministic TS snapshots for independent Python engine parity checks.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const ts = require('../frontend/node_modules/typescript');
const root = path.resolve(__dirname, '..');
function load(file) {
  if (file.endsWith('.json')) return JSON.parse(fs.readFileSync(file, 'utf8'));
  const exports = {};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true, target: ts.ScriptTarget.ES2020 } }).outputText,
    { exports, require: name => load(path.resolve(path.dirname(file), name + (name.endsWith('.json') ? '' : '.ts'))), structuredClone, Date, TextEncoder });
  return exports;
}
const demo = load(path.join(root, 'frontend/lib/automatic-demo.ts'));
const cases = ['single', 'mnc'].flatMap(scope => Array.from({ length: demo.totalCycles + 1 }, (_, cycle) => demo.demoSnapshot(cycle, scope)));
fs.writeFileSync(path.join(root, 'frontend/tests/fixtures/automatic-engine.json'), JSON.stringify({ source: 'Synthetic automatic-update snapshots; independently checked with unchanged Python engines', cases }, null, 2) + '\n');
process.stdout.write(JSON.stringify({ cycles: cases.length, company_data: false, execution_enabled: false }) + '\n');
