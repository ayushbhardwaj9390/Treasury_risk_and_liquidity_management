# Weekly money-plan review

`ForecastReview` accepts `points: {week:number,date:string,closing:string}[]` and `source:string`. Mount it beside completed cash-plan results. The date identifies the first day of the seven-day week, matching the planner's existing convention; actual and planned balances both refer to the close of that week. All amounts are USD. Changing any point or the source clears the observations before the new plan renders.

Users enter actual weekly closing money manually. Blank is unknown, not zero. Invalid amounts are shown and excluded. The comparison matches exact dates; duplicate dates/weeks and invalid plan inputs are rejected. Up to 52 weeks and absolute amounts up to one trillion USD are supported. Arithmetic uses integer cents with symmetric half-up rounding.

The review shows mean absolute error, signed mean actual-minus-plan difference, and optionally weighted absolute percentage error (sum of absolute errors / sum of absolute actual balances). The percentage is unavailable when the denominator is zero, can exceed 100%, and is not advertised as an overall accuracy score. Negative balances are valid.

Manual observations are unverified browser-session inputs. They do not persist, train models, change forecasts or authoritative records, approve hedges, or execute transactions. Use fictional data in the public demonstration. Approved actual-bank evidence, reconciled period alignment and independent validation remain necessary before making production performance claims.

Validation: `frontend/tests/forecast-review.test.cjs` covers signed balances, missing/zero values, cent rounding, misleading percentage boundaries, invalid amounts, unmatched periods and duplicate/invalid periods.
