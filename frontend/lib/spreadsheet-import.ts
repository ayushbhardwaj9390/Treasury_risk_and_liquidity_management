// Local, values-only import. The planner still validates every mapped cash-flow row.
export type WorkbookSheet = { name: string; headers: string[]; rows: Record<string, string>[] };
export const workbookLimits = { fileBytes: 2 * 1024 * 1024, expandedBytes: 10 * 1024 * 1024, entryBytes: 2 * 1024 * 1024, entries: 100, sheets: 10, rows: 500, columns: 30 };
const decoder = new TextDecoder("utf-8", { fatal: true });
const invalid = () => Error("This is not a readable .xlsx workbook. Save a fresh .xlsx file in Excel, or use CSV.");

function directory(bytes: Uint8Array) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let end = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (view.getUint32(i, true) === 0x06054b50 && i + 22 + view.getUint16(i + 20, true) === bytes.length) { end = i; break; }
  }
  if (end < 0 || view.getUint16(end + 4, true) || view.getUint16(end + 6, true)) throw invalid();
  const count = view.getUint16(end + 10, true), size = view.getUint32(end + 12, true), offset = view.getUint32(end + 16, true);
  if (!count || count > workbookLimits.entries || view.getUint16(end + 8, true) !== count || offset + size !== end) throw invalid();
  const files = new Map<string, number>();
  let cursor = offset, total = 0;
  for (let i = 0; i < count; i++) {
    if (cursor + 46 > end || view.getUint32(cursor, true) !== 0x02014b50) throw invalid();
    const flags = view.getUint16(cursor + 8, true), method = view.getUint16(cursor + 10, true), packed = view.getUint32(cursor + 20, true), unpacked = view.getUint32(cursor + 24, true);
    const nameLength = view.getUint16(cursor + 28, true), extra = view.getUint16(cursor + 30, true), comment = view.getUint16(cursor + 32, true), local = view.getUint32(cursor + 42, true);
    if (cursor + 46 + nameLength + extra + comment > end || local + 30 > offset || flags & 1 || ![0, 8].includes(method) || unpacked > workbookLimits.entryBytes || packed > bytes.length) throw invalid();
    const name = decoder.decode(bytes.subarray(cursor + 46, cursor + 46 + nameLength));
    if (!name || name.length > 240 || files.has(name) || name.startsWith("/") || name.includes("\\") || name.split("/").includes("..")) throw invalid();
    if (/vba|macrosheet|externallinks|\.bin$/i.test(name)) throw Error("Use a values-only .xlsx file without macros or links to other workbooks.");
    if (view.getUint32(local, true) !== 0x04034b50 || view.getUint16(local + 8, true) !== method || view.getUint16(local + 6, true) !== flags) throw invalid();
    const localNameLength = view.getUint16(local + 26, true), localExtra = view.getUint16(local + 28, true);
    if (local + 30 + localNameLength + localExtra + packed > offset || decoder.decode(bytes.subarray(local + 30, local + 30 + localNameLength)) !== name) throw invalid();
    total += unpacked;
    if (total > workbookLimits.expandedBytes) throw Error("This workbook expands to too much data. Use a smaller values-only workbook.");
    files.set(name, unpacked);
    cursor += 46 + nameLength + extra + comment;
  }
  if (cursor !== end || !files.has("xl/workbook.xml") || !files.has("[Content_Types].xml")) throw invalid();
  return files;
}

function checkAddress(address: string) {
  const match = /^([A-Z]{1,3})([1-9]\d{0,6})$/.exec(address);
  if (!match) throw invalid();
  let column = 0;
  for (const char of match[1]) column = column * 26 + char.charCodeAt(0) - 64;
  if (column > workbookLimits.columns || Number(match[2]) > workbookLimits.rows + 1) throw Error("Use at most 500 data rows and 30 columns per sheet. Remove unused rows and columns before saving.");
}

function checkSheetNames(names: string[]) {
  const seen = new Set<string>();
  for (const sheet of names) {
    const name = sheet.toLowerCase();
    if (!sheet.trim() || sheet.length > 31 || /[\\/\[\]:*?\x00-\x1f]/.test(sheet) || sheet.startsWith("'") || sheet.endsWith("'") || seen.has(name)) throw Error("Use unique Excel worksheet names of 1 to 31 characters, without / \\ [ ] : * ? or control characters.");
    seen.add(name);
  }
}

function xmlName(value: string) {
  return value.replace(/&([^;]*);/g, (_, entity: string) => {
    const named: Record<string, string> = {amp:"&",lt:"<",gt:">",quot:'"',apos:"'"};
    if (Object.prototype.hasOwnProperty.call(named, entity)) return named[entity];
    const point = /^#x[\da-f]+$/i.test(entity) ? parseInt(entity.slice(2), 16) : /^#\d+$/.test(entity) ? Number(entity.slice(1)) : NaN;
    if (!Number.isInteger(point) || point < 0 || point > 0x10ffff) throw invalid();
    return String.fromCodePoint(point);
  });
}

function checkXml(name: string, text: string) {
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw invalid();
  if (/macroEnabled|vbaProject/i.test(text) || /TargetMode\s*=\s*["']External["']/i.test(text)) throw Error("Use a values-only .xlsx file without macros or external links.");
  if (name === "xl/workbook.xml") {
    const names: string[] = [];
    for (const tag of text.matchAll(/<(?:[\w.-]+:)?sheet\b((?:[^>"']|"[^"]*"|'[^']*')*)>/g)) {
      const attributes = [...tag[1].matchAll(/(?:^|\s)name\s*=\s*(["'])(.*?)\1/g)];
      if (attributes.length !== 1) throw invalid();
      names.push(xmlName(attributes[0][2]));
    }
    if (names.length > workbookLimits.sheets) throw Error("Use a workbook with at most 10 sheets.");
    checkSheetNames(names);
  }
  if (!/^xl\/worksheets\/[^/]+\.xml$/.test(name)) return;
  // Reject all formulas: even a cached result may be stale. Never calculate or trust it.
  if (/<(?:[\w.-]+:)?f(?:\s|>|\/)/.test(text)) throw Error("This sheet contains formulas. In Excel, copy the table and Paste Special → Values into a new sheet, then save and try again.");
  if (/<(?:[\w.-]+:)?c\b[^>]*\bt\s*=\s*["']e["']/.test(text)) throw Error("This sheet contains an Excel error. Correct the cell or paste valid values before importing.");
  let cells = 0;
  for (const match of text.matchAll(/<(?:[\w.-]+:)?(?:c|row|dimension)\b((?:[^>"']|"[^"]*"|'[^']*')*)>/g)) {
    const tag = match[0];
    if (/^<(?:[\w.-]+:)?c\b/.test(tag) && ++cells > (workbookLimits.rows + 1) * workbookLimits.columns) throw Error("Use at most 500 data rows and 30 columns per sheet.");
    const attributes = [...match[1].matchAll(/(?:^|\s)(?:r|ref)\s*=\s*(["'])(.*?)\1/g)];
    if (attributes.length !== 1) throw invalid();
    const attribute = attributes[0];
    if (/^<(?:[\w.-]+:)?row\b/.test(tag)) {
      if (!/^[1-9]\d{0,6}$/.test(attribute[2])) throw invalid();
      if (Number(attribute[2]) > workbookLimits.rows + 1) throw Error("Use at most 500 data rows per sheet. Remove unused rows before saving.");
    } else for (const address of attribute[2].split(":")) checkAddress(address);
  }
}

async function preflight(bytes: Uint8Array) {
  const expected = directory(bytes);
  const { Unzip, UnzipInflate } = await import("fflate");
  const seen = new Set<string>();
  const completed = new Set<string>();
  let failure: Error | undefined;
  let total = 0, sheets = 0;
  const unzip = new Unzip(file => {
    if (!expected.has(file.name) || seen.has(file.name)) throw invalid();
    seen.add(file.name);
    if (/^xl\/worksheets\/[^/]+\.xml$/.test(file.name) && ++sheets > workbookLimits.sheets) throw Error("Use a workbook with at most 10 sheets.");
    const chunks: Uint8Array[] = [];
    let size = 0;
    file.ondata = (error, data, final) => {
      if (failure) throw failure;
      try {
        if (error) throw invalid();
        size += data.length; total += data.length;
        if (size > workbookLimits.entryBytes || total > workbookLimits.expandedBytes || size > expected.get(file.name)!) throw Error("This workbook expands to too much data. Use a smaller values-only workbook.");
        if (/\.(?:xml|rels)$/.test(file.name)) chunks.push(data);
        if (final) {
          if (size !== expected.get(file.name)) throw invalid();
          completed.add(file.name);
          if (chunks.length) {
            const content = new Uint8Array(size);
            let at = 0; for (const chunk of chunks) { content.set(chunk, at); at += chunk.length; }
            checkXml(file.name, decoder.decode(content));
          }
        }
      } catch (error) { failure = error as Error; throw failure; }
    };
    file.start();
  });
  unzip.register(UnzipInflate);
  // Small compressed chunks prevent a forged size from allocating a giant inflate output.
  for (let offset = 0; offset < bytes.length; offset += 256) unzip.push(bytes.subarray(offset, Math.min(offset + 256, bytes.length)), offset + 256 >= bytes.length);
  if (seen.size !== expected.size || completed.size !== expected.size || !sheets) throw invalid();
}

function plainNumber(value: string): string {
  const match = /^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match || value.length > 64 || Math.abs(Number(match[4] ?? 0)) > 32) throw Error("Use ordinary numbers with no currency symbols, errors or very large exponents.");
  const digits = match[2] + (match[3] ?? ""), point = match[2].length + Number(match[4] ?? 0);
  return match[1] + (point <= 0 ? "0." + "0".repeat(-point) + digits : point >= digits.length ? digits + "0".repeat(point - digits.length) : digits.slice(0, point) + "." + digits.slice(point));
}

export async function parseWorkbook(buffer: ArrayBuffer): Promise<WorkbookSheet[]> {
  if (buffer.byteLength > workbookLimits.fileBytes) throw Error("Choose an Excel workbook under 2 MB, with at most 500 data rows and 30 columns per sheet.");
  if (buffer.byteLength < 22) throw invalid();
  await preflight(new Uint8Array(buffer));
  const { default: readWorkbook } = await import("read-excel-file/browser");
  let sheets;
  try { sheets = await readWorkbook(buffer, { parseNumber: plainNumber }); }
  catch { throw invalid(); }
  if (!sheets.length || sheets.length > workbookLimits.sheets) throw Error("Use a workbook with 1 to 10 sheets.");
  checkSheetNames(sheets.map(({sheet}) => sheet));
  const result: WorkbookSheet[] = [];
  for (const sheet of sheets) {
    const data = sheet.data.map(row => row.map(value => value instanceof Date ? value.toISOString().slice(0, 10) : value == null ? "" : String(value).trim()));
    while (data.length && !data[data.length - 1].some(Boolean)) data.pop();
    if (!data.length) continue;
    const headers = data.shift()!;
    if (!headers.length || headers.some(header => !header) || new Set(headers).size !== headers.length) throw Error(`Sheet “${sheet.sheet}”: use unique, non-empty headings in the first row.`);
    if (headers.length > workbookLimits.columns || data.length > workbookLimits.rows) throw Error("Use at most 500 data rows and 30 columns per sheet.");
    if (data.some(row => row.length > headers.length && row.slice(headers.length).some(Boolean))) throw Error(`Sheet “${sheet.sheet}”: some values have no column heading.`);
    if (!data.length) continue;
    result.push({ name: sheet.sheet, headers, rows: data.map(row => Object.fromEntries(headers.map((header, i) => [header, row[i] ?? ""]))) });
  }
  if (!result.length) throw Error("No table found. Put column headings in row 1, followed by your cash movements.");
  return result;
}
