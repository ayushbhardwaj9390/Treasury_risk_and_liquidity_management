# Direct Excel import

Cash planning can read a local `.xlsx` workbook. The browser reads the workbook; this adapter does not upload it, call an AI service, save it to a server or alter authoritative treasury records.

Prepare one simple table per sheet: column headings in row 1, then cash movements. Choose the sheet, review the column suggestions and run the existing **Check data** step before using the rows in the simulator. Existing cash-flow validation still checks references, dates, amounts, currencies, directions and other mapped fields. Importing a workbook never bypasses those checks.

Limits: 2 MB compressed file; 10 MB expanded archive; 2 MB per ZIP entry; 100 archive entries; 10 sheets; 500 data rows and 30 columns per sheet. Oversized sheet coordinates are rejected before the reader can allocate a sparse table. Remove unused rows and columns if Excel has saved a much larger used range than the visible table.

Supported: ordinary `.xlsx`, multiple sheets, plain numeric amounts (including stored scientific notation, converted without floating-point rounding), inline/shared text and recognised Excel date formats. Dates become `YYYY-MM-DD`. The amount validator still requires at most two decimal places. Old `.xls`, password-protected/encrypted files, macro workbooks, external links and formula cells are rejected. Even cached formula results may be stale: copy the table, use **Paste Special → Values** in a new workbook, save as `.xlsx` and try again. No formulas or macros are executed.

Implementation contract: dynamically import `frontend/lib/spreadsheet-import.ts`, then call `await parseWorkbook(await file.arrayBuffer())`. It returns selectable `{name, headers, rows}` sheets; pass the selected rows to `validateRows` with the reviewed mapping. Blank sheets are skipped. Do not treat returned rows as validated engine inputs.

The adapter checks ZIP metadata and streams decompression in small chunks, enforcing actual output limits as well as declared sizes. It checks worksheet coordinates and XML content before calling the workbook reader. Dependencies are pinned: `read-excel-file` 9.3.10 and `fflate` 0.8.3. Browser imports are loaded on demand. Current `pnpm audit --prod` reports no known vulnerabilities; that is dependency evidence, not a security certification.

Primary implementation references: [read-excel-file documentation](https://github.com/catamphetamine/read-excel-file), [fflate streaming ZIP API](https://github.com/101arrowz/fflate). Seven regression tests cover multiple sheets, validated cash movements, native dates, formulas/errors, malformed and unsafe files, size/dimension limits and dishonest expanded-size metadata.

The application offers Download Excel example, a two-sheet fictional workbook. Sheet 1 has USD 1,000 incoming and USD 500 outgoing on 12–13 October 2026. Use USD 1,000 starting cash, USD 800 minimum, start 12 October and two weeks to check USD 1,500 ending cash. Sheet 2 has EUR amounts and requires a manual USD-per-EUR assumption.
