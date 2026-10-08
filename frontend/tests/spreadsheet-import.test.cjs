const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), ts = require('typescript'), vm = require('node:vm');
const { zipSync, strToU8 } = require('fflate');
const helper = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, '../lib/spreadsheet-import.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true } }).outputText, { exports: helper, require, TextDecoder, Uint8Array, DataView, Date });
const planner = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, '../lib/planning.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, { exports: planner, TextEncoder, Date });
const ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
const cell = (address, value) => typeof value === 'number' ? `<c r="${address}"><v>${value}</v></c>` : `<c r="${address}" t="inlineStr"><is><t>${escape(value)}</t></is></c>`;
function sheet(rows) {
  return `<worksheet xmlns="${ns}"><sheetData>${rows.map((row, i) => `<row r="${i + 1}">${row.map((value, j) => cell(String.fromCharCode(65 + j) + (i + 1), value)).join('')}</row>`).join('')}</sheetData></worksheet>`;
}
function workbook(sheets, extra = {}) {
  const files = {
    '[Content_Types].xml': `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>`,
    '_rels/.rels': `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
    'xl/workbook.xml': `<workbook xmlns="${ns}" xmlns:r="${rel}"><sheets>${sheets.map((_, i) => `<sheet name="Sheet ${i + 1}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('')}</sheets></workbook>`,
    'xl/_rels/workbook.xml.rels': `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${sheets.map((_, i) => `<Relationship Id="rId${i + 1}" Type="${rel}/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('')}</Relationships>`,
    ...Object.fromEntries(sheets.map((content, i) => [`xl/worksheets/sheet${i + 1}.xml`, content])), ...extra
  };
  const zipped = zipSync(Object.fromEntries(Object.entries(files).map(([name, text]) => [name, strToU8(text)])));
  return zipped.buffer.slice(zipped.byteOffset, zipped.byteOffset + zipped.byteLength);
}
const good = () => sheet([['id', 'date', 'amount', 'currency', 'direction'], ['A-1', '2026-10-12', 1250.25, 'USD', 'INFLOW'], ['A-2', '2026-10-13', -750, 'USD', 'OUTFLOW']]);
test('XLSX imports multiple selectable sheets, exact numeric values and planner validation', async () => {
  const result = await helper.parseWorkbook(workbook([good(), sheet([['Reference', 'Payment date', 'Amount'], ['B-1', '2026-10-14', 2.5e-2]])]));
  assert.equal(result.length, 2); assert.equal(result[0].name, 'Sheet 1');
  assert.equal(result[0].rows[0].amount, '1250.25'); assert.equal(result[0].rows[1].amount, '-750');
  assert.equal(result[1].rows[0].Amount, '0.025');
  const checked = planner.validateRows(result[0].rows, planner.suggestMapping(result[0].headers));
  assert.equal(checked.errors.length, 0); assert.equal(checked.flows.length, 2);
  assert.equal(checked.flows[1].direction, 'OUTFLOW'); assert.equal(checked.flows[1].amount, '750');
});
test('XLSX native date cells become ISO dates and blank trailing cells are safe', async () => {
  const xml = `<worksheet xmlns="${ns}"><sheetData><row r="1">${cell('A1', 'id')}${cell('B1', 'date')}${cell('C1', 'amount')}</row><row r="2">${cell('A2', 'D-1')}<c r="B2" t="d"><v>2026-10-12T00:00:00Z</v></c>${cell('C2', 500)}</row></sheetData></worksheet>`;
  const result = await helper.parseWorkbook(workbook([xml]));
  assert.equal(result[0].rows[0].date, '2026-10-12');
  const serial = (Date.parse('2026-10-12T00:00:00Z') - Date.parse('1899-12-30T00:00:00Z')) / 86400000;
  const styled = xml.replace('<c r="B2" t="d"><v>2026-10-12T00:00:00Z</v></c>', `<c r="B2" s="1"><v>${serial}</v></c>`);
  const style = `<styleSheet xmlns="${ns}"><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>`;
  const styledResult = await helper.parseWorkbook(workbook([styled], { 'xl/styles.xml': style }));
  assert.equal(styledResult[0].rows[0].date, '2026-10-12');
});
test('XLSX rejects formula cells with or without cached values and Excel errors', async () => {
  for (const bad of ['<c r="C2"><f>1+1</f><v>2</v></c>', '<c r="C2"><f>1+1</f></c>', '<c r="C2" t="e"><v>#DIV/0!</v></c>']) {
    await assert.rejects(helper.parseWorkbook(workbook([good().replace(cell('C2', 1250.25), bad)])), /formula|Excel error/);
  }
});
test('XLSX rejects malformed files, unsafe XML, macros, external links and missing headings', async () => {
  await assert.rejects(helper.parseWorkbook(new ArrayBuffer(24)), /readable/);
  await assert.rejects(helper.parseWorkbook(workbook([good()], { 'xl/vbaProject.bin': 'unsafe' })), /macros/);
  await assert.rejects(helper.parseWorkbook(workbook([good()], { 'xl/externalLinks/externalLink1.xml': '<x/>' })), /links/);
  await assert.rejects(helper.parseWorkbook(workbook([good().replace('<sheetData>', '<!DOCTYPE x><sheetData>')])), /readable/);
  await assert.rejects(helper.parseWorkbook(workbook([good().replace('r="C2"', 'r="C2" note=">" r="XFD1048576"')])), /readable/);
  await assert.rejects(helper.parseWorkbook(workbook([sheet([['id', 'id'], ['A-1', 'B-1']])])), /headings/);
  await assert.rejects(helper.parseWorkbook(workbook([sheet([['id', ''], ['A-1', 'B-1']])])), /headings/);
});
test('XLSX bounds compressed bytes, expanded entries, sheet dimensions and sheet counts', async () => {
  await assert.rejects(helper.parseWorkbook(new ArrayBuffer(helper.workbookLimits.fileBytes + 1)), /under 2 MB/);
  await assert.rejects(helper.parseWorkbook(workbook([good()], { 'padding.xml': 'x'.repeat(helper.workbookLimits.entryBytes + 1) })), /readable/);
  await assert.rejects(helper.parseWorkbook(workbook([good().replace('r="C2"', 'r="XFD1048576"')])), /500 data rows/);
  await assert.rejects(helper.parseWorkbook(workbook([good().replace('<sheetData>', '<dimension ref="A1:AE502"/><sheetData>')])), /500 data rows/);
  await assert.rejects(helper.parseWorkbook(workbook(Array.from({ length: 11 }, good))), /10 sheets/);
});
test('XLSX rejects dishonest decompressed size before the workbook parser sees it', async () => {
  const buffer = workbook([good()], { 'padding.xml': 'x'.repeat(1000000) }), bytes = new Uint8Array(buffer), view = new DataView(buffer);
  for (let i = 0; i < bytes.length - 46; i++) {
    if (view.getUint32(i, true) === 0x02014b50) {
      const name = new TextDecoder().decode(bytes.subarray(i + 46, i + 46 + view.getUint16(i + 28, true)));
      if (name === 'padding.xml') { view.setUint32(i + 24, 1, true); break; }
    }
  }
  await assert.rejects(helper.parseWorkbook(buffer), /expands to too much/);
});
test('XLSX rejects ambiguous duplicate names and invalid or oversized worksheet names', async () => {
  for (const name of ['Sheet 1', 'sheet 1', 'x'.repeat(32), 'Bad/name', "'Quoted", '']) {
    const metadata = `<workbook xmlns="${ns}" xmlns:r="${rel}"><sheets><sheet name="Sheet 1" sheetId="1" r:id="rId1"/><sheet name="${escape(name)}" sheetId="2" r:id="rId2"/></sheets></workbook>`;
    await assert.rejects(helper.parseWorkbook(workbook([good(), good()], { 'xl/workbook.xml': metadata })), /unique Excel worksheet names|readable/);
  }
});
