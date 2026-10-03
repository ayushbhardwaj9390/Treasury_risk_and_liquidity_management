from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import brier_score_loss, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    BankAccount,
    CollateralAgreement,
    DerivativePosition,
    DerivativeValuationTerms,
    LegalEntity,
    LegalNettingSet,
    MarketCurvePoint,
    ModelDeployment,
    NettingSetTrade,
    ResilienceControl,
    VolatilityQuote,
)
from app.schemas.treasury import (
    ChampionChallengerOut,
    CollateralOptimizationOut,
    CollateralOptimizationRow,
    InstitutionalValuationOut,
    InstitutionalValuationTradeOut,
    LiquidityAtRiskOut,
    NettingSetExposureOut,
    NettingSummaryOut,
    OperationalResilienceOut,
    ResilienceComponentOut,
    SecurityPostureOut,
)
from app.services.advanced_intelligence import FEATURES, _history_frame, _models, validate_payment_model
from app.services.fx import FXConversionError, convert, latest_rate
from app.services.global_treasury import calculate_collateral_liquidity
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _d(value: float | Decimal, places: int = 2) -> Decimal:
    return Decimal(str(round(float(value), places)))


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _interpolate(points: list[tuple[int, float]], target_days: int) -> float:
    if not points:
        raise ValueError("No market curve points available")
    points = sorted(points)
    if target_days <= points[0][0]:
        return points[0][1]
    if target_days >= points[-1][0]:
        return points[-1][1]
    for (d1, r1), (d2, r2) in zip(points, points[1:]):
        if d1 <= target_days <= d2:
            w = (target_days - d1) / max(d2 - d1, 1)
            return r1 + w * (r2 - r1)
    return points[-1][1]


def _curve_rate(db: Session, currency: str, target_days: int) -> tuple[float, datetime, str]:
    rows = db.scalars(
        select(MarketCurvePoint)
        .where(MarketCurvePoint.currency == currency, MarketCurvePoint.curve_type == "DISCOUNT")
        .order_by(MarketCurvePoint.tenor_days)
    ).all()
    if not rows:
        raise ValueError(f"Missing discount curve for {currency}")
    rate = _interpolate([(x.tenor_days, float(x.zero_rate)) for x in rows], target_days)
    newest = max(x.as_of for x in rows)
    source = rows[0].source if all(x.source == rows[0].source for x in rows) else "MIXED_CURVE_SOURCES"
    return rate, newest, source


def _volatility(db: Session, underlying: str, target_days: int) -> tuple[float, datetime, str]:
    rows = db.scalars(
        select(VolatilityQuote)
        .where(VolatilityQuote.underlying == underlying, VolatilityQuote.asset_class == "FX")
        .order_by(VolatilityQuote.tenor_days)
    ).all()
    if not rows:
        raise ValueError(f"Missing volatility surface for {underlying}")
    vol = _interpolate([(x.tenor_days, float(x.volatility)) for x in rows], target_days)
    newest = max(x.as_of for x in rows)
    source = rows[0].source if all(x.source == rows[0].source for x in rows) else "MIXED_VOL_SOURCES"
    return vol, newest, source


def _pair(pair: str) -> tuple[str, str]:
    parts = pair.upper().split("/")
    if len(parts) != 2 or any(len(p) != 3 for p in parts):
        raise ValueError(f"Invalid currency pair {pair}")
    return parts[0], parts[1]


def _price_fx_forward(db: Session, trade: DerivativePosition, terms: DerivativeValuationTerms) -> tuple[Decimal, datetime, str]:
    if not terms.currency_pair or terms.contracted_rate is None:
        raise ValueError("FX forward missing currency pair or contracted rate")
    base, quote = _pair(terms.currency_pair)
    days = max((trade.maturity_date - date.today()).days, 1)
    t = days / 365.0
    spot = float(latest_rate(db, base, quote))
    r_base, as_of_base, src_base = _curve_rate(db, base, days)
    r_quote, as_of_quote, src_quote = _curve_rate(db, quote, days)
    forward = spot * math.exp((r_quote - r_base) * t)
    discount_quote = math.exp(-r_quote * t)
    k = float(terms.contracted_rate)
    signed_quote = float(trade.notional) * ((k - forward) if trade.hedge_direction == "SELL" else (forward - k)) * discount_quote
    value_reporting = convert(db, Decimal(str(signed_quote)), quote, settings.group_reporting_currency)
    return value_reporting, min(as_of_base, as_of_quote), f"{src_base}+{src_quote}"


def _price_fx_option(db: Session, trade: DerivativePosition, terms: DerivativeValuationTerms) -> tuple[Decimal, datetime, str]:
    if not terms.currency_pair or terms.strike is None or not terms.option_type:
        raise ValueError("FX option missing pair, strike or option type")
    base, quote = _pair(terms.currency_pair)
    days = max((trade.maturity_date - date.today()).days, 1)
    t = max(days / 365.0, 1 / 365.0)
    spot = float(latest_rate(db, base, quote))
    strike = float(terms.strike)
    rd, as_of_q, src_q = _curve_rate(db, quote, days)
    rf, as_of_b, src_b = _curve_rate(db, base, days)
    vol, as_of_v, src_v = _volatility(db, terms.currency_pair, days)
    sigma_sqrt = max(vol * math.sqrt(t), 1e-9)
    d1 = (math.log(max(spot, 1e-12) / max(strike, 1e-12)) + (rd - rf + 0.5 * vol * vol) * t) / sigma_sqrt
    d2 = d1 - sigma_sqrt
    call = spot * math.exp(-rf * t) * _norm_cdf(d1) - strike * math.exp(-rd * t) * _norm_cdf(d2)
    put = strike * math.exp(-rd * t) * _norm_cdf(-d2) - spot * math.exp(-rf * t) * _norm_cdf(-d1)
    unit = call if terms.option_type.upper() == "CALL" else put
    quote_value = float(trade.notional) * max(unit, 0.0)
    reporting = convert(db, Decimal(str(quote_value)), quote, settings.group_reporting_currency)
    return reporting, min(as_of_q, as_of_b, as_of_v), f"{src_q}+{src_b}+{src_v}"


def _price_irs(db: Session, trade: DerivativePosition, terms: DerivativeValuationTerms) -> tuple[Decimal, datetime, str]:
    if terms.fixed_rate is None:
        raise ValueError("IRS missing fixed rate")
    ccy = terms.notional_currency or trade.exposure_currency
    days = max((trade.maturity_date - date.today()).days, 1)
    years = days / 365.0
    par_rate, as_of, source = _curve_rate(db, ccy, days)
    freq = max(int(terms.payment_frequency_per_year), 1)
    n = max(1, int(math.ceil(years * freq)))
    annuity = sum(math.exp(-par_rate * min(i / freq, years)) / freq for i in range(1, n + 1))
    fixed = float(terms.fixed_rate)
    sign = 1.0 if trade.hedge_direction == "PAY_FIXED" else -1.0
    value_local = sign * float(trade.notional) * (par_rate - fixed) * annuity
    reporting = convert(db, Decimal(str(value_local)), ccy, settings.group_reporting_currency)
    return reporting, as_of, source


def calculate_institutional_valuation(db: Session) -> InstitutionalValuationOut:
    trades = db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN").order_by(DerivativePosition.id)).all()
    terms_by_trade = {
        x.derivative_position_id: x
        for x in db.scalars(select(DerivativeValuationTerms)).all()
    }
    rows: list[InstitutionalValuationTradeOut] = []
    warnings: list[str] = []
    total_model = ZERO
    total_book = ZERO
    unpriced = 0

    for trade in trades:
        terms = terms_by_trade.get(trade.id)
        if terms is None:
            unpriced += 1
            warnings.append(f"Trade {trade.id} has no approved valuation terms.")
            continue
        try:
            if terms.model_type == "FX_FORWARD":
                model_value, as_of, source = _price_fx_forward(db, trade, terms)
            elif terms.model_type == "GARMAN_KOHLHAGEN":
                model_value, as_of, source = _price_fx_option(db, trade, terms)
            elif terms.model_type == "IRS_PAR_RATE":
                model_value, as_of, source = _price_irs(db, trade, terms)
            else:
                raise ValueError(f"Unsupported model {terms.model_type}")
        except (ValueError, FXConversionError) as exc:
            unpriced += 1
            warnings.append(f"Trade {trade.id}: {exc}")
            continue

        book = Decimal(trade.market_value_reporting_ccy)
        diff = model_value - book
        age_min = max(int((_now() - as_of).total_seconds() / 60), 0)
        source_quality = "PRIMARY_FRESH" if age_min <= 60 and "SYNTHETIC_PRIMARY" in source else "REVIEW_SOURCE"
        abs_diff = abs(diff)
        tolerance = max(Decimal("100000"), abs(model_value) * Decimal("0.15"))
        status = "PASS" if abs_diff <= tolerance else "REVIEW"
        total_model += model_value
        total_book += book
        rows.append(InstitutionalValuationTradeOut(
            derivative_position_id=trade.id,
            instrument_type=trade.instrument_type,
            counterparty=trade.counterparty,
            model_type=terms.model_type,
            model_value_reporting=_d(model_value),
            book_value_reporting=_d(book),
            valuation_difference=_d(diff),
            source_quality=source_quality,
            model_status=status,
            inputs_as_of=as_of,
        ))
    return InstitutionalValuationOut(
        reporting_currency=settings.group_reporting_currency,
        total_model_value=_d(total_model),
        total_book_value=_d(total_book),
        aggregate_difference=_d(total_model - total_book),
        priced_trade_count=len(rows),
        unpriced_trade_count=unpriced,
        rows=rows,
        warnings=warnings,
    )


def calculate_liquidity_at_risk(
    db: Session,
    horizon_weeks: int = 13,
    confidence: Decimal = Decimal("0.95"),
    simulations: int = 4000,
    seed: int = 42,
) -> LiquidityAtRiskOut:
    if not 1 <= horizon_weeks <= 52:
        raise ValueError("horizon_weeks must be between 1 and 52")
    if not Decimal("0.90") <= confidence < Decimal("1"):
        raise ValueError("confidence must be between 0.90 and 1.00")
    if not 500 <= simulations <= 20000:
        raise ValueError("simulations must be between 500 and 20000")

    from app.models import CashFlow

    horizon = date.today() + timedelta(days=horizon_weeks * 7)
    flows = db.scalars(select(CashFlow).where(CashFlow.status == "OPEN", CashFlow.due_date <= horizon)).all()
    receivables = 0.0
    payables = 0.0
    warnings: list[str] = []
    for f in flows:
        try:
            amount = float(convert(db, Decimal(f.amount), f.currency, settings.group_reporting_currency))
        except FXConversionError as exc:
            warnings.append(str(exc))
            continue
        if f.flow_type == "RECEIVABLE":
            receivables += amount * float(f.probability)
        elif f.flow_type == "PAYABLE":
            payables += amount

    liquidity = calculate_global_liquidity(db)
    collateral = calculate_collateral_liquidity(db)
    opening_cash = float(liquidity.deployable_cash)
    minimum = float(liquidity.minimum_cash)
    facilities = float(liquidity.undrawn_credit)
    current_margin = float(collateral.current_margin_call)
    stressed_margin = float(collateral.stressed_margin_call)

    rng = np.random.default_rng(seed)
    # Mixture distribution: normal trading conditions plus a low-frequency combined treasury shock.
    shock = rng.random(simulations) < 0.12
    collection_factor = np.clip(rng.normal(0.94, 0.08, simulations), 0.55, 1.05)
    collection_factor[shock] *= np.clip(rng.normal(0.70, 0.08, int(shock.sum())), 0.45, 0.90)
    payable_factor = np.clip(rng.lognormal(mean=0.0, sigma=0.07, size=simulations), 0.90, 1.35)
    payable_factor[shock] *= np.clip(rng.normal(1.16, 0.06, int(shock.sum())), 1.05, 1.35)
    facility_factor = np.clip(rng.beta(9, 2, simulations), 0.25, 1.00)
    facility_factor[shock] *= np.clip(rng.normal(0.55, 0.10, int(shock.sum())), 0.20, 0.80)
    margin_factor = np.clip(rng.lognormal(mean=0.0, sigma=0.40, size=simulations), 0.5, 3.0)
    collateral_call = current_margin + (stressed_margin - current_margin) * np.minimum(margin_factor / 2.0, 1.5)

    ending_headroom = (
        opening_cash
        + receivables * collection_factor
        - payables * payable_factor
        + facilities * facility_factor
        - minimum
        - collateral_call
    )
    funding_need = np.maximum(-ending_headroom, 0.0)
    expected = float(np.mean(ending_headroom))
    p05 = float(np.quantile(ending_headroom, 1 - float(confidence)))
    p01 = float(np.quantile(ending_headroom, 0.01))
    cfar = max(expected - p05, 0.0)
    lar = float(np.quantile(funding_need, float(confidence)))
    prob_breach = float(np.mean(ending_headroom < 0))
    expected_need = float(np.mean(funding_need))
    tail_need = float(np.quantile(funding_need, 0.99))

    if prob_breach > 0.05:
        warnings.append("Simulated liquidity-buffer breach probability exceeds 5%; contingency funding should be reviewed.")
    warnings.append("LaR/CFaR is a modelled distribution, not a guaranteed maximum loss or funding requirement.")

    return LiquidityAtRiskOut(
        reporting_currency=settings.group_reporting_currency,
        horizon_weeks=horizon_weeks,
        confidence=confidence,
        simulations=simulations,
        expected_ending_headroom=_d(expected),
        p05_ending_headroom=_d(p05),
        p01_ending_headroom=_d(p01),
        cash_flow_at_risk=_d(cfar),
        liquidity_at_risk=_d(lar),
        probability_of_buffer_breach=Decimal(str(round(prob_breach, 6))),
        expected_funding_need=_d(expected_need),
        tail_funding_need=_d(tail_need),
        seed=seed,
        methodology="Monte Carlo operating cash, facility availability and collateral-liquidity mixture model",
        warnings=warnings,
    )


def calculate_legal_netting(db: Session) -> NettingSummaryOut:
    valuation = calculate_institutional_valuation(db)
    model_values = {x.derivative_position_id: Decimal(x.model_value_reporting) for x in valuation.rows}
    book_trades = {x.id: x for x in db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all()}
    agreements = {x.id: x for x in db.scalars(select(CollateralAgreement)).all()}
    links = db.scalars(select(NettingSetTrade)).all()
    by_set: dict[int, list[int]] = {}
    for link in links:
        by_set.setdefault(link.netting_set_id, []).append(link.derivative_position_id)

    rows: list[NettingSetExposureOut] = []
    warnings: list[str] = []
    gross_total = ZERO
    net_total = ZERO
    benefit_total = ZERO
    enforceable_count = 0
    review_count = 0

    for ns in db.scalars(select(LegalNettingSet).order_by(LegalNettingSet.netting_set_code)).all():
        trade_ids = by_set.get(ns.id, [])
        mtms = [model_values.get(tid, Decimal(book_trades[tid].market_value_reporting_ccy)) for tid in trade_ids if tid in book_trades]
        gross_pos = sum((max(x, ZERO) for x in mtms), ZERO)
        gross_neg = sum((min(x, ZERO) for x in mtms), ZERO)
        raw_net = sum(mtms, ZERO)
        enforceable = ns.close_out_netting_enforceable and ns.legal_opinion_status == "APPROVED"
        credit_before_collateral = max(raw_net, ZERO) if enforceable else gross_pos
        benefit = gross_pos - credit_before_collateral
        agreement = agreements.get(ns.collateral_agreement_id) if ns.collateral_agreement_id else None
        posted = Decimal(agreement.collateral_posted_reporting_ccy) if agreement else ZERO
        received = Decimal(agreement.collateral_received_reporting_ccy) if agreement else ZERO
        exposure_after = max(credit_before_collateral - received, ZERO)
        status = "LEGAL_OK" if enforceable else "REVIEW_REQUIRED"
        if enforceable:
            enforceable_count += 1
        else:
            review_count += 1
            warnings.append(f"{ns.netting_set_code}: close-out netting benefit is not recognized until legal enforceability is approved.")
        gross_total += gross_pos
        net_total += exposure_after
        benefit_total += benefit
        rows.append(NettingSetExposureOut(
            netting_set_code=ns.netting_set_code,
            counterparty=ns.counterparty,
            close_out_netting_enforceable=ns.close_out_netting_enforceable,
            legal_opinion_status=ns.legal_opinion_status,
            gross_positive_mtm=_d(gross_pos),
            gross_negative_mtm=_d(gross_neg),
            net_mtm=_d(raw_net),
            netting_benefit=_d(benefit),
            collateral_posted=_d(posted),
            collateral_received=_d(received),
            exposure_after_netting_and_collateral=_d(exposure_after),
            trade_count=len(mtms),
            status=status,
        ))

    return NettingSummaryOut(
        reporting_currency=settings.group_reporting_currency,
        gross_credit_exposure=_d(gross_total),
        net_credit_exposure=_d(net_total),
        total_netting_benefit=_d(benefit_total),
        legally_enforceable_sets=enforceable_count,
        review_required_sets=review_count,
        rows=rows,
        warnings=warnings,
    )


def optimize_collateral_liquidity(db: Session) -> CollateralOptimizationOut:
    valuation = calculate_institutional_valuation(db)
    model_values = {x.derivative_position_id: Decimal(x.model_value_reporting) for x in valuation.rows}
    trades = {x.id: x for x in db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all()}
    agreements = {x.id: x for x in db.scalars(select(CollateralAgreement)).all()}
    links = db.scalars(select(NettingSetTrade)).all()
    by_set: dict[int, list[int]] = {}
    for x in links:
        by_set.setdefault(x.netting_set_id, []).append(x.derivative_position_id)

    entities = {x.id: x for x in db.scalars(select(LegalEntity)).all()}
    accounts = db.scalars(select(BankAccount)).all()
    available_by_ccy_entity: dict[tuple[str, int], Decimal] = {}
    for account in accounts:
        available = max(Decimal(account.book_balance) - Decimal(account.restricted_balance) - Decimal(account.committed_outflows), ZERO)
        available_by_ccy_entity[(account.currency, account.entity_id)] = available_by_ccy_entity.get((account.currency, account.entity_id), ZERO) + available

    rows: list[CollateralOptimizationRow] = []
    warnings: list[str] = []
    total_required = ZERO
    total_cross = ZERO
    for ns in db.scalars(select(LegalNettingSet).order_by(LegalNettingSet.netting_set_code)).all():
        if not ns.collateral_agreement_id or ns.collateral_agreement_id not in agreements:
            continue
        agreement = agreements[ns.collateral_agreement_id]
        mtms = [model_values.get(tid, Decimal(trades[tid].market_value_reporting_ccy)) for tid in by_set.get(ns.id, []) if tid in trades]
        if not mtms:
            continue
        net_mtm = sum(mtms, ZERO) if ns.close_out_netting_enforceable and ns.legal_opinion_status == "APPROVED" else min(sum(mtms, ZERO), ZERO)
        liability = max(-net_mtm, ZERO)
        threshold = Decimal(agreement.threshold_reporting_ccy)
        posted = Decimal(agreement.collateral_posted_reporting_ccy)
        independent = Decimal(agreement.independent_amount_reporting_ccy)
        required = max(liability + independent - threshold - posted, ZERO)
        if required <= 0:
            continue
        ccy = agreement.eligible_collateral_currency
        candidates: list[tuple[Decimal, int]] = []
        for (acc_ccy, entity_id), amount_local in available_by_ccy_entity.items():
            if acc_ccy != ccy:
                continue
            try:
                reporting = convert(db, amount_local, ccy, settings.group_reporting_currency)
            except FXConversionError:
                reporting = ZERO
            candidates.append((reporting, entity_id))
        candidates.sort(reverse=True, key=lambda x: x[0])
        same_ccy_reporting = sum((x[0] for x in candidates), ZERO)
        cross = max(required - same_ccy_reporting, ZERO)
        source_entity = entities[candidates[0][1]].name if candidates and candidates[0][1] in entities else None
        total_required += required
        total_cross += cross
        status = "SAME_CURRENCY_CAPACITY" if cross == 0 else "CROSS_CURRENCY_FUNDING_REQUIRED"
        if cross > 0:
            warnings.append(f"{ns.counterparty}: collateral call exceeds immediately identified same-currency cash capacity.")
        rows.append(CollateralOptimizationRow(
            counterparty=ns.counterparty,
            netting_set_code=ns.netting_set_code,
            eligible_currency=ccy,
            additional_collateral_required=_d(required),
            same_currency_available=_d(same_ccy_reporting),
            cross_currency_funding_required=_d(cross),
            recommended_source_entity=source_entity,
            status=status,
        ))
    return CollateralOptimizationOut(
        reporting_currency=settings.group_reporting_currency,
        total_additional_collateral_required=_d(total_required),
        total_cross_currency_funding_required=_d(total_cross),
        rows=rows,
        warnings=warnings,
    )


def champion_challenger_analysis(db: Session) -> ChampionChallengerOut:
    champion = validate_payment_model(db, persist=True)
    df = _history_frame(db)
    if len(df) < 20:
        return ChampionChallengerOut(
            model_code="PAYMENT_BEHAVIOUR",
            champion_version=champion.version,
            challenger_version="GB_1.0.0",
            champion_mae=champion.mae_delay_days,
            challenger_mae=champion.mae_delay_days,
            champion_brier=champion.brier_score,
            challenger_brier=champion.brier_score,
            mae_improvement_pct=ZERO,
            brier_improvement_pct=ZERO,
            promotion_threshold_pct=Decimal("0.05"),
            recommendation="INSUFFICIENT_DATA",
            auto_promotion_allowed=False,
            governance_note="No model promotion can occur without independent validation and approval.",
        )
    split = max(12, int(len(df) * 0.78))
    split = min(split, len(df) - 8)
    train, test = df.iloc[:split].copy(), df.iloc[split:].copy()
    cat = ["counterparty", "country_code", "currency"]
    num = ["amount_reporting", "terms_days", "invoice_month"]
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
        ("num", "passthrough", num),
    ])
    clf = Pipeline([("prep", prep), ("model", GradientBoostingClassifier(random_state=7, n_estimators=80, max_depth=2))])
    reg = Pipeline([("prep", prep), ("model", GradientBoostingRegressor(random_state=7, n_estimators=100, max_depth=2, loss="huber"))])
    clf.fit(train[FEATURES], train["late"])
    reg.fit(train[FEATURES], train["delay_days"])
    challenger_prob = clf.predict_proba(test[FEATURES])[:, 1]
    challenger_delay = reg.predict(test[FEATURES])
    ch_mae = float(mean_absolute_error(test["delay_days"], challenger_delay))
    ch_brier = float(brier_score_loss(test["late"], challenger_prob))
    champ_mae = float(champion.mae_delay_days)
    champ_brier = float(champion.brier_score)
    mae_improvement = (champ_mae - ch_mae) / champ_mae if champ_mae > 0 else 0.0
    brier_improvement = (champ_brier - ch_brier) / champ_brier if champ_brier > 0 else 0.0
    deployment = db.scalar(select(ModelDeployment).where(ModelDeployment.model_code == "PAYMENT_BEHAVIOUR_RF", ModelDeployment.deployment_role == "CHALLENGER"))
    threshold = Decimal(deployment.promotion_threshold_pct) if deployment else Decimal("0.05")
    qualifies = mae_improvement >= float(threshold) and brier_improvement >= float(threshold)
    recommendation = "INDEPENDENT_VALIDATION_FOR_PROMOTION" if qualifies else "KEEP_CHAMPION"
    return ChampionChallengerOut(
        model_code="PAYMENT_BEHAVIOUR",
        champion_version=champion.version,
        challenger_version="GB_1.0.0",
        champion_mae=_d(champ_mae, 4),
        challenger_mae=_d(ch_mae, 4),
        champion_brier=_d(champ_brier, 6),
        challenger_brier=_d(ch_brier, 6),
        mae_improvement_pct=Decimal(str(round(mae_improvement, 6))),
        brier_improvement_pct=Decimal(str(round(brier_improvement, 6))),
        promotion_threshold_pct=threshold,
        recommendation=recommendation,
        auto_promotion_allowed=False,
        governance_note="Champion/challenger comparison is advisory; production promotion requires independent model-risk approval.",
    )


def operational_resilience_status(db: Session) -> OperationalResilienceOut:
    now = _now()
    rows: list[ResilienceComponentOut] = []
    warnings: list[str] = []
    tier1_count = 0
    tier1_gaps = 0
    for x in db.scalars(select(ResilienceControl).order_by(ResilienceControl.criticality_tier, ResilienceControl.component_name)).all():
        stale_test = x.last_dr_test_at is None or (now - x.last_dr_test_at).days > 180
        gap = x.last_dr_test_result != "PASS" or stale_test or (x.criticality_tier == "TIER_1" and not x.multi_region)
        status = "GAP" if gap else "READY"
        if x.criticality_tier == "TIER_1":
            tier1_count += 1
            if gap:
                tier1_gaps += 1
        if gap:
            warnings.append(f"{x.component_name}: resilience control requires remediation or retest.")
        rows.append(ResilienceComponentOut(
            component_name=x.component_name,
            criticality_tier=x.criticality_tier,
            rto_minutes=x.rto_minutes,
            rpo_minutes=x.rpo_minutes,
            multi_region=x.multi_region,
            last_dr_test_at=x.last_dr_test_at,
            last_dr_test_result=x.last_dr_test_result,
            status=status,
        ))
    overall = "GAP" if tier1_gaps else "READY"
    return OperationalResilienceOut(
        overall_status=overall,
        tier1_count=tier1_count,
        tier1_gaps=tier1_gaps,
        components=rows,
        warnings=warnings,
    )


def security_posture() -> SecurityPostureOut:
    prod = settings.environment.lower() == "production"
    oidc_ready = settings.auth_mode == "oidc_jwt" and bool(settings.oidc_issuer and settings.oidc_audience)
    database_backend = "POSTGRESQL" if settings.database_url.startswith(("postgresql", "postgres")) else "SQLITE_DEMO"
    warnings: list[str] = []
    if prod and not oidc_ready:
        warnings.append("Production identity is not configured for verified OIDC/JWT claims.")
    if prod and database_backend != "POSTGRESQL":
        warnings.append("Production deployment should use PostgreSQL or an approved enterprise database service.")
    if not prod:
        warnings.append("Development mode permits the demo identity adapter; it is blocked by design in production.")
    status = "READY" if (not prod or (oidc_ready and database_backend == "POSTGRESQL")) else "GAP"
    return SecurityPostureOut(
        environment=settings.environment,
        auth_mode=settings.auth_mode,
        production_identity_ready=oidc_ready,
        demo_identity_blocked_in_production=True,
        database_backend=database_backend,
        tls_expected=prod,
        secrets_in_environment_only=True,
        write_idempotency_required_in_production=True,
        security_headers_enabled=True,
        status=status,
        warnings=warnings,
    )
