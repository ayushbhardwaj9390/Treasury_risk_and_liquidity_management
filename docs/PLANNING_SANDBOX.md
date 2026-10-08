# Private upload and what-if planning workspace

Open **Upload & what if** in the application. This workspace works without a hosted backend or external credentials.

Excel users can copy a table including headings and paste it into **Excel table**
under Choose data → **Paste from Excel**, then choose **Check copied Excel table**. Excel's tab-separated
clipboard values use the same mapping, validation and calculation workflow as files.
Format dates as YYYY-MM-DD and amounts without currency symbols or separators
before copying. Formula text is not evaluated. Native XLSX upload is still unsupported.
Choose **Try sample data** for the guided fictional example, or **Upload CSV / TSV**
for a file. Common headings such as Reference, Due Date, Transaction Amount and
Currency Code are suggested automatically. Review every mapping; ambiguous headings
remain unassigned and require a choice.

The starting inputs now say First day of your plan, How many weeks?, Money you start
with (USD), and Minimum money to keep (USD). Results distinguish money left without
changes from money left after your changes. Biggest gap below your minimum measures
the chosen minimum target, not unpaid bills. Amount above or below minimum at the
end applies to the final week; earlier gaps remain visible in the weekly table.
Use Show a simple example or Rodger → Explain in everyday words for context.

## Use it

1. Download the fictional CSV example, or export a bank/Excel cash-flow sheet as UTF-8 CSV or TSV.
2. Select the file, choose its separator and map reference, due date and amount columns. Other columns are optional.
3. Check data, inspect errors and preview records, then choose **Use checked data in simulator**. Invalid records block application of the entire dataset.
4. Enter your opening USD-equivalent cash, minimum buffer, forecast start/horizon and manual USD exchange rates. Applying an uploaded dataset clears the fictional cash, buffer and rate assumptions.
5. Adjust receipt delays, receipts, payments, oil-linked amounts or foreign-currency values and calculate a base/scenario comparison. Export the comparison as CSV.

## File contract

Required: unique reference, valid YYYY-MM-DD due date and nonzero amount with at most two decimals. Up to 500 records, 30 columns and 512 KB. Plain numbers only; no currency symbols or thousands separators. Native XLSX files and PDF statements are unsupported.

Optional columns: direction (INFLOW/OUTFLOW or CREDIT/DEBIT), currency, entity, category and receipt probability. Defaults are direction inferred from the signed amount, USD, GROUP, OTHER and probability 1. Payments cannot be probability discounted. Categories are CRUDE_PURCHASE, PRODUCT_SALE, FREIGHT, OPERATING and OTHER. Crude purchases must be payments and product sales must be receipts. Unsupported currencies, duplicate references, malformed CSV, impossible dates and inconsistent amounts are rejected.

## Calculation boundaries

The local calculator uses deterministic fixed-point arithmetic and weekly closing cash. It assumes no credit facilities and does not model restricted cash, entity-specific funding, intraday positions, inventory valuations or hedges. Receipt delays range from 0 to 90 days. Percentage changes range from -100% to +200% in 0.1% steps; applicable changes multiply. Oil changes apply to crude purchases and product sales only. FX changes affect future non-USD flows; opening USD cash stays fixed. Overdue and post-horizon flows are counted and their excluded expected amounts are shown.

Files and assumptions remain in client memory, with no file-data requests or local-storage persistence. Navigating workspaces preserves the session; reloading clears it. Uploaded data never changes authoritative balances, approved forecasts, release evidence, source authority or payments. This is a planning sandbox, not a bank connector or certified production forecast. The existing Python engines, five-agent architecture, authentication and human approval controls are unchanged.

## Verification — 6 October 2026

Seven generated golden cases compare the browser calculator against the unchanged Python forecast engine using isolated synthetic databases: base, receipt delay, oil change, FX change, combined changes, reduced receipts and receipts outside the horizon. CI regenerates fixtures and fails if committed expectations differ. Frontend checks also cover parsing, validation, precision, missing rates, invalid assumptions and decimal percentage steps.

Local browser checks observed the sample base ending cash of USD 34.2 million and a ten-day receipt-delay shortfall of USD 2.8 million in week 2. A duplicate-reference CSV displayed its error and disabled application to the simulator. Further interactive upload checking was interrupted, then the browser security policy blocked reconnection to the local preview; no workaround was used. Automated parsing and calculation checks remain available independently. No real company file or external certification was used.

Measured checks: 35 frontend tests passed; seven engine fixtures regenerated successfully; Python parity-script compilation passed; optimized Next.js production build and TypeScript checks passed. No schema changes or treasury-engine changes were introduced, so this addition requires no new migration. Existing CI continues to run backend regressions, clean migrations and dependency audits.

## Published verification

Implementation commit `982e761` was pushed to `main` and deployed successfully to https://treasuryriskandliquiditymanagement.vercel.app/. GitHub workflow [37443484183](https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37443484183) completed successfully, including backend regressions, migration upgrade/check, fixture regeneration, dependency audits, frontend tests, type checks and build.

The public browser test successfully loaded the two-row synthetic `verification/planning-valid.csv`, validated and previewed it, then applied it with opening cash, buffer and FX cleared. Entering USD 1,000 opening cash, USD 800 buffer, two weeks and a ten-day receipt delay produced ending cash USD 1,500 and a week-1 shortfall of USD 300. Adding a 10% payment increase produced ending cash USD 1,450 and shortfall USD 350. Input changes disabled stale-result downloads. The downloaded comparison CSV contained the same two weekly results. No browser console errors were reported. This completed the valid-upload test that was interrupted locally.

Responsive CSS includes single-column forms and mappings below 760 px and scrolling tables/navigation. The browser viewport override did not change the measured viewport (still 1,280 px); this feature's phone/tablet layout was not independently verified on real devices. No mobile compatibility certification is claimed.
